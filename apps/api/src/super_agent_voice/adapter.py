from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AudioReply:
    audio: bytes
    turn_complete: bool = True


class VoiceAdapter(Protocol):
    async def send_audio(self, audio: bytes) -> AudioReply: ...

    async def interrupt(self) -> None: ...

    async def close(self) -> None: ...


class FakeVoiceAdapter:
    """Deterministic offline adapter; echoes bounded synthetic PCM."""

    def __init__(self) -> None:
        self.closed = False
        self.interruptions = 0

    async def send_audio(self, audio: bytes) -> AudioReply:
        if self.closed:
            raise RuntimeError("adapter closed")
        return AudioReply(audio=bytes(audio))

    async def interrupt(self) -> None:
        if not self.closed:
            self.interruptions += 1

    async def close(self) -> None:
        self.closed = True
