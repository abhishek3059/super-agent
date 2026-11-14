from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


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


@dataclass(frozen=True)
class Thinking:
    """The adapter heard a complete utterance and is preparing a reply."""


@dataclass(frozen=True)
class Transcript:
    """Words heard or spoken, for display in the console only; never logged."""
    role: str  # "user" or "assistant"
    text: str


@dataclass(frozen=True)
class ApprovalRequest:
    """An action waits for the user's click. The summary is built by code, never by the model."""
    id: str
    summary: str


@dataclass(frozen=True)
class ApprovalClosed:
    """The request ended for any reason (approved, denied, timed out, cancelled)."""
    id: str


AdapterEvent = (
    AudioChunk | TurnComplete | Interrupted | Thinking | Transcript | ApprovalRequest | ApprovalClosed
)

# Fixed browser-facing categories (design section 5); provider detail never
# leaves the adapter.
ERROR_CATEGORIES = frozenset({
    "provider-unavailable", "provider-limits", "provider-unsupported",
    "provider-session-ended", "session-failed",
})


class AdapterError(Exception):
    """Carries a fixed category only, never provider detail."""

    def __init__(self, category: str) -> None:
        self.category = category if category in ERROR_CATEGORIES else "session-failed"
        super().__init__(self.category)


class VoiceAdapter(Protocol):
    name: str
    output_rate_hz: int

    async def start(self) -> None: ...

    async def enqueue_audio(self, audio: bytes) -> None: ...

    async def end_audio_stream(self) -> None: ...

    async def interrupt(self) -> None: ...

    def events(self) -> AsyncIterator[AdapterEvent]: ...

    async def close(self) -> None: ...


class FakeVoiceAdapter:
    """Local streaming echo; no network, persistent audio, or provider key."""

    name = "fake"
    output_rate_hz = 16000

    def __init__(self, max_input_frames: int = 16) -> None:
        if max_input_frames < 1:
            raise ValueError("input queue must be bounded and nonempty")
        self._input: asyncio.Queue[tuple[int, bytes] | None] = asyncio.Queue(
            maxsize=max_input_frames
        )
        self._started = False
        self._consuming = False
        self._generation = 0
        self.closed = False
        self.interruptions = 0
        self.input_frames = 0
        self.dropped_input_frames = 0

    async def start(self) -> None:
        if self._started or self.closed:
            raise RuntimeError("adapter cannot start")
        self._started = True

    async def enqueue_audio(self, audio: bytes) -> None:
        if not self._started or self.closed:
            raise RuntimeError("adapter is not ready")
        if not isinstance(audio, bytes) or not audio or len(audio) % 2 or len(audio) > 32 * 1024:
            raise ValueError("invalid PCM frame")
        self.input_frames += 1
        if self._input.full():
            self._input.get_nowait()
            self.dropped_input_frames += 1
        self._input.put_nowait((self._generation, audio))

    async def end_audio_stream(self) -> None:
        pass

    async def events(self) -> AsyncIterator[AdapterEvent]:
        if not self._started or self._consuming:
            raise RuntimeError("adapter requires one started event consumer")
        self._consuming = True
        while not self.closed:
            frame = await self._input.get()
            if frame is None:
                return
            generation, audio = frame
            if generation != self._generation:
                continue
            yield AudioChunk(data=audio, rate_hz=self.output_rate_hz)
            # A control may interrupt between the audio and turn events.
            if generation == self._generation and not self.closed:
                yield TurnComplete()

    async def interrupt(self) -> None:
        if not self.closed:
            self.interruptions += 1
            self._generation += 1
            self._clear_input()

    async def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self._clear_input()
        self._input.put_nowait(None)

    def _clear_input(self) -> None:
        while not self._input.empty():
            self._input.get_nowait()
