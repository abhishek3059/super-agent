"""Offline OpenAI Realtime call contract through the voice bridge.

The spike requires a supplied transport. There is no dialer, credential
loader, provider selection or user microphone path in this module.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import struct
from collections.abc import AsyncIterator
from typing import Any, Protocol
from uuid import uuid4

from super_agent_voice.adapter import (
    AdapterError,
    AdapterEvent,
    AudioChunk,
    Interrupted,
    Transcript,
    TurnComplete,
)

RATE = 24_000
FRAME_BYTES = 32 * 1024
MAX_PCM_MESSAGE_BYTES = 256 * 1024


class Transport(Protocol):
    async def send(self, text: str) -> None: ...
    async def recv(self) -> str: ...
    async def close(self) -> None: ...


class Pcm16kTo24k:
    """Resample mono PCM16LE without resetting at capture-frame boundaries."""

    def __init__(self) -> None:
        self.previous: int | None = None
        # Input and output intervals are 3 and 2 ticks on a common 48 kHz clock.
        self.offset = 2

    def convert(self, audio: bytes) -> bytes:
        output: list[int] = []
        for (sample,) in struct.iter_unpack("<h", audio):
            if self.previous is None:
                output.append(sample)
            else:
                while self.offset <= 3:
                    output.append(self.previous + (sample - self.previous) * self.offset // 3)
                    self.offset += 2
                self.offset -= 3
            self.previous = sample
        return struct.pack(f"<{len(output)}h", *output)


class OpenAIRealtimeProbe:
    name = "openai-realtime-probe"
    output_rate_hz = RATE

    def __init__(self, transport: Transport, output_frame_bytes: int = FRAME_BYTES) -> None:
        if (
            type(output_frame_bytes) is not int
            or not 2 <= output_frame_bytes <= FRAME_BYTES
            or output_frame_bytes % 2
        ):
            raise ValueError("output_frame_bytes must be an even PCM16 frame size within the bridge cap")
        self.transport = transport
        self.output_frame_bytes = output_frame_bytes
        self.input_resampler = Pcm16kTo24k()
        self.caption_item_id: str | None = None
        self.response_id: str | None = None
        self.awaiting_response = False
        self.cancel_on_start = False
        self.interrupted = False
        self.cancel_request: tuple[str, str] | None = None

    async def _send(self, event_type: str, **fields: object) -> None:
        await self.transport.send(json.dumps({"type": event_type, **fields}))

    async def _receive(self) -> dict[str, Any]:
        message = await self.transport.recv()
        if not isinstance(message, str) or len(message) > 4 * MAX_PCM_MESSAGE_BYTES // 3 + 4096:
            raise AdapterError("session-failed")
        try:
            event = json.loads(message)
        except (ValueError, RecursionError):
            raise AdapterError("session-failed") from None
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise AdapterError("session-failed")
        if event["type"] == "error":
            error = event.get("error")
            code = error.get("code") if isinstance(error, dict) else None
            if code in ("rate_limit_exceeded", "insufficient_quota", "credit_balance_exhausted"):
                raise AdapterError("provider-limits")
            if code == "model_not_found":
                raise AdapterError("provider-unsupported")
            if isinstance(error, dict) and self.cancel_request is not None:
                event_id, response_id = self.cancel_request
                if error.get("event_id") == event_id and self.response_id != response_id:
                    # The terminal event already settled the same response.
                    self.cancel_request = None
                    return event
            raise AdapterError("session-failed")
        return event

    async def start(self) -> None:
        pcm = {"type": "audio/pcm", "rate": RATE}
        detection = {"type": "server_vad", "create_response": True, "interrupt_response": True}
        await self._send("session.update", session={
            "type": "realtime",
            "output_modalities": ["audio"],
            "tools": [],
            "tool_choice": "none",
            "audio": {
                "input": {"format": pcm, "turn_detection": detection},
                "output": {"format": pcm},
            },
        })
        try:
            async with asyncio.timeout(2):
                event = await self._receive()
                if event["type"] == "session.created":
                    event = await self._receive()
        except TimeoutError:
            raise AdapterError("provider-unavailable") from None
        try:
            session = event["session"]
            audio = session["audio"]
            actual_detection = audio["input"]["turn_detection"]
            negotiated = (
                event["type"] == "session.updated"
                and session["type"] == "realtime"
                and session["output_modalities"] == ["audio"]
                and session["tools"] == [] and session["tool_choice"] == "none"
                and audio["input"]["format"] == pcm and audio["output"]["format"] == pcm
                and isinstance(actual_detection, dict)
                and actual_detection.get("type") == "server_vad"
                and actual_detection.get("create_response") is True
                and actual_detection.get("interrupt_response") is True
            )
        except (KeyError, TypeError):
            negotiated = False
        if not negotiated:
            raise AdapterError("provider-unsupported")

    async def enqueue_audio(self, audio: bytes) -> None:
        if not audio or len(audio) % 2 or len(audio) > FRAME_BYTES:
            raise AdapterError("session-failed")
        pcm = self.input_resampler.convert(audio)
        await self._send("input_audio_buffer.append", audio=base64.b64encode(pcm).decode("ascii"))

    async def end_audio_stream(self) -> None:
        self.input_resampler = Pcm16kTo24k()
        self.caption_item_id = None
        await self._send("input_audio_buffer.clear")

    async def interrupt(self) -> None:
        if self.response_id is not None and not self.interrupted:
            self.interrupted = True
            await self._cancel(self.response_id)
        elif self.awaiting_response:
            self.cancel_on_start = True

    async def _cancel(self, response_id: str) -> None:
        event_id = uuid4().hex
        self.cancel_request = (event_id, response_id)
        await self._send("response.cancel", event_id=event_id, response_id=response_id)

    async def close(self) -> None:
        await self.transport.close()

    async def events(self) -> AsyncIterator[AdapterEvent]:
        while True:
            event = await self._receive()
            kind = event["type"]
            if kind == "input_audio_buffer.committed":
                self.awaiting_response = True
                item_id = event.get("item_id")
                self.caption_item_id = item_id if isinstance(item_id, str) and 0 < len(item_id) <= 128 else None
            elif kind == "conversation.item.input_audio_transcription.completed":
                if self.caption_item_id is not None and event.get("item_id") == self.caption_item_id:
                    self.caption_item_id = None
                    caption = event.get("transcript")
                    if isinstance(caption, str) and caption[:500].strip():
                        yield Transcript("user", caption[:500])
            elif kind == "input_audio_buffer.speech_started":
                if not self.interrupted:
                    self.interrupted = self.response_id is not None
                    yield Interrupted()
            elif kind in ("response.created", "response.done"):
                response = event.get("response")
                identifier = response.get("id") if isinstance(response, dict) else None
                if not isinstance(identifier, str) or not identifier or len(identifier) > 128:
                    raise AdapterError("session-failed")
                if kind == "response.created":
                    if self.response_id is not None:
                        raise AdapterError("session-failed")
                    self.response_id, self.interrupted = identifier, self.cancel_on_start
                    self.awaiting_response = False
                    self.cancel_on_start = False
                    if self.interrupted:
                        await self._cancel(identifier)
                elif identifier == self.response_id:
                    status = response.get("status")
                    was_interrupted = self.interrupted
                    self.response_id, self.interrupted = None, False
                    if status == "completed" and not was_interrupted:
                        yield TurnComplete()
                    elif status == "cancelled" and not was_interrupted:
                        yield Interrupted()
                    elif status not in ("completed", "cancelled"):
                        raise AdapterError("session-failed")
            elif kind in ("response.output_audio.delta", "response.output_audio_transcript.done"):
                if self.response_id is None or event.get("response_id") != self.response_id or self.interrupted:
                    continue
                if kind == "response.output_audio_transcript.done":
                    caption = event.get("transcript")
                    if isinstance(caption, str) and caption[:500].strip():
                        yield Transcript("assistant", caption[:500])
                    continue
                delta = event.get("delta")
                if not isinstance(delta, str):
                    raise AdapterError("session-failed")
                try:
                    pcm = base64.b64decode(delta, validate=True)
                except (binascii.Error, ValueError):
                    raise AdapterError("session-failed") from None
                if not pcm or len(pcm) % 2 or len(pcm) > MAX_PCM_MESSAGE_BYTES:
                    raise AdapterError("session-failed")
                for offset in range(0, len(pcm), self.output_frame_bytes):
                    if self.interrupted:
                        break
                    yield AudioChunk(pcm[offset : offset + self.output_frame_bytes], RATE)
                    # Give the bridge sender and local controls a turn during a burst.
                    await asyncio.sleep(0)
