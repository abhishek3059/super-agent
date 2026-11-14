"""Fully local voice adapter: speech-to-text, a local LLM, and text-to-speech.

Everything stays on this machine. The only network peer is the Ollama server
on loopback. The model is told the current date and time and can call one
fixed pure function, a calculator. That reads no personal data, touches no
network, and changes nothing, so the assistant still cannot act (DEC-18 tier T0).
Audio and text are kept in memory for the session and are never logged.
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import datetime
import functools
import json
import math
import operator
import os
import re
import tempfile
import urllib.request
import wave
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

from .adapter import (
    AdapterError, AdapterEvent, AudioChunk, Interrupted, Thinking, Transcript, TurnComplete,
)

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
    "Talk, explain, and give advice freely. For arithmetic, call the calculate tool and "
    "never work sums out yourself. You cannot take any other action, set reminders, or "
    "look anything up, and you must never say you did. If asked to act, say you can only "
    "talk and do sums for now."
)
TOOLS = [
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Evaluate arithmetic with numbers and + - * / // % ** and parentheses.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}},
                       "required": ["expression"]}}},
]
MAX_TOOL_ROUNDS = 2
_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def calculate(expression: str) -> str:
    """Arithmetic only. The expression comes from the model, so it is parsed, never evaluated as code."""
    def value(node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
            return _OPERATORS[type(node.op)](value(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
            left, right = value(node.left), value(node.right)
            # Bounds keep a huge power from freezing the voice loop.
            if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
                raise ValueError("power too large")
            return _OPERATORS[type(node.op)](left, right)
        raise ValueError("not arithmetic")

    try:
        if not isinstance(expression, str) or len(expression) > 100:
            raise ValueError("expression too long")
        result = value(ast.parse(expression.strip(), mode="eval").body)
        # A negative number to a fractional power is complex; that is not an answer to speak.
        if type(result) not in (int, float) or not math.isfinite(result):
            raise ValueError("not a real number")
        text = f"{result:.10g}" if isinstance(result, float) else str(result)
        if len(text) > 60:
            raise ValueError("result too long to say")
        return text
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, RecursionError):
        return "error: I can only do arithmetic with numbers."


def run_tool(name: object, arguments: object) -> str:
    """The only code a model call can reach. Unknown names and bad arguments do nothing."""
    if name == "calculate" and isinstance(arguments, dict):
        return calculate(arguments.get("expression"))
    return "error: no such tool."


Transcribe = Callable[[bytes], Awaitable[str]]
Reply = Callable[[list[dict[str, str]]], AsyncIterator[str]]
Synthesize = Callable[[str], Awaitable[bytes]]
Detect = Callable[[bytes], bool]  # one microphone frame in, speech or not out

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
        detect: Detect | None = None,
        *,
        # shortcut: a fixed silence ends the turn, so a long thinking pause still
        # cuts the speaker off; add an end-of-turn model (Smart Turn) to fix that.
        end_silence_seconds: float = 0.5,
        min_speech_seconds: float = 0.25,
        max_utterance_seconds: float = 30.0,
        max_history_messages: int = 12,
        pace_output: bool = True,
    ) -> None:
        self._transcribe = transcribe or whisper_transcribe
        self._reply = reply or ollama_reply
        self._synthesize = synthesize
        self._detect = detect
        self._warm: asyncio.Task[None] | None = None
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
        self._ready = False
        self.closed = False

    async def start(self) -> None:
        if self._started or self.closed:
            raise RuntimeError("adapter cannot start")
        # Model files load off the event loop so other sockets and the session
        # deadline are not stalled while they do.
        self._started = True  # set first, so a second start() during the load is refused
        self._detect = self._detect or await asyncio.to_thread(default_detector)
        self._synthesize = self._synthesize or await asyncio.to_thread(default_synthesize)
        if self.closed:  # closed while loading; nothing may start after that
            return
        self._ready = True
        if self._reply is ollama_reply:
            # Loading the model takes seconds; do it while the user is still
            # getting ready to speak, not during the first reply.
            self._warm = asyncio.create_task(_warm_model())

    async def enqueue_audio(self, audio: bytes) -> None:
        if not self._ready or self.closed:
            raise RuntimeError("adapter is not ready")
        if not isinstance(audio, bytes) or not audio or len(audio) % 2 or len(audio) > 32 * 1024:
            raise ValueError("invalid PCM frame")
        seconds = len(audio) / 2 / INPUT_RATE_HZ
        if self._detect(audio):
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
        # shortcut: the browser calls this on two loud frames, before any words are
        # known, so a cough or speaker echo still stops a reply; add a resume after
        # a false interruption if that happens often.
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
        if self._warm:
            self._warm.cancel()
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
            await self._events.put(Thinking())
            await self._events.put(Transcript("user", text))
            # The model asked for the time would call a tool and then invent the
            # answer anyway, so the clock is stated as a fact in every turn.
            now = datetime.datetime.now().astimezone().strftime("%A %d %B %Y, %H:%M")
            messages = [{"role": "system", "content": f"{SYSTEM_PROMPT} It is now {now}."},
                        *self._history, {"role": "user", "content": text}]
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
        await self._events.put(Transcript("assistant", sentence.strip()))
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


def _chat_request(messages: list[dict], *, tools: bool, stream: bool = True) -> urllib.request.Request:
    body = {
        "model": os.environ.get("SUPER_AGENT_LOCAL_MODEL", "qwen3.5:9b"),
        "messages": messages, "stream": stream, "think": False, "keep_alive": "30m",
        "options": {"num_ctx": 8192, "num_predict": 200},
    }
    if tools:
        body["tools"] = TOOLS
    return urllib.request.Request(OLLAMA_CHAT_URL, json.dumps(body).encode(),
                                  {"Content-Type": "application/json"})


async def _warm_model() -> None:
    try:
        # An empty message list makes Ollama load the model and generate nothing,
        # so the first real question never queues behind a throwaway reply.
        request = _chat_request([], tools=False, stream=False)
        await asyncio.to_thread(lambda: _DIRECT.open(request, timeout=120).close())
    except Exception:
        pass  # a real turn reports the failure; warming is only an optimisation


async def _chat_stream(messages: list[dict], *, tools: bool) -> AsyncIterator[dict]:
    """Yields the message object of each streamed line from the local model."""
    request = _chat_request(messages, tools=tools)
    queue: asyncio.Queue[dict | BaseException | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    responses = []
    stopped = False

    def deliver(item: dict | BaseException | None) -> None:
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
                    message = json.loads(line).get("message")
                    if isinstance(message, dict):
                        deliver(message)
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


async def ollama_reply(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    conversation: list[dict] = list(messages)
    for round_number in range(MAX_TOOL_ROUNDS + 1):
        calls: list[dict] = []
        # The last round offers no tools, so the model must answer in words.
        stream = _chat_stream(conversation, tools=round_number < MAX_TOOL_ROUNDS)
        async with contextlib.aclosing(stream):  # closes the HTTP stream on the break below
            async for message in stream:
                if isinstance(piece := message.get("content"), str) and piece:
                    yield piece
                if isinstance(found := message.get("tool_calls"), list):
                    calls += found
                    # The model keeps writing after a tool call and makes the result
                    # up. Stop reading here; closing the stream ends that generation.
                    break
        if not calls:
            return
        # A spoken turn never needs more than two lookups, and only well-formed
        # calls are echoed back, so a malformed one cannot break the next request.
        calls = [call for call in calls if isinstance(call, dict)
                 and isinstance(call.get("function"), dict)][:2]
        conversation.append({"role": "assistant", "content": "", "tool_calls": calls})
        for call in calls:
            function = call["function"]
            conversation.append({"role": "tool", "tool_name": str(function.get("name")),
                                 "content": run_tool(function.get("name"), function.get("arguments"))})


def rms_detector(threshold: float = 0.02) -> Detect:
    return lambda audio: frame_rms(audio) >= threshold


@functools.lru_cache(maxsize=1)  # one model load per process; state stays per session
def _silero_session():
    import onnxruntime

    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    return onnxruntime.InferenceSession(
        str(MODEL_DIR / "silero_vad.onnx"), options, providers=["CPUExecutionProvider"])


def silero_detector() -> Detect:
    """Neural speech detection, so a keyboard click or a fan is not taken for a voice."""
    import numpy

    session = _silero_session()
    state = numpy.zeros((2, 1, 128), numpy.float32)
    context = numpy.zeros((1, 64), numpy.float32)
    pending = numpy.zeros(0, numpy.float32)
    rate = numpy.array(INPUT_RATE_HZ, numpy.int64)

    def detect(audio: bytes) -> bool:
        nonlocal state, context, pending
        # The model takes 512-sample windows, each prefixed with the last 64
        # samples. Samples that do not fill a window wait for the next frame.
        samples = numpy.concatenate([pending, numpy.frombuffer(audio, "<i2").astype(numpy.float32) / 32768])
        speech = False
        whole = len(samples) - len(samples) % 512
        for offset in range(0, whole, 512):
            window = samples[None, offset:offset + 512]
            output, state = session.run(
                None, {"input": numpy.concatenate([context, window], 1), "state": state, "sr": rate})
            context = window[:, -64:]
            speech = speech or float(output[0][0]) > 0.5
        pending = samples[whole:]
        return speech

    return detect


def default_detector() -> Detect:
    choice = os.environ.get("SUPER_AGENT_VAD", "silero")
    if choice == "rms":
        return rms_detector()
    if choice != "silero":
        raise RuntimeError("SUPER_AGENT_VAD must be 'silero' or 'rms'")
    return silero_detector()


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
    # Opt-in only: kokoro-onnx depends on GPL-3.0 phonemizer code and the
    # repository is MIT, so it is never the default (OD-8; requirements-kokoro.lock).
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
    choice = os.environ.get("SUPER_AGENT_TTS", "say")
    if choice == "say":
        return say_synthesize
    if choice != "kokoro":
        raise RuntimeError("SUPER_AGENT_TTS must be 'kokoro' or 'say'")
    return kokoro_synthesize()
