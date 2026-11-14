"""State-only status lines: present, and never carrying content (REQ-12)."""
from __future__ import annotations

import asyncio
import logging

from super_agent_voice.adapter import AudioChunk, Interrupted, Transcript, TurnComplete
from super_agent_voice.app import _forward_events, _OutboundQueue, _SessionFailure, _SessionState
from super_agent_voice.config import VoiceConfig

SECRET_TEXT = "SENTINEL-transcript-words"
SECRET_ARG = "SENTINEL-tool-argument"


class Scripted:
    name = "scripted"

    async def events(self):
        yield Transcript("user", SECRET_TEXT)
        yield AudioChunk(b"\x00\x00" * 2048, 24000)
        yield TurnComplete(("calculate", "run_shell"))
        yield AudioChunk(b"\x00\x00", 24000)
        yield Interrupted()


def test_status_lines_appear_and_carry_no_content(caplog) -> None:
    caplog.set_level(logging.INFO, logger="super_agent_voice")
    state = _SessionState(deadline=9.0, last_input=0.0)

    async def scenario():
        try:
            await _forward_events(Scripted(), VoiceConfig(local_token="t" * 40), state, _OutboundQueue())
        except _SessionFailure:
            pass

    asyncio.run(scenario())
    lines = [record.getMessage() for record in caplog.records if record.name == "super_agent_voice"]
    assert lines[0].startswith("voice: turn complete adapter=scripted audio_kb=4 first_audio_ms=")
    assert lines[0].endswith("tools=[calculate,unknown]")
    assert lines[1] == "voice: interrupted adapter=scripted"
    everything = " ".join(record.getMessage() + str(record.args) for record in caplog.records)
    assert SECRET_TEXT not in everything and SECRET_ARG not in everything


def test_session_lines_for_start_failure_and_close(caplog) -> None:
    from fastapi.testclient import TestClient

    from super_agent_voice.adapter import AdapterError, FakeVoiceAdapter
    from super_agent_voice.app import create_app

    class Refusing(FakeVoiceAdapter):
        async def start(self) -> None:
            raise AdapterError("provider-limits")

    caplog.set_level(logging.INFO, logger="super_agent_voice")
    origin = "http://127.0.0.1:4200"
    token = "t" * 32
    for factory in (FakeVoiceAdapter, Refusing):
        with TestClient(create_app(VoiceConfig(local_token=token), factory), base_url=origin) as client:
            with client.websocket_connect(
                "/ws/voice", headers={"host": "127.0.0.1:8000", "origin": origin}
            ) as websocket:
                websocket.send_json({"type": "session.auth", "token": token})
                websocket.receive_json()
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "voice: adapter=fake connected in " in text
    assert text.count("start failed category=provider-limits") == 1
    assert text.count("voice: session closed adapter=fake") == 2
    assert token not in text
