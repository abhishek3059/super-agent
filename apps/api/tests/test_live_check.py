"""Offline tests for the opt-in live command. No key, SDK, network, or `say`."""
from __future__ import annotations

import asyncio
import wave

import pytest

from super_agent_voice import live_check
from super_agent_voice.adapter import FakeVoiceAdapter
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
    monkeypatch.setattr(live_check.getpass, "getpass", lambda prompt: "")
    with pytest.raises(SystemExit, match="GEMINI_API_KEY is not set"):
        live_check.main(["--send-synthetic-audio"])


def test_wav_must_be_16k_mono(tmp_path) -> None:
    good, bad = tmp_path / "good.wav", tmp_path / "bad.wav"
    write_wav(good)
    write_wav(bad, rate=24000)
    assert len(live_check.load_pcm(good)) == 3200
    with pytest.raises(SystemExit, match="16 kHz"):
        live_check.load_pcm(bad)


def test_summary_reports_tools_and_prints_no_transcript_text(capsys) -> None:
    from super_agent_voice.adapter import AudioChunk, Transcript, TurnComplete

    class Scripted(FakeVoiceAdapter):
        def __init__(self, tools) -> None:
            super().__init__()
            self.tools = tools

        async def events(self):
            yield Transcript("user", "SENTINEL words")
            yield AudioChunk(b"\x00\x00", 24000)
            yield TurnComplete(self.tools)

    per_step = iter([(), (), (), ("calculate",), ("current_time",)])
    clip = b"\x00\x00" * 8
    asyncio.run(live_check.run_all(
        "k", "m", {"hello": clip, "calculate": clip, "clock": clip},
        adapter_for=lambda model, key: Scripted(next(per_step)),
    ))
    out = capsys.readouterr().out
    assert "SENTINEL" not in out
    assert '"transcript_user_chars": 14' in out
    assert '"reached_gemini": true, "tools_ok": true' in out
