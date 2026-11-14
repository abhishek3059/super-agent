"""Gemini Live adapter behind the streaming seam (design section 6).

The `google-genai` SDK is imported only when a real session starts, so offline
tests and CI need no provider dependency. Tests inject `connect` and `blob`.
No reconnect, session resumption, or context compression in this slice.
"""
from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from typing import Any

from .adapter import AdapterError, AdapterEvent, AudioChunk, Interrupted, Transcript, TurnComplete
from .tools import GEMINI_FUNCTIONS, run_tool

INPUT_RATE_HZ = 16000
OUTPUT_RATE_HZ = 24000
MAX_INPUT_FRAMES = 64
MAX_TOOL_CALLS_PER_TURN = 4
MAX_TRANSCRIPT_CHARS = 2000
INPUT_MIME = f"audio/pcm;rate={INPUT_RATE_HZ}"
SYSTEM_INSTRUCTION = (
    "You are a concise voice assistant. Keep answers short. You have two tools: calculate, "
    "for arithmetic, and current_time, for the local date and time. Use them instead of "
    "guessing. You cannot take any other action or look anything up, and you must never "
    "say you did."
)

TOOL_NAME_ALLOWLIST = frozenset(declaration["name"] for declaration in GEMINI_FUNCTIONS)

Connect = Callable[[], Any]  # returns an async context manager yielding a session
Blob = Callable[[bytes], Any]
ToolResponse = Callable[[Any, str, str], Any]  # (call id, tool name, output) -> response object
_WAKE = object()  # tells the send loop that a tool response is waiting


def classify(error: BaseException) -> str:
    """Reduce any provider failure to a fixed category; never forwards detail."""
    if isinstance(error, AdapterError):
        return error.category
    code = getattr(error, "code", None) or getattr(error, "status_code", None)
    status = str(getattr(error, "status", "") or "").upper()
    if code == 429 or status == "RESOURCE_EXHAUSTED":
        return "provider-limits"
    # 1008 is the close code the Live API sent for an unknown model (observed 2026-11-12).
    if code in (400, 404, 1008) or status in ("INVALID_ARGUMENT", "NOT_FOUND", "UNIMPLEMENTED"):
        return "provider-unsupported"
    if type(error).__name__.startswith("ConnectionClosed"):
        return "provider-session-ended"
    if isinstance(error, (OSError, TimeoutError)):
        return "provider-unavailable"
    return "session-failed"


def _sdk_connect(api_key: str, model: str) -> Connect:
    def connect() -> Any:
        from google import genai  # load only for an actual provider session
        from google.genai import types

        client = genai.Client(
            api_key=api_key,
            enterprise=False,
            http_options=types.HttpOptions(base_url="https://generativelanguage.googleapis.com"),
        )
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(**declaration) for declaration in GEMINI_FUNCTIONS
            ])],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )
        return client.aio.live.connect(model=model, config=config)

    return connect


def _sdk_blob(data: bytes) -> Any:
    from google.genai import types

    return types.Blob(data=data, mime_type=INPUT_MIME)


def _sdk_tool_response(call_id: Any, name: str, output: str) -> Any:
    from google.genai import types

    return types.FunctionResponse(id=call_id, name=name, response={"output": output})


class GeminiLiveAdapter:
    name = "gemini-live"
    output_rate_hz = OUTPUT_RATE_HZ

    def __init__(
        self,
        model: str,
        api_key: str = "",
        *,
        connect: Connect | None = None,
        blob: Blob | None = None,
        tool_response: ToolResponse | None = None,
        interrupt_timeout: float = 5.0,
    ) -> None:
        if connect is None and not api_key:
            raise AdapterError("provider-unavailable")
        self._connect = connect or _sdk_connect(api_key, model)
        self._blob = blob or _sdk_blob
        self._tool_response = tool_response or _sdk_tool_response
        self._interrupt_timeout = interrupt_timeout
        # None is the end-of-stream marker, ordered after queued audio.
        self._input: asyncio.Queue[Any] = asyncio.Queue(MAX_INPUT_FRAMES)
        # Tool responses must never be dropped like stale audio, so they wait here
        # (bounded by the per-turn cap) and the send loop serves them first.
        self._tool_out: asyncio.Queue[list[Any]] = asyncio.Queue()
        self._tool_calls = 0
        self._turn_tools: list[str] = []  # allowlisted names only, never arguments or outputs
        self._turn_spoke = False  # whether this reply has sent any audio yet
        self._said = ""  # transcript fragments of one speaker, joined into a line
        self._said_role = ""
        self._events: asyncio.Queue[
            tuple[int, AudioChunk] | Transcript | TurnComplete | Interrupted | AdapterError | None
        ] = asyncio.Queue()
        self._audio_epoch = 0
        self._stack = contextlib.AsyncExitStack()
        self._session: Any = None
        self._tasks: list[asyncio.Task[None]] = []
        self._stream_open = False
        self._turn_active = False
        self._ack = asyncio.Event()
        self._ack_task: asyncio.Task[None] | None = None
        self._release: asyncio.Task[None] | None = None
        self.closed = False

    async def start(self) -> None:
        if self.closed:  # a late start would open a session nothing closes
            raise AdapterError("session-failed")
        try:
            self._session = await self._stack.enter_async_context(self._connect())
        except Exception as error:
            raise AdapterError(classify(error)) from None
        if self.closed:  # closed while connecting: that close saw nothing to release
            with contextlib.suppress(Exception):
                await self._stack.aclose()
            raise AdapterError("session-failed")
        self._tasks = [
            asyncio.create_task(self._send_loop()),
            asyncio.create_task(self._receive_loop()),
        ]

    async def enqueue_audio(self, audio: bytes) -> None:
        if self.closed:
            raise AdapterError("session-failed")
        self._put(audio)

    async def end_audio_stream(self) -> None:
        # Through the send loop so only one task calls the session.
        # shortcut: under overload drop-oldest can evict this marker, delaying
        # the stream end to the next mute; use a flag if that shows up live.
        if not self.closed:
            self._put(None)

    async def interrupt(self) -> None:
        if self.closed:
            return
        # Even a completed turn may have PCM waiting for the event consumer.
        self._audio_epoch += 1
        if not self._turn_active:
            return
        # Otherwise the provider must confirm with `interrupted` or a turn
        # completion, or the session fails closed instead of pretending.
        self._put(None)
        # A fresh event per timer: an ack for an earlier turn must not satisfy
        # this one. A pending timer is kept so repeats cannot extend it.
        if self._ack_task is None or self._ack_task.done() or self._ack.is_set():
            self._ack = asyncio.Event()
            self._ack_task = asyncio.create_task(self._await_ack(self._ack))

    async def events(self) -> AsyncIterator[AdapterEvent]:
        while True:
            item = await self._events.get()
            if item is None:
                return
            if isinstance(item, AdapterError):
                raise item
            if isinstance(item, tuple):
                epoch, chunk = item
                if epoch == self._audio_epoch:
                    yield chunk
                continue
            yield item

    async def close(self) -> None:
        self.closed = True
        # The app cancels a slow close, retries once, and reads a clean return
        # as confirmed closure. Shielding one shared release makes that true.
        if self._release is None:
            self._release = asyncio.create_task(self._release_session())
        await asyncio.shield(self._release)

    async def _release_session(self) -> None:
        tasks = [*self._tasks, *([self._ack_task] if self._ack_task else [])]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await self._stack.aclose()
        except Exception:
            # The bridge may release its session slot only after a clean close.
            raise AdapterError("session-failed") from None
        finally:
            self._events.put_nowait(None)

    def _put(self, item: Any) -> None:
        # Stale audio is worse than a gap, so a full queue drops the oldest.
        if self._input.full():
            self._input.get_nowait()
        self._input.put_nowait(item)

    def _fail(self, category: str) -> None:
        if not self.closed:
            self._events.put_nowait(AdapterError(category))

    async def _await_ack(self, ack: asyncio.Event) -> None:
        try:
            await asyncio.wait_for(ack.wait(), self._interrupt_timeout)
        except TimeoutError:
            self._fail("session-failed")

    async def _send_loop(self) -> None:
        try:
            while True:
                frame = await self._input.get()
                while not self._tool_out.empty():
                    await self._session.send_tool_response(function_responses=self._tool_out.get_nowait())
                if frame is _WAKE:
                    continue
                if frame is None:
                    if self._stream_open:
                        self._stream_open = False
                        await self._session.send_realtime_input(audio_stream_end=True)
                    continue
                self._stream_open = True
                await self._session.send_realtime_input(audio=self._blob(frame))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._fail(classify(error))

    async def _receive_loop(self) -> None:
        try:
            while True:
                received = False
                # The SDK's receive() ends after each model turn; loop to keep listening.
                async for response in self._session.receive():
                    received = True
                    if getattr(response, "go_away", None) is not None:
                        self._fail("provider-session-ended")
                        return
                    # tool_call_cancellation is ignored: tools run instantly, nothing is pending.
                    self._answer(getattr(response, "tool_call", None))
                    self._map(getattr(response, "server_content", None))
                if not received:
                    self._fail("provider-session-ended")
                    return
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._fail(classify(error))

    def _answer(self, tool_call: Any) -> None:
        calls = getattr(tool_call, "function_calls", None) or ()
        responses = []
        for call in calls:
            name = getattr(call, "name", None)
            self._tool_calls += 1
            self._turn_tools.append(name if name in TOOL_NAME_ALLOWLIST else "unknown")
            if self._tool_calls > MAX_TOOL_CALLS_PER_TURN:
                output = "error: too many tool calls."
            else:
                output = run_tool(name, getattr(call, "args", None) or {})
            responses.append(self._tool_response(getattr(call, "id", None), name if isinstance(name, str) else "", output))
        if responses:
            self._tool_out.put_nowait(responses)
            self._put(_WAKE)

    def _say(self, role: str, fragment: Any) -> None:
        """Gemini sends words in fragments; one line per speaker turn reaches the console."""
        if not isinstance(fragment, str):
            return
        if role != self._said_role:
            self._flush_said()
            self._said_role = role
        self._said = (self._said + fragment)[:MAX_TRANSCRIPT_CHARS]

    def _flush_said(self) -> None:
        text = self._said.strip()
        if text:
            self._events.put_nowait(Transcript(self._said_role, text))
        self._said = ""
        self._said_role = ""

    def _map(self, content: Any) -> None:
        if content is None:
            return
        self._say("user", getattr(getattr(content, "input_transcription", None), "text", None))
        self._say("assistant", getattr(getattr(content, "output_transcription", None), "text", None))
        turn = getattr(content, "model_turn", None)
        for part in getattr(turn, "parts", None) or ():
            data = getattr(getattr(part, "inline_data", None), "data", None)
            if data:
                self._turn_active = True
                self._turn_spoke = True
                # The bridge already advanced its playback epoch at local stop.
                # Until the provider settles that turn, its PCM is still stale.
                if self._ack_task is None or self._ack.is_set():
                    self._events.put_nowait((self._audio_epoch, AudioChunk(bytes(data), OUTPUT_RATE_HZ)))
        if getattr(content, "interrupted", False):
            self._flush_said()
            self._tool_calls = 0
            self._turn_tools = []
            self._turn_spoke = False
            self._turn_active = False
            self._ack.set()
            self._events.put_nowait(Interrupted())
        if getattr(content, "turn_complete", False):
            self._flush_said()
            self._tool_calls = 0
            self._turn_active = False
            self._ack.set()
            # Gemini ends the turn in which it calls a tool, then speaks the answer in a
            # second turn. Reporting the first as complete told the console and the live
            # check the reply was over before a word was said. The tool names carry over.
            if self._turn_tools and not self._turn_spoke:
                return
            self._events.put_nowait(TurnComplete(tuple(self._turn_tools)))
            self._turn_tools = []
            self._turn_spoke = False
