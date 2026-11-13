r"""Opt-in live check against Gemini Live with synthetic speech only (R-01.8).

    GEMINI_API_KEY=... python -m super_agent_voice.live_check --send-synthetic-audio

PowerShell (prompts for the key if GEMINI_API_KEY is not set):

    $env:PYTHONPATH = "apps\api\src"
    & "$env:LOCALAPPDATA\Temp\super-agent-voice-venv\Scripts\python.exe" -m super_agent_voice.live_check --send-synthetic-audio

Steps: conversation, interrupt, unsupported-model, tool-calculate, tool-clock,
then one summary line. Speech comes from macOS `say`, Windows SAPI, or --wav.

Not collected by pytest and never run by CI. It prints timing, state, tool names
and character counts only: no audio, transcript text, key, or provider payload. Free-tier inputs may be used by
Google for training, so the audio must be synthetic (REQ-13).
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

from .adapter import AdapterError, AudioChunk, Interrupted, Transcript, TurnComplete, VoiceAdapter
from .config import VoiceConfig
from .gemini_adapter import GeminiLiveAdapter

FRAME_BYTES = 3200  # 100 ms of 16 kHz PCM16
STEP_TIMEOUT_SECONDS = 40
PHRASE = "Hello. In one short sentence, what is two plus two?"
CALC_PHRASE = "What is seventeen times twenty three? Use the calculator."
CLOCK_PHRASE = "What time is it right now?"
# The text and path travel in the environment, never inside the script string.
SAPI_SCRIPT = (
    "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, 'Sixteen', 'Mono'); "
    "$s.SetOutputToWaveFile($env:SA_WAV, $f); $s.Speak($env:SA_TEXT); $s.Dispose()"
)


def load_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wav:
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (16000, 1, 2):
            raise SystemExit("WAV must be 16 kHz, mono, 16-bit")
        return wav.readframes(wav.getnframes())


def speak(text: str) -> bytes:
    """macOS `say` speech, written to a temporary folder that is deleted at once."""
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "synthetic.wav"
        subprocess.run(["say", "-o", str(out), "--data-format=LEI16@16000", text], check=True, timeout=30)
        return load_pcm(out)


def speak_windows(text: str) -> bytes:
    """Windows SAPI speech (16 kHz mono 16-bit, as load_pcm requires), deleted at once."""
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "synthetic.wav"
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", SAPI_SCRIPT],
            check=True, timeout=60, env={**os.environ, "SA_WAV": str(out), "SA_TEXT": text},
        )
        return load_pcm(out)


async def converse(
    adapter: VoiceAdapter, pcm: bytes, result: dict, *, interrupt: bool = False, pace: float = 0.1
) -> None:
    """Fills `result` as it goes, so a timeout still reports how far it got."""
    started = time.monotonic()

    def elapsed() -> int:
        return round((time.monotonic() - started) * 1000)

    async def send() -> None:
        for offset in range(0, len(pcm), FRAME_BYTES):
            await adapter.enqueue_audio(pcm[offset : offset + FRAME_BYTES])
            await asyncio.sleep(pace)  # real-time pacing so the provider's VAD hears speech
        await adapter.end_audio_stream()
        result["input_done_ms"] = elapsed()

    sender: asyncio.Task[None] | None = None
    try:
        await adapter.start()
        result["connect_ms"] = elapsed()
        sender = asyncio.create_task(send())
        result["events"] = []
        async for event in adapter.events():
            if isinstance(event, AudioChunk):
                if "first_audio_ms" not in result:
                    result["first_audio_ms"] = elapsed()
                    if interrupt:
                        await adapter.interrupt()
                        result["interrupt_sent_ms"] = elapsed()
                result["audio_bytes"] = result.get("audio_bytes", 0) + len(event.data)
            else:
                result["events"].append(type(event).__name__)
                result["ended_ms"] = elapsed()
                if isinstance(event, Transcript):  # counts only, the text is dropped here
                    key = f"transcript_{event.role}_chars"
                    result[key] = result.get(key, 0) + len(event.text)
                if isinstance(event, TurnComplete):
                    result["tools"] = list(event.tools)
                if isinstance(event, (TurnComplete, Interrupted)):
                    break
    except AdapterError as error:
        result["error"] = error.category
        result["error_ms"] = elapsed()
    finally:
        if sender is not None:
            sender.cancel()
        await adapter.close()


async def run_step(name: str, adapter: VoiceAdapter, pcm: bytes, **options: bool) -> dict:
    result: dict = {"step": name}
    try:
        await asyncio.wait_for(converse(adapter, pcm, result, **options), STEP_TIMEOUT_SECONDS)
    except TimeoutError:
        result["error"] = "step-timeout"
    return result


async def run_all(
    api_key: str, model: str, clips: dict[str, bytes], adapter_for=GeminiLiveAdapter
) -> list[dict]:
    steps = [
        ("conversation", model, "hello", {}),
        ("interrupt", model, "hello", {"interrupt": True}),
        ("unsupported-model", "not-a-real-model", "hello", {}),
        ("tool-calculate", model, "calculate", {}),
        ("tool-clock", model, "clock", {}),
    ]
    results = []
    for name, step_model, clip, options in steps:
        result = await run_step(name, adapter_for(step_model, api_key), clips[clip], **options)
        result["model"] = step_model
        if name == "unsupported-model":
            result["fails_closed"] = "error" in result and "first_audio_ms" not in result
        print(json.dumps(result), flush=True)
        results.append(result)
    by_name = {r["step"]: r for r in results}
    summary = {
        "reached_gemini": "first_audio_ms" in by_name["conversation"],
        "tools_ok": "calculate" in by_name["tool-calculate"].get("tools", [])
        and "current_time" in by_name["tool-clock"].get("tools", []),
        "fails_closed": by_name["unsupported-model"]["fails_closed"],
    }
    print(json.dumps({"summary": summary}), flush=True)
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Synthetic-speech check against Gemini Live.")
    parser.add_argument("--send-synthetic-audio", action="store_true", required=True,
                        help="confirm that the audio is synthetic and may be sent to Google")
    parser.add_argument("--wav", type=Path,
                        help="16 kHz mono 16-bit WAV of synthetic speech (default: macOS `say`)")
    args = parser.parse_args(argv)
    api_key = os.environ.get("GEMINI_API_KEY") or getpass.getpass("Gemini API key: ")
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set")
    if args.wav:
        pcm = load_pcm(args.wav)
        clips = {"hello": pcm, "calculate": pcm, "clock": pcm}
    else:
        if shutil.which("say"):
            say = speak
        elif sys.platform == "win32":
            say = speak_windows
        else:
            sys.exit("no `say` command on this system; pass --wav with synthetic speech")
        clips = {"hello": say(PHRASE), "calculate": say(CALC_PHRASE), "clock": say(CLOCK_PHRASE)}
        pcm = clips["hello"]
    model = os.environ.get("SUPER_AGENT_GEMINI_MODEL") or VoiceConfig.gemini_model
    print(json.dumps({"model": model, "input_seconds": round(len(pcm) / 32000, 1)}), flush=True)
    asyncio.run(run_all(api_key, model, clips))


if __name__ == "__main__":
    main()
