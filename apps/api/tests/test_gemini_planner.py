"""Offline tests for the Gemini planner and its opt-in check. A fake client stands in for the SDK; no network."""
import json
import logging
import socket
import time
from types import SimpleNamespace

import pytest

from super_agent_voice import delegation, ledger, planner, planner_check
from super_agent_voice.gemini_planner import GeminiPlanner

KEY, SECRET = "KEY-abc123-secret", "PROVIDER-TEXT-secret"
PLAN = {"steps": [{"type": "read_tool", "tool": "calculate", "args": {"expression": "17*23"}},
                  {"type": "finish", "after": [0]}]}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    attempts = []

    def refuse(*args, **kwargs):
        attempts.append(1)
        raise OSError("network blocked in tests")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    yield
    assert attempts == [], "a test tried to open a network connection"


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "DB_PATH", tmp_path / "led" / "ledger.db")


class FakeClient:
    def __init__(self, reply=None, error=None):
        self.calls, self._reply, self._error = [], reply, error
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(text=self._reply)


class QuotaError(Exception):
    code = 429


def make(reply=None, error=None):
    client = FakeClient(reply, error)
    return GeminiPlanner(KEY, "m", client), client


def test_complete_returns_parsed_json_and_asks_for_json():
    model, client = make(json.dumps(PLAN))
    assert model.complete("p") == PLAN
    call = client.calls[0]
    assert call["model"] == "m" and call["contents"] == "p"
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].http_options.timeout == 20_000


def test_complete_text_returns_text():
    model, client = make("four hundred")
    assert model.complete_text("p") == "four hundred"
    assert client.calls[0]["config"].response_mime_type == "text/plain"


@pytest.mark.parametrize("error,code", [
    (OSError(SECRET + KEY), "unavailable"), (QuotaError(SECRET), "unavailable"),
    (TimeoutError(SECRET), "timeout"), (type("ReadTimeout", (Exception,), {})(SECRET), "timeout"),
])
@pytest.mark.parametrize("method", ["complete", "complete_text"])
def test_client_failures_map_to_fixed_codes_without_provider_text(error, code, method, caplog, capsys):
    model, _ = make(error=error)
    with caplog.at_level(logging.DEBUG), pytest.raises(planner.ModelError) as raised:
        getattr(model, method)("the prompt PROMPT-secret")
    assert raised.value.code == code and str(raised.value) == code and raised.value.__cause__ is None
    assert raised.value.__suppress_context__
    out = capsys.readouterr()
    for hidden in (SECRET, KEY, "PROMPT-secret"):
        assert hidden not in caplog.text + out.out + out.err + repr(raised.value)


@pytest.mark.parametrize("reply", [None, "", "  \n", "not json {" + SECRET, 7,
                                   pytest.param("x" * (planner.MAX_REPLY_CHARS + 1), id="oversized")])
def test_bad_replies_are_malformed(reply):
    model, _ = make(reply)
    with pytest.raises(planner.ModelError) as raised:
        model.complete("p")
    assert raised.value.code == "malformed" and SECRET not in repr(raised.value)


def test_oversized_text_and_non_string_prompt_are_refused():
    with pytest.raises(planner.ModelError):
        make("x" * (planner.MAX_REPLY_CHARS + 1))[0].complete_text("p")
    model, client = make("{}")
    with pytest.raises(planner.ModelError):
        model.complete(b"bytes")
    assert client.calls == []


def test_it_is_a_cloud_model_that_cannot_be_made_local():
    model, _ = make("{}")
    assert model.is_local is False
    with pytest.raises(AttributeError):
        model.is_local = True


def test_a_missing_key_or_model_is_refused_without_a_client_call():
    for args in (("", "m"), ("k", "")):
        with pytest.raises(planner.ModelError):
            GeminiPlanner(*args, client=FakeClient())


def test_the_real_client_is_built_on_the_developer_api_without_a_call(monkeypatch):
    # The SDK honours this variable; the pinned host must still win.
    monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", "https://other.example")
    client = GeminiPlanner(KEY, "m")._client
    assert client._api_client.vertexai is False
    assert str(client._api_client._http_options.base_url).startswith("https://generativelanguage.googleapis.com")
    assert "other.example" not in str(client._api_client._http_options.base_url)


def test_conversation_data_class_refuses_the_cloud_planner_with_no_client_call():
    model, client = make(json.dumps(PLAN))
    service = delegation.Service(model)  # default data class: personal
    try:
        assert service.delegate("answer", "what is 2 plus 2?", "k1") == {"refused": "personal_data_cloud_planner"}
    finally:
        service.close()
    assert client.calls == [] and ledger.list_jobs() == []


def test_check_runs_a_synthetic_job_on_a_temp_ledger_and_prints_no_text(capsys, tmp_path, monkeypatch):
    model, client = make(json.dumps(PLAN))
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    monkeypatch.setattr(planner_check, "GeminiPlanner", lambda key, name: model)
    real = ledger.DB_PATH
    seen = []
    orig = delegation.Service

    def spy(*args, **kwargs):
        seen.append(ledger.DB_PATH)
        return orig(*args, **kwargs)

    monkeypatch.setattr(delegation, "Service", spy)
    with pytest.raises(SystemExit) as done:
        planner_check.main(["--send-synthetic-task"])
    assert done.value.code == 0
    assert ledger.DB_PATH == real and seen and seen[0] != real and not seen[0].exists()
    out = capsys.readouterr().out
    summary = json.loads(out)
    assert summary["state"] == "succeeded" and summary["step_types"] == ["read_tool", "finish"]
    assert summary["model"] == planner_check.DEFAULT_MODEL
    for hidden in (KEY, planner_check.INSTRUCTION, "391"):
        assert hidden not in out
    assert client.calls[0]["contents"].count(planner_check.INSTRUCTION) == 1 and not real.exists()


def test_check_exits_nonzero_and_prints_only_the_code_when_the_model_fails(capsys, monkeypatch):
    model, _ = make(error=OSError(SECRET))
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    monkeypatch.setattr(planner_check, "GeminiPlanner", lambda key, name: model)
    with pytest.raises(SystemExit) as done:
        planner_check.main(["--send-synthetic-task"])
    out = capsys.readouterr().out
    assert done.value.code == 1 and json.loads(out)["state"] == "failed" and json.loads(out)["reason"] == "work_error"
    assert SECRET not in out and KEY not in out


class SlowClient(FakeClient):
    def __init__(self, release, reply):
        super().__init__(reply)
        self.release = release

    def _generate(self, **kwargs):
        self.release.wait(5)
        return super()._generate(**kwargs)


def test_a_slow_model_never_lets_the_real_ledger_path_be_opened(monkeypatch):
    import threading

    real = ledger.DB_PATH
    release = threading.Event()
    threading.Timer(0.5, release.set).start()
    monkeypatch.setattr(planner_check, "WAIT_S", 0.1)
    monkeypatch.setattr(planner_check, "GRACE_S", 10)
    model = GeminiPlanner(KEY, "m", SlowClient(release, json.dumps(PLAN)))
    summary = planner_check.run_check(model, "m")
    assert summary["state"] != "succeeded" and summary["reason"] == "wait_timeout"
    release.wait(2)
    time.sleep(0.7)  # a worker still alive would now write to whatever path is current
    assert ledger.DB_PATH == real and not real.exists() and not real.parent.exists()


def test_a_worker_that_will_not_finish_leaves_the_path_on_the_temporary_ledger(monkeypatch):
    import threading

    real = ledger.DB_PATH
    release = threading.Event()
    monkeypatch.setattr(planner_check, "WAIT_S", 0.1)
    monkeypatch.setattr(planner_check, "GRACE_S", 0.2)
    model = GeminiPlanner(KEY, "m", SlowClient(release, json.dumps(PLAN)))
    try:
        summary = planner_check.run_check(model, "m")
        assert summary["state"] == "worker_unfinished" and ledger.DB_PATH != real
    finally:
        release.set()  # let the worker end before the path is put back by the fixture
        time.sleep(0.5)
    assert not real.exists() and not real.parent.exists()


def test_the_ledger_path_is_restored_when_the_service_cannot_start(monkeypatch):
    real = ledger.DB_PATH

    def boom(now):
        raise RuntimeError("purge failed")

    monkeypatch.setattr(ledger, "purge", boom)
    with pytest.raises(RuntimeError):
        planner_check.run_check(make("{}")[0], "m")
    assert ledger.DB_PATH == real
