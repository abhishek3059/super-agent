"""Offline tests for the hosted planner and its opt-in check. A fake opener stands in for the network."""
import io
import json
import socket
import time
import urllib.error
from types import SimpleNamespace

import pytest

from super_agent_voice import delegation, hosted_planner, ledger, planner, planner_check, policy
from super_agent_voice.hosted_planner import HostedPlanner
from super_agent_voice.planner import ModelError

KEY = "KEY-abc123-secret"
URL = "https://api.openai.com/v1"
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
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "DB_PATH", tmp_path / "led" / "ledger.db")
    monkeypatch.setattr(hosted_planner, "time", SimpleNamespace(sleep=lambda s: None))
    monkeypatch.setenv("SUPER_AGENT_PLANNER_BASE_URL", URL)
    monkeypatch.setenv("SUPER_AGENT_PLANNER_MODEL", "m-1")
    monkeypatch.setenv("SUPER_AGENT_PLANNER_KEY_ENV", "TEST_PLANNER_KEY")
    monkeypatch.setenv("TEST_PLANNER_KEY", KEY)


class Reply:
    def __init__(self, content, raw=None):
        self._raw = raw or json.dumps({"choices": [{"message": {"content": content}}]}).encode()

    def read(self, n=-1):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    def __init__(self, *outcomes):
        self.outcomes, self.requests, self.timeouts = list(outcomes), [], []

    def open(self, request, timeout=None):
        self.requests.append(request)
        self.timeouts.append(timeout)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def http(code):
    return urllib.error.HTTPError(URL, code, "provider text SECRET", {}, io.BytesIO(b"SECRET"))


def use(monkeypatch, *outcomes):
    opener = FakeOpener(*outcomes)
    monkeypatch.setattr(hosted_planner, "_DIRECT", opener)
    return opener


def test_complete_parses_json_and_sends_the_expected_request(monkeypatch):
    opener = use(monkeypatch, Reply(json.dumps(PLAN)))
    assert HostedPlanner().complete("PROMPT") == PLAN
    req = opener.requests[0]
    body = json.loads(req.data)
    assert req.full_url == URL + "/chat/completions" and req.get_method() == "POST"
    assert body == {"model": "m-1", "messages": [{"role": "user", "content": "PROMPT"}],
                    "response_format": {"type": "json_object"}}
    assert req.get_header("Authorization") == f"Bearer {KEY}" and KEY not in req.full_url
    assert opener.timeouts == [hosted_planner.ATTEMPT_TIMEOUT_S]
    assert HostedPlanner().is_local is False


def test_complete_text_has_no_response_format(monkeypatch):
    opener = use(monkeypatch, Reply("hello"))
    assert HostedPlanner().complete_text("p") == "hello"
    assert "response_format" not in json.loads(opener.requests[0].data)


@pytest.mark.parametrize("base", [
    "http://api.openai.com/v1", "https://evil.example/v1", "https://u:p@api.openai.com/v1",
    "https://api.openai.com/v1?x=1", "https://api.openai.com/v1#f", "https://api.openai.com.evil.example/v1", ""])
def test_refused_base_urls_make_no_request(monkeypatch, base):
    monkeypatch.setenv("SUPER_AGENT_PLANNER_BASE_URL", base)
    opener = use(monkeypatch)
    with pytest.raises(ModelError) as caught:
        HostedPlanner().complete("p")
    assert caught.value.code == "unavailable" and opener.requests == []


def test_nvidia_host_is_allowed(monkeypatch):
    monkeypatch.setenv("SUPER_AGENT_PLANNER_BASE_URL", "https://integrate.api.nvidia.com/v1")
    use(monkeypatch, Reply("ok"))
    assert HostedPlanner().complete_text("p") == "ok"


@pytest.mark.parametrize("name,value", [
    ("SUPER_AGENT_PLANNER_MODEL", ""), ("SUPER_AGENT_PLANNER_KEY_ENV", ""),
    ("SUPER_AGENT_PLANNER_KEY_ENV", "NO_SUCH_VAR"), ("TEST_PLANNER_KEY", "")])
def test_missing_config_is_unavailable_with_no_request(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    opener = use(monkeypatch)
    with pytest.raises(ModelError) as caught:
        HostedPlanner().complete("p")
    assert caught.value.code == "unavailable" and opener.requests == []


def test_429_then_success_retries_once(monkeypatch):
    opener = use(monkeypatch, http(429), Reply("ok"))
    assert HostedPlanner().complete_text("p") == "ok" and len(opener.requests) == 2


def test_5xx_stops_after_two_retries_and_leaks_nothing(monkeypatch):
    opener = use(monkeypatch, http(503), http(500), http(502))
    with pytest.raises(ModelError) as caught:
        HostedPlanner().complete_text("p")
    assert caught.value.code == "unavailable" and len(opener.requests) == 3
    assert KEY not in repr(caught.value) and "SECRET" not in repr(caught.value)
    assert caught.value.__cause__ is None


def test_400_is_not_retried(monkeypatch):
    opener = use(monkeypatch, http(400))
    with pytest.raises(ModelError) as caught:
        HostedPlanner().complete_text("p")
    assert caught.value.code == "unavailable" and len(opener.requests) == 1


def test_timeout_is_code_timeout_after_retries(monkeypatch):
    opener = use(monkeypatch, TimeoutError(), urllib.error.URLError(TimeoutError()), TimeoutError())
    with pytest.raises(ModelError) as caught:
        HostedPlanner().complete_text("p")
    assert caught.value.code == "timeout" and len(opener.requests) == 3


def test_connection_error_is_unavailable(monkeypatch):
    use(monkeypatch, OSError(KEY), OSError(KEY), OSError(KEY))
    with pytest.raises(ModelError) as caught:
        HostedPlanner().complete_text("p")
    assert caught.value.code == "unavailable" and KEY not in repr(caught.value)


@pytest.mark.parametrize("content", ["", "   ", None, 5, "x" * (planner.MAX_REPLY_CHARS + 1)],
                         ids=["empty", "blank", "none", "int", "oversized"])
def test_bad_replies_are_malformed_and_not_retried(monkeypatch, content):
    opener = use(monkeypatch, Reply(content))
    with pytest.raises(ModelError) as caught:
        HostedPlanner().complete_text("p")
    assert caught.value.code == "malformed" and len(opener.requests) == 1


def test_non_json_content_and_bad_envelope_are_malformed(monkeypatch):
    use(monkeypatch, Reply("not json"))
    with pytest.raises(ModelError) as caught:
        HostedPlanner().complete("p")
    assert caught.value.code == "malformed"
    use(monkeypatch, Reply(None, raw=b'{"choices": []}'))
    with pytest.raises(ModelError) as caught:
        HostedPlanner().complete_text("p")
    assert caught.value.code == "malformed"


def test_worst_case_fits_inside_the_step_deadline():
    worst = (hosted_planner.MAX_RETRIES + 1) * hosted_planner.ATTEMPT_TIMEOUT_S + sum(hosted_planner.BACKOFF_S)
    assert len(hosted_planner.BACKOFF_S) == hosted_planner.MAX_RETRIES
    assert worst + 10 <= policy.Limits().step_deadline_s


def test_personal_data_is_refused_and_synthetic_succeeds(monkeypatch):
    opener = use(monkeypatch, Reply(json.dumps(PLAN)), Reply("unused"))
    refused = delegation.Service(HostedPlanner())
    receipt = refused.delegate("answer", "What is 17 times 23?", "k1")
    refused.close()
    assert "job_id" not in receipt and receipt.get("refused") and opener.requests == []

    service = delegation.Service(HostedPlanner(), data_class="synthetic")
    try:
        receipt = service.delegate("answer", "What is 17 times 23?", "k2")
        deadline = time.monotonic() + 10
        while ledger.get_job(receipt["job_id"]).state not in ledger.TERMINAL and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ledger.get_job(receipt["job_id"]).state == "succeeded"
    finally:
        service.close()


def test_check_prints_no_key_prompt_or_text(monkeypatch, capsys):
    use(monkeypatch, Reply(json.dumps(PLAN)))
    with pytest.raises(SystemExit) as done:
        planner_check.main(["--send-synthetic-task", "--hosted"])
    out = capsys.readouterr().out
    summary = json.loads(out)
    assert done.value.code == 0 and summary["state"] == "succeeded" and summary["host"] == "api.openai.com"
    assert summary["model"] == "m-1" and summary["transitions"] and summary["utc"]
    for hidden in (KEY, planner_check.HOSTED_INSTRUCTION, "391"):
        assert hidden not in out
