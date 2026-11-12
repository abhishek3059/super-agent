"""Opt-in live check against Gemini Live with synthetic speech only (R-01.8).

    GEMINI_API_KEY=... python -m super_agent_voice.live_check --send-synthetic-audio

Not collected by pytest and never run by CI. It prints timing and state only:
no audio, transcript, key, or provider payload. Free-tier inputs may be used by
Google for training, so the audio must be synthetic (REQ-13).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

from .adapter import AdapterError, AudioChunk, Interrupted, TurnComplete, VoiceAdapter
from .config import VoiceConfig
from .gemini_adapter import GeminiLiveAdapter

FRAME_BYTES = 3200  # 100 ms of 16 kHz PCM16
STEP_TIMEOUT_SECONDS = 40
PHRASE = "Hello. In one short sentence, what is two plus two?"


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


async def run_all(api_key: str, model: str, pcm: bytes) -> list[dict]:
    steps = [
        ("conversation", model, {}),
        ("interrupt", model, {"interrupt": True}),
        ("unsupported-model", "not-a-real-model", {}),
    ]
    results = []
    for name, step_model, options in steps:
        result = await run_step(name, GeminiLiveAdapter(step_model, api_key), pcm, **options)
        if name == "unsupported-model":
            result["fails_closed"] = "error" in result and "first_audio_ms" not in result
        print(json.dumps(result), flush=True)
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Synthetic-speech check against Gemini Live.")
    parser.add_argument("--send-synthetic-audio", action="store_true", required=True,
                        help="confirm that the audio is synthetic and may be sent to Google")
    parser.add_argument("--wav", type=Path,
                        help="16 kHz mono 16-bit WAV of synthetic speech (default: macOS `say`)")
    args = parser.parse_args(argv)
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set")
    if args.wav is None and not shutil.which("say"):
        sys.exit("no `say` command on this system; pass --wav with synthetic speech")
    pcm = load_pcm(args.wav) if args.wav else speak(PHRASE)
    model = os.environ.get("SUPER_AGENT_GEMINI_MODEL") or VoiceConfig.gemini_model
    print(json.dumps({"model": model, "input_seconds": round(len(pcm) / 32000, 1)}), flush=True)
    asyncio.run(run_all(api_key, model, pcm))


if __name__ == "__main__":
    main()
