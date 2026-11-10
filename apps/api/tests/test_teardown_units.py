"""Unit tests for the bounded teardown mechanic (addendum revision 2).

Covers the matrix rows T-6 to T-11 and T-13 directly against the
internal-but-signed helper interfaces (`_SessionTeardown`, `_bounded_teardown`,
`_ensure_supervisor` via its caller, `_send`, `_OutboundQueue`, `_SessionState`),
without the TestClient layer. T-1 to T-5 and T-12 run end to end in
`test_voice_api.py` (parent scope; not duplicated here).

Discipline:
- Event driven: the `Suspender` gate replaces sleeps; `await asyncio.sleep(0)`
  is only ever a microtask yield between deterministic steps.
- Every handler wait budgets from the one shared deadline; every await of an
  unbounded-by-design owner (the residual supervisor) is capped by a loose
  safety bound so a failure cannot hang pytest.
- Every test releases all injected blockers in a `finally` and settles its
  tasks, so no cancellation-resistant stub survives a failed assertion.

Stub suppression emulates mechanical cancellation suppression with `shield`
inside the stub (addendum section 2), sharing one strongly owned waiter task
per gate: repeated `asyncio.shield` awaits of that single task create no
per-delivery waiter tasks.
"""

from __future__ import annotations

import asyncio

import pytest

from super_agent_voice.app import (
    SessionGate,
    _Outbound,
    _OutboundQueue,
    _SessionFailure,
    _SessionState,
    _SessionTeardown,
    _bounded_teardown,
    _send,
)
from super_agent_voice.config import VoiceConfig

TOKEN = "t" * 32
# Short injected teardown budget (addendum 4.1: test-injected values expected).
TEARDOWN_SECONDS = 0.05
# Windows loop-timer and task-scheduling slack around deadline measurements.
EPSILON = 0.10
# Loose upper bound for bounded-by-test waits that must never hang pytest.
SAFETY_BOUND = 0.5


class Suspender:
    """Reusable cancellation-resistant event gate for injected blockers.

    The stub waits on exactly one underlying waiter task held by a strong
    reference; the suspend loop re-shields that same task after every
    cancelled attempt, so repeated deliveries leave no per-cancel event tasks
    behind. Tests release the gate (or, defensively, the owner is cancelled
    and the pending-owner guard exits the loop) in cleanup.
    """

    def __init__(self) -> None:
        self._event = asyncio.Event()
        self.owner: asyncio.Task | None = None

    def set(self) -> None:
        self._event.set()

    async def suspend(self) -> None:
        if self._event.is_set():
            return
        owner = asyncio.create_task(self._event.wait())
        self.owner = owner
        try:
            while not self._event.is_set():
                if owner.done():
                    # Owner cancelled in cleanup; re-shielding would spin.
                    return
                try:
                    await asyncio.shield(owner)
                except asyncio.CancelledError:
                    continue
        finally:
            if not owner.done():
                owner.cancel()
            self.owner = None


class StubWebSocket:
    """In-memory WebSocket stand-in: records wire ops, gates sends."""

    def __init__(self) -> None:
        self.send_gate: Suspender | None = None
        self.sent: list[dict[str, object]] = []
        self.bytes_sent: list[bytes] = []
        self.closes: list[int] = []
        self.send_starts = asyncio.Event()
        self.send_delivered = asyncio.Event()

    async def send_json(self, message: dict[str, object]) -> None:
        self.send_starts.set()
        if self.send_gate is not None:
            await self.send_gate.suspend()
        self.sent.append(message)
        self.send_delivered.set()

    async def send_bytes(self, data: bytes) -> None:
        self.bytes_sent.append(data)

    async def close(self, code: int = 1000) -> None:
        self.closes.append(code)


class StubAdapter:
    """Adapter stub: instrumented close attempts, optional blocker and raise."""

    def __init__(
        self, close_gate: Suspender | None = None, fail_first: int = 0
    ) -> None:
        self._close_gate = close_gate
        self._fail_first = fail_first
        self.close_calls = 0
        self.max_concurrent_close = 0
        self._active_close = 0
        self.closed = False
        self.close_entered = asyncio.Event()

    async def close(self) -> None:
        self.close_calls += 1
        self._active_close += 1
        self.max_concurrent_close = max(self.max_concurrent_close, self._active_close)
        try:
            if self._close_gate is not None:
                self.close_entered.set()
                await self._close_gate.suspend()
            self.closed = True
            if self.close_calls <= self._fail_first:
                raise RuntimeError("close exploded on attempt")
        finally:
            self._active_close -= 1


async def _resistant_worker(gate: Suspender) -> None:
    """Worker stub that swallows cancellation until the test opens the gate."""
    await gate.suspend()


def _build_record(
    loop: asyncio.AbstractEventLoop,
    websocket: StubWebSocket,
    gate: SessionGate,
    adapter: StubAdapter | None,
    workers: list[asyncio.Task],
    failure: _SessionFailure | None,
) -> _SessionTeardown:
    settings = VoiceConfig(local_token=TOKEN, teardown_seconds=TEARDOWN_SECONDS)
    return _SessionTeardown(
        websocket=websocket,  # type: ignore[arg-type]
        gate=gate,
        adapter=adapter,  # type: ignore[arg-type]
        settings=settings,
        loop=loop,
        workers=list(workers),
        failure=failure,
        stopped=False,
        close_code=1000,
        deadline=loop.time() + TEARDOWN_SECONDS,
    )


async def _bounded_own(record: _SessionTeardown, supervisors: list[asyncio.Task]) -> None:
    """Handler shape under test (the voice socket finally body)."""
    await _bounded_teardown(record, supervisors)


async def _await_completion(task: asyncio.Task | None, what: str) -> None:
    """Bounded wait for a task whose own design waits may be unbounded."""
    assert task is not None, f"{what} must exist"
    _, pending = await asyncio.wait([task], timeout=SAFETY_BOUND)
    assert not pending, f"{what} did not settle within the {SAFETY_BOUND}s safety bound"


async def _settle_tasks(tasks: list[asyncio.Task | None]) -> None:
    """Release-driven settlement: bounded wait, cancel stragglers, retrieve."""
    live = [t for t in tasks if t is not None and not t.done()]
    if live:
        await asyncio.wait(live, timeout=SAFETY_BOUND)
    for task in live:
        if not task.done():
            task.cancel()
    if live:
        await asyncio.gather(*live, return_exceptions=True)


# ---------------------------------------------------------------------------
# T-6
# ---------------------------------------------------------------------------


def test_worker_suppressing_cancel_quarantines_and_holds_gate() -> None:
    asyncio.run(_t6_worker_suppression_quarantine())


async def _t6_worker_suppression_quarantine() -> None:
    loop = asyncio.get_running_loop()
    gate = SessionGate(1)
    assert gate.acquire() is True
    websocket = StubWebSocket()
    adapter = StubAdapter()
    release = Suspender()
    worker = asyncio.create_task(_resistant_worker(release))
    supervisors: list[asyncio.Task] = []
    record = _build_record(
        loop, websocket, gate, adapter, [worker], _SessionFailure("session-timeout")
    )
    try:
        started = loop.time()
        await _bounded_own(record, supervisors)
        elapsed = loop.time() - started
        # The handler returns bounded even though the worker never quiesced.
        assert elapsed < TEARDOWN_SECONDS + EPSILON
        assert record.workers_quiesced is False
        assert record.released is False
        assert record.wire_pass_started is False
        # Quarantine: no worker/adapter state claimed over the wire.
        assert websocket.sent == []
        assert websocket.bytes_sent == []
        assert websocket.closes == []
        # Ownership transferred to the single residual supervisor.
        assert len(supervisors) == 1
        assert record.supervisor is supervisors[0]
        assert gate.acquire() is False  # fail closed while not confirmed
        # Release the resistant worker: the supervisor quiesces and releases.
        release.set()
        await _await_completion(record.supervisor, "supervisor")
        assert record.workers_quiesced is True
        assert record.close_confirmed is True
        assert record.released is True
        assert gate._active == 0
        assert record.wire_pass_done is True
        # Deferred final wire ops ran under the supervisor, with the boundary.
        assert websocket.sent == [
            {"type": "session.error", "category": "session-timeout"},
        ]
        assert websocket.closes == [1000]
    finally:
        release.set()
        await _settle_tasks([worker, record.supervisor, *record.wire])


# ---------------------------------------------------------------------------
# T-7
# ---------------------------------------------------------------------------


def test_blocked_final_wire_op_is_bounded_and_stops_sequence() -> None:
    asyncio.run(_t7_blocked_final_wire_op())


async def _t7_blocked_final_wire_op() -> None:
    loop = asyncio.get_running_loop()
    gate = SessionGate(1)
    assert gate.acquire() is True
    websocket = StubWebSocket()
    adapter = StubAdapter()
    send_gate = Suspender()
    websocket.send_gate = send_gate  # the final session.error send blocks
    supervisors: list[asyncio.Task] = []
    record = _build_record(
        loop, websocket, gate, adapter, [], _SessionFailure("invalid-audio")
    )
    try:
        started = loop.time()
        await _bounded_own(record, supervisors)
        elapsed = loop.time() - started
        # Workers and close quiesce; only the wire op blocks.
        assert record.workers_quiesced is True
        assert record.close_confirmed is True
        # Gate released while the wire op is pending (residual, disclosed).
        assert record.released is True
        assert record.wire_pass_started is True
        assert record.wire_pass_done is False
        assert elapsed < TEARDOWN_SECONDS + EPSILON
        # Undelivered, never claimed as sent; the sequence stopped.
        assert websocket.sent == []
        assert websocket.bytes_sent == []
        assert websocket.closes == []  # no later close while a wire op pends
        assert record.wire, "timed-out wire task must be strongly owned"
        assert not record.wire[0].done()
        assert len(record.wire) == 1
        assert len(supervisors) == 1
        # Release the blocker: the supervisor settles and retrieves the wire
        # op; no retry, no new wire op is spawned.
        send_gate.set()
        await _await_completion(record.supervisor, "supervisor")
        assert record.wire[0].done()
        assert len(record.wire) == 1
        assert websocket.closes == []  # still stopped: close op never issued
        assert record.undelivered is True
    finally:
        send_gate.set()
        await _settle_tasks([record.supervisor, *record.wire])


# ---------------------------------------------------------------------------
# T-8
# ---------------------------------------------------------------------------


def test_external_cancel_reraised_original_after_bounded_cleanup() -> None:
    asyncio.run(_t8_external_cancel_signal())


async def _t8_external_cancel_signal() -> None:
    loop = asyncio.get_running_loop()
    gate = SessionGate(1)
    assert gate.acquire() is True
    websocket = StubWebSocket()
    close_gate = Suspender()
    adapter = StubAdapter(close_gate=close_gate)
    supervisors: list[asyncio.Task] = []
    record = _build_record(
        loop, websocket, gate, adapter, [], _SessionFailure("session-timeout")
    )
    handler_task = asyncio.create_task(_bounded_own(record, supervisors))
    try:
        while not adapter.close_entered.is_set():
            await asyncio.sleep(0)  # microtask yield until the close is in flight
        await adapter.close_entered.wait()
        # One external delivery mid gated close.
        handler_task.cancel("external-stop")
        await asyncio.sleep(0)  # the waiter processes exactly this delivery
        assert record.cancel_deliveries == 1
        _, pending = await asyncio.wait([handler_task], timeout=SAFETY_BOUND)
        assert not pending, "bounded handler never finished"
        try:
            handler_task.result()
            raise AssertionError("handler must re-raise the delivered cancellation")
        except asyncio.CancelledError as exc:
            assert exc.args == ("external-stop",)  # original signal, not fabricated
        assert record.released is False
        assert len(supervisors) == 1 and record.supervisor is supervisors[0]
        # Open the gate: the close attempt finally settles, the supervisor
        # confirms it and releases exactly once.
        close_gate.set()
        await _await_completion(record.supervisor, "supervisor")
        assert record.close_settled is True
        assert record.close_confirmed is True
        assert record.workers_quiesced is True
        assert record.released is True
        assert gate._active == 0
        assert websocket.sent == [
            {"type": "session.error", "category": "session-timeout"},
        ]
        assert websocket.closes == [1000]
    finally:
        close_gate.set()
        await _settle_tasks([handler_task, record.supervisor, *record.wire])


# ---------------------------------------------------------------------------
# T-9
# ---------------------------------------------------------------------------


def test_shared_deadline_bounds_total_not_per_await() -> None:
    asyncio.run(_t9_shared_deadline())


async def _t9_shared_deadline() -> None:
    loop = asyncio.get_running_loop()
    gate = SessionGate(1)
    assert gate.acquire() is True
    websocket = StubWebSocket()
    worker_gate = Suspender()
    close_gate = Suspender()
    adapter = StubAdapter(close_gate=close_gate)
    worker = asyncio.create_task(_resistant_worker(worker_gate))
    supervisors: list[asyncio.Task] = []
    record = _build_record(
        loop, websocket, gate, adapter, [worker], _SessionFailure("session-timeout")
    )
    try:
        started = loop.time()
        await _bounded_own(record, supervisors)
        elapsed = loop.time() - started
        # One shared deadline: the worker suppression and the suppressed close
        # share the budget instead of each getting a fresh step budget.
        assert elapsed >= TEARDOWN_SECONDS - 0.005  # the budget was consumed
        assert elapsed < 2 * TEARDOWN_SECONDS  # strictly less than two budgets
        assert elapsed < TEARDOWN_SECONDS + EPSILON
        assert record.workers_quiesced is False
        assert record.released is False
        assert record.wire_pass_started is False
        assert len(supervisors) == 1
        # Release everything: the supervisor drains and releases exactly once.
        worker_gate.set()
        close_gate.set()
        await _await_completion(record.supervisor, "supervisor")
        # Both steps stayed owned by the shared deadline, not per-await budgets.
        assert record.workers_quiesced is True
        assert record.close_task is not None  # the second blocker was owned
        assert record.close_confirmed is True
        assert record.released is True
        assert gate._active == 0
        assert record.wire_pass_done is True
        assert websocket.closes == [1000]
    finally:
        worker_gate.set()
        close_gate.set()
        await _settle_tasks([worker, record.supervisor, *record.wire])


# ---------------------------------------------------------------------------
# T-10
# ---------------------------------------------------------------------------


def test_no_final_status_inside_audio_pair_when_quarantined() -> None:
    asyncio.run(_t10_no_status_inside_audio_pair())


async def _t10_no_status_inside_audio_pair() -> None:
    loop = asyncio.get_running_loop()
    gate = SessionGate(1)
    assert gate.acquire() is True
    websocket = StubWebSocket()
    send_gate = Suspender()
    websocket.send_gate = send_gate  # the real sender blocks inside send_json
    outbound = _OutboundQueue()
    state = _SessionState(deadline=loop.time() + 60, last_input=loop.time())
    pair_meta = {
        "type": "audio.chunk", "playbackEpoch": 0, "rateHz": 16000,
        "channels": 1, "format": "pcm16",
    }
    outbound.put(_Outbound(pair_meta, audio=b"\x01\x00", epoch=0))
    sender = asyncio.create_task(_send(websocket, state, outbound))  # type: ignore[arg-type]
    supervisors: list[asyncio.Task] = []
    record = _build_record(
        loop, websocket, gate, None, [sender], _SessionFailure("session-timeout")
    )
    try:
        while not websocket.send_starts.is_set():
            await asyncio.sleep(0)  # yield until the sender owns the pair
        await websocket.send_starts.wait()
        assert websocket.sent == [] and websocket.bytes_sent == []
        # The cancel "resolves": stop is recorded, so the pair's epoch/mute
        # state expires while the sender owns it (CT-01 preconditions).
        state.muted = True
        state.epoch = 1
        started = loop.time()
        await _bounded_own(record, supervisors)
        elapsed = loop.time() - started
        # Quarantine: the pair owner still holds the sender, so no final
        # status, no socket close, and no gate release.
        assert elapsed < TEARDOWN_SECONDS + EPSILON
        assert record.workers_quiesced is False
        assert record.released is False
        assert record.wire_pass_started is False
        assert websocket.sent == []  # final status NEVER while the worker owns the pair
        assert websocket.bytes_sent == []
        assert websocket.closes == []
        assert len(supervisors) == 1
        # Release the sender: the metadata already owned completes, but the
        # payload half must NOT be forwarded once the cancel resolved (CT-01
        # recheck), and the supervisor reconciles without interleaving.
        send_gate.set()
        await websocket.send_delivered.wait()
        assert websocket.sent == [pair_meta]
        assert websocket.bytes_sent == []
        assert websocket.closes == []
        sender.cancel()
        _, pending = await asyncio.wait([sender], timeout=SAFETY_BOUND)
        assert not pending, "sender did not settle after cancellation"
        await _await_completion(record.supervisor, "supervisor")
        assert record.workers_quiesced is True
        assert record.released is True
        assert gate._active == 0
        # One error, after the pair's delivered half; no close interleaved.
        assert websocket.sent == [
            pair_meta,
            {"type": "session.error", "category": "session-timeout"},
        ]
        assert websocket.closes == [1000]
    finally:
        send_gate.set()
        sender.cancel()
        await _settle_tasks([sender, record.supervisor, *record.wire])


# ---------------------------------------------------------------------------
# T-11
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["hanging-close", "first-fail-retry"])
def test_supervisor_ownership_and_no_overlapping_close(mode: str) -> None:
    asyncio.run(_t11_supervisor_ownership(mode))


async def _t11_supervisor_ownership(mode: str) -> None:
    loop = asyncio.get_running_loop()
    hanging = mode == "hanging-close"
    gate = SessionGate(1)
    assert gate.acquire() is True
    websocket = StubWebSocket()
    close_gate = Suspender()
    adapter = StubAdapter(
        close_gate=close_gate if hanging else None,
        fail_first=0 if hanging else 1,
    )
    supervisors: list[asyncio.Task] = []
    record = _build_record(
        loop, websocket, gate, adapter, [], _SessionFailure("invalid-audio")
    )
    try:
        await _bounded_own(record, supervisors)
        # Quarantine: a pending or exceptional close never releases the gate.
        assert record.workers_quiesced is True
        assert record.close_confirmed is False
        assert record.close_settled is (not hanging)
        assert record.released is False
        assert record.wire_pass_started is False
        assert websocket.sent == [] and websocket.closes == []
        assert len(supervisors) == 1 and record.supervisor is supervisors[0]
        if hanging:
            close_gate.set()
        await _await_completion(record.supervisor, "supervisor")
        # Record flags after the supervisor finished.
        assert record.close_settled is True
        assert record.close_confirmed is True
        assert record.workers_quiesced is True
        assert record.released is True
        assert gate._active == 0
        # The hanging attempt is retried never; the settled-raise case gets
        # exactly one idempotent retry. No second close while one is pending.
        assert adapter.close_calls == (1 if hanging else 2)
        assert adapter.max_concurrent_close == 1
        # The deferred boundary is delivered once, with the original category.
        assert websocket.sent == [
            {"type": "session.error", "category": "invalid-audio"},
        ]
        assert websocket.closes == [1000]
    finally:
        close_gate.set()
        await _settle_tasks([record.supervisor, *record.wire])


# ---------------------------------------------------------------------------
# T-13
# ---------------------------------------------------------------------------


def test_five_cancels_during_close_preserve_the_first_signal() -> None:
    asyncio.run(_t13_repeated_cancels())


async def _t13_repeated_cancels() -> None:
    loop = asyncio.get_running_loop()
    gate = SessionGate(1)
    assert gate.acquire() is True
    websocket = StubWebSocket()
    close_gate = Suspender()
    adapter = StubAdapter(close_gate=close_gate)
    supervisors: list[asyncio.Task] = []
    record = _build_record(
        loop, websocket, gate, adapter, [], _SessionFailure("session-timeout")
    )
    handler_task = asyncio.create_task(_bounded_own(record, supervisors))
    try:
        while not adapter.close_entered.is_set():
            await asyncio.sleep(0)
        await adapter.close_entered.wait()
        # Deliver five external cancels while the close is in flight; each
        # delivery is yielded so the waiter absorbs exactly one.
        for index in range(5):
            handler_task.cancel(str(index))
            await asyncio.sleep(0)  # microtask yield, no fixed sleeps
            assert record.cancel_deliveries == index + 1
        _, pending = await asyncio.wait([handler_task], timeout=SAFETY_BOUND)
        assert not pending, "bounded handler never finished"
        try:
            handler_task.result()
            raise AssertionError("handler must re-raise the first cancellation")
        except asyncio.CancelledError as exc:
            assert exc.args == ("0",)  # FIRST captured signal, not a later one
        assert record.cancel_deliveries == 5
        assert record.released is False
        assert len(supervisors) == 1
        # Release the close: cleanup finishes under the supervisor, the
        # original close attempt settles, and the gate is released once.
        close_gate.set()
        await _await_completion(record.supervisor, "supervisor")
        assert record.cleanup_task is None
        assert record.workers_quiesced is True
        assert record.close_confirmed is True
        assert record.released is True
        assert gate.acquire() is True
        assert gate.acquire() is False
        gate.release()
        assert websocket.sent == [
            {"type": "session.error", "category": "session-timeout"},
        ]
        assert websocket.closes == [1000]
    finally:
        close_gate.set()
        await _settle_tasks([handler_task, record.supervisor, *record.wire])
