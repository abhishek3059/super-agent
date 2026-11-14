"""Gemini Live adapter behind the streaming seam (design section 6).

The `google-genai` SDK is imported only when a real session starts, so offline
tests and CI need no provider dependency. Tests inject `connect` and `blob`.
Long sessions: the server sends go_away and closes a connection after a limited
lifetime, so the adapter keeps the latest session resumption handle and reconnects
with it (bounded). The handle is a credential: it is never logged or emitted.
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
# Half the app's 32 KiB frame limit (a security boundary there): Gemini sometimes sends
# larger inline chunks, so the adapter splits them. Even, so pieces stay whole PCM16 samples.
MAX_OUTPUT_CHUNK_BYTES = 16 * 1024
MAX_RECONNECTS = 20  # per session; each go_away or unexpected close gets one attempt
RESUME_WAIT_S = 10.0  # how long a failed send waits for the reconnect before giving up
# Reconnecting cannot fix these, so they fail with their own category right away.
NO_RESUME = frozenset({"provider-limits", "provider-unsupported"})
INPUT_MIME = f"audio/pcm;rate={INPUT_RATE_HZ}"
SYSTEM_INSTRUCTION = (
    "You are a concise voice assistant. Keep answers short. You have two tools: calculate, "
    "for arithmetic, and current_time, for the local date and time. Use them instead of "
    "guessing. You cannot take any other action or look anything up, and you must never "
    "say you did."
)

TOOL_NAME_ALLOWLIST = frozenset(declaration["name"] for declaration in GEMINI_FUNCTIONS)

Connect = Callable[..., Any]  # () or (resumption handle) -> async context manager yielding a session
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
    # The free tier refuses sessions opened in quick succession with close code 1011 and
    # "Resource has been exhausted" (observed 2026-11-14). The text is read, never forwarded.
    if code == 1011 and "exhausted" in str(error).lower():
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
    def connect(handle: str | None = None) -> Any:
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
            session_resumption=types.SessionResumptionConfig(handle=handle),
            # Without compression, audio sessions end after a short fixed duration.
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow()
            ),
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
        self._tool_gap = False  # a tool was answered and the spoken answer has not ended yet
        self._hold = False  # hold back the provider's next turn_complete: it ends only the tool turn
        self._resume_failure = "provider-session-ended"  # what a failed reconnect reports
        self._said = ""  # transcript fragments of one speaker, joined into a line
        self._said_role = ""
        self._events: asyncio.Queue[
            tuple[int, AudioChunk] | Transcript | TurnComplete | Interrupted | AdapterError | None
        ] = asyncio.Queue()
        self._audio_epoch = 0
        self._stack = contextlib.AsyncExitStack()
        self._session: Any = None
        self._tasks: list[asyncio.Task[None]] = []
        self._handle: str | None = None  # latest resumable session handle; a credential
        self._reconnects = 0
        self._odd = b""  # a stray trailing PCM byte, joined to the next chunk of the turn
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
        if not (self._turn_active or self._tool_gap):
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
                    await self._send("send_tool_response", function_responses=self._tool_out.get_nowait())
                if frame is _WAKE:
                    continue
                if frame is None:
                    if self._stream_open:
                        self._stream_open = False
                        await self._send("send_realtime_input", audio_stream_end=True)
                    continue
                self._stream_open = True
                await self._send("send_realtime_input", audio=self._blob(frame))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._fail(classify(error))

    async def _send(self, method: str, **kwargs: Any) -> None:
        """Send audio or a tool answer; if the connection just died, retry once on the resumed one.
        A tool answer is dropped after a resume: the new session never made that call."""
        session = self._session
        try:
            await getattr(session, method)(**kwargs)
        except asyncio.CancelledError:
            raise
        except Exception:
            if not await self._resumed_from(session):
                raise
            if method == "send_realtime_input":
                await self._session.send_realtime_input(**kwargs)

    async def _resumed_from(self, dead: Any) -> bool:
        if not self._handle or self.closed:
            return False
        for _ in range(int(RESUME_WAIT_S / 0.05)):
            if self._session is not dead:
                return True
            if self._tasks[1].done():  # the receive loop gave up: no reconnect is coming
                return False
            await asyncio.sleep(0.05)
        return False

    async def _receive_loop(self) -> None:
        try:
            while True:
                received = False
                failure = "provider-session-ended"
                try:
                    # The SDK's receive() ends after each model turn; loop to keep listening.
                    async for response in self._session.receive():
                        received = True
                        self._note_handle(getattr(response, "session_resumption_update", None))
                        if getattr(response, "go_away", None) is not None and not self._handle:
                            self._fail("provider-session-ended")
                            return
                        # With a handle, keep reading: the server closes soon after go_away
                        # and the reconnect happens then, so a spoken reply can finish.
                        # tool_call_cancellation is ignored: tools run instantly, nothing is pending.
                        self._answer(getattr(response, "tool_call", None))
                        self._map(getattr(response, "server_content", None))
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    failure = classify(error)
                    if failure in NO_RESUME:
                        self._fail(failure)
                        return
                    received = False
                if received:
                    continue
                self._resume_failure = failure
                if not await self._resume():
                    self._fail(self._resume_failure)
                    return
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._fail(classify(error))

    def _note_handle(self, update: Any) -> None:
        handle = getattr(update, "new_handle", None)
        if getattr(update, "resumable", None) and isinstance(handle, str) and handle:
            self._handle = handle

    async def _resume(self) -> bool:
        """Reconnect once with the stored handle; queued input stays in place for the send loop."""
        if self.closed or not self._handle or self._reconnects >= MAX_RECONNECTS:
            return False
        self._reconnects += 1
        stack = contextlib.AsyncExitStack()
        try:
            session = await stack.enter_async_context(self._connect(self._handle))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._resume_failure = classify(error)  # a quota refusal is reported as one
            return False
        if self.closed:  # close() ran while connecting and released only the old stack
            with contextlib.suppress(Exception):
                await stack.aclose()
            return False
        old, self._stack, self._session = self._stack, stack, session
        # The provider's turn state did not survive: end any half-spoken reply for the browser.
        self._odd = b""
        while not self._tool_out.empty():  # answers to calls the new session never made
            self._tool_out.get_nowait()
        if self._turn_active or self._tool_gap:
            self._interrupted()
        else:
            self._flush_said()
        self._tool_calls = 0
        self._turn_tools = []
        self._turn_spoke = False
        self._tool_gap = self._hold = False
        self._ack.set()
        with contextlib.suppress(Exception):
            await old.aclose()
        return True

    def _answer(self, tool_call: Any) -> None:
        calls = getattr(tool_call, "function_calls", None) or ()
        responses = []
        for call in calls:
            name = getattr(call, "name", None)
            self._tool_calls += 1
            if len(self._turn_tools) < MAX_TOOL_CALLS_PER_TURN:
                self._turn_tools.append(name if name in TOOL_NAME_ALLOWLIST else "unknown")
            if self._tool_calls > MAX_TOOL_CALLS_PER_TURN:
                output = "error: too many tool calls."
            else:
                output = run_tool(name, getattr(call, "args", None) or {})
            responses.append(self._tool_response(getattr(call, "id", None), name if isinstance(name, str) else "", output))
        if responses:
            # Past the cap the reply is not held open any longer, so a model that keeps
            # calling tools cannot keep the turn from ending.
            self._tool_gap = True
            self._hold = self._tool_calls <= MAX_TOOL_CALLS_PER_TURN
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

    def _pcm_pieces(self, data: bytes) -> list[bytes]:
        """Split provider audio into even-length pieces the app accepts, in order."""
        data = self._odd + data
        keep = len(data) % 2
        self._odd = data[len(data) - keep:]
        data = data[:len(data) - keep]
        return [data[i:i + MAX_OUTPUT_CHUNK_BYTES] for i in range(0, len(data), MAX_OUTPUT_CHUNK_BYTES)]

    def _interrupted(self) -> None:
        self._flush_said()
        self._odd = b""
        self._tool_calls = 0
        self._turn_tools = []
        self._turn_spoke = False
        self._tool_gap = self._hold = False
        self._turn_active = False
        self._ack.set()
        self._events.put_nowait(Interrupted())

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
                pieces = self._pcm_pieces(bytes(data))
                # The bridge already advanced its playback epoch at local stop.
                # Until the provider settles that turn, its PCM is still stale.
                if self._ack_task is None or self._ack.is_set():
                    for piece in pieces:
                        self._events.put_nowait((self._audio_epoch, AudioChunk(piece, OUTPUT_RATE_HZ)))
        if getattr(content, "interrupted", False):
            self._interrupted()
        if getattr(content, "turn_complete", False):
            self._odd = b""  # a dangling byte cannot start the next turn
            self._flush_said()
            self._turn_active = False
            self._ack.set()
            # Gemini ends the turn in which it calls a tool, then speaks the answer in a
            # second turn. Reporting the first as complete told the console and the live
            # check the reply was over before a word was said. Only that one turn_complete
            # is held back; the tool names and the per-reply tool count carry over.
            if self._hold and not self._turn_spoke:
                self._hold = False
                return
            self._tool_gap = self._hold = False
            self._tool_calls = 0
            self._events.put_nowait(TurnComplete(tuple(self._turn_tools)))
            self._turn_tools = []
            self._turn_spoke = False
