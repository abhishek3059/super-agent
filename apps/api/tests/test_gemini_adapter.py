"""Offline tests for the Gemini Live adapter. No SDK, key, network, or audio."""
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

    def __call__(self):
        outer = self

        class Context:
            async def __aenter__(self):
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
        [flag(go_away=NS(time_left="5s"))],
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


def test_ack_for_an_earlier_turn_does_not_satisfy_a_new_interrupt() -> None:
    async def scenario():
        session = FakeSession([[audio(b"\x01\x00"), flag(turn_complete=True)], [audio(b"\x02\x00")]])
        adapter = make(session, interrupt_timeout=0.05)
        await adapter.start()
        await take(adapter, 1)
        await adapter.interrupt()  # acknowledged by the first turn completing
        await take(adapter, 2)  # TurnComplete, then the second turn's audio
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
