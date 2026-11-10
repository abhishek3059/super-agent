"""Streaming voice adapter seam (design section 4) and the offline fake."""
from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Protocol, Union

INPUT_RATE_HZ = 16000
MAX_INPUT_FRAMES = 64


@dataclass(frozen=True)
class AudioChunk:
    data: bytes
    rate_hz: int


@dataclass(frozen=True)
class TurnComplete:
    pass


@dataclass(frozen=True)
class Interrupted:
    pass


AdapterEvent = Union[AudioChunk, TurnComplete, Interrupted]

# Fixed browser-facing categories (design section 5). Provider detail never
# leaves the adapter.
ERROR_CATEGORIES = frozenset(
    {
        "provider-unavailable",
        "provider-limits",
        "provider-unsupported",
        "provider-session-ended",
        "session-failed",
    }
)


class AdapterError(Exception):
    """Raised by an adapter with a fixed category only."""

    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category if category in ERROR_CATEGORIES else "session-failed"


class VoiceAdapter(Protocol):
    name: str
    output_rate_hz: int

    async def start(self) -> None: ...

    async def enqueue_audio(self, audio: bytes) -> None: ...

    async def end_audio_stream(self) -> None: ...

    async def interrupt(self) -> None: ...

    def events(self) -> AsyncIterator[AdapterEvent]: ...

    async def close(self) -> None: ...


class AudioInputQueue:
    """Bounded input queue; drops the oldest frame because stale audio is worse than a gap."""

    def __init__(self, max_frames: int = MAX_INPUT_FRAMES) -> None:
        self._frames: deque[bytes] = deque(maxlen=max_frames)
        self._ready = asyncio.Event()
        self.dropped = 0

    def put(self, frame: bytes) -> None:
        if len(self._frames) == self._frames.maxlen:
            self.dropped += 1
        self._frames.append(frame)
        self._ready.set()

    async def get(self) -> bytes:
        while not self._frames:
            self._ready.clear()
            await self._ready.wait()
        return self._frames.popleft()


_CLOSED = object()


class FakeVoiceAdapter:
    """Deterministic offline adapter.

    By default it echoes each input frame as one chunk followed by a turn
    completion. Tests can instead pass a script of events (or exceptions)
    that `events()` yields in order.
    """

    name = "fake"
    output_rate_hz = INPUT_RATE_HZ

    def __init__(
        self,
        script: Iterable[AdapterEvent | Exception] | None = None,
        echo: bool = True,
        start_error: str | None = None,
        start_delay: float = 0.0,
    ) -> None:
        self._events: asyncio.Queue[object] = asyncio.Queue()
        self._echo = echo and script is None
        self._start_error = start_error
        self._start_delay = start_delay
        for item in script or ():
            self._events.put_nowait(item)
        self.started = False
        self.closed = False
        self.interruptions = 0
        self.stream_ends = 0
        self.received: list[bytes] = []

    async def start(self) -> None:
        if self._start_delay:
            await asyncio.sleep(self._start_delay)
        if self._start_error:
            raise AdapterError(self._start_error)
        self.started = True

    async def enqueue_audio(self, audio: bytes) -> None:
        if self.closed:
            raise AdapterError("session-failed")
        self.received.append(audio)
        if self._echo:
            self._events.put_nowait(AudioChunk(bytes(audio), self.output_rate_hz))
            self._events.put_nowait(TurnComplete())

    async def end_audio_stream(self) -> None:
        self.stream_ends += 1

    async def interrupt(self) -> None:
        if not self.closed:
            self.interruptions += 1

    def push(self, item: AdapterEvent | Exception) -> None:
        """Test hook: emit an event or raise an error from `events()`."""
        self._events.put_nowait(item)

    async def events(self) -> AsyncIterator[AdapterEvent]:
        while True:
            item = await self._events.get()
            if item is _CLOSED:
                return
            if isinstance(item, Exception):
                raise item
            yield item  # type: ignore[misc]

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            self._events.put_nowait(_CLOSED)
