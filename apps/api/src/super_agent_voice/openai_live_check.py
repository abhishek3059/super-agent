"""Run one bounded OpenAI Realtime session with built-in synthetic speech."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

from .adapter import AdapterError, AudioChunk, TurnComplete
from .live_check import FRAME_BYTES, speak, speak_windows
from .openai_realtime import MODEL, OpenAIRealtimeAdapter, RealtimeTool, Transport, open_openai_transport
from .tools import calculate

PHRASE = "Use the calculator tool for nineteen plus twenty-three. Say the result only."
MAX_SESSION_SECONDS = 35


def _calculate(arguments: dict[str, object]) -> dict[str, object]:
    expression = arguments.get("expression")
    if arguments.keys() != {"expression"} or not isinstance(expression, str):
        return {"error": "invalid-arguments"}
    return {"result": calculate(expression)}


async def exercise(clip: bytes, transport: Transport, *, pace: float = 0.1) -> dict[str, bool | int]:
    result: dict[str, bool | int] = {"closed": False, "completed": False, "output_bytes": 0, "calculator_verified": False}
    def calculate_and_record(args: dict[str, object]) -> dict[str, object]:
        answer = _calculate(args)
        result["calculator_verified"] = answer.get("result") == "42"
        return answer

    tool = RealtimeTool("calculate", "Evaluate arithmetic using the local calculator.", {
        "type": "object", "properties": {"expression": {"type": "string"}},
        "required": ["expression"], "additionalProperties": False,
    }, calculate_and_record)
    adapter = OpenAIRealtimeAdapter(transport, tool=tool)
    started = time.monotonic()

    async def send_input() -> None:
        # Realtime VAD needs trailing silence. The browser mute equivalent
        # clears the provider buffer and must never be used to finish speech.
        pcm = clip + bytes(12 * FRAME_BYTES)
        for offset in range(0, len(pcm), FRAME_BYTES):
            await adapter.enqueue_audio(pcm[offset : offset + FRAME_BYTES])
            await asyncio.sleep(pace)

    async def receive_output() -> None:
        async for event in adapter.events():
            if isinstance(event, AudioChunk) and result["calculator_verified"]:
                result.setdefault("first_output_ms", round((time.monotonic() - started) * 1000))
                result["output_bytes"] += len(event.data)
            elif isinstance(event, TurnComplete):
                result["completed"] = True
                return

    try:
        if not clip or len(clip) % 2 or len(clip) > 10 * 32_000:
            raise AdapterError("session-failed")
        await adapter.start()
        result["configured_ms"] = round((time.monotonic() - started) * 1000)
        sender = asyncio.create_task(send_input())
        receiver = asyncio.create_task(receive_output())
        try:
            await asyncio.gather(sender, receiver)
        finally:
            sender.cancel()
            receiver.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)
    finally:
        await adapter.close()
        result["closed"] = True
    return result


async def run(api_key: str, clip: bytes) -> dict[str, bool | int]:
    async with asyncio.timeout(MAX_SESSION_SECONDS):
        return await exercise(clip, await open_openai_transport(api_key))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send-synthetic-audio", action="store_true", required=True)
    parser.parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required in the backend process environment", file=sys.stderr)
        return 2
    try:
        generate = speak_windows if sys.platform == "win32" else speak
        result = asyncio.run(run(api_key, generate(PHRASE)))
    except AdapterError as error:
        print(json.dumps({"model": MODEL, "error": error.category}))
        return 1
    except TimeoutError:
        print(json.dumps({"model": MODEL, "error": "step-timeout"}))
        return 1
    except (OSError, ValueError, RuntimeError):
        print(json.dumps({"model": MODEL, "error": "check-failed"}))
        return 1
    print(json.dumps({"model": MODEL, **result}))
    return 0 if all(result[check] for check in ("completed", "output_bytes", "closed", "calculator_verified")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
