"""Offline tests for the Gemini Live adapter. No network, real key, or audio."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace as NS

import pytest

from super_agent_voice.adapter import AdapterError, AudioChunk, Interrupted, TurnComplete
from super_agent_voice.gemini_adapter import GeminiLiveAdapter, classify


class FakeSession:
    """Stands in for an SDK live session: scripted turns, recorded sends."""

    def __init__(self, turns: list[list[object]] | None = None, send_error: Exception | None = None) -> None:
        self.turns = list(turns or [])
        self.sent: list[dict] = []
        self.send_error = send_error
        self.closed = False
        self.more = asyncio.Event()

    async def send_realtime_input(self, **kwargs) -> None:
        if self.send_error:
            raise self.send_error
        self.sent.append(kwargs)

    async def receive(self):
        if not self.turns:
            await self.more.wait()  # an idle provider: nothing until closed
            return
        for response in self.turns.pop(0):
            if isinstance(response, Exception):
                raise response
            yield response


class FakeConnect:
    def __init__(self, session: FakeSession | None = None, error: Exception | None = None) -> None:
        self.session = session
        self.error = error
        self.exit_gate: asyncio.Event | None = None
        self.enter_gate: asyncio.Event | None = None
        self.handles: list[str | None] = []

    def __call__(self, handle: str | None = None):
        outer = self
        self.handles.append(handle)

        class Context:
            async def __aenter__(self):
                if outer.enter_gate:
                    await outer.enter_gate.wait()
                if outer.error:
                    raise outer.error
                return outer.session

            async def __aexit__(self, *exc):
                if outer.exit_gate:
                    await outer.exit_gate.wait()
                outer.session.closed = True

        return Context()


MODEL = "test-model"


def audio(data: bytes) -> NS:
    return NS(server_content=NS(model_turn=NS(parts=[NS(inline_data=NS(data=data))]), interrupted=False, turn_complete=False), go_away=None)


def flag(**kwargs) -> NS:
    content = {"model_turn": None, "interrupted": False, "turn_complete": False}
    content.update(kwargs)
    return NS(server_content=NS(**content), go_away=None)


def make(session: FakeSession, **kwargs) -> GeminiLiveAdapter:
    return GeminiLiveAdapter(MODEL, connect=FakeConnect(session), blob=lambda data: ("blob", data), **kwargs)


async def take(adapter: GeminiLiveAdapter, count: int) -> list:
    out = []
    async def collect():
        async for event in adapter.events():
            out.append(event)
            if len(out) == count:
                return
    await asyncio.wait_for(collect(), 2)
    return out


async def sent(session: FakeSession, count: int) -> None:
    async def poll():
        while len(session.sent) < count:
            await asyncio.sleep(0)
    await asyncio.wait_for(poll(), 2)


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("enterprise", ["false", "true"])
def test_sdk_live_destination_stays_on_developer_api(monkeypatch, enterprise) -> None:
    from urllib.parse import urlsplit

    from google.genai import live

    monkeypatch.setenv("GOOGLE_GENAI_USE_ENTERPRISE", enterprise)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", "https://gemini.invalid")
    monkeypatch.setenv("GOOGLE_VERTEX_BASE_URL", "https://vertex.invalid")
    destinations = []

    def refuse_network(uri, **_):
        destination = urlsplit(uri)
        destinations.append((destination.scheme, destination.hostname, destination.path))
        raise OSError

    monkeypatch.setattr(live, "ws_connect", refuse_network)
    adapter = GeminiLiveAdapter(MODEL, api_key="offline-test-placeholder")
    with pytest.raises(AdapterError, match="^provider-unavailable$"):
        run(adapter.start())
    assert destinations == [(
        "wss",
        "generativelanguage.googleapis.com",
        "/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent",
    )]


def test_maps_audio_interrupt_and_turn_complete_in_order() -> None:
    async def scenario():
        session = FakeSession([[audio(b"\x01\x00"), flag(interrupted=True)], [audio(b"\x02\x00"), flag(turn_complete=True)]])
        adapter = make(session)
        await adapter.start()
        events = await take(adapter, 4)
        await adapter.close()
        return events, session

    events, session = run(scenario())
    assert events == [AudioChunk(b"\x01\x00", 24000), Interrupted(), AudioChunk(b"\x02\x00", 24000), TurnComplete()]
    assert session.closed


def test_send_path_uses_blob_and_ends_stream_once_on_mute() -> None:
    async def scenario():
        session = FakeSession()
        adapter = make(session)
        await adapter.start()
        await adapter.enqueue_audio(b"\x05\x00")
        await sent(session, 1)
        await adapter.end_audio_stream()
        await adapter.end_audio_stream()  # second call is a no-op
        await sent(session, 2)
        await adapter.close()
        await adapter.close()  # idempotent
        return session.sent

    assert run(scenario()) == [{"audio": ("blob", b"\x05\x00")}, {"audio_stream_end": True}]


def test_go_away_and_silent_provider_end_fail_closed() -> None:
    async def ended(turn: list[object]) -> str:
        adapter = make(FakeSession([turn]))
        await adapter.start()
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)
        await adapter.close()
        return error.value.category

    for turn in (
        [NS(server_content=None, go_away=NS(time_left="5s"))],
        [],  # the provider ends the stream without sending anything
    ):
        assert run(ended(turn)) == "provider-session-ended"


def test_cancelled_close_is_not_confirmed_until_the_session_is_released() -> None:
    async def scenario():
        session = FakeSession()
        connect = FakeConnect(session)
        connect.exit_gate = asyncio.Event()
        adapter = GeminiLiveAdapter(MODEL, connect=connect, blob=bytes)
        await adapter.start()
        first = asyncio.create_task(adapter.close())
        await asyncio.sleep(0)
        first.cancel()
        retry = asyncio.create_task(adapter.close())
        await asyncio.sleep(0.05)
        pending_while_held = not retry.done() and not session.closed
        connect.exit_gate.set()
        await asyncio.wait_for(retry, 2)
        return pending_while_held, session.closed

    assert run(scenario()) == (True, True)


def test_failed_sdk_exit_is_not_confirmed_on_close_or_retry() -> None:
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def broken_exit():
        yield FakeSession()
        raise RuntimeError("SENTINEL provider detail")

    async def scenario():
        adapter = GeminiLiveAdapter(MODEL, connect=broken_exit, blob=bytes)
        await adapter.start()
        for _ in range(2):
            with pytest.raises(AdapterError, match="^session-failed$"):
                await adapter.close()

    run(scenario())


def test_ack_for_an_earlier_turn_does_not_satisfy_a_new_interrupt() -> None:
    async def scenario():
        session = FakeSession([[audio(b"\x01\x00")]])
        adapter = make(session, interrupt_timeout=0.05)
        await adapter.start()
        await take(adapter, 1)
        await adapter.interrupt()
        adapter._map(flag(turn_complete=True).server_content)
        assert await take(adapter, 1) == [TurnComplete()]
        adapter._map(audio(b"\x02\x00").server_content)
        assert await take(adapter, 1) == [AudioChunk(b"\x02\x00", 24000)]
        await adapter.interrupt()  # never acknowledged
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)
        await adapter.close()
        return error.value.category

    assert run(scenario()) == "session-failed"


def test_interrupt_during_turn_without_provider_ack_fails_closed() -> None:
    async def scenario():
        adapter = make(FakeSession([[audio(b"\x01\x00")]]), interrupt_timeout=0.05)
        await adapter.start()
        assert await take(adapter, 1) == [AudioChunk(b"\x01\x00", 24000)]
        await adapter.interrupt()
        await adapter.interrupt()  # a second interrupt does not add another timer
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)
        await adapter.close()
        return error.value.category

    assert run(scenario()) == "session-failed"


def test_interrupt_with_no_turn_in_flight_is_local_only() -> None:
    async def scenario():
        session = FakeSession()
        adapter = make(session, interrupt_timeout=0.05)
        await adapter.start()
        await adapter.interrupt()
        await asyncio.sleep(0.15)
        healthy = adapter._events.empty()
        await adapter.close()
        return healthy, session.sent

    healthy, sent = run(scenario())
    assert healthy and sent == []


def test_stream_end_is_ordered_after_queued_audio_and_needs_open_stream() -> None:
    async def scenario():
        session = FakeSession()
        adapter = make(session)
        await adapter.start()
        await adapter.end_audio_stream()  # nothing sent yet: no stream to end
        await adapter.enqueue_audio(b"\x01\x00")
        await adapter.enqueue_audio(b"\x02\x00")
        await adapter.end_audio_stream()
        await sent(session, 3)
        await adapter.close()
        return session.sent

    assert run(scenario()) == [
        {"audio": ("blob", b"\x01\x00")},
        {"audio": ("blob", b"\x02\x00")},
        {"audio_stream_end": True},
    ]


def test_full_input_queue_drops_the_oldest_frames() -> None:
    async def scenario():
        session = FakeSession()
        adapter = make(session)
        for index in range(66):  # two more than the queue holds, before any send
            await adapter.enqueue_audio(bytes([index, 0]))
        await adapter.start()
        await sent(session, 64)
        await adapter.close()
        return session.sent

    frames = run(scenario())
    assert len(frames) == 64 and frames[0] == {"audio": ("blob", b"\x02\x00")}


def test_close_while_connecting_releases_the_late_session() -> None:
    async def scenario():
        session = FakeSession()
        connect = FakeConnect(session)
        connect.enter_gate = asyncio.Event()
        adapter = GeminiLiveAdapter(MODEL, connect=connect, blob=bytes)
        starting = asyncio.create_task(adapter.start())
        await asyncio.sleep(0)
        await adapter.close()
        connect.enter_gate.set()
        with pytest.raises(AdapterError) as error:
            await starting
        return error.value.category, session.closed, adapter._tasks

    assert run(scenario()) == ("session-failed", True, [])


def test_same_tick_ack_then_interrupt_still_arms_a_timer() -> None:
    async def scenario():
        adapter = make(FakeSession([[audio(b"\x01\x00")]]), interrupt_timeout=0.05)
        await adapter.start()
        await take(adapter, 1)
        await adapter.interrupt()
        await asyncio.sleep(0)  # the first timer is now waiting on its event
        # No await between these: the first timer has not yet seen its ack.
        adapter._map(flag(turn_complete=True).server_content)
        adapter._map(audio(b"\x02\x00").server_content)
        await adapter.interrupt()
        assert await take(adapter, 1) == [TurnComplete()]
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)  # the queued audio was invalidated
        await adapter.close()
        return error.value.category

    assert run(scenario()) == "session-failed"


def test_start_after_close_is_refused() -> None:
    async def scenario():
        session = FakeSession()
        adapter = make(session)
        await adapter.close()
        with pytest.raises(AdapterError, match="session-failed"):
            await adapter.start()
        return session.sent, adapter._tasks

    assert run(scenario()) == ([], [])


def test_start_failures_map_to_fixed_categories() -> None:
    def start_error(error: Exception) -> str:
        async def scenario():
            adapter = GeminiLiveAdapter(MODEL, connect=FakeConnect(FakeSession(), error=error))
            with pytest.raises(AdapterError) as raised:
                await adapter.start()
            return raised.value.category
        return run(scenario())

    assert start_error(OSError("dns SENTINEL")) == "provider-unavailable"
    assert start_error(NS_error(code=429)) == "provider-limits"
    assert start_error(NS_error(code=404)) == "provider-unsupported"
    assert start_error(NS_error(code=1008)) == "provider-unsupported"
    assert start_error(ValueError("SENTINEL")) == "session-failed"


def test_send_error_is_redacted_to_category() -> None:
    async def scenario():
        adapter = make(FakeSession(send_error=ConnectionResetError("SENTINEL")))
        await adapter.start()
        await adapter.enqueue_audio(b"\x00\x00")
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)
        await adapter.close()
        return error.value

    error = run(scenario())
    assert error.category == "provider-unavailable"
    assert "SENTINEL" not in str(error)


def test_requires_key_or_injected_connection() -> None:
    with pytest.raises(AdapterError) as error:
        GeminiLiveAdapter(MODEL)
    assert error.value.category == "provider-unavailable"
    assert classify(AdapterError("provider-limits")) == "provider-limits"


def NS_error(**attrs) -> Exception:
    error = RuntimeError("SENTINEL")
    for key, value in attrs.items():
        setattr(error, key, value)
    return error


# --- provider audio sizing -------------------------------------------------

LIMIT = 16 * 1024  # the adapter's chunk cap, half the app's 32 KiB frame limit


def test_large_and_odd_provider_chunks_become_valid_frames_in_order() -> None:
    big = bytes(range(256)) * 400  # 100 KiB
    odd = b"\x01\x02\x03\x04\x05"  # 5 bytes: one is carried into the next chunk
    tail = b"\x06\x07\x08"  # carry + 3 bytes is even again
    dangling = b"\x09\x0a\x0b"  # an odd byte left at turn end is dropped

    async def scenario():
        turn = [audio(big), audio(odd), audio(tail), audio(dangling), flag(turn_complete=True)]
        adapter = make(FakeSession([turn]))
        await adapter.start()
        events = []
        async for event in adapter.events():
            events.append(event)
            if isinstance(event, TurnComplete):
                break
        await adapter.close()
        return events

    chunks = [e.data for e in run(scenario()) if isinstance(e, AudioChunk)]
    assert all(0 < len(c) <= LIMIT and len(c) % 2 == 0 for c in chunks)
    sent = big + odd + tail + dangling
    assert b"".join(chunks) == sent[:-1]  # only the final stray byte is dropped


def test_odd_byte_does_not_carry_into_the_next_turn() -> None:
    async def scenario():
        turn_one = [audio(b"\x01\x02\x03"), flag(turn_complete=True)]
        adapter = make(FakeSession([turn_one, [audio(b"\x04\x05"), flag(turn_complete=True)]]))
        await adapter.start()
        events = await take(adapter, 4)
        await adapter.close()
        return events

    assert run(scenario()) == [
        AudioChunk(b"\x01\x02", 24000), TurnComplete(), AudioChunk(b"\x04\x05", 24000), TurnComplete(),
    ]


# --- session resumption ----------------------------------------------------

HANDLE = "resume-handle-SENTINEL"


def update(handle: str, resumable: bool = True) -> NS:
    return NS(session_resumption_update=NS(new_handle=handle, resumable=resumable), go_away=None, server_content=None)


def go_away() -> NS:
    return NS(server_content=None, go_away=NS(time_left="5s"))


class ResumeConnect:
    """Hands out sessions in order; an Exception entry makes that connect fail."""

    def __init__(self, *sessions: FakeSession | Exception) -> None:
        self.sessions = list(sessions)
        self.handles: list[str | None] = []
        self.resume_gate: asyncio.Event | None = None

    def __call__(self, handle: str | None = None):
        self.handles.append(handle)
        outer = self
        entry = self.sessions.pop(0)

        class Context:
            async def __aenter__(self):
                if handle is not None and outer.resume_gate:
                    await outer.resume_gate.wait()
                if isinstance(entry, Exception):
                    raise entry
                return entry

            async def __aexit__(self, *exc):
                if not isinstance(entry, Exception):
                    entry.closed = True

        return Context()


def resumable(connect: ResumeConnect) -> GeminiLiveAdapter:
    return GeminiLiveAdapter(MODEL, connect=connect, blob=lambda data: ("blob", data))


def test_go_away_then_close_resumes_with_the_latest_handle(caplog) -> None:
    async def scenario():
        first = FakeSession([[update("old-handle"), update(HANDLE), audio(b"\x01\x00"), go_away(), update("", False)]])
        first.turns.append([OSError("server closed")])
        second = FakeSession([[audio(b"\x02\x00"), flag(turn_complete=True)]])
        connect = ResumeConnect(first, second)
        adapter = resumable(connect)
        await adapter.start()
        events = await take(adapter, 4)
        await adapter.close()
        return events, connect, first, second

    with caplog.at_level("DEBUG"):
        events, connect, first, second = run(scenario())
    # The half-spoken reply is ended for the browser, then the resumed session continues.
    assert events == [AudioChunk(b"\x01\x00", 24000), Interrupted(), AudioChunk(b"\x02\x00", 24000), TurnComplete()]
    assert connect.handles == [None, HANDLE]  # a non-resumable update never replaces the handle
    assert first.closed and second.closed
    assert HANDLE not in caplog.text and HANDLE not in repr(events)


def test_queued_input_is_delivered_to_the_resumed_session() -> None:
    async def scenario():
        first = FakeSession([[update(HANDLE), audio(b"\x01\x00"), OSError("closed")]], send_error=ConnectionResetError())
        second = FakeSession()
        connect = ResumeConnect(first, second)
        connect.resume_gate = asyncio.Event()  # hold the reconnect while a frame is sent
        adapter = resumable(connect)
        await adapter.start()
        await take(adapter, 1)
        await adapter.enqueue_audio(b"\x07\x00")
        await asyncio.sleep(0.1)  # the send fails on the dead session and waits
        connect.resume_gate.set()
        await sent(second, 1)
        await adapter.close()
        return second.sent

    assert run(scenario()) == [{"audio": ("blob", b"\x07\x00")}]


def test_failed_reconnect_fails_closed_without_the_handle() -> None:
    async def scenario(second):
        first = FakeSession([[update(HANDLE), go_away()], []])  # then the stream ends
        adapter = resumable(ResumeConnect(first, second))
        await adapter.start()
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)
        await adapter.close()
        return error.value

    error = run(scenario(OSError(f"SENTINEL {HANDLE}")))
    assert error.category == "provider-unavailable"  # the reconnect's own failure, not a generic end
    assert HANDLE not in str(error) and "SENTINEL" not in str(error)


def test_without_a_resumable_handle_go_away_fails_closed() -> None:
    async def scenario():
        connect = ResumeConnect(FakeSession([[update("", False), go_away()]]))
        adapter = resumable(connect)
        await adapter.start()
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)
        await adapter.close()
        return error.value.category, connect.handles

    assert run(scenario()) == ("provider-session-ended", [None])


def test_reconnects_are_capped_per_session(monkeypatch) -> None:
    import super_agent_voice.gemini_adapter as module

    monkeypatch.setattr(module, "MAX_RECONNECTS", 2)

    async def scenario():
        ending = lambda: FakeSession([[update(HANDLE)], []])  # noqa: E731
        connect = ResumeConnect(ending(), ending(), ending(), ending())
        adapter = resumable(connect)
        await adapter.start()
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)
        await adapter.close()
        return error.value.category, connect.handles

    assert run(scenario()) == ("provider-session-ended", [None, HANDLE, HANDLE])


def test_limit_and_unsupported_closes_are_not_retried() -> None:
    async def scenario():
        connect = ResumeConnect(FakeSession([[update(HANDLE), NS_error(code=429)]]), FakeSession())
        adapter = resumable(connect)
        await adapter.start()
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)
        await adapter.close()
        return error.value.category, connect.handles

    assert run(scenario()) == ("provider-limits", [None])


def test_sdk_config_enables_resumption_and_compression(monkeypatch) -> None:
    from google.genai import live

    from super_agent_voice.gemini_adapter import _sdk_connect

    captured: dict = {}
    monkeypatch.setattr(live.AsyncLive, "connect", lambda self, **kwargs: captured.update(kwargs))
    _sdk_connect("offline-test-placeholder", MODEL)(None)
    assert captured["config"].session_resumption.handle is None
    assert captured["config"].context_window_compression.sliding_window is not None
    _sdk_connect("offline-test-placeholder", MODEL)(HANDLE)
    assert captured["config"].session_resumption.handle == HANDLE


def test_a_free_tier_session_refusal_is_reported_as_a_limit() -> None:
    class APIError(Exception):
        code = 1011

    assert classify(APIError("1011 None. Resource has been exhausted (e.g. check quota).")) == "provider-limits"
    assert classify(APIError("1011 internal error")) == "session-failed"



def test_a_quota_refusal_on_reconnect_is_reported_as_a_limit() -> None:
    class APIError(Exception):
        code = 1011

    async def scenario():
        first = FakeSession([[update(HANDLE), go_away()], []])
        adapter = resumable(ResumeConnect(first, APIError("1011 None. Resource has been exhausted")))
        await adapter.start()
        with pytest.raises(AdapterError) as error:
            await take(adapter, 1)
        await adapter.close()
        return error.value

    assert run(scenario()).category == "provider-limits"
