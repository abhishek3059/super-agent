"""Offline tests for Gemini mode in the console: selection, tools, transcripts."""
from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace as NS

import pytest

from super_agent_voice import tools
from super_agent_voice.adapter import Interrupted, Transcript, TurnComplete
from super_agent_voice.app import _adapter_from_environment
from super_agent_voice.gemini_adapter import MAX_TOOL_CALLS_PER_TURN, GeminiLiveAdapter
from test_gemini_adapter import FakeConnect, FakeSession, flag, run, sent, take


class ToolSession(FakeSession):
    def __init__(self, turns=None) -> None:
        super().__init__(turns)
        self.tool_sent: list = []
        self.gate: asyncio.Event | None = None

    async def send_realtime_input(self, **kwargs) -> None:
        if self.gate:
            await self.gate.wait()
        await super().send_realtime_input(**kwargs)

    async def send_tool_response(self, *, function_responses) -> None:
        self.tool_sent.append(function_responses)


def make(session: FakeSession) -> GeminiLiveAdapter:
    return GeminiLiveAdapter(
        "m", connect=FakeConnect(session), blob=lambda data: ("blob", data),
        tool_response=lambda call_id, name, output: (call_id, name, output),
    )


def calls(*items: tuple[str, str, object]) -> NS:
    return NS(tool_call=NS(function_calls=[NS(id=i, name=n, args=a) for i, n, a in items]),
              server_content=None, go_away=None)


async def tool_sent(session: ToolSession, count: int) -> None:
    async def poll():
        while len(session.tool_sent) < count:
            await asyncio.sleep(0)
    await asyncio.wait_for(poll(), 2)


def test_gemini_selection_needs_the_key_and_never_echoes_it(monkeypatch):
    monkeypatch.setenv("SUPER_AGENT_ADAPTER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as error:
        _adapter_from_environment()
    assert "GEMINI_API_KEY" in str(error.value)
    monkeypatch.setenv("GEMINI_API_KEY", "secret-key-value-123")
    factory = _adapter_from_environment("some-model")
    assert factory.name == "gemini-live"
    adapter = factory()
    assert isinstance(adapter, GeminiLiveAdapter)
    monkeypatch.setenv("SUPER_AGENT_ADAPTER", "fake")
    assert _adapter_from_environment().name == "fake"


def test_a_tool_call_is_run_and_answered_through_the_send_loop():
    async def scenario():
        session = ToolSession([[calls(("c1", "calculate", {"expression": "6 * 7"}),
                                       ("c2", "current_time", None))]])
        adapter = make(session)
        await adapter.start()
        await tool_sent(session, 1)
        await adapter.close()
        return session.tool_sent

    [batch] = run(scenario())
    assert batch[0] == ("c1", "calculate", "42")
    assert batch[1][:2] == ("c2", "current_time")


def test_unknown_tools_get_an_error_and_cancellations_are_ignored():
    async def scenario():
        cancel = NS(tool_call=None, tool_call_cancellation=NS(ids=["c1"]), server_content=None, go_away=None)
        session = ToolSession([[calls(("c1", "run_shell", {"command": "id"})), cancel,
                                flag(turn_complete=True)]])
        adapter = make(session)
        await adapter.start()
        await tool_sent(session, 1)
        events = await take(adapter, 1)
        await adapter.close()
        return session.tool_sent, events

    sent_, events = run(scenario())
    assert sent_ == [[("c1", "run_shell", "error: no such tool.")]]
    assert events == [TurnComplete(("unknown",))]  # never the model-chosen name


def test_a_tool_response_survives_a_full_audio_queue():
    async def scenario():
        session = ToolSession([[]])
        session.gate = asyncio.Event()
        adapter = make(session)
        await adapter.start()
        for i in range(200):  # the loop is stuck on the first frame; the queue overflows
            await adapter.enqueue_audio(bytes([i % 256, 0]))
        await asyncio.sleep(0)
        adapter._answer(calls(("c9", "calculate", {"expression": "1 + 1"})).tool_call)
        session.gate.set()
        await tool_sent(session, 1)
        await adapter.close()
        return session.tool_sent

    assert run(scenario()) == [[("c9", "calculate", "2")]]


def test_tool_calls_are_capped_per_turn_and_the_cap_resets():
    async def scenario():
        many = [("c%d" % i, "calculate", {"expression": "1 + 1"}) for i in range(MAX_TOOL_CALLS_PER_TURN + 2)]
        session = ToolSession([[calls(*many), flag(turn_complete=True), calls(("n", "calculate", {"expression": "2 + 2"}))]])
        adapter = make(session)
        await adapter.start()
        await tool_sent(session, 2)
        await adapter.close()
        return session.tool_sent

    first, second = run(scenario())
    assert [r[2] for r in first] == ["2"] * MAX_TOOL_CALLS_PER_TURN + ["error: too many tool calls."] * 2
    assert second == [("n", "calculate", "4")]


def test_transcript_fragments_become_one_line_per_speaker_turn():
    def part(user=None, model=None):
        return flag(input_transcription=NS(text=user) if user is not None else None,
                    output_transcription=NS(text=model) if model is not None else None)

    async def scenario():
        session = FakeSession([[part(user="what is"), part(user=" two plus"), part(user=" two"),
                                part(model="Four"), part(model=", I think."), flag(turn_complete=True),
                                part(model="Hi"), flag(interrupted=True)]])
        adapter = make(session)
        await adapter.start()
        events = await take(adapter, 5)
        await adapter.close()
        return events

    assert run(scenario()) == [
        Transcript("user", "what is two plus two"), Transcript("assistant", "Four, I think."), TurnComplete(),
        Transcript("assistant", "Hi"), Interrupted(),
    ]


def test_current_time_reads_aloud_and_only_gemini_declares_it():
    assert re.fullmatch(r"[A-Z][a-z]+ \d{2} [A-Z][a-z]+ \d{4}, \d{2}:\d{2}", tools.run_tool("current_time", {}))
    assert [f["name"] for f in tools.GEMINI_FUNCTIONS] == ["calculate", "current_time"]
    assert [t["function"]["name"] for t in tools.TOOLS] == ["calculate"]
