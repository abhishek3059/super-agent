from __future__ import annotations

import asyncio
import hmac
import json
from collections.abc import Callable

from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from .adapter import FakeVoiceAdapter, VoiceAdapter
from .config import VoiceConfig

AdapterFactory = Callable[[], VoiceAdapter]


def create_app(
    config: VoiceConfig | None = None,
    adapter_factory: AdapterFactory = FakeVoiceAdapter,
) -> FastAPI:
    settings = config or VoiceConfig.from_environment()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "provider": "fake"}

    @app.websocket("/ws/voice")
    async def voice_socket(websocket: WebSocket) -> None:
        await _voice_socket(websocket, settings, adapter_factory)

    return app


async def _safe_error(websocket: WebSocket, category: str) -> None:
    try:
        await websocket.send_json({"type": "session.error", "category": category})
    except (RuntimeError, WebSocketDisconnect):
        pass


async def _voice_socket(
    websocket: WebSocket,
    settings: VoiceConfig,
    adapter_factory: AdapterFactory,
) -> None:
    if websocket.headers.get("host") != settings.allowed_host:
        await websocket.close(code=1008)
        return
    if websocket.headers.get("origin") != settings.allowed_origin:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    adapter = adapter_factory()
    muted = False
    playback_epoch = 0
    try:
        auth = await asyncio.wait_for(websocket.receive_text(), timeout=5)
        if len(auth.encode("utf-8")) > settings.max_control_bytes:
            await websocket.close(code=1009)
            return
        message = json.loads(auth)
        supplied = (
            message.get("token", "")
            if message.get("type") == "session.auth"
            else ""
        )
        if not isinstance(supplied, str) or not hmac.compare_digest(
            supplied, settings.local_token
        ):
            await websocket.close(code=1008)
            return
        await websocket.send_json(
            {"type": "session.ready", "playbackEpoch": playback_epoch}
        )

        while True:
            incoming = await asyncio.wait_for(websocket.receive(), timeout=60)
            if incoming["type"] == "websocket.disconnect":
                break
            if incoming.get("bytes") is not None:
                audio = incoming["bytes"]
                if len(audio) > settings.max_audio_frame_bytes:
                    await websocket.close(code=1009)
                    return
                if muted:
                    continue
                reply = await adapter.send_audio(audio)
                await websocket.send_json(
                    {"type": "audio.chunk", "playbackEpoch": playback_epoch}
                )
                await websocket.send_bytes(reply.audio)
                if reply.turn_complete:
                    await websocket.send_json(
                        {"type": "turn.complete", "playbackEpoch": playback_epoch}
                    )
                continue
            event = await _handle_control(
                websocket, incoming.get("text"), adapter, settings, muted, playback_epoch
            )
            if event == "capture.mute":
                muted = True
            elif event == "capture.unmute":
                muted = False
            elif event == "playback.interrupt":
                playback_epoch += 1
            elif event == "session.stop":
                break
    except (asyncio.TimeoutError, TimeoutError):
        await _safe_error(websocket, "session-timeout")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        await _safe_error(websocket, "invalid-control")
    except WebSocketDisconnect:
        pass
    except Exception:
        await _safe_error(websocket, "session-failed")
    finally:
        await adapter.close()
        try:
            await websocket.close(code=1000)
        except RuntimeError:
            pass


async def _handle_control(
    websocket: WebSocket,
    text: str | None,
    adapter: VoiceAdapter,
    settings: VoiceConfig,
    muted: bool,
    playback_epoch: int,
) -> str:
    if text is None or len(text.encode("utf-8")) > settings.max_control_bytes:
        raise ValueError("invalid control frame")
    message = json.loads(text)
    if not isinstance(message, dict):
        raise ValueError("control frame must be an object")
    event = message.get("type")
    if event == "capture.mute":
        await websocket.send_json({"type": "session.state", "muted": True})
    elif event == "capture.unmute":
        await websocket.send_json({"type": "session.state", "muted": False})
    elif event == "playback.interrupt":
        await adapter.interrupt()
        await websocket.send_json(
            {"type": "playback.interrupted", "playbackEpoch": playback_epoch + 1}
        )
    elif event == "session.stop":
        await websocket.send_json({"type": "session.state", "state": "stopping"})
    else:
        raise ValueError("unknown control event")
    return event
