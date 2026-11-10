from __future__ import annotations

import asyncio
import hmac
import json
import threading
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request, WebSocket
from starlette.websockets import WebSocketDisconnect

from .adapter import AdapterError, AudioChunk, FakeVoiceAdapter, Interrupted, TurnComplete, VoiceAdapter
from .config import VoiceConfig

AdapterFactory = Callable[[], VoiceAdapter]
OUTBOUND_QUEUE_ITEMS = 256
AUTH_TIMEOUT_SECONDS = 5


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


class _SessionEnd(Exception):
    """Ends the session with a fixed category (None means a clean stop)."""

    def __init__(self, category: str | None = None, close_code: int = 1000) -> None:
        super().__init__(category)
        self.category = category
        self.close_code = close_code


def create_app(
    config: VoiceConfig | None = None,
    adapter_factory: AdapterFactory = FakeVoiceAdapter,
) -> FastAPI:
    settings = config or VoiceConfig.from_environment()
    gate = SessionGate(settings.max_active_sessions)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    provider = getattr(adapter_factory, "name", "custom")

    @app.get("/health")
    async def health(request: Request) -> dict[str, str]:
        if request.headers.get("host") != settings.allowed_host:
            raise HTTPException(status_code=403)
        return {"status": "ok", "provider": provider}

    @app.websocket("/ws/voice")
    async def voice_socket(websocket: WebSocket) -> None:
        await _voice_socket(websocket, settings, adapter_factory, gate)

    return app


async def _safe_error(websocket: WebSocket, category: str) -> None:
    try:
        await websocket.send_json({"type": "session.error", "category": category})
    except (RuntimeError, WebSocketDisconnect):
        pass


async def _safe_close(websocket: WebSocket, code: int) -> None:
    try:
        await websocket.close(code=code)
    except RuntimeError:
        pass


async def _authenticate(websocket: WebSocket, settings: VoiceConfig) -> bool:
    auth = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
    if len(auth.encode("utf-8")) > settings.max_control_bytes:
        raise _SessionEnd(close_code=1009)
    message = json.loads(auth)
    supplied = message.get("token", "") if isinstance(message, dict) and message.get("type") == "session.auth" else ""
    if not isinstance(supplied, str):
        return False
    # Bytes, not str: compare_digest raises on non-ASCII str input (review CR-08).
    return hmac.compare_digest(supplied.encode("utf-8"), settings.local_token.encode("utf-8"))


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
    await websocket.accept()

    # Authenticate before taking the single session slot, so an unauthenticated
    # client cannot hold it (design section 5 step 3, review CR-06).
    try:
        if not await _authenticate(websocket, settings):
            await _safe_close(websocket, 1008)
            return
    except _SessionEnd as end:
        await _safe_close(websocket, end.close_code)
        return
    except (asyncio.TimeoutError, TimeoutError):
        await _safe_error(websocket, "session-timeout")
        await _safe_close(websocket, 1000)
        return
    except (json.JSONDecodeError, ValueError, TypeError):
        await _safe_error(websocket, "invalid-control")
        await _safe_close(websocket, 1000)
        return
    except KeyError:
        # A binary first frame has no text; treat it as a failed auth.
        await _safe_close(websocket, 1008)
        return
    except WebSocketDisconnect:
        return

    if not gate.acquire():
        await _safe_close(websocket, 1013)
        return

    adapter: VoiceAdapter | None = None
    close_code = 1000
    try:
        try:
            adapter = adapter_factory()
            await asyncio.wait_for(adapter.start(), settings.provider_start_timeout_seconds)
        except AdapterError as error:
            # A missing key or unusable provider config is reported as unavailable.
            category = "provider-unavailable" if error.category == "provider-unsupported" and adapter is None else error.category
            await _safe_error(websocket, category)
            return
        except (asyncio.TimeoutError, TimeoutError):
            await _safe_error(websocket, "provider-unavailable")
            return
        await websocket.send_json(
            {
                "type": "session.ready",
                "playbackEpoch": 0,
                "outputRateHz": adapter.output_rate_hz,
                "provider": adapter.name,
            }
        )
        close_code = await _run_session(websocket, settings, adapter)
    except WebSocketDisconnect:
        pass
    except Exception:
        await _safe_error(websocket, "session-failed")
    finally:
        # Close the provider before freeing the slot so two provider sessions
        # never overlap; the close itself is time-bounded.
        if adapter is not None:
            try:
                await asyncio.wait_for(adapter.close(), settings.teardown_timeout_seconds)
            except Exception:
                pass
        gate.release()
        await _safe_close(websocket, close_code)


async def _run_session(websocket: WebSocket, settings: VoiceConfig, adapter: VoiceAdapter) -> int:
    """Runs receiver, forwarder, and watchdog; one sender owns every socket write."""
    outbound: asyncio.Queue[object] = asyncio.Queue(maxsize=OUTBOUND_QUEUE_ITEMS)
    state = {"muted": False, "epoch": 0}

    def send_control(message: dict[str, object]) -> None:
        try:
            outbound.put_nowait(message)
        except asyncio.QueueFull:
            # Control events are never dropped; a full queue fails closed.
            raise _SessionEnd("session-failed") from None

    async def sender() -> None:
        while True:
            item = await outbound.get()
            if item is None:
                return
            if isinstance(item, bytes):
                await websocket.send_bytes(item)
            else:
                await websocket.send_json(item)

    async def receiver() -> None:
        while True:
            incoming = await asyncio.wait_for(websocket.receive(), timeout=settings.idle_timeout_seconds)
            if incoming["type"] == "websocket.disconnect":
                raise _SessionEnd()
            audio = incoming.get("bytes")
            if audio is not None:
                if len(audio) > settings.max_audio_frame_bytes:
                    raise _SessionEnd(close_code=1009)
                if len(audio) % 2:
                    raise _SessionEnd("invalid-audio")
                if not audio:
                    continue  # empty frames carry nothing (and b"" is the adapter's stream-end marker)
                if not state["muted"]:
                    await adapter.enqueue_audio(audio)
                continue
            text = incoming.get("text")
            if text is None or len(text.encode("utf-8")) > settings.max_control_bytes:
                raise _SessionEnd("invalid-control")
            try:
                message = json.loads(text)
            except json.JSONDecodeError:
                raise _SessionEnd("invalid-control") from None
            event = message.get("type") if isinstance(message, dict) else None
            if event == "capture.mute":
                state["muted"] = True
                await adapter.end_audio_stream()
                send_control({"type": "session.state", "muted": True})
            elif event == "capture.unmute":
                state["muted"] = False
                send_control({"type": "session.state", "muted": False})
            elif event == "playback.interrupt":
                # Bump and announce the epoch before awaiting, so the forwarder
                # cannot interleave a newer epoch ahead of this message.
                state["epoch"] += 1
                send_control({"type": "playback.interrupted", "playbackEpoch": state["epoch"], "source": "local"})
                await adapter.interrupt()
            elif event == "session.stop":
                send_control({"type": "session.state", "state": "stopping"})
                raise _SessionEnd()
            else:
                raise _SessionEnd("invalid-control")

    async def forwarder() -> None:
        async for event in adapter.events():
            if isinstance(event, AudioChunk):
                if outbound.maxsize - outbound.qsize() < 2:
                    # shortcut: drops the newest chunk when the outbound queue is full;
                    # true drop-oldest needs paired metadata/binary removal; upgrade if measured.
                    continue
                outbound.put_nowait(
                    {"type": "audio.chunk", "playbackEpoch": state["epoch"], "rateHz": event.rate_hz, "channels": 1, "format": "pcm16"}
                )
                outbound.put_nowait(event.data)
            elif isinstance(event, TurnComplete):
                send_control({"type": "turn.complete", "playbackEpoch": state["epoch"]})
            elif isinstance(event, Interrupted):
                state["epoch"] += 1
                send_control({"type": "playback.interrupted", "playbackEpoch": state["epoch"], "source": "provider"})
        raise _SessionEnd("provider-session-ended")

    async def watchdog() -> None:
        await asyncio.sleep(settings.max_session_seconds)
        raise _SessionEnd("max-duration")

    send_task = asyncio.create_task(sender())
    work = [asyncio.create_task(job()) for job in (receiver, forwarder, watchdog)]
    try:
        done, _ = await asyncio.wait([*work, send_task], return_when=asyncio.FIRST_COMPLETED)
        for task in work:
            task.cancel()
        await asyncio.gather(*work, return_exceptions=True)

        category, close_code = _outcome(done)
        if send_task.done():
            return close_code  # the socket is gone; nothing more can be sent
        if category:
            try:
                outbound.put_nowait({"type": "session.error", "category": category})
            except asyncio.QueueFull:
                pass
        try:
            outbound.put_nowait(None)
        except asyncio.QueueFull:
            send_task.cancel()
        # A stalled client must not hold the session open: bound the final drain.
        try:
            await asyncio.wait_for(asyncio.shield(send_task), settings.teardown_timeout_seconds)
        except (asyncio.TimeoutError, TimeoutError):
            send_task.cancel()
        except Exception:
            pass
        return close_code
    finally:
        # Also runs when this handler is cancelled, so no child task outlives it.
        for task in (*work, send_task):
            task.cancel()
        await asyncio.gather(*work, send_task, return_exceptions=True)


def _outcome(done: set[asyncio.Task[None]]) -> tuple[str | None, int]:
    # Read every finished task's exception so none is reported as unretrieved.
    errors = [task.exception() for task in done if not task.cancelled()]
    for error in errors:
        if isinstance(error, _SessionEnd):
            return error.category, error.close_code
        if isinstance(error, AdapterError):
            return error.category, 1000
        if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
            return "session-timeout", 1000
        if isinstance(error, WebSocketDisconnect):
            return None, 1000
        if error is not None:
            return "session-failed", 1000
    return None, 1000
