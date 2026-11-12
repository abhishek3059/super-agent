"""Fully local voice adapter: speech-to-text, a local LLM, and text-to-speech.

Everything stays on this machine. The only network peer is the Ollama server
on loopback. Conversation only: the model gets no tools (DEC-18 tier T0).
Audio and text are kept in memory for the session and are never logged.
"""
from __future__ import annotations

import asyncio
import functools
import json
import os
import re
import tempfile
import urllib.request
import wave
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

from .adapter import AdapterError, AdapterEvent, AudioChunk, Interrupted, TurnComplete

# Loopback only (REQ-11). Not configurable, so no setting can point it at a remote host.
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
# The default opener honours http_proxy and the macOS system proxy even for
# 127.0.0.1, which would send the conversation to the proxy. This one never does.
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MODEL_DIR = Path.home() / ".super-agent" / "models"
INPUT_RATE_HZ = 16000
OUTPUT_RATE_HZ = 24000
SYSTEM_PROMPT = (
    "You are a helpful personal voice assistant running privately on the user's own computer. "
    "Reply in one to three spoken sentences, in plain words without lists, markdown, or emoji. "
    # Speech starts when the first sentence is done, so a short opener cuts the wait.
    "Open with a sentence of at most six words, and keep every sentence under fifteen words. "
    "You have no tools: you cannot take actions, set reminders, or look anything up. "
    "Never say you did something. If asked to act, say you can only talk for now."
)

Transcribe = Callable[[bytes], Awaitable[str]]
Reply = Callable[[list[dict[str, str]]], AsyncIterator[str]]
Synthesize = Callable[[str], Awaitable[bytes]]

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def frame_rms(audio: bytes) -> float:
    samples = memoryview(audio).cast("h")
    return (sum(sample * sample for sample in samples) / len(samples)) ** 0.5 / 32768


class LocalVoiceAdapter:
    name = "local"
    output_rate_hz = OUTPUT_RATE_HZ

    def __init__(
        self,
        transcribe: Transcribe | None = None,
        reply: Reply | None = None,
        synthesize: Synthesize | None = None,
        *,
        # shortcut: energy endpointing, fooled by steady noise; upgrade to Silero VAD
        # plus a turn model if turns get cut off or never end.
        speech_rms: float = 0.02,  # same level as the browser's barge-in check
        end_silence_seconds: float = 0.7,
        min_speech_seconds: float = 0.25,
        max_utterance_seconds: float = 30.0,
        max_history_messages: int = 12,
        pace_output: bool = True,
    ) -> None:
        self._transcribe = transcribe or whisper_transcribe
        self._reply = reply or ollama_reply
        self._synthesize = synthesize or default_synthesize()
        self._speech_rms = speech_rms
        self._end_silence = end_silence_seconds
        self._min_speech = min_speech_seconds
        self._max_utterance_bytes = int(max_utterance_seconds * INPUT_RATE_HZ) * 2
        self._max_history = max_history_messages
        self._pace = pace_output
        self._events: asyncio.Queue[AdapterEvent | AdapterError | None] = asyncio.Queue(maxsize=64)
        self._utterance = bytearray()
        self._speech_seconds = 0.0
        self._silence_seconds = 0.0
        self._history: list[dict[str, str]] = []
        self._turns: dict[asyncio.Task[None], int] = {}  # task -> utterance number
        self._replying: set[asyncio.Task[None]] = set()
        self._utterances = 0
        self._started = False
        self.closed = False

    async def start(self) -> None:
        if self._started or self.closed:
            raise RuntimeError("adapter cannot start")
        self._started = True

    async def enqueue_audio(self, audio: bytes) -> None:
        if not self._started or self.closed:
            raise RuntimeError("adapter is not ready")
        if not isinstance(audio, bytes) or not audio or len(audio) % 2 or len(audio) > 32 * 1024:
            raise ValueError("invalid PCM frame")
        seconds = len(audio) / 2 / INPUT_RATE_HZ
        if frame_rms(audio) >= self._speech_rms:
            self._speech_seconds += seconds
            self._silence_seconds = 0.0
            self._utterance += audio
        elif self._utterance:
            self._silence_seconds += seconds
            self._utterance += audio
        ended = self._silence_seconds >= self._end_silence
        if self._utterance and (ended or len(self._utterance) >= self._max_utterance_bytes):
            pcm, spoken = bytes(self._utterance), self._speech_seconds
            self._reset_utterance()
            if spoken >= self._min_speech:
                self._utterances += 1
                turn = asyncio.create_task(self._run_turn(pcm, self._utterances))
                self._turns[turn] = self._utterances
                turn.add_done_callback(self._forget_turn)

    async def end_audio_stream(self) -> None:
        self._reset_utterance()

    async def interrupt(self) -> None:
        await self._cancel_turn()

    async def events(self) -> AsyncIterator[AdapterEvent]:
        while True:
            event = await self._events.get()
            if event is None:
                return
            if isinstance(event, AdapterError):
                raise event
            yield event

    async def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        await self._cancel_turn()
        self._history.clear()
        self._reset_utterance()
        self._events.put_nowait(None)

    def _reset_utterance(self) -> None:
        self._utterance = bytearray()
        self._speech_seconds = self._silence_seconds = 0.0

    def _forget_turn(self, turn: asyncio.Task[None]) -> None:
        self._turns.pop(turn, None)
        self._replying.discard(turn)

    async def _cancel_turn(self, before: int | None = None) -> bool:
        """Cancels unfinished turns, or only those older than utterance `before`.

        Returns whether a cancelled turn had started to reply.
        """
        targets = [turn for turn, number in self._turns.items()
                   if not turn.done() and (before is None or number < before)]
        was_replying = any(turn in self._replying for turn in targets)
        for turn in targets:
            turn.cancel()
        await asyncio.gather(*targets, return_exceptions=True)
        if was_replying:
            # Drop the audio the cancelled reply queued, but keep an error from
            # an earlier turn so a failure is never swallowed.
            kept = []
            while not self._events.empty():
                if isinstance(event := self._events.get_nowait(), AdapterError):
                    kept.append(event)
            for event in kept:
                self._events.put_nowait(event)
        return was_replying

    async def _run_turn(self, pcm: bytes, number: int) -> None:
        try:
            text = (await self._transcribe(pcm)).strip()
            if not text:
                return
            # Only real words replace an older reply; a cough or leftover echo that
            # transcribes to nothing leaves it alone. A turn never cancels a newer
            # one, so later words are not lost to a slow transcription.
            # shortcut: an older utterance still being transcribed is dropped, not
            # merged into this one; carry its text over if split questions get lost.
            if await self._cancel_turn(before=number):
                self._events.put_nowait(Interrupted())
            self._replying.add(asyncio.current_task())
            messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self._history,
                        {"role": "user", "content": text}]
            spoken, pending = "", ""
            loop = asyncio.get_running_loop()
            playhead = loop.time()
            async for piece in self._reply(messages):
                pending += piece
                *sentences, pending = _SENTENCE_END.split(pending)
                for sentence in sentences:
                    playhead = await self._speak(sentence, playhead)
                    spoken += sentence + " "
            if pending.strip():
                playhead = await self._speak(pending, playhead)
                spoken += pending
            # Only a reply that finished is remembered; an interrupted one is dropped.
            self._history += [{"role": "user", "content": text},
                              {"role": "assistant", "content": spoken.strip()}]
            del self._history[:-self._max_history]
            await self._events.put(TurnComplete())
        except asyncio.CancelledError:
            raise
        except AdapterError as error:
            await self._events.put(error)
        except Exception:
            # Fail closed with a fixed category; local detail never leaves the adapter.
            await self._events.put(AdapterError("provider-unavailable"))

    async def _speak(self, sentence: str, playhead: float) -> float:
        if not sentence.strip():
            return playhead
        pcm = await self._synthesize(sentence.strip())
        loop = asyncio.get_running_loop()
        step = OUTPUT_RATE_HZ * 2 // 5  # 200 ms of PCM16, well under the 32 KiB frame cap
        for offset in range(0, len(pcm) - len(pcm) % 2, step):
            chunk = pcm[offset:offset + step]
            # Stay at most ~300 ms ahead of real time so an interrupt stops
            # speech quickly and the bounded outbound queue never overflows.
            if self._pace and (lead := playhead - loop.time() - 0.3) > 0:
                await asyncio.sleep(lead)
            await self._events.put(AudioChunk(data=chunk, rate_hz=OUTPUT_RATE_HZ))
            playhead = max(playhead, loop.time()) + len(chunk) / 2 / OUTPUT_RATE_HZ
        return playhead


async def _run(*command: str) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=60)
    except BaseException:
        if process.returncode is None:
            process.kill()
        raise
    if process.returncode:
        raise AdapterError("provider-unavailable")
    return output


async def whisper_transcribe(pcm: bytes) -> str:
    model = MODEL_DIR / Path(os.environ.get("SUPER_AGENT_WHISPER_MODEL", "ggml-base.en.bin")).name
    # shortcut: whisper-cli needs a file, so the utterance sits in a 0600 temp file
    # for the length of one transcription, and a hard kill in that window leaves
    # it in the temp folder; switch to whisper-server to keep audio off disk.
    with tempfile.NamedTemporaryFile(suffix=".wav") as handle:
        with wave.open(handle, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(INPUT_RATE_HZ)
            wav.writeframes(pcm)
        handle.flush()
        output = await _run("whisper-cli", "-m", str(model), "-f", handle.name, "-nt", "-np", "-l", "en")
    text = output.decode("utf-8", "replace").strip()
    # Whisper labels non-speech as [BLANK_AUDIO] or (music); those are not user turns.
    return "" if re.fullmatch(r"[\[(].*[\])]", text, re.DOTALL) else text


async def ollama_reply(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    body = json.dumps({
        "model": os.environ.get("SUPER_AGENT_LOCAL_MODEL", "qwen3.5:9b"),
        "messages": messages, "stream": True, "think": False,
        "options": {"num_ctx": 8192, "num_predict": 200},
    }).encode()
    request = urllib.request.Request(OLLAMA_CHAT_URL, body, {"Content-Type": "application/json"})
    queue: asyncio.Queue[str | BaseException | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    responses = []
    stopped = False

    def deliver(item: str | BaseException | None) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, item)
        except RuntimeError:
            pass  # the loop closed while the thread was finishing

    def pump() -> None:
        try:
            with _DIRECT.open(request, timeout=60) as response:
                responses.append(response)
                if stopped:  # the consumer left before the response existed
                    return
                for line in response:
                    piece = json.loads(line).get("message", {}).get("content", "")
                    if piece:
                        deliver(piece)
            deliver(None)
        except BaseException as error:
            if not stopped:
                deliver(error)

    worker = loop.run_in_executor(None, pump)
    try:
        while (item := await queue.get()) is not None:
            if isinstance(item, BaseException):
                raise AdapterError("provider-unavailable") from None
            yield item
    finally:
        # Closing the response ends the thread's read, and Ollama stops generating
        # when its client disconnects.
        stopped = True
        for response in responses:
            response.close()
        worker.cancel()


async def say_synthesize(text: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav") as handle:
        command = ["say", "-o", handle.name, "--file-format=WAVE",
                   f"--data-format=LEI16@{OUTPUT_RATE_HZ}"]
        if voice := os.environ.get("SUPER_AGENT_SAY_VOICE"):
            command += ["-v", voice]
        # "--" keeps text that starts with a dash from being read as an option.
        await _run(*command, "--", text)
        with wave.open(handle.name, "rb") as wav:
            return wav.readframes(wav.getnframes())


@functools.lru_cache(maxsize=1)  # one model load per process, not per session
def kokoro_synthesize() -> Synthesize:
    # Optional and not in the lock file: kokoro-onnx pulls in GPL-3.0 phonemizer code.
    import numpy
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(str(MODEL_DIR / "kokoro-v1.0.int8.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    voice = os.environ.get("SUPER_AGENT_KOKORO_VOICE", "am_michael")

    async def synthesize(text: str) -> bytes:
        samples, rate = await asyncio.to_thread(kokoro.create, text, voice=voice, lang="en-us")
        if rate != OUTPUT_RATE_HZ:
            raise AdapterError("provider-unsupported")
        return (numpy.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()

    return synthesize


def default_synthesize() -> Synthesize:
    return kokoro_synthesize() if os.environ.get("SUPER_AGENT_TTS") == "kokoro" else say_synthesize
