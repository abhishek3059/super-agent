from __future__ import annotations

import asyncio
import hmac
import json
import math
import threading
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request, WebSocket
from starlette.websockets import WebSocketDisconnect

from .adapter import AdapterError, AudioChunk, FakeVoiceAdapter, Interrupted, TurnComplete, VoiceAdapter
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
    adapter_factory: AdapterFactory = FakeVoiceAdapter,
) -> FastAPI:
    settings = config or VoiceConfig.from_environment()
    # Fails closed before any session can run (teardown addendum 4.1).
    _validated_teardown_seconds(settings.teardown_seconds)
    gate = SessionGate(settings.max_active_sessions)
    # Strong references to one residual supervisor per quarantined session
    # are owned here, by the app scope (addendum section 4.7).
    supervisors: list[asyncio.Task] = []
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    async def health(request: Request) -> dict[str, str]:
        if request.headers.get("host") != settings.allowed_host:
            raise HTTPException(status_code=403)
        return {"status": "ok", "provider": "fake"}

    @app.websocket("/ws/voice")
    async def voice_socket(websocket: WebSocket) -> None:
        await _voice_socket(websocket, settings, adapter_factory, gate, supervisors)

    return app


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


def _validated_teardown_seconds(value: object) -> None:
    """Fail closed on a teardown budget that is not a real deadline (4.1)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError("teardown_seconds must be a real number")
    if not math.isfinite(float(value)) or value <= 0:
        raise RuntimeError("teardown_seconds must be finite and strictly positive")


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



async def _voice_socket(
    websocket: WebSocket,
    settings: VoiceConfig,
    adapter_factory: AdapterFactory,
    gate: SessionGate,
    supervisors: list[asyncio.Task],
) -> None:
    if (
        websocket.headers.get("host") != settings.allowed_host
        or websocket.headers.get("origin") != settings.allowed_origin
    ):
        await websocket.close(code=1008)
        return
    # CT-05: the single-session slot is taken before authentication on
    # purpose, so a busy session rejects the second connection immediately
    # with 1013 instead of letting it negotiate auth. The window an
    # unauthenticated connection can hold the slot is bounded by
    # auth_timeout_seconds inside the total budget (CT-04). Teardown releases
    # the slot only after worker quiescence and confirmed adapter closure.
    if not gate.acquire():
        await websocket.accept()
        await websocket.close(code=1013)
        return

    adapter: VoiceAdapter | None = None
    tasks: list[asyncio.Task[None]] = []
    failure: _SessionFailure | None = None
    stopped = False
    close_code = 1000
    loop = asyncio.get_running_loop()
    try:
        await websocket.accept()
        deadline = loop.time() + settings.max_session_seconds
        # CT-04: authentication has its own explicit deadline and is still
        # bounded by whatever remains of the total session budget, so the
        # total budget is never dropped during auth.
        auth_deadline = loop.time() + settings.auth_timeout_seconds
        effective = min(deadline, auth_deadline)
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
            return
        message = _control(incoming.get("text"), settings)
        supplied = message.get("token")
        if (
            message.get("type") != "session.auth"
            or not isinstance(supplied, str)
            or not hmac.compare_digest(supplied.encode("utf-8"), settings.local_token.encode("utf-8"))
        ):
            close_code = 1008
            return

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
