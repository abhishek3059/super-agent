from __future__ import annotations

import asyncio
import hmac
import json
import logging
import math
import os
import threading
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request, WebSocket
from starlette.websockets import WebSocketDisconnect

from .adapter import (
    AdapterError, AudioChunk, FakeVoiceAdapter, Interrupted, Thinking, Transcript, TurnComplete,
    VoiceAdapter,
)
from .config import VoiceConfig

AdapterFactory = Callable[[], VoiceAdapter]

# Fixed grace interval before the supervisor's one additional worker
# cancellation nudge (teardown addendum revision 2, section 4.7). Not
# configurable: it is a liveness heuristic for the trusted residual, not a
# deadline.
_SUPERVISOR_NUDGE_GRACE_SECONDS = 5.0


class SessionGate:
    """Enforces the code-level limit on concurrent voice sessions."""

    def __init__(self, max_active: int) -> None:
        self._max_active = max_active
        self._active = 0
        # TestClient portals may use different threads from the voice loop.
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


class _AuthControl:
    """Pre-auth state: connection cap, failed-attempt delay, and token expiry.

    The two gates are thread-safe like the session gate. The failure window is
    plain loop state: it is read and updated with no await in between.
    """

    def __init__(self, settings: VoiceConfig) -> None:
        self.settings = settings
        self.connections = SessionGate(settings.max_pre_auth_connections)
        self.sleepers = SessionGate(settings.max_delayed_rejections)
        # Memory bound only: the delay reaches its cap long before 32 doublings.
        self._failures: deque[float] = deque(maxlen=settings.auth_failure_threshold + 32)
        self._started = time.monotonic()

    def expired(self) -> bool:
        return time.monotonic() - self._started >= self.settings.token_max_age_seconds

    def failed(self) -> float:
        """Record a failed attempt and return how long to hold its rejection."""
        now = time.monotonic()
        while self._failures and now - self._failures[0] > self.settings.auth_failure_window_seconds:
            self._failures.popleft()
        self._failures.append(now)
        excess = len(self._failures) - self.settings.auth_failure_threshold
        if excess <= 0:
            return 0.0
        return min(
            self.settings.auth_delay_base_seconds * 2 ** (excess - 1),
            self.settings.auth_delay_cap_seconds,
        )

    def succeeded(self) -> None:
        self._failures.clear()


class _SessionFailure(Exception):
    def __init__(self, category: str, close_code: int = 1000) -> None:
        super().__init__(category)
        self.category = category
        self.close_code = close_code


class _Stopped(Exception):
    pass


@dataclass
class _SessionState:
    deadline: float
    last_input: float
    muted: bool = False
    epoch: int = 0


@dataclass(frozen=True)
class _Outbound:
    message: dict[str, object]
    audio: bytes | None = None
    epoch: int | None = None


class _OutboundQueue:
    """Keeps audio metadata and bytes atomic, without dropping controls.

    Audio overflow drops the oldest queued audio item; control overflow
    fails the whole session closed (fail-closed bound).
    """

    def __init__(self, max_audio: int = 16, max_controls: int = 32) -> None:
        self._items: deque[_Outbound] = deque()
        self._available = asyncio.Event()
        self._max_audio = max_audio
        self._max_controls = max_controls
        self._audio_count = 0
        self._control_count = 0
        self.dropped_audio = 0

    def put(self, item: _Outbound) -> None:
        if item.audio is not None:
            if self._audio_count >= self._max_audio:
                oldest = next(queued for queued in self._items if queued.audio is not None)
                self._items.remove(oldest)
                self._audio_count -= 1
                self.dropped_audio += 1
            self._audio_count += 1
        else:
            if self._control_count >= self._max_controls:
                raise _SessionFailure("session-failed")
            self._control_count += 1
        self._items.append(item)
        self._available.set()

    async def get(self) -> _Outbound:
        while not self._items:
            await self._available.wait()
        item = self._items.popleft()
        if item.audio is None:
            self._control_count -= 1
        else:
            self._audio_count -= 1
        if not self._items:
            self._available.clear()
        return item

    def clear_playback(self) -> None:
        # Untagged control acknowledgements survive mute and interruption.
        self._items = deque(item for item in self._items if item.epoch is None)
        self._audio_count = 0
        self._control_count = len(self._items)
        if not self._items:
            self._available.clear()


def create_app(
    config: VoiceConfig | None = None,
    adapter_factory: AdapterFactory | None = None,
) -> FastAPI:
    settings = config or VoiceConfig.from_environment()
    adapter_factory = adapter_factory or _adapter_from_environment()
    # Fails closed before any session can run (teardown addendum 4.1).
    for name in (
        "teardown_seconds", "token_max_age_seconds", "auth_failure_window_seconds",
        "auth_delay_base_seconds", "auth_delay_cap_seconds",
    ):
        _validated_positive(name, getattr(settings, name))
    for name in ("max_pre_auth_connections", "auth_failure_threshold", "max_delayed_rejections"):
        _validated_positive(name, getattr(settings, name), integer=True)
    if _frame_logging_enabled():
        raise RuntimeError("debug logging would record the session token; use --log-level info")
    gate = SessionGate(settings.max_active_sessions)
    auth = _AuthControl(settings)
    # Strong references to one residual supervisor per quarantined session
    # are owned here, by the app scope (addendum section 4.7).
    supervisors: list[asyncio.Task] = []
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    async def health(request: Request) -> dict[str, str]:
        if request.headers.get("host") != settings.allowed_host:
            raise HTTPException(status_code=403)
        return {"status": "ok", "provider": getattr(adapter_factory, "name", "unknown")}

    @app.websocket("/ws/voice")
    async def voice_socket(websocket: WebSocket) -> None:
        await _voice_socket(websocket, settings, adapter_factory, gate, supervisors, auth)

    return app


def _adapter_from_environment() -> AdapterFactory:
    choice = os.environ.get("SUPER_AGENT_ADAPTER", "fake")
    if choice == "fake":
        return FakeVoiceAdapter
    if choice == "local":
        from .local_adapter import LocalVoiceAdapter
        return LocalVoiceAdapter
    # Fail closed: an unknown name never falls back to some other provider.
    raise RuntimeError("SUPER_AGENT_ADAPTER must be 'fake' or 'local'")


def _frame_logging_enabled() -> bool:
    """DEBUG frame logging would write the token from the first message (REQ-12).

    Checked at startup and again per connection, because a launcher can build
    the app before uvicorn sets up logging, or raise the level later.
    """
    return any(logging.getLogger(name).isEnabledFor(logging.DEBUG) for name in ("uvicorn.error", "websockets"))


def _control(text: str | None, settings: VoiceConfig) -> dict[str, object]:
    if text is None or len(text.encode("utf-8")) > settings.max_control_bytes:
        raise _SessionFailure("invalid-control")
    try:
        message = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        raise _SessionFailure("invalid-control") from None
    if not isinstance(message, dict):
        raise _SessionFailure("invalid-control")
    return message


def _validated_positive(name: str, value: object, integer: bool = False) -> None:
    """Fail closed on a budget or limit that is not a real positive number (4.1)."""
    if isinstance(value, bool) or not isinstance(value, int if integer else (int, float)):
        raise RuntimeError(f"{name} must be {'an integer' if integer else 'a real number'}")
    if not math.isfinite(float(value)) or value <= 0:
        raise RuntimeError(f"{name} must be finite and strictly positive")


def _settled_error(task: asyncio.Task) -> BaseException | None:
    """Retrieve a settled task's outcome; a cancellation is retrieved too.

    ``Task.exception()`` raises ``CancelledError`` when the task itself was
    cancelled, so the cancellation is returned as the outcome instead of
    escaping the retrieval call.
    """
    try:
        return task.exception()
    except asyncio.CancelledError as exc:
        return exc


async def _presence_wait(
    tasks: set[asyncio.Task], budget: float
) -> tuple[set[asyncio.Task], set[asyncio.Task]]:
    """``asyncio.wait`` presence semantics under a bounded budget.

    Presence waits return on time regardless of cancellation-suppressing
    tasks (addendum section 2): a timed-out wait never cancels the inner
    tasks, and an externally cancelled waiter leaves them untouched too.
    """
    if not tasks:
        return set(), set()
    if budget <= 0:
        done = {task for task in tasks if task.done()}
        return done, tasks - done
    return await asyncio.wait(tasks, timeout=budget)


@dataclass
class _SessionTeardown:
    """Per-session teardown bookkeeping shared by handler and supervisor.

    Strong references to every owned task live here; the asyncio loop keeps
    only weak references (addendum section 2). ``deadline`` is the one shared
    monotonic teardown deadline; nothing below resets or extends it while the
    handler owns the cleanup.
    """

    websocket: WebSocket
    gate: SessionGate
    adapter: VoiceAdapter | None
    settings: VoiceConfig
    loop: asyncio.AbstractEventLoop
    workers: list[asyncio.Task]
    failure: _SessionFailure | None
    stopped: bool
    close_code: int
    deadline: float
    close_settled: bool = False
    close_confirmed: bool = False
    released: bool = False
    undelivered: bool = False
    cleanup_task: asyncio.Task | None = None
    close_task: asyncio.Task | None = None
    supervisor: asyncio.Task | None = None
    wire: list[asyncio.Task] = field(default_factory=list)
    wire_pass_started: bool = False
    wire_pass_done: bool = False
    workers_quiesced: bool = False
    cancel_deliveries: int = 0

    def remaining(self) -> float:
        return max(0.0, self.deadline - self.loop.time())


async def _teardown_session(record: _SessionTeardown) -> None:
    """Bounded cleanup sequence (addendum sections 4.2 to 4.6).

    Workers are cancelled, quiescence is a presence wait under the shared
    deadline, the close attempt is one task with two distinct verdicts
    (settled / confirmed), and the gate is released exactly once and only on
    quiescence plus confirmed closure. Quarantine never emits wire ops here.
    """
    for task in record.workers:
        task.cancel()
    done, pending = await _presence_wait(set(record.workers), record.remaining())
    for finished in done:
        _settled_error(finished)
    if pending:
        # Exactly once: re-request cancellation as a nudge, not cleanup.
        for task in pending:
            task.cancel()
    record.workers_quiesced = not pending

    if record.adapter is not None:
        close_task = asyncio.create_task(record.adapter.close())
        record.close_task = close_task
        _, pending_close = await _presence_wait({close_task}, record.remaining())
        if pending_close:
            # One explicit cancel request, never waited for; the verdict
            # stays "not settled" and the supervisor owns the task.
            close_task.cancel()
            record.close_settled = False
            record.close_confirmed = False
        else:
            record.close_settled = True
            record.close_confirmed = _settled_error(close_task) is None
    else:
        # No adapter authority exists before authentication, so there is
        # nothing pending to close and nothing the release gate would keep.
        record.close_confirmed = True

    # Release is exactly-once per session, guarded by record.released, and
    # happens only when quiescence is observed AND the closure is confirmed
    # (amended CT-03). A settled-but-exceptional or unsettled close keeps
    # the slot in quarantine (4.6) pending the supervisor's single retry.
    if record.workers_quiesced and record.close_confirmed and not record.released:
        record.released = True
        record.gate.release()

    if record.workers_quiesced and record.close_confirmed:
        await _run_wire_ops(record)
    # Quarantine (4.6): no further wire ops in this teardown block, nothing
    # about adapter or worker state is claimed to the client, and ownership
    # of the remainder goes to the one trusted supervisor via the handler.


async def _run_wire_ops(record: _SessionTeardown) -> None:
    """Final wire ops: serialized, presence-bounded, stop-on-pending (4.5).

    At most one pending wire operation exists anywhere in this pass. An op
    that misses its budget is cancelled once, marked undelivered, and the
    whole sequence stops: no later close or status op may interleave with a
    pending cancel-resistant wire op on the same socket. A timed-out op stays
    strongly owned via record.wire; its exception is retrieved by whoever
    owns it when it settles.
    """
    ops: list[tuple[str, Callable[[], Awaitable[None]]]] = []
    if record.failure is not None:
        category = record.failure.category
        ops.append((
            "session.error",
            lambda: record.websocket.send_json({
                "type": "session.error", "category": category,
            }),
        ))
    elif record.stopped:
        ops.append((
            "stopping",
            lambda: record.websocket.send_json({
                "type": "session.state", "state": "stopping",
            }),
        ))
    ops.append((
        "close",
        lambda: record.websocket.close(code=record.close_code),
    ))
    record.wire_pass_started = True
    for _, op in ops:
        if record.remaining() <= 0:
            record.undelivered = True
            return
        task = asyncio.ensure_future(op())
        record.wire.append(task)
        _, pending = await _presence_wait({task}, record.remaining())
        if pending:
            task.cancel()
            record.undelivered = True
            # Stop the whole wire sequence: the recorded op is undelivered,
            # never claimed as sent, and waits for its owner to settle it.
            return
        # A settled op (even one that raised, for example because the client
        # left) is no longer pending, so the sequence may continue.
        if _settled_error(task) is not None:
            record.undelivered = True
    record.wire_pass_done = True



# Internal marker for a rejected credential: closes 1008 and sends nothing.
_AUTH_FAILED = "auth-failed"


async def _authenticate(
    websocket: WebSocket, settings: VoiceConfig, auth: _AuthControl, deadline: float
) -> None:
    loop = asyncio.get_running_loop()
    # CT-04: authentication has its own explicit deadline and is still
    # bounded by whatever remains of the total session budget, so the
    # total budget is never dropped during auth.
    effective = min(deadline, loop.time() + settings.auth_timeout_seconds)
    try:
        incoming = await asyncio.wait_for(
            websocket.receive(), timeout=effective - loop.time()
        )
    except TimeoutError:
        # The category records which actual deadline expired.
        raise _SessionFailure(
            "max-duration" if loop.time() >= deadline else "session-timeout"
        ) from None
    if incoming["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(incoming.get("code", 1000))
    message = _control(incoming.get("text"), settings)
    supplied = message.get("token")
    # CR-08: compare UTF-8 bytes; surrogatepass keeps a lone surrogate in the
    # JSON from raising, so it is only a failed attempt.
    token_ok = isinstance(supplied, str) and hmac.compare_digest(
        supplied.encode("utf-8", "surrogatepass"), settings.local_token.encode("utf-8")
    )
    if message.get("type") != "session.auth" or not token_ok or auth.expired():
        raise _SessionFailure(_AUTH_FAILED, close_code=1008)


async def _refuse(
    websocket: WebSocket, settings: VoiceConfig, auth: _AuthControl, failure: _SessionFailure
) -> None:
    """Reject a connection that never became a session.

    No adapter, worker, or session slot exists yet, so the whole teardown is a
    bounded delay (credential failures only) and the two final wire ops.
    """
    try:
        if failure.category in (_AUTH_FAILED, "invalid-control"):
            delay = auth.failed()
            # Past the sleeper cap the rejection is immediate instead of queued.
            if delay and auth.sleepers.acquire():
                try:
                    await _hold_open(websocket, delay)
                finally:
                    auth.sleepers.release()
        async with asyncio.timeout(settings.teardown_seconds):
            if failure.category != _AUTH_FAILED:
                await websocket.send_json({"type": "session.error", "category": failure.category})
            await websocket.close(code=failure.close_code)
    except Exception:
        # The client left or the wire is stuck: nothing is owed to it.
        pass


async def _hold_open(websocket: WebSocket, seconds: float) -> None:
    """Wait ``seconds``, ending early if the client disconnects."""
    loop = asyncio.get_running_loop()
    end = loop.time() + seconds
    while (left := end - loop.time()) > 0:
        try:
            incoming = await asyncio.wait_for(websocket.receive(), timeout=left)
        except TimeoutError:
            return
        if incoming["type"] == "websocket.disconnect":
            return


async def _voice_socket(
    websocket: WebSocket,
    settings: VoiceConfig,
    adapter_factory: AdapterFactory,
    gate: SessionGate,
    supervisors: list[asyncio.Task],
    auth: _AuthControl,
) -> None:
    if (
        websocket.headers.get("host") != settings.allowed_host
        or websocket.headers.get("origin") != settings.allowed_origin
    ):
        await websocket.close(code=1008)
        return
    if _frame_logging_enabled():
        await websocket.close(code=1011)
        return
    loop = asyncio.get_running_loop()
    deadline = loop.time() + settings.max_session_seconds
    # CR-06: authentication happens before the single-session slot is taken, so
    # an unauthenticated client can never starve the real user. Pre-auth sockets
    # have their own cap instead, taken before accept so a client that sees the
    # accept is already counted.
    if not auth.connections.acquire():
        await websocket.accept()
        await websocket.close(code=1013)
        return
    failure: _SessionFailure | None = None
    try:
        await websocket.accept()
        await _authenticate(websocket, settings, auth, deadline)
    except WebSocketDisconnect:
        return
    except _SessionFailure as error:
        failure = error
    except Exception:
        failure = _SessionFailure("session-failed")
    finally:
        # Released before any failure delay (review N1): a delayed rejection
        # must not fill the cap and lock the real user out.
        auth.connections.release()
    if failure is not None:
        await _refuse(websocket, settings, auth, failure)
        return
    auth.succeeded()
    # Teardown releases the slot only after worker quiescence and confirmed
    # adapter closure.
    if not gate.acquire():
        await websocket.close(code=1013)
        return

    adapter: VoiceAdapter | None = None
    tasks: list[asyncio.Task[None]] = []
    failure = None
    stopped = False
    close_code = 1000
    try:
        # No adapter or future provider session exists before authentication.
        adapter = adapter_factory()
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise _SessionFailure("max-duration")
        try:
            await asyncio.wait_for(adapter.start(), timeout=remaining)
        except TimeoutError:
            raise _SessionFailure("max-duration") from None
        except AdapterError as error:
            raise _SessionFailure(error.category) from None
        except Exception:
            raise _SessionFailure("provider-unavailable") from None

        state = _SessionState(deadline=deadline, last_input=loop.time())
        outbound = _OutboundQueue()
        outbound.put(_Outbound({
            "type": "session.ready", "playbackEpoch": 0,
            "outputRateHz": adapter.output_rate_hz, "provider": adapter.name,
        }))
        tasks = [
            asyncio.create_task(_receive(websocket, adapter, settings, state, outbound)),
            asyncio.create_task(_forward(adapter, settings, state, outbound)),
            asyncio.create_task(_send(websocket, state, outbound)),
            asyncio.create_task(_watchdog(settings, state)),
        ]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except _Stopped:
        stopped = True
    except _SessionFailure as error:
        failure = error
        close_code = error.close_code
    except WebSocketDisconnect:
        pass
    except Exception:
        failure = _SessionFailure("session-failed")
    finally:
        record = _SessionTeardown(
            websocket=websocket,
            gate=gate,
            adapter=adapter,
            settings=settings,
            loop=loop,
            workers=tasks,
            failure=failure,
            stopped=stopped,
            close_code=close_code,
            deadline=loop.time() + settings.teardown_seconds,
        )
        # 4.8: one dedicated cleanup task runs the whole teardown sequence;
        # external delivery interrupts only the bounded waiter below, never
        # the task. All waits budget from record.remaining().
        await _bounded_teardown(record, supervisors)


async def _bounded_teardown(
    record: _SessionTeardown, supervisors: list[asyncio.Task]
) -> None:
    """Protected bounded teardown: waiter bound, owned residual (4.8).

    The handler waits in a loop of presence waits under the shared deadline.
    Each cancellation delivery is counted and only interrupts the waiter; the
    first captured cancellation is re-raised after the bounded wait. When the
    deadline expires with cleanup still running, cleanup ownership transfers
    atomically to the one residual supervisor. The task's own lifetime is
    owned, not bounded: claiming it bounded would be a false bound.
    """

    async def cleanup() -> None:
        try:
            await _teardown_session(record)
        except asyncio.CancelledError:
            # The waiter never cancels this task; a cancelled cleanup leaves
            # reconciliation to the supervisor (fail closed, no claims).
            return
        except Exception:
            # An unexpected teardown fault never escapes as a raw exception
            # and never fabricates closure or success: the flags below stay
            # as they are and the supervisor reconciles the leftovers.
            return

    cleanup_task = asyncio.create_task(cleanup())
    record.cleanup_task = cleanup_task  # strong ref while anyone waits on it
    first_cancel: asyncio.CancelledError | None = None
    while not cleanup_task.done():
        budget = record.remaining()
        if budget <= 0:
            break  # shared deadline expired; ownership transfer below
        try:
            await asyncio.wait([cleanup_task], timeout=budget)
        except asyncio.CancelledError as exc:
            record.cancel_deliveries += 1
            if first_cancel is None:
                first_cancel = exc
            continue  # no per-delivery task, no deadline reset, no busy loop
    transfer = not cleanup_task.done()
    if not transfer:
        _settled_error(cleanup_task)
    leftover_wire = any(not task.done() for task in record.wire)
    if (
        transfer
        or not record.workers_quiesced
        or not record.close_confirmed
        or leftover_wire
    ):
        # Quarantine (4.6) or deadline transfer (4.8): the handler issues no
        # wire ops and does not release the gate here; the one supervisor
        # owns the remainder.
        _ensure_supervisor(record, supervisors)
    elif record.released:
        record.cleanup_task = None
    if first_cancel is not None:
        # The first captured external cancellation is preserved, not
        # replaced by later deliveries nor converted to another category.
        raise first_cancel


def _ensure_supervisor(record: _SessionTeardown, supervisors: list[asyncio.Task]) -> None:
    """Ownership transfer target: created at most once per session (4.7)."""
    if record.supervisor is None:
        record.supervisor = asyncio.create_task(_residual_supervisor(record))
        supervisors.append(record.supervisor)

        def settled(task: asyncio.Task) -> None:
            _settled_error(task)
            supervisors.remove(task)

        record.supervisor.add_done_callback(settled)


async def _residual_supervisor(record: _SessionTeardown) -> None:
    """One trusted residual owner per session (addendum section 4.7).

    Its waits are the single documented unbounded-by-design exception. It
    waits for actual worker quiescence and for the original close attempt to
    settle, never starts a second close while one is pending, retries at most
    once, and only ever releases the gate on the same two conditions as the
    bounded path. Every owned task is strong-referenced and its outcome
    retrieved; nothing per attempt is spawned.
    """
    try:
        # 1. An abandoned in-flight teardown completes under this owner.
        if record.cleanup_task is not None:
            if not record.cleanup_task.done():
                await asyncio.wait([record.cleanup_task])
            _settled_error(record.cleanup_task)
            record.cleanup_task = None
        # Leftover wire ops settle first so no new op can interleave with a
        # pending wire op on the same socket (4.5).
        for task in list(record.wire):
            if not task.done():
                await asyncio.wait([task])
            _settled_error(task)
        if not record.released:
            await _pursue_release(record)
        for task in [*record.workers, *record.wire]:
            if not task.done():
                await asyncio.wait([task])
            _settled_error(task)
    except Exception:
        # Fail closed: no automatic success, no fabricated closure; a fault
        # leaves the gate held for operator recovery.
        return


async def _pursue_release(record: _SessionTeardown) -> None:
    """Steps 1 to 3 of the trusted residual sequence (4.7)."""
    pending = [task for task in record.workers if not task.done()]
    if pending:
        _, still_pending = await _presence_wait(set(pending), _SUPERVISOR_NUDGE_GRACE_SECONDS)
        pending = list(still_pending)
        if pending:
            for task in pending:
                task.cancel()  # one additional nudge, no periodic loop
            await asyncio.wait(pending)  # trusted
    record.workers_quiesced = not [
        task for task in record.workers if not task.done()
    ]

    if record.adapter is not None:
        # Never start a second close while an earlier attempt is pending:
        # first wait for the original attempt to actually settle.
        if record.close_task is not None:
            if not record.close_task.done():
                await asyncio.wait([record.close_task])
            record.close_settled = True
            record.close_confirmed = _settled_error(record.close_task) is None
        else:
            record.close_task = asyncio.create_task(record.adapter.close())
            await asyncio.wait([record.close_task])
            record.close_settled = True
            record.close_confirmed = _settled_error(record.close_task) is None
        if not record.close_confirmed:
            # At most one idempotent retry, only after the prior attempt
            # settled as cancelled or raised. A failing retry is terminal:
            # the gate stays held, and no success is recorded anywhere.
            retry = asyncio.create_task(record.adapter.close())
            record.close_task = retry
            record.close_settled = False
            await asyncio.wait([retry])
            record.close_settled = True
            record.close_confirmed = _settled_error(retry) is None

    if record.workers_quiesced and record.close_confirmed:
        if not record.released:
            record.released = True
            record.gate.release()
        # Deferred final wire ops, only here where the sequence never ran.
        if not record.wire_pass_started:
            # Start the residual wire budget only after cleanup and authority
            # reconciliation. Never extend an in-flight handler's deadline.
            record.deadline = record.loop.time() + record.settings.teardown_seconds
            await _run_wire_ops(record)


async def _receive(
    websocket: WebSocket,
    adapter: VoiceAdapter,
    settings: VoiceConfig,
    state: _SessionState,
    outbound: _OutboundQueue,
) -> None:
    loop = asyncio.get_running_loop()
    while True:
        incoming = await websocket.receive()
        if incoming["type"] == "websocket.disconnect":
            return
        state.last_input = loop.time()
        audio = incoming.get("bytes")
        if audio is not None:
            if not audio or len(audio) % 2 or len(audio) > settings.max_audio_frame_bytes:
                raise _SessionFailure("invalid-audio", close_code=1009)
            if not state.muted:
                await adapter.enqueue_audio(audio)
            continue
        event = _control(incoming.get("text"), settings).get("type")
        if event == "capture.mute":
            state.muted = True
            outbound.clear_playback()
            await adapter.end_audio_stream()
            await adapter.interrupt()
            outbound.put(_Outbound({"type": "session.state", "muted": True}))
        elif event == "capture.unmute":
            state.muted = False
            outbound.put(_Outbound({"type": "session.state", "muted": False}))
        elif event == "playback.interrupt":
            state.epoch += 1
            outbound.clear_playback()
            await adapter.interrupt()
            outbound.put(_Outbound({
                "type": "playback.interrupted", "playbackEpoch": state.epoch, "source": "local",
            }))
        elif event == "session.stop":
            raise _Stopped()
        else:
            raise _SessionFailure("invalid-control")


async def _forward(
    adapter: VoiceAdapter,
    settings: VoiceConfig,
    state: _SessionState,
    outbound: _OutboundQueue,
) -> None:
    try:
        await _forward_events(adapter, settings, state, outbound)
    except AdapterError as error:
        raise _SessionFailure(error.category) from None


async def _forward_events(
    adapter: VoiceAdapter,
    settings: VoiceConfig,
    state: _SessionState,
    outbound: _OutboundQueue,
) -> None:
    async for event in adapter.events():
        if isinstance(event, Interrupted):
            state.epoch += 1
            outbound.clear_playback()
            outbound.put(_Outbound({
                "type": "playback.interrupted", "playbackEpoch": state.epoch, "source": "provider",
            }))
        elif isinstance(event, AudioChunk):
            if (
                not isinstance(event.data, bytes) or not event.data or len(event.data) % 2
                or len(event.data) > settings.max_audio_frame_bytes
                or type(event.rate_hz) is not int or event.rate_hz not in {8000, 16000, 24000, 48000}
            ):
                raise _SessionFailure("invalid-audio")
            if not state.muted:
                outbound.put(_Outbound({
                    "type": "audio.chunk", "playbackEpoch": state.epoch,
                    "rateHz": event.rate_hz, "channels": 1, "format": "pcm16",
                }, audio=event.data, epoch=state.epoch))
        elif isinstance(event, Thinking):
            if not state.muted:
                outbound.put(_Outbound({"type": "turn.state", "state": "thinking"}, epoch=state.epoch))
        elif isinstance(event, Transcript):
            # Shown in the console for this session only; sizes are bounded here,
            # not trusted from the adapter.
            if not state.muted and event.role in ("user", "assistant") and isinstance(event.text, str):
                outbound.put(_Outbound({
                    "type": "conversation.text", "role": event.role, "text": event.text[:500],
                }, epoch=state.epoch))
        elif isinstance(event, TurnComplete):
            if not state.muted:
                outbound.put(_Outbound({
                    "type": "turn.complete", "playbackEpoch": state.epoch,
                }, epoch=state.epoch))
        else:
            raise _SessionFailure("session-failed")
    raise _SessionFailure("provider-session-ended")


async def _send(websocket: WebSocket, state: _SessionState, outbound: _OutboundQueue) -> None:
    while True:
        item = await outbound.get()
        if item.epoch is not None and (item.epoch != state.epoch or state.muted):
            continue
        await websocket.send_json(item.message)
        if item.audio is None:
            continue
        # CT-01: a control can change the epoch or mute state during the
        # awaited JSON send, so ownership is re-checked before the bytes go
        # out under metadata whose epoch or mute state has expired.
        if item.epoch != state.epoch or state.muted:
            continue
        await websocket.send_bytes(item.audio)


async def _watchdog(settings: VoiceConfig, state: _SessionState) -> None:
    loop = asyncio.get_running_loop()
    while True:
        idle_deadline = state.last_input + settings.idle_timeout_seconds
        deadline = min(state.deadline, idle_deadline)
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise _SessionFailure(
                "max-duration" if state.deadline <= idle_deadline else "session-timeout"
            )
        await asyncio.sleep(remaining)
