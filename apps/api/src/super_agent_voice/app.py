from __future__ import annotations

import asyncio
import hmac
import json
import threading
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request, WebSocket
from starlette.websockets import WebSocketDisconnect

from .adapter import FakeVoiceAdapter, VoiceAdapter
from .config import VoiceConfig

AdapterFactory = Callable[[], VoiceAdapter]


class SessionGate:
    """Enforces the code-level limit on concurrent voice sessions."""

    def __init__(self, max_active: int) -> None:
        self._max_active = max_active
        self._active = 0
        # The TestClient portal and Uvicorn may use different threads; uvicorn's
        # event loop is single-threaded either way, the lock only costs a check.
        self._guard = threading.Lock()

    def acquire(self) -> bool:
        with self._guard:
            if self._active >= self._max_active:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._guard:
            self._active -= 1


def create_app(
    config: VoiceConfig | None = None,
    adapter_factory: AdapterFactory = FakeVoiceAdapter,
) -> FastAPI:
    settings = config or VoiceConfig.from_environment()
    gate = SessionGate(settings.max_active_sessions)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    async def health(request: Request) -> dict[str, str]:
        if request.headers.get("host") != settings.allowed_host:
            raise HTTPException(status_code=403)
        return {"status": "ok", "provider": "fake"}

    @app.websocket("/ws/voice")
    async def voice_socket(websocket: WebSocket) -> None:
        await _voice_socket(websocket, settings, adapter_factory, gate)

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
    gate: SessionGate,
) -> None:
    if (
        websocket.headers.get("host") != settings.allowed_host
        or websocket.headers.get("origin") != settings.allowed_origin
    ):
        await websocket.close(code=1008)
        return
    if not gate.acquire():
        await websocket.accept()
        await websocket.close(code=1013)
        return

    adapter: VoiceAdapter | None = None
    loop = asyncio.get_running_loop()
    # Infinite until authenticated so early timeouts classify as session-timeout.
    deadline = float("inf")
    try:
        await websocket.accept()
        adapter = adapter_factory()
        muted = False
        playback_epoch = 0
        deadline = loop.time() + settings.max_session_seconds
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
            remaining = deadline - loop.time()
            if remaining <= 0:
                await _safe_error(websocket, "max-duration")
                return
            incoming = await asyncio.wait_for(
                websocket.receive(),
                timeout=min(settings.idle_timeout_seconds, remaining),
            )
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
        expired = deadline != float("inf") and deadline - loop.time() <= 0
        await _safe_error(websocket, "max-duration" if expired else "session-timeout")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        await _safe_error(websocket, "invalid-control")
    except WebSocketDisconnect:
        pass
    except Exception:
        await _safe_error(websocket, "session-failed")
    finally:
        gate.release()
        if adapter is not None:
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
