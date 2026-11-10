from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable, Sequence

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from super_agent_voice.adapter import (
    AudioChunk,
    FakeVoiceAdapter,
    Interrupted,
    TurnComplete,
)
from super_agent_voice.app import create_app
from super_agent_voice.config import VoiceConfig

TOKEN = "t" * 32
ORIGIN = "http://127.0.0.1:4200"

READY = {
    "type": "session.ready",
    "playbackEpoch": 0,
    "outputRateHz": 16000,
    "provider": "fake",
}


class ScriptedAdapter:
    """Deterministic streaming adapter driven by a fixed event script.

    The scripted provider output is independent of the input path: nothing
    enqueued by the client is echoed, and the event stream stays open (like
    a live provider) until close or cleanup cancellation.
    """

    def __init__(self, events: Sequence[object]) -> None:
        self._events = list(events)
        self.closed = False
        self.interruptions = 0
        self.enqueued: list[bytes] = []
        self._hold = asyncio.Event()

    async def start(self) -> None: ...

    async def enqueue_audio(self, audio: bytes) -> None:
        if self.closed:
            raise RuntimeError("adapter closed")
        if not isinstance(audio, bytes) or not audio or len(audio) % 2 or len(audio) > 32 * 1024:
            raise ValueError("invalid PCM frame")
        self.enqueued.append(audio)

    async def interrupt(self) -> None:
        self.interruptions += 1

    async def close(self) -> None:
        self.closed = True
        self._hold.set()

    async def events(self):
        for event in self._events:
            yield event
        await self._hold.wait()


class CloseRaisingOnceAdapter(ScriptedAdapter):
    """close() does its cleanup work, then raises once (T-3 shape).

    The second close attempt therefore settles cleanly, honoring the
    idempotent-close contract, and the supervisor may confirm closure on the
    retry only.
    """

    def __init__(self, events: Sequence[object]) -> None:
        super().__init__(events)
        self.close_calls = 0

    async def close(self) -> None:
        self.close_calls += 1
        await super().close()
        if self.close_calls == 1:
            raise RuntimeError("close exploded once")


class CloseAlwaysRaisingAdapter(ScriptedAdapter):
    """close() cleans up and raises every time (T-4 shape)."""

    def __init__(self, events: Sequence[object]) -> None:
        super().__init__(events)
        self.close_calls = 0
        # Set once the second attempt has settled exceptionally: the
        # supervisor's terminal state, observable from the test thread.
        self.attempts_ended = threading.Event()

    async def close(self) -> None:
        self.close_calls += 1
        try:
            await super().close()
            raise RuntimeError("close always explodes")
        finally:
            if self.close_calls >= 2:
                self.attempts_ended.set()


class HangingCloseAdapter(ScriptedAdapter):
    """close() blocks until the test releases it; suppression is emulated
    with shield inside the stub (addendum section 2), so the two handler /
    supervisor cancel requests never truncate the attempt (T-2, T-11)."""

    def __init__(self, events: Sequence[object]) -> None:
        super().__init__(events)
        self._close_gate: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.close_calls = 0

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        await super().start()

    async def close(self) -> None:
        self.close_calls += 1
        gate = self._close_gate
        if gate is None:
            gate = self._close_gate = asyncio.Event()
        while not gate.is_set():
            try:
                await asyncio.shield(gate.wait())
            except asyncio.CancelledError:
                continue
        await super().close()


def make_client(
    adapter: FakeVoiceAdapter | ScriptedAdapter | None = None,
    config: VoiceConfig | None = None,
    factory: Callable[[], object] | None = None,
) -> TestClient:
    if factory is not None:
        adapter_factory = factory
    elif adapter is not None:
        adapter_factory = lambda: adapter
    else:
        adapter_factory = FakeVoiceAdapter
    app = create_app(
        config if config is not None else VoiceConfig(local_token=TOKEN),
        adapter_factory,
    )
    return TestClient(app, base_url=ORIGIN)


def connect(client: TestClient):
    return client.websocket_connect(
        "/ws/voice",
        headers={"host": "127.0.0.1:8000", "origin": ORIGIN},
    )


def authenticate(websocket) -> None:
    websocket.send_json({"type": "session.auth", "token": TOKEN})
    assert websocket.receive_json() == READY


def test_health_is_key_free() -> None:
    with make_client() as client:
        # The in-process client host differs from the loopback server host, so
        # the allowed Host value is passed explicitly, as a real browser would.
        assert client.get("/health", headers={"host": "127.0.0.1:8000"}).json() == {
            "status": "ok",
            "provider": "fake",
        }


def test_health_rejects_foreign_host() -> None:
    with make_client() as client:
        assert (
            client.get("/health", headers={"host": "evil.example"}).status_code == 403
        )
        assert (
            client.get("/health", headers={"host": "127.0.0.1:8000"}).status_code == 200
        )


def test_only_one_active_session_is_allowed() -> None:
    with make_client() as client:
        with connect(client) as first:
            authenticate(first)
            # CT-05 keeps the gate before authentication: the second socket is
            # accepted only to be closed with 1013 while the slot is held.
            with connect(client) as second:
                with pytest.raises(WebSocketDisconnect) as rejected:
                    second.receive_json()
                assert rejected.value.code == 1013
            # Synchronize on the server's own close sequence instead of
            # assuming context exit finished the server cleanup: Stop ->
            # stopping state -> close frame, with the gate release strictly
            # before both messages.
            first.send_json({"type": "session.stop"})
            assert first.receive_json() == {"type": "session.state", "state": "stopping"}
            with pytest.raises(WebSocketDisconnect) as stopped_first:
                first.receive_json()
            assert stopped_first.value.code == 1000
        # The slot is released once the active session ends.
        with connect(client) as third:
            authenticate(third)


def test_total_session_budget_expires_with_fixed_error() -> None:
    settings = VoiceConfig(local_token=TOKEN, max_session_seconds=0.3)
    with make_client(config=settings) as client, connect(client) as websocket:
        authenticate(websocket)
        started = time.monotonic()
        assert websocket.receive_json() == {
            "type": "session.error",
            "category": "max-duration",
        }
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()
        assert closed.value.code == 1000
        assert time.monotonic() - started < 5


def test_idle_timeout_is_retained() -> None:
    settings = VoiceConfig(local_token=TOKEN, idle_timeout_seconds=0.2)
    with make_client(config=settings) as client, connect(client) as websocket:
        authenticate(websocket)
        started = time.monotonic()
        assert websocket.receive_json() == {
            "type": "session.error",
            "category": "session-timeout",
        }
        assert time.monotonic() - started < 5


def test_environment_requires_high_entropy_local_token(monkeypatch) -> None:
    monkeypatch.delenv("SUPER_AGENT_LOCAL_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        VoiceConfig.from_environment()
    monkeypatch.setenv("SUPER_AGENT_LOCAL_TOKEN", "short")
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        VoiceConfig.from_environment()


def test_rejects_bad_origin_and_token() -> None:
    with make_client() as client:
        with pytest.raises(WebSocketDisconnect) as denied:
            with client.websocket_connect(
                "/ws/voice",
                headers={
                    "host": "127.0.0.1:8000",
                    "origin": "https://evil.example",
                },
            ):
                pass
        assert denied.value.code == 1008

        with pytest.raises(WebSocketDisconnect) as bad_host:
            with client.websocket_connect(
                "/ws/voice",
                headers={"host": "evil.example", "origin": ORIGIN},
            ):
                pass
        assert bad_host.value.code == 1008

        with connect(client) as websocket:
            websocket.send_json({"type": "session.auth", "token": "wrong"})
            with pytest.raises(WebSocketDisconnect) as bad_token:
                websocket.receive_json()
            assert bad_token.value.code == 1008
        # A-02: a failed handshake does not throttle the next valid session.
        with connect(client) as after:
            authenticate(after)


def test_adapter_never_created_without_valid_auth() -> None:
    # Host/Origin are checked before accept, and the adapter is created only
    # after a valid session.auth; every denial below must show zero factory
    # calls and a valid session must show exactly one.
    created = 0

    def factory() -> FakeVoiceAdapter:
        nonlocal created
        created += 1
        return FakeVoiceAdapter()

    with make_client(factory=factory) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                "/ws/voice",
                headers={"host": "evil.example", "origin": ORIGIN},
            ):
                pass
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                "/ws/voice",
                headers={"host": "127.0.0.1:8000", "origin": "https://evil.example"},
            ):
                pass
        with connect(client) as websocket:
            websocket.send_json({"type": "session.auth", "token": "wrong"})
            with pytest.raises(WebSocketDisconnect):
                websocket.receive_json()
        assert created == 0

        with connect(client) as reopened:
            authenticate(reopened)
        assert created == 1


@pytest.mark.parametrize(
    "message",
    [
        "{not json",
        "[]",
        '"text"',
        '{"type": "capture.mute"}',
        '{"type": "session.auth"}',
        '{"type": "session.auth", "token": null}',
        '{"type": "session.auth", "token": 40}',
        pytest.param("x" * (65 * 1024), id="oversized-text"),
    ],
)
def test_invalid_auth_messages_fail_before_adapter(message: str) -> None:
    created = 0

    def factory() -> FakeVoiceAdapter:
        nonlocal created
        created += 1
        return FakeVoiceAdapter()

    with make_client(factory=factory) as client, connect(client) as websocket:
        websocket.send_text(message)
        # Some shapes fail with a redacted session.error before the close;
        # others only close. Either way the adapter factory stays untouched.
        try:
            first_message = websocket.receive_json()
        except WebSocketDisconnect:
            first_message = None
        if first_message is not None:
            assert first_message == {"type": "session.error", "category": "invalid-control"}
            with pytest.raises(WebSocketDisconnect):
                websocket.receive_json()
        assert created == 0


def test_total_budget_expiring_during_adapter_start_reports_max_duration() -> None:
    class SlowStartAdapter(FakeVoiceAdapter):
        async def start(self) -> None:
            await asyncio.sleep(5)

    adapter = SlowStartAdapter()
    settings = VoiceConfig(local_token=TOKEN, max_session_seconds=0.4)
    with make_client(adapter, settings) as client, connect(client) as websocket:
        websocket.send_json({"type": "session.auth", "token": TOKEN})
        assert websocket.receive_json() == {
            "type": "session.error",
            "category": "max-duration",
        }
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_abrupt_disconnect_completes_cleanup_and_releases_gate() -> None:
    # Regression for the cancellation-safety fix: the session coroutine is
    # externally cancelled while it runs cleanup, and the client's context
    # exit waits for that cleanup to finish (the shield loop), so the gate is
    # released and the adapter closed before any reconnect. Each session gets
    # a fresh adapter from the factory; the first instance must be closed by
    # the time the second authenticates.
    created: list[FakeVoiceAdapter] = []

    def factory() -> FakeVoiceAdapter:
        adapter = FakeVoiceAdapter()
        created.append(adapter)
        return adapter

    with make_client(factory=factory) as client:
        with connect(client) as first:
            authenticate(first)
        with connect(client) as second:
            authenticate(second)
    assert created

    assert created[0].closed


def test_failing_adapter_start_never_reaches_ready() -> None:
    class NoStartAdapter(FakeVoiceAdapter):
        async def start(self) -> None:
            raise RuntimeError("boot failed")

    adapter = NoStartAdapter()
    with make_client(adapter) as client, connect(client) as websocket:
        websocket.send_json({"type": "session.auth", "token": TOKEN})
        assert websocket.receive_json() == {
            "type": "session.error",
            "category": "provider-unavailable",
        }
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_silent_adapter_times_out_and_is_closed() -> None:
    # CT-07: with a silent event source and no input, the idle deadline must
    # still end the session and the adapter must be closed.
    adapter = FakeVoiceAdapter()
    settings = VoiceConfig(local_token=TOKEN, idle_timeout_seconds=0.2)
    with make_client(adapter, settings) as client, connect(client) as websocket:
        authenticate(websocket)
        started = time.monotonic()
        assert websocket.receive_json() == {
            "type": "session.error",
            "category": "session-timeout",
        }
        assert time.monotonic() - started < 5
    assert adapter.closed


def test_stop_with_silent_adapter_reports_stopping_and_closes() -> None:
    # CT-13 (backend side): Stop while the adapter emits nothing must still
    # arrive through receive as session.stop and close everything.
    adapter = FakeVoiceAdapter()
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_json({"type": "session.stop"})
        assert websocket.receive_json() == {"type": "session.state", "state": "stopping"}
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()
        assert closed.value.code == 1000
    assert adapter.closed


def test_auth_timeout_reports_session_timeout_and_releases_gate() -> None:
    # CT-04 (a): the explicit auth deadline yields its fixed category, and
    # the single-session slot is released for the next client. The follow-up
    # connection stays inside the open TestClient context; the error message
    # is sent after the gate release, so reaching it proves the release.
    settings = VoiceConfig(local_token=TOKEN, auth_timeout_seconds=0.25)
    with make_client(config=settings) as client:
        with connect(client) as websocket:
            started = time.monotonic()
            assert websocket.receive_json() == {
                "type": "session.error",
                "category": "session-timeout",
            }
            with pytest.raises(WebSocketDisconnect):
                websocket.receive_json()
            assert time.monotonic() - started < 5
        with connect(client) as reopened:
            authenticate(reopened)


def test_total_budget_expiring_during_auth_reports_max_duration() -> None:
    # CT-04 (b): the total session budget survives during auth; when it
    # expires first, the category is max-duration and the gate is released.
    settings = VoiceConfig(local_token=TOKEN, max_session_seconds=0.4, auth_timeout_seconds=2)
    with make_client(config=settings) as client:
        with connect(client) as websocket:
            assert websocket.receive_json() == {
                "type": "session.error",
                "category": "max-duration",
            }
        with connect(client) as reopened:
            authenticate(reopened)


def test_close_failure_keeps_original_category_and_releases_gate() -> None:
    # CT-03 as amended (teardown addendum revision 2, section 4.4): a close
    # that settles with an exception never overwrites the earlier redacted
    # category, and the slot is released only after the supervisor's single
    # idempotent retry confirms closure. The old "raising close releases the
    # gate immediately" expectation is superseded per T-3/T-4; the
    # category-preservation assertion is carried over verbatim.
    broken = CloseRaisingOnceAdapter([AudioChunk(data=b"\x01\x00\x01", rate_hz=16000)])
    with make_client(broken) as client:
        with connect(client) as websocket:
            authenticate(websocket)
            # Quarantine emits nothing on the wire, so the deferred redacted
            # category arrives only after the supervisor confirms closure.
            assert websocket.receive_json() == {
                "type": "session.error",
                "category": "invalid-audio",
            }
            with pytest.raises(WebSocketDisconnect) as closed:
                websocket.receive_json()
            assert closed.value.code == 1000
        # Exactly two attempts: the settled raise, then one idempotent retry.
        assert broken.close_calls == 2
        with connect(client) as reopened:
            authenticate(reopened)


def test_permanent_close_failure_holds_gate() -> None:
    # T-4 (explicit CT-03 amendment): a close that raises every time holds
    # the gate after the handler's bounded quarantine and the supervisor's
    # at-most-one retry; no automatic success or closure claim exists. At
    # most two exceptional settlements ever happen.
    broken = CloseAlwaysRaisingAdapter([AudioChunk(data=b"\x01\x00\x01", rate_hz=16000)])
    with make_client(broken) as client:
        with connect(client) as websocket:
            authenticate(websocket)
            # The supervisor settles both attempts while this socket stays
            # open; a thread event bridges the terminal state.
            assert broken.attempts_ended.wait(5.0)
            assert broken.close_calls == 2
        # Fail closed: the slot is retained, the next connection is refused.
        with connect(client) as refused:
            with pytest.raises(WebSocketDisconnect) as held:
                refused.receive_json()
            assert held.value.code == 1013


def test_hanging_close_is_bounded_and_gate_released_only_at_confirmed_close() -> None:
    # T-2: the close attempt is cancel-suppressing, so the handler's bounded
    # quarantine keeps the slot while no close is confirmed; once the test
    # releases the close (via the adapter-held loop reference), the original
    # attempt settles, the supervisor confirms it, releases the gate exactly
    # once, and the deferred redacted category is delivered. No overlapping
    # second close is ever started, and no provider-end state is claimed.
    settings = VoiceConfig(
        local_token=TOKEN, idle_timeout_seconds=0.2, teardown_seconds=0.35
    )
    hang = HangingCloseAdapter([])
    with make_client(hang, settings) as client:
        with connect(client) as first:
            authenticate(first)
            # The idle deadline fails the session; quarantine returns the
            # handler without emitting anything, and the slot stays held.
            # Wire silence is contractual here, so a short sleep is the only
            # honest separator for this cross-thread check: the handler must
            # be past the idle (0.2s) and teardown (0.35s) budget before the
            # gate is proven still held.
            time.sleep(0.8)
            with connect(client) as second:
                with pytest.raises(WebSocketDisconnect) as held:
                    second.receive_json()
                assert held.value.code == 1013
            assert hang.close_calls == 1
            assert hang._loop is not None
            hang._loop.call_soon_threadsafe(hang._close_gate.set)
            # The original attempt settles and the supervisor delivers the
            # deferred boundary: blocking receive, no polling.
            assert first.receive_json() == {
                "type": "session.error",
                "category": "session-timeout",
            }
            with pytest.raises(WebSocketDisconnect):
                first.receive_json()
        assert hang.close_calls == 1
        with connect(client) as reopened:
            authenticate(reopened)


def test_empty_audio_chunk_fails_closed_and_releases_gate() -> None:
    # T-1 (review gap): an empty AudioChunk is invalid audio, not the
    # zero-yield events-end variant: the session fails closed with the fixed
    # redacted category, no fabricated turn.complete arrives, teardown
    # quiesces, and the gate is released exactly once.
    adapter = ScriptedAdapter([AudioChunk(data=b"", rate_hz=16000)])
    with make_client(adapter) as client:
        with connect(client) as websocket:
            authenticate(websocket)
            assert websocket.receive_json() == {
                "type": "session.error",
                "category": "invalid-audio",
            }
            with pytest.raises(WebSocketDisconnect) as closed:
                websocket.receive_json()
            assert closed.value.code == 1000
        with connect(client) as followup:
            authenticate(followup)
        assert adapter.closed


def test_session_control_overflow_teardown_bounded_and_gate_released() -> None:
    # T-5: controls past the control bound fail the whole session closed
    # (_SessionFailure("session-failed")); teardown quiesces quickly, the
    # boundary is delivered first, and the gate is released for a follow-up.
    class BurstAdapter(ScriptedAdapter):
        def __init__(self) -> None:
            super().__init__([])
            self.burst = asyncio.Event()

        async def enqueue_audio(self, audio: bytes) -> None:
            await super().enqueue_audio(audio)
            self.burst.set()

        async def events(self):
            await self.burst.wait()
            # No await between yields: the producer fills the control queue
            # before the sender can drain it, independently of thread timing.
            for _ in range(33):
                yield TurnComplete()
            await self._hold.wait()

    adapter = BurstAdapter()
    created = 0

    def factory():
        nonlocal created
        created += 1
        return adapter if created == 1 else FakeVoiceAdapter()

    settings = VoiceConfig(local_token=TOKEN, idle_timeout_seconds=1)
    with make_client(config=settings, factory=factory) as client:
        with connect(client) as websocket:
            authenticate(websocket)
            messages: list[dict[str, object]] = []
            websocket.send_bytes(b"\x01\x00")
            # At most 32 queued controls precede the final failure. A wrong
            # category or missing boundary fails rather than looping forever.
            for _ in range(33):
                message = websocket.receive_json()
                messages.append(message)
                if message.get("type") == "session.error":
                    break
            assert messages[-1] == {
                "type": "session.error",
                "category": "session-failed",
            }
            # No stopping status exists alongside a failure, and no status is
            # delivered after the boundary: the teardown sequence is single.
            assert not any(
                message.get("type") == "session.state"
                and message.get("state") == "stopping"
                for message in messages
            )
            with pytest.raises(WebSocketDisconnect) as closed:
                websocket.receive_json()
            assert closed.value.code == 1000
        with connect(client) as followup:
            authenticate(followup)
        assert adapter.closed


@pytest.mark.parametrize(
    "bad_value",
    [0, -1.0, float("nan"), float("inf"), True, False, "2", None],
)
def test_teardown_config_validity(bad_value: object) -> None:
    # T-12: the teardown budget must be a real, finite, strictly positive
    # number; create_app fails closed on everything else with the explicit
    # config-error style, and the default passes.
    settings = VoiceConfig(local_token=TOKEN, teardown_seconds=bad_value)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="teardown_seconds"):
        create_app(settings, FakeVoiceAdapter)
    with make_client() as client:
        assert client.get("/health", headers={"host": "127.0.0.1:8000"}).json() == {
            "status": "ok",
            "provider": "fake",
        }


def test_independent_output_without_input_delivers_ordered_audio_and_turn() -> None:
    # CT-10: scripted provider output arrives with no input at all.
    adapter = ScriptedAdapter([
        AudioChunk(data=b"\x01\x00\x02\x00", rate_hz=24000),
        TurnComplete(),
    ])
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        assert websocket.receive_json() == {
            "type": "audio.chunk",
            "playbackEpoch": 0,
            "rateHz": 24000,
            "channels": 1,
            "format": "pcm16",
        }
        assert websocket.receive_bytes() == b"\x01\x00\x02\x00"
        assert websocket.receive_json() == {"type": "turn.complete", "playbackEpoch": 0}
        websocket.send_json({"type": "session.stop"})
        assert websocket.receive_json() == {"type": "session.state", "state": "stopping"}
        assert adapter.enqueued == []


@pytest.mark.parametrize(
    ("chunk", "category"),
    [
        (AudioChunk(data=b"\x01\x00\x01", rate_hz=16000), "invalid-audio"),
        (AudioChunk(data=b"x" * (32 * 1024 + 2), rate_hz=16000), "invalid-audio"),
        (AudioChunk(data=b"\x01\x00\x02\x00", rate_hz=22050), "invalid-audio"),
    ],
)
def test_invalid_adapter_output_fails_the_session(chunk, category) -> None:
    # CT-08 (adapter side): odd, oversized, and unknown-rate output frames
    # all end the session with one fixed category.
    adapter = ScriptedAdapter([chunk])
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        assert websocket.receive_json() == {
            "type": "session.error",
            "category": category,
        }
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_invalid_browser_frames_fail_closed() -> None:
    # CT-08 (browser side): odd and empty frames are rejected with 1009.
    for bad in (b"\x01\x00\x01", b""):
        with make_client() as client, connect(client) as websocket:
            authenticate(websocket)
            websocket.send_bytes(bad)
            assert websocket.receive_json() == {
                "type": "session.error",
                "category": "invalid-audio",
            }
            with pytest.raises(WebSocketDisconnect) as closed:
                websocket.receive_json()
            assert closed.value.code == 1009


def test_adapter_error_is_redacted() -> None:
    # CT-09: a scripted events() raising after start() ends the session with
    # the fixed category only; no provider detail is returned anywhere.
    class RaisingEventsAdapter(FakeVoiceAdapter):
        async def events(self):
            raise RuntimeError("SENTINEL provider detail")
            yield  # pragma: no cover - keeps this an async generator

    adapter = RaisingEventsAdapter()
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        response = websocket.receive_json()
        assert response == {"type": "session.error", "category": "session-failed"}
        assert "SENTINEL" not in str(response)
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()
        assert closed.value.code == 1000
    assert adapter.closed


def test_fake_audio_interrupt_and_stop() -> None:
    adapter = FakeVoiceAdapter()
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        sample = b"\x01\x00\x02\x00"
        websocket.send_bytes(sample)
        assert websocket.receive_json() == {
            "type": "audio.chunk",
            "playbackEpoch": 0,
            "rateHz": 16000,
            "channels": 1,
            "format": "pcm16",
        }
        assert websocket.receive_bytes() == sample
        assert websocket.receive_json() == {
            "type": "turn.complete",
            "playbackEpoch": 0,
        }

        websocket.send_json({"type": "playback.interrupt"})
        assert websocket.receive_json() == {
            "type": "playback.interrupted",
            "playbackEpoch": 1,
            "source": "local",
        }
        assert adapter.interruptions == 1

        # Audio enqueued after the interrupt belongs to the new epoch.
        websocket.send_bytes(sample)
        assert websocket.receive_json() == {
            "type": "audio.chunk",
            "playbackEpoch": 1,
            "rateHz": 16000,
            "channels": 1,
            "format": "pcm16",
        }
        assert websocket.receive_bytes() == sample
        assert websocket.receive_json() == {
            "type": "turn.complete",
            "playbackEpoch": 1,
        }

        websocket.send_json({"type": "session.stop"})
        assert websocket.receive_json() == {
            "type": "session.state",
            "state": "stopping",
        }
    assert adapter.closed


def test_provider_interrupt_advances_the_epoch() -> None:
    adapter = ScriptedAdapter([
        Interrupted(),
        AudioChunk(data=b"\x03\x00\x04\x00", rate_hz=16000),
        TurnComplete(),
    ])
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        assert websocket.receive_json() == {
            "type": "playback.interrupted",
            "playbackEpoch": 1,
            "source": "provider",
        }
        assert websocket.receive_json() == {
            "type": "audio.chunk",
            "playbackEpoch": 1,
            "rateHz": 16000,
            "channels": 1,
            "format": "pcm16",
        }
        assert websocket.receive_bytes() == b"\x03\x00\x04\x00"
        assert websocket.receive_json() == {"type": "turn.complete", "playbackEpoch": 1}


def test_muted_audio_is_not_sent_to_adapter() -> None:
    adapter = FakeVoiceAdapter()
    calls = 0
    original = adapter.enqueue_audio

    async def counted(audio: bytes):
        nonlocal calls
        calls += 1
        return await original(audio)

    adapter.enqueue_audio = counted  # type: ignore[method-assign]
    with make_client(adapter) as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_json({"type": "capture.mute"})
        assert websocket.receive_json() == {"type": "session.state", "muted": True}
        websocket.send_bytes(b"\x00\x00")
        assert calls == 0
        websocket.send_json({"type": "capture.unmute"})
        assert websocket.receive_json() == {"type": "session.state", "muted": False}
        websocket.send_bytes(b"\x00\x00")
        assert websocket.receive_json() == {
            "type": "audio.chunk",
            "playbackEpoch": 0,
            "rateHz": 16000,
            "channels": 1,
            "format": "pcm16",
        }
        assert calls == 1


def test_invalid_control_and_oversized_audio_fail_closed() -> None:
    with make_client() as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_text('{"type":"unknown"}')
        assert websocket.receive_json() == {
            "type": "session.error",
            "category": "invalid-control",
        }
        with pytest.raises(WebSocketDisconnect) as invalid_control:
            websocket.receive_json()
        assert invalid_control.value.code == 1000

    with make_client() as client, connect(client) as websocket:
        authenticate(websocket)
        websocket.send_bytes(b"x" * (32 * 1024 + 1))
        # The fixed category is sent before the 1009 close; consume it so the
        # redacted error and the closure are both observed.
        assert websocket.receive_json() == {
            "type": "session.error",
            "category": "invalid-audio",
        }
        with pytest.raises(WebSocketDisconnect) as oversized:
            websocket.receive_json()
        assert oversized.value.code == 1009
