"""Offline tests for the opt-in live command. No key, SDK, network, or `say`."""
from __future__ import annotations

import asyncio
import wave

import pytest

from super_agent_voice import live_check
from super_agent_voice.adapter import AdapterError, AudioChunk, FakeVoiceAdapter, Interrupted, TurnComplete
from super_agent_voice.gemini_adapter import GeminiLiveAdapter


def write_wav(path, rate=16000, channels=1) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setframerate(rate)
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.writeframes(b"\x00\x00" * 1600)


def test_converse_records_timing_and_state_only() -> None:
    async def scenario():
        result: dict = {}
        await live_check.converse(FakeVoiceAdapter(), b"\x01\x00" * 3200, result, pace=0)
        return result

    result = asyncio.run(scenario())
    assert result["events"] == ["TurnComplete"]
    assert {"connect_ms", "first_audio_ms", "ended_ms", "audio_bytes"} <= result.keys()
    assert not {"audio", "transcript", "text"} & result.keys()


@pytest.mark.parametrize("provider_event", [Interrupted(), TurnComplete()])
def test_barge_in_reports_provider_interrupt_after_second_clip(provider_event) -> None:
    class ScriptedAdapter(FakeVoiceAdapter):
        def __init__(self):
            super().__init__()
            self.input_ended = asyncio.Event()
            self.barge_in_received = asyncio.Event()

        async def enqueue_audio(self, audio):
            await super().enqueue_audio(audio)
            if audio == b"\x02\x00":
                self.barge_in_received.set()

        async def end_audio_stream(self):
            self.input_ended.set()

        async def events(self):
            await self.input_ended.wait()
            yield AudioChunk(b"\x03\x00", 24000)
            await self.barge_in_received.wait()
            yield provider_event

    result = asyncio.run(live_check.run_step(
        "barge-in", ScriptedAdapter(), b"\x01\x00", barge_in_pcm=b"\x02\x00",
    ))
    assert result["first_audio_ms"] <= result["barge_in_first_frame_ms"] <= result["ended_ms"]
    assert result["provider_interrupted_after_enqueue"] is isinstance(provider_event, Interrupted)


def test_close_failure_is_reported_without_losing_turn_observation() -> None:
    class CloseFailure(FakeVoiceAdapter):
        async def close(self):
            await super().close()
            raise AdapterError("session-failed")

    result = asyncio.run(live_check.run_step("conversation", CloseFailure(), b"\x01\x00"))
    assert result["events"] == ["TurnComplete"]
    assert result["error"] == "session-failed"


def test_provider_failure_is_reported_as_a_fixed_category() -> None:
    def refuse():
        raise OSError("SENTINEL host detail")

    async def scenario():
        adapter = GeminiLiveAdapter("m", connect=refuse, blob=bytes)
        return await live_check.run_step("conversation", adapter, b"\x00\x00")

    result = asyncio.run(scenario())
    assert result["error"] == "provider-unavailable" and "SENTINEL" not in str(result)


def test_command_needs_the_flag_and_a_key(monkeypatch) -> None:
    with pytest.raises(SystemExit) as no_flag:
        live_check.main([])
    assert no_flag.value.code == 2
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="GEMINI_API_KEY is not set"):
        live_check.main(["--send-synthetic-audio"])


def test_wav_must_be_16k_mono(tmp_path) -> None:
    good, bad = tmp_path / "good.wav", tmp_path / "bad.wav"
    write_wav(good)
    write_wav(bad, rate=24000)
    assert len(live_check.load_pcm(good)) == 3200
    with pytest.raises(SystemExit, match="16 kHz"):
        live_check.load_pcm(bad)
