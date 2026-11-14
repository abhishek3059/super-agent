"""LFM3-Audio as the assistant's ears and mouth, with the brain in between.

The speech model does only speech-to-text and text-to-speech here. Every
word the assistant says comes from the brain (the Ollama model), so tool
results, refusals, and the tier rules stay in one place. Runs fully on this
Mac through MLX; opt-in with SUPER_AGENT_STT=lfm3 and SUPER_AGENT_TTS=lfm3.

The weights use the LFM Open License v1.0, not MIT: they stay outside the
repository in ~/.super-agent/models (spike A5).
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import os
import tempfile
import threading
import wave
from collections.abc import AsyncIterator, Callable
from pathlib import Path

INPUT_RATE_HZ = 16000
OUTPUT_RATE_HZ = 24000
DEFAULT_DIR = "lfm3-audio-2b-mlx-4bit-f73a8a6"
# MLX state is not shared across threads, so every model call runs on this one thread.
_WORKER = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="lfm3")


def model_dir() -> Path:
    # A name inside ~/.super-agent/models/a5, never a path the environment can point elsewhere.
    name = Path(os.environ.get("SUPER_AGENT_LFM3_DIR", DEFAULT_DIR)).name
    return Path.home() / ".super-agent" / "models" / "a5" / name


@functools.lru_cache(maxsize=1)
def _load():
    import mlx.core as mx
    from mlx_vlm import load

    # Keep MLX's buffer cache small so the brain model has room next to it.
    mx.set_cache_limit(256 * 1024 * 1024)
    model, processor = load(str(model_dir()))
    return model, processor, model.codec()


STREAM_FRAMES = 12  # speech frames per streamed chunk; the first chunk is about a second of audio


def _run(system: str, user: str, audio_path: str | None, mode: str,
         emit: Callable[[bytes], None] | None = None, stop: threading.Event | None = None) -> tuple[str, bytes]:
    import mlx.core as mx
    import numpy
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import prepare_inputs

    model, processor, codec = _load()
    config = model.config
    prompt = apply_chat_template(
        processor, config, [{"role": "system", "content": system}, {"role": "user", "content": user}],
        num_audios=1 if audio_path else 0, use_tts_template=True)
    inputs = prepare_inputs(processor, audio=audio_path, prompts=prompt) if audio_path else \
        prepare_inputs(processor, prompts=prompt)
    ids = inputs.pop("input_ids")
    inputs.pop("attention_mask", None)
    def decode(frames: list) -> bytes:
        wave_out = codec.decode(mx.stack(frames, axis=-1))
        mx.eval(wave_out)
        samples = numpy.clip(numpy.asarray(wave_out, dtype=numpy.float32).reshape(-1), -1, 1)
        return (samples * 32767).astype("<i2").tobytes()

    tokens, frames, sent = [], [], 0
    for token, codes in model.stream_slots(
        ids, generation_mode=mode, max_tokens=1024, **{**model.audio_sampling, **inputs}
    ):
        if stop is not None and stop.is_set():
            return "", b""  # the turn was interrupted; stop generating at once
        if codes is None:
            tokens.append(token)
        elif codes[0].item() != config.audio_eos_code:
            frames.append(codes)
            if emit is not None and len(frames) % STREAM_FRAMES == 0:
                # shortcut: re-decodes all frames so far and sends only the new samples,
                # which keeps chunk edges clean at a cost that grows with sentence length.
                pcm = decode(frames)
                emit(pcm[sent:])
                sent = len(pcm)
    text = processor.tokenizer.decode(tokens, skip_special_tokens=True)
    pcm = decode(frames) if frames else b""
    if emit is not None:
        emit(pcm[sent:])
    return text, pcm


async def _on_worker(*args):
    return await asyncio.get_running_loop().run_in_executor(_WORKER, _run, *args)


async def warm() -> None:
    await asyncio.get_running_loop().run_in_executor(_WORKER, _load)


async def lfm3_transcribe(pcm: bytes) -> str:
    # shortcut: the processor reads a file, so the utterance sits in a 0600 temp
    # file for one transcription; pass an array if the processor accepts one.
    with tempfile.NamedTemporaryFile(suffix=".wav") as handle:
        with wave.open(handle, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(INPUT_RATE_HZ)
            wav.writeframes(pcm)
        handle.flush()
        text, _ = await _on_worker("Perform ASR in English.", "", handle.name, "text")
    return text.strip()


async def lfm3_synthesize(text: str) -> AsyncIterator[bytes]:
    """Yields speech as it is generated, so playback starts before the sentence is done."""
    voice = "female" if os.environ.get("SUPER_AGENT_LFM3_VOICE") == "female" else "male"
    loop = asyncio.get_running_loop()
    chunks: asyncio.Queue[bytes] = asyncio.Queue()
    stop = threading.Event()

    def emit(pcm: bytes) -> None:
        if pcm:
            loop.call_soon_threadsafe(chunks.put_nowait, pcm)

    job = loop.run_in_executor(_WORKER, _run, f"Perform TTS in American English using a {voice} voice.",
                               text, None, "audio", emit, stop)
    try:
        while not (job.done() and chunks.empty()):
            getter = asyncio.ensure_future(chunks.get())
            await asyncio.wait({getter, job}, return_when=asyncio.FIRST_COMPLETED)
            if getter.done():
                yield getter.result()
            else:
                getter.cancel()
        job.result()  # surface a failure in the speech model
    finally:
        stop.set()  # an interrupted reply stops the worker within one frame
