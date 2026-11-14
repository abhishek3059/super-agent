"""Opt-in live check against Gemini Live with synthetic speech only (R-01.8).

    GEMINI_API_KEY=... python -m super_agent_voice.live_check --send-synthetic-audio

Not collected by pytest and never run by CI. It prints timing and state only:
no audio, transcript, key, or provider payload. Free-tier inputs may be used by
Google for training, so the audio must be synthetic (REQ-13).
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
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
BARGE_IN_PROMPT = "Please count out loud from one to one hundred, one number at a time."
BARGE_IN_PHRASE = "Stop counting. Say the word done instead."


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
    adapter: VoiceAdapter, pcm: bytes, result: dict, *, barge_in_pcm: bytes = b"", pace: float = 0.1
) -> None:
    """Fills `result` as it goes, so a timeout still reports how far it got."""
    started = time.monotonic()

    def elapsed() -> int:
        return round((time.monotonic() - started) * 1000)

    async def send(clip: bytes, done_key: str, first_key: str | None = None) -> None:
        for offset in range(0, len(clip), FRAME_BYTES):
            await adapter.enqueue_audio(clip[offset : offset + FRAME_BYTES])
            if offset == 0 and first_key is not None:
                result[first_key] = elapsed()
            await asyncio.sleep(pace)  # real-time pacing so the provider's VAD hears speech
        await adapter.end_audio_stream()
        result[done_key] = elapsed()

    sender: asyncio.Task[None] | None = None
    try:
        await adapter.start()
        result["connect_ms"] = elapsed()
        sender = asyncio.create_task(send(pcm, "input_done_ms"))
        result["events"] = []
        async for event in adapter.events():
            if isinstance(event, AudioChunk):
                if "first_audio_ms" not in result:
                    result["first_audio_ms"] = elapsed()
                    if barge_in_pcm and "input_done_ms" in result:
                        await sender
                        sender = asyncio.create_task(
                            send(barge_in_pcm, "barge_in_input_done_ms", "barge_in_first_frame_ms")
                        )
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
        try:
            if sender is not None:
                with contextlib.suppress(asyncio.CancelledError):
                    await sender
        finally:
            await adapter.close()


async def run_step(name: str, adapter: VoiceAdapter, pcm: bytes, *, barge_in_pcm: bytes = b"") -> dict:
    result: dict = {"step": name}
    try:
        await asyncio.wait_for(converse(adapter, pcm, result, barge_in_pcm=barge_in_pcm), STEP_TIMEOUT_SECONDS)
    except AdapterError as error:
        result.setdefault("error", error.category)
    except TimeoutError:
        result["error"] = "step-timeout"
    if barge_in_pcm:
        result["provider_interrupted_after_enqueue"] = (
            "barge_in_first_frame_ms" in result
            and "Interrupted" in result.get("events", [])
            and "error" not in result
        )
    return result


async def run_all(
    api_key: str, model: str, pcm: bytes, barge_in: tuple[bytes, bytes] | None = None
) -> None:
    print(json.dumps(await run_step("conversation", GeminiLiveAdapter(model, api_key), pcm)), flush=True)
    if barge_in is None:
        result = {"step": "barge-in", "skipped": "requires generated clips"}
    else:
        prompt, interruption = barge_in
        result = await run_step("barge-in", GeminiLiveAdapter(model, api_key), prompt, barge_in_pcm=interruption)
    print(json.dumps(result), flush=True)
    result = await run_step("unsupported-model", GeminiLiveAdapter("not-a-real-model", api_key), pcm)
    result["fails_closed"] = "error" in result and "first_audio_ms" not in result
    result["unsupported_confirmed"] = result["fails_closed"] and result.get("error") == "provider-unsupported"
    print(json.dumps(result), flush=True)


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
    barge_in = None if args.wav else (speak(BARGE_IN_PROMPT), speak(BARGE_IN_PHRASE))
    model = os.environ.get("SUPER_AGENT_GEMINI_MODEL") or VoiceConfig.gemini_model
    print(json.dumps({"model": model, "input_seconds": round(len(pcm) / 32000, 1)}), flush=True)
    asyncio.run(run_all(api_key, model, pcm, barge_in))


if __name__ == "__main__":
    main()
