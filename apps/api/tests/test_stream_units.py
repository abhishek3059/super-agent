from __future__ import annotations

import asyncio

import pytest

from super_agent_voice.adapter import AudioChunk, FakeVoiceAdapter, TurnComplete
from super_agent_voice.app import (
    _Outbound,
    _OutboundQueue,
    _SessionFailure,
    _SessionState,
    _send,
)


def pop(queue: _OutboundQueue, count: int) -> list[_Outbound]:
    async def run() -> list[_Outbound]:
        return [await queue.get() for _ in range(count)]

    return asyncio.run(run())


# CT-02: equal-content pairs overflow the queue and the drop-oldest removal
# must never disturb a control placed before the dropped audio.
def test_equal_content_audio_overflow_drops_exactly_one_audio_pair() -> None:
    queue = _OutboundQueue(max_audio=2, max_controls=4)
    pair = _Outbound(
        {"type": "audio.chunk", "playbackEpoch": 0, "rateHz": 16000},
        audio=b"\x07\x00",
        epoch=1,
    )
    queue.put(pair)
    queue.put(_Outbound({"type": "playback.interrupted", "source": "local"}))
    queue.put(pair)
    queue.put(pair)
    assert queue.dropped_audio == 1
    items = pop(queue, 3)
    # The untagged control comes out first: no audio pair took its place.
    assert items[0].audio is None
    assert items[1] == pair
    assert items[2] == pair


# CT-02: the removal must take the oldest queued audio item, not the newest.
def test_audio_overflow_drops_the_oldest_item_not_the_newest() -> None:
    queue = _OutboundQueue(max_audio=2, max_controls=8)
    first = _Outbound({"type": "audio.chunk", "tag": 0}, audio=b"\x00\x00", epoch=1)
    second = _Outbound({"type": "audio.chunk", "tag": 1}, audio=b"\x01\x00", epoch=1)
    third = _Outbound({"type": "audio.chunk", "tag": 2}, audio=b"\x02\x00", epoch=1)
    queue.put(first)
    queue.put(second)
    queue.put(third)
    assert queue.dropped_audio == 1
    assert pop(queue, 2) == [second, third]


# Finding 5.2: mute drops queued audio and epoch-tagged turn events but
# keeps untagged acknowledgements.
def test_clear_playback_keeps_untagged_acknowledgements_only() -> None:
    queue = _OutboundQueue()
    queue.put(
        _Outbound({"type": "audio.chunk", "playbackEpoch": 1}, audio=b"\x01\x00", epoch=1)
    )
    queue.put(_Outbound({"type": "turn.complete", "playbackEpoch": 1}, epoch=1))
    ack = _Outbound({"type": "playback.interrupted", "source": "local"})
    queue.put(ack)
    queue.clear_playback()
    assert pop(queue, 1) == [ack]


# Finding 5.2: control overflow fails closed instead of dropping controls.
def test_control_overflow_fails_the_session_closed() -> None:
    queue = _OutboundQueue(max_controls=2)
    queue.put(_Outbound({"type": "a"}))
    queue.put(_Outbound({"type": "b"}))
    with pytest.raises(_SessionFailure) as failure:
        queue.put(_Outbound({"type": "c"}))
    assert failure.value.category == "session-failed"


# CT-01: a control may change the epoch or mute state during the awaited
# JSON send; the stale payload bytes must never leave under that metadata
# and the session continues with the next queue item.
@pytest.mark.parametrize("mode", ["interrupt", "mute"])
def test_sender_rechecks_epoch_and_mute_before_sending_bytes(mode: str) -> None:
    async def scenario() -> list[tuple[str, object]]:
        state = _SessionState(deadline=9.0, last_input=0.0)
        outbound = _OutboundQueue()
        metadata_sent = asyncio.Event()
        control_sent = asyncio.Event()
        release_json = asyncio.Event()
        sent: list[tuple[str, object]] = []

        class StubWebSocket:
            async def send_json(self, message: dict[str, object]) -> None:
                sent.append(("json", message))
                if message.get("type") == "audio.chunk":
                    metadata_sent.set()
                    await release_json.wait()
                else:
                    control_sent.set()

            async def send_bytes(self, data: bytes) -> None:
                sent.append(("bytes", data))

        sender = asyncio.create_task(_send(StubWebSocket(), state, outbound))
        outbound.put(_Outbound(
            {"type": "audio.chunk", "playbackEpoch": 0, "rateHz": 16000},
            audio=b"\x01\x00",
            epoch=0,
        ))
        await metadata_sent.wait()
        if mode == "interrupt":
            state.epoch = 1
            outbound.clear_playback()
            outbound.put(_Outbound({"type": "playback.interrupted", "playbackEpoch": 1}))
        else:
            state.muted = True
            outbound.clear_playback()
            outbound.put(_Outbound({"type": "session.state", "muted": True}))
        release_json.set()
        await control_sent.wait()
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)
        return sent

    sent = asyncio.run(scenario())
    assert [kind for kind, _ in sent] == ["json", "json"]
    assert ("bytes", b"\x01\x00") not in sent


# CT-06: close is idempotent and wakes a consumer blocked on an empty queue.
def test_fake_close_wakes_blocked_consumer_and_is_idempotent() -> None:
    async def scenario() -> None:
        adapter = FakeVoiceAdapter()
        await adapter.start()
        events = adapter.events()
        blocked = asyncio.create_task(events.__anext__())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await adapter.close()
        with pytest.raises(StopAsyncIteration):
            await blocked
        await adapter.close()
        await adapter.close()
        assert adapter.closed

    asyncio.run(scenario())


def test_fake_adapter_requires_start() -> None:
    async def scenario() -> None:
        adapter = FakeVoiceAdapter()
        with pytest.raises(RuntimeError):
            await adapter.enqueue_audio(b"\x01\x00")
        before_start = adapter.events()
        # The generator guard fires on first iteration, not on the call.
        with pytest.raises(RuntimeError):
            await before_start.__anext__()
        await adapter.start()
        with pytest.raises(ValueError):
            await adapter.enqueue_audio("not bytes")

    asyncio.run(scenario())


def test_fake_adapter_admits_exactly_one_consumer() -> None:
    async def scenario() -> None:
        adapter = FakeVoiceAdapter()
        await adapter.start()
        first = adapter.events()
        consumer = asyncio.create_task(first.__anext__())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        # A second consumer raises while the first is still iterating.
        with pytest.raises(RuntimeError):
            await adapter.events().__anext__()
        await adapter.close()
        with pytest.raises(StopAsyncIteration):
            await consumer

    asyncio.run(scenario())


def test_fake_enqueue_audio_after_close_raises() -> None:
    async def scenario() -> None:
        adapter = FakeVoiceAdapter()
        await adapter.start()
        await adapter.interrupt()
        await adapter.close()
        assert adapter.interruptions == 1
        with pytest.raises(RuntimeError):
            await adapter.enqueue_audio(b"\x01\x00")

    asyncio.run(scenario())


# CT-06: the scripted full input queue drops the oldest frame in order.
def test_fake_input_queue_drops_oldest_when_full() -> None:
    async def scenario() -> None:
        adapter = FakeVoiceAdapter(max_input_frames=2)
        await adapter.start()
        await adapter.enqueue_audio(b"\x01\x00")
        await adapter.enqueue_audio(b"\x02\x00")
        await adapter.enqueue_audio(b"\x03\x00")
        assert adapter.dropped_input_frames == 1
        events = adapter.events()
        assert await events.__anext__() == AudioChunk(data=b"\x02\x00", rate_hz=16000)
        assert await events.__anext__() == TurnComplete()
        assert await events.__anext__() == AudioChunk(data=b"\x03\x00", rate_hz=16000)

    asyncio.run(scenario())


# CT-06: queued audio from before an interrupt is silently consumed and
# never yielded; only audio of the current generation passes.
def test_fake_consumer_never_sees_old_generation_audio() -> None:
    async def scenario() -> None:
        adapter = FakeVoiceAdapter()
        await adapter.start()
        events = adapter.events()
        await adapter.enqueue_audio(b"\x01\x00")
        await adapter.interrupt()
        await adapter.enqueue_audio(b"\x02\x00")
        assert await events.__anext__() == AudioChunk(data=b"\x02\x00", rate_hz=16000)
        assert await events.__anext__() == TurnComplete()
        # The old-generation frame never appears between or after these.

    asyncio.run(scenario())
