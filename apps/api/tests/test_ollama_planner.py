import json
import os
import time

import pytest
from langsmith import utils as ls_utils

from super_agent_voice import delegation, ledger, local_adapter
from super_agent_voice.adapter import AdapterError
from super_agent_voice.ollama_planner import OllamaPlanner
from super_agent_voice.planner import ModelError

PLAN = {"steps": [{"type": "read_tool", "tool": "calculate", "args": {"expression": "17*23"}},
                  {"type": "finish", "after": [0]}]}


class Replies:
    """Stands in for local_adapter._DIRECT: replays queued Ollama message texts or raises queued errors."""

    def __init__(self, replies):
        self.replies, self.bodies = list(replies), []

    def open(self, request, timeout=None):
        self.bodies.append(json.loads(request.data))
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        self.current = reply
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return json.dumps({"message": {"content": self.current}}).encode()


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "DB_PATH", tmp_path / "led" / "ledger.db")
    ls_utils.get_env_var.cache_clear()
    for key in list(os.environ):
        if key.upper().startswith(("LANGSMITH_", "LANGCHAIN_")):
            monkeypatch.delenv(key)
    monkeypatch.delenv("SUPER_AGENT_LOCAL_MODEL", raising=False)
    monkeypatch.setattr(local_adapter, "_refuse_remote_model", lambda name: None)


def fake(monkeypatch, replies):
    opener = Replies(replies)
    monkeypatch.setattr(local_adapter, "_DIRECT", opener)
    return opener


def test_complete_returns_parsed_json_and_asks_for_json_mode(monkeypatch):
    opener = fake(monkeypatch, [json.dumps(PLAN)])
    assert OllamaPlanner().complete("p") == PLAN
    assert opener.bodies[0]["format"] == "json" and opener.bodies[0]["stream"] is False


@pytest.mark.parametrize("reply", ["not json", "", "   "])
def test_bad_json_or_empty_reply_is_malformed(monkeypatch, reply):
    fake(monkeypatch, [reply])
    with pytest.raises(ModelError) as err:
        OllamaPlanner().complete("p")
    assert err.value.code == "malformed"


@pytest.mark.parametrize("error,code", [(OSError("refused"), "unavailable"), (TimeoutError("slow"), "timeout")])
def test_transport_errors_carry_fixed_codes(monkeypatch, error, code):
    fake(monkeypatch, [error])
    with pytest.raises(ModelError) as err:
        OllamaPlanner().complete("p")
    assert err.value.code == code and "refused" not in str(err.value)


def test_complete_text_returns_text(monkeypatch):
    fake(monkeypatch, ["391"])
    assert OllamaPlanner().complete_text("p") == "391"


def test_cloud_model_is_not_local_and_personal_data_is_refused(monkeypatch):
    monkeypatch.setenv("SUPER_AGENT_LOCAL_MODEL", "x:cloud")
    assert OllamaPlanner().is_local is False
    service = delegation.Service(OllamaPlanner())
    try:
        assert "refused" in service.delegate("answer", "What is 2 plus 2?", "k1")
    finally:
        service.close()


def test_a_model_ollama_will_not_vouch_for_is_not_local(monkeypatch):
    def refuse(name):
        raise AdapterError("provider-unsupported")

    monkeypatch.setattr(local_adapter, "_refuse_remote_model", refuse)
    assert OllamaPlanner().is_local is False


def test_plan_then_finish_reaches_succeeded(monkeypatch):
    fake(monkeypatch, [json.dumps(PLAN)])
    service = delegation.Service(OllamaPlanner())
    try:
        receipt = service.delegate("answer", "What is 17 times 23?", "k1")
        assert "job_id" in receipt
        end = time.monotonic() + 5
        while ledger.get_job(receipt["job_id"]).state not in ledger.TERMINAL and time.monotonic() < end:
            time.sleep(0.01)
        job = ledger.get_job(receipt["job_id"])
        assert job.state == "succeeded" and "391" in ledger.list_events(job.id)[-1].receipt["result"]
    finally:
        service.close()
