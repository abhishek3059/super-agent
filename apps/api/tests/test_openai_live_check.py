from __future__ import annotations

import asyncio
import base64
import json

import pytest

from super_agent_voice import openai_live_check, openai_realtime
from super_agent_voice.adapter import AdapterError


class RealtimeFixture:
    def __init__(self, tool_name="calculate", pre_tool_audio_only=False):
        self.incoming = asyncio.Queue()
        self.tool_name = tool_name
        self.output = None
        self.closed = False
        self.frames = 0
        self.pre_tool_audio_only = pre_tool_audio_only

    def emit(self, kind, **fields):
        self.incoming.put_nowait(json.dumps({"type": kind, **fields}))

    async def send(self, text):
        event = json.loads(text)
        if event["type"] == "session.update":
            assert [tool["name"] for tool in event["session"]["tools"]] == ["calculate"]
            self.emit("session.created")
            self.emit("session.updated", session=event["session"])
        elif event["type"] == "input_audio_buffer.append":
            self.frames += 1
            if self.frames == 13:
                self.emit("response.created", response={"id": "tool-response"})
                if self.pre_tool_audio_only:
                    self.emit("response.output_audio.delta", response_id="tool-response",
                              delta=base64.b64encode(b"\x01\x00" * 10).decode())
                self.emit("response.done", response={"id": "tool-response", "status": "completed", "output": [{
                    "type": "function_call", "name": self.tool_name, "call_id": "generated-call",
                    "arguments": '{"expression":"19+23"}', "status": "completed",
                }]})
        elif event["type"] == "conversation.item.create":
            assert event["item"]["call_id"] == "generated-call"
            self.output = json.loads(event["item"]["output"])
        elif event["type"] == "response.create":
            assert self.output == {"result": "42"}
            self.emit("response.created", response={"id": "spoken-response"})
            if not self.pre_tool_audio_only:
                self.emit("response.output_audio.delta", response_id="spoken-response",
                          delta=base64.b64encode(b"\x01\x00" * 10).decode())
            self.emit("response.done", response={"id": "spoken-response", "status": "completed"})

    async def recv(self):
        return await self.incoming.get()

    async def close(self):
        self.closed = True


def test_synthetic_audio_exercises_calculator_and_closes():
    fixture = RealtimeFixture()
    result = asyncio.run(openai_live_check.exercise(b"\x01\x00" * 10, fixture, pace=0))
    assert result["calculator_verified"] and result["completed"] and result["closed"]
    assert result["output_bytes"] == 20 and fixture.closed
    assert fixture.frames == 13


def test_pre_tool_audio_does_not_count_as_the_spoken_tool_result():
    fixture = RealtimeFixture(pre_tool_audio_only=True)
    result = asyncio.run(openai_live_check.exercise(b"\x01\x00" * 10, fixture, pace=0))
    assert result["calculator_verified"] and result["completed"] and result["closed"]
    assert result["output_bytes"] == 0 and "first_output_ms" not in result


def test_unregistered_function_is_not_executed():
    fixture = RealtimeFixture("shell")
    with pytest.raises(AdapterError, match="session-failed"):
        asyncio.run(openai_live_check.exercise(b"\x01\x00" * 10, fixture, pace=0))
    assert fixture.output is None and fixture.closed


def test_wire_connect_refuses_redirects_ambient_proxy_and_verbose_logging(monkeypatch, tmp_path):
    original = openai_realtime._DirectConnect
    redirect = RuntimeError("fixture redirect")
    assert original.process_redirect(None, redirect) is redirect
    fixture = RealtimeFixture()
    actual = {}

    async def connect(uri, **kwargs):
        actual.update(uri=uri, **kwargs)
        return fixture

    monkeypatch.setattr(openai_realtime, "_DirectConnect", connect)
    keylog = tmp_path / "tls-keys"
    monkeypatch.setenv("SSLKEYLOGFILE", str(keylog))
    assert asyncio.run(openai_realtime.open_openai_transport("synthetic-fixture")) is fixture
    assert actual["uri"] == "wss://api.openai.com/v1/realtime?model=gpt-realtime-2.1"
    assert actual["proxy"] is None and actual["max_size"] == openai_realtime.MAX_MESSAGE
    assert actual["logger"].parent is None
    assert actual["ssl"].keylog_filename is None and not keylog.exists()


def test_command_requires_key_before_launching_synthesis(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["openai_live_check", "--send-synthetic-audio"])
    assert openai_live_check.main() == 2
    assert "OPENAI_API_KEY is required" in capsys.readouterr().err
