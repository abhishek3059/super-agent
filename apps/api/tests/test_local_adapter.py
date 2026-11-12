import asyncio
import struct

import pytest

from super_agent_voice import local_adapter
from super_agent_voice.adapter import AdapterError, AudioChunk, Interrupted, TurnComplete
from super_agent_voice.app import _adapter_from_environment
from super_agent_voice.local_adapter import LocalVoiceAdapter

LOUD = struct.pack("<2048h", *([8000, -8000] * 1024))  # 128 ms at 16 kHz
QUIET = bytes(4096)


def make(reply_text="Hello there. How can I help?", *, heard="what time is it", gate=None, **options):
    seen = []

    async def transcribe(pcm):
        seen.append(("pcm", len(pcm)))
        return heard

    async def reply(messages):
        seen.append(("messages", [dict(message) for message in messages]))
        for word in reply_text.split(" "):
            if gate:
                await gate.wait()
            yield word + " "

    async def synthesize(text):
        seen.append(("say", text))
        return bytes(24000)  # 0.5 s of silence at 24 kHz

    adapter = LocalVoiceAdapter(transcribe, reply, synthesize, pace_output=False, **options)
    return adapter, seen


async def speak(adapter, loud_frames=4, quiet_frames=7):
    for frame in [LOUD] * loud_frames + [QUIET] * quiet_frames:
        await adapter.enqueue_audio(frame)


async def collect(adapter, until=TurnComplete):
    events = []
    async for event in adapter.events():
        events.append(event)
        if isinstance(event, until):
            return events


def run(coroutine):
    return asyncio.run(asyncio.wait_for(coroutine, timeout=5))


def test_utterance_becomes_sentence_by_sentence_speech_then_turn_complete():
    async def scenario():
        adapter, seen = make()
        await adapter.start()
        await speak(adapter)
        events = await collect(adapter)
        await adapter.close()
        return events, seen

    events, seen = run(scenario())
    assert [text for kind, text in seen if kind == "say"] == ["Hello there.", "How can I help?"]
    audio = [event for event in events if isinstance(event, AudioChunk)]
    assert audio and all(e.rate_hz == 24000 and len(e.data) <= 32 * 1024 and len(e.data) % 2 == 0 for e in audio)
    assert sum(len(event.data) for event in audio) == 2 * 24000
    assert isinstance(events[-1], TurnComplete)
    messages = next(value for kind, value in seen if kind == "messages")
    assert messages[0]["role"] == "system" and messages[-1] == {"role": "user", "content": "what time is it"}


def test_silence_and_short_noise_start_no_turn():
    async def scenario():
        adapter, seen = make()
        await adapter.start()
        for _ in range(40):
            await adapter.enqueue_audio(QUIET)
        await speak(adapter, loud_frames=1)  # 128 ms click, below the minimum
        await asyncio.sleep(0)
        await adapter.close()
        return seen

    assert run(scenario()) == []


def test_empty_transcript_produces_no_reply():
    async def scenario():
        adapter, seen = make(heard="  ")
        await adapter.start()
        await speak(adapter)
        await asyncio.sleep(0.05)
        await adapter.close()
        return [kind for kind, _ in seen], [event async for event in adapter.events()]

    assert run(scenario()) == (["pcm"], [])


def test_interrupt_stops_the_reply_and_forgets_it():
    async def scenario():
        gate = asyncio.Event()
        adapter, seen = make("One. Two. Three. Four.", gate=gate)
        await adapter.start()
        await speak(adapter)
        await asyncio.sleep(0.05)  # reply is blocked on the gate
        await adapter.interrupt()
        gate.set()
        await asyncio.sleep(0.05)
        said = [text for kind, text in seen if kind == "say"]
        # The next turn must not carry the interrupted exchange in its history.
        await speak(adapter)
        events = await collect(adapter)
        await adapter.close()
        return said, events, [value for kind, value in seen if kind == "messages"][-1]

    said, events, messages = run(scenario())
    assert said == []
    assert isinstance(events[-1], TurnComplete)
    assert [message["role"] for message in messages] == ["system", "user"]


def test_new_utterance_during_a_reply_emits_interrupted():
    async def scenario():
        gate = asyncio.Event()
        adapter, _ = make(gate=gate)
        await adapter.start()
        await speak(adapter)
        await asyncio.sleep(0.05)
        await speak(adapter)  # the user talks over the pending reply
        gate.set()
        events = await collect(adapter)
        await adapter.close()
        return events

    events = run(scenario())
    assert isinstance(events[0], Interrupted) and isinstance(events[-1], TurnComplete)


def test_history_is_bounded_and_cleared_on_close():
    async def scenario():
        adapter, seen = make(max_history_messages=2)
        await adapter.start()
        for _ in range(3):
            await speak(adapter)
            await collect(adapter)
        last = [value for kind, value in seen if kind == "messages"][-1]
        await adapter.close()
        return last, adapter._history

    last, history = run(scenario())
    assert len(last) == 4 and history == []  # system + one remembered exchange + new user turn


def test_stage_failure_fails_closed_with_a_fixed_category():
    async def scenario():
        adapter, _ = make()

        async def broken(pcm):
            raise OSError("/private/path/to/model secret detail")

        adapter._transcribe = broken
        await adapter.start()
        await speak(adapter)
        with pytest.raises(AdapterError) as caught:
            await collect(adapter)
        await adapter.close()
        return caught.value

    error = run(scenario())
    assert error.category == "provider-unavailable" and "secret" not in str(error)


def test_invalid_frames_and_lifecycle_are_rejected():
    async def scenario():
        adapter, _ = make()
        with pytest.raises(RuntimeError):
            await adapter.enqueue_audio(LOUD)
        await adapter.start()
        for bad in (b"", b"\x00", bytes(32 * 1024 + 2), "text"):
            with pytest.raises(ValueError):
                await adapter.enqueue_audio(bad)
        await adapter.close()
        await adapter.close()
        with pytest.raises(RuntimeError):
            await adapter.start()

    run(scenario())


def test_noise_that_transcribes_to_nothing_does_not_cut_off_a_reply():
    async def scenario():
        gate = asyncio.Event()
        heard = iter(["what time is it", ""])
        adapter, _ = make(gate=gate)

        async def transcribe(pcm):
            return next(heard)

        adapter._transcribe = transcribe
        await adapter.start()
        await speak(adapter)
        await asyncio.sleep(0.05)
        await speak(adapter)  # a cough over the pending reply
        await asyncio.sleep(0.05)
        gate.set()
        events = await collect(adapter)
        await adapter.close()
        return events

    events = run(scenario())
    assert not any(isinstance(event, Interrupted) for event in events)
    assert isinstance(events[-1], TurnComplete)


def test_a_slow_newer_transcription_is_not_cancelled_by_the_older_turn():
    async def scenario():
        adapter, seen = make()
        delays = iter([("first question", 0.01), ("second question", 0.2)])

        async def transcribe(pcm):
            text, delay = next(delays)
            await asyncio.sleep(delay)
            return text

        adapter._transcribe = transcribe
        await adapter.start()
        await speak(adapter)
        await speak(adapter)  # ends while the first turn is replying
        events = []
        async for event in adapter.events():
            events.append(event)
            if sum(isinstance(seen_event, TurnComplete) for seen_event in events) == 2:
                break
        asked = [value[-1]["content"] for kind, value in seen if kind == "messages"]
        await adapter.close()
        return asked, events

    asked, events = run(scenario())
    assert asked[-1] == "second question"
    assert isinstance(events[-1], TurnComplete)


def test_close_during_a_reply_ends_the_event_stream():
    async def scenario():
        gate = asyncio.Event()
        adapter, seen = make(gate=gate)
        await adapter.start()
        await speak(adapter)
        await asyncio.sleep(0.05)
        await adapter.close()
        return [event async for event in adapter.events()], adapter._turns, seen

    events, turns, seen = run(scenario())
    assert events == [] and not turns and not any(kind == "say" for kind, _ in seen)


def test_a_queued_error_survives_a_later_interrupt():
    async def scenario():
        adapter, _ = make()

        async def broken(pcm):
            raise OSError("detail")

        adapter._transcribe = broken
        await adapter.start()
        await speak(adapter)
        await asyncio.sleep(0.05)  # the failed turn has finished and queued its error
        await adapter.interrupt()
        with pytest.raises(AdapterError):
            await collect(adapter)
        await adapter.close()

    run(scenario())


def test_model_calls_ignore_proxies_and_stay_on_loopback(monkeypatch):
    monkeypatch.setenv("http_proxy", "http://10.0.0.1:3128")
    monkeypatch.setenv("HTTP_PROXY", "http://10.0.0.1:3128")
    assert local_adapter.OLLAMA_CHAT_URL.startswith("http://127.0.0.1:")
    handlers = [type(handler).__name__ for handler in local_adapter._DIRECT.handlers]
    assert "ProxyHandler" not in handlers  # an empty ProxyHandler installs no proxy route
    opened = []

    class EmptyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def __iter__(self):
            return iter(())

        def close(self):
            pass

    monkeypatch.setattr(local_adapter._DIRECT, "open", lambda request, timeout: opened.append(request) or EmptyResponse())

    async def scenario():
        return [piece async for piece in local_adapter.ollama_reply([{"role": "user", "content": "hi"}])]

    assert run(scenario()) == []
    assert opened[0].full_url == local_adapter.OLLAMA_CHAT_URL
    assert b'"tools"' not in opened[0].data


def test_adapter_selection_fails_closed(monkeypatch):
    monkeypatch.delenv("SUPER_AGENT_ADAPTER", raising=False)
    assert _adapter_from_environment().name == "fake"
    monkeypatch.setenv("SUPER_AGENT_ADAPTER", "local")
    assert _adapter_from_environment() is LocalVoiceAdapter
    monkeypatch.setenv("SUPER_AGENT_ADAPTER", "gemini-typo")
    with pytest.raises(RuntimeError):
        _adapter_from_environment()
