import asyncio
import json
import queue
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import UUID

import pytest

from super_agent_voice.hermes_runs import HermesRunsClient, HermesRunsError, HermesStatus


JOB = UUID("4f1539a1-b3a2-4563-a397-3d1ab2423637")
RUN = "run_" + "a1" * 16
OTHER_RUN = "run_" + "b2" * 16
BEARER = "synthetic-test-hermes-loopback-bearer-0123456789"


@dataclass
class Reply:
    status: int
    body: dict | bytes
    headers: dict[str, str] = field(default_factory=dict)
    drip: bool = False


@pytest.fixture
def gateway():
    replies = queue.Queue()
    requests = queue.Queue()

    class FixtureHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def handle_request(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            requests.put((self.command, self.path, self.headers, body))
            try:
                reply = replies.get_nowait()
            except queue.Empty:
                reply = Reply(418, {})
            content = reply.body if isinstance(reply.body, bytes) else json.dumps(reply.body).encode()
            self.send_response(reply.status)
            headers = {"Content-Type": "application/json", "Content-Length": str(len(content)), **reply.headers}
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            try:
                if reply.drip:
                    for value in content:
                        self.wfile.write(bytes((value,)))
                        self.wfile.flush()
                        time.sleep(0.04)
                else:
                    self.wfile.write(content)
            except OSError:
                pass  # Malformed or too-large replies may make the client close early.

        do_POST = do_GET = handle_request

    with ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield server.server_port, replies, requests
        finally:
            server.shutdown()
            thread.join()


def run_status(status: str, **extra) -> dict:
    return {"object": "hermes.run", "run_id": RUN, "status": status, **extra}


@pytest.mark.asyncio
async def test_create_replays_an_identical_admission_and_ignores_environment_proxy(gateway, monkeypatch):
    port, replies, requests = gateway
    for name in ("HTTP_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    replies.put(Reply(202, {"run_id": RUN, "status": "started", "replayed": False}))
    replies.put(Reply(202, {"run_id": RUN, "status": "completed", "replayed": True, "output": "Untrusted"}))
    client = HermesRunsClient(port, BEARER)
    for replayed, expected in [(False, HermesStatus.STARTED), (True, HermesStatus.COMPLETED)]:
        receipt = await client.create(JOB, "Summarize the synthetic fixture")
        assert (receipt.run_id, receipt.status, receipt.replayed, receipt.output) == (RUN, expected, replayed, None)
        method, path, headers, content = requests.get_nowait()
        assert (method, path) == ("POST", "/v1/runs")
        assert headers.get("Authorization") == f"Bearer {BEARER}"
        assert headers.get("Idempotency-Key") == str(JOB)
        assert json.loads(content) == {"input": "Summarize the synthetic fixture"}


@pytest.mark.asyncio
async def test_poll_only_canonical_completion_exposes_output_and_runtime(gateway):
    port, replies, requests = gateway
    replies.put(Reply(200, run_status("running", output="Not done", error="Discard me")))
    replies.put(Reply(200, run_status(
        "completed", completed=True, partial=False, interrupted=False, output="Synthetic receipt",
        runtime={"provider": "openai-codex", "model": "example/model", "requested": {"model": "other"}},
    )))
    client = HermesRunsClient(port, BEARER)
    running = await client.poll(RUN)
    assert running.status is HermesStatus.RUNNING and not running.terminal and running.output is None
    result = await client.poll(RUN)
    assert result.status is HermesStatus.COMPLETED and result.terminal
    assert (result.run_id, result.output, result.provider, result.model) == (
        RUN, "Synthetic receipt", "openai-codex", "example/model",
    )
    for _ in range(2):
        method, path, headers, body = requests.get_nowait()
        assert (method, path, body) == ("GET", f"/v1/runs/{RUN}", b"")
        assert headers.get("Idempotency-Key") is None


@pytest.mark.asyncio
async def test_stop_acknowledgment_means_stopping_until_a_terminal_receipt(gateway):
    port, replies, requests = gateway
    replies.put(Reply(200, {"run_id": RUN, "status": "stopping"}))
    replies.put(Reply(200, run_status("cancelled", output="discarded")))
    client = HermesRunsClient(port, BEARER)
    ack = await client.stop(RUN)
    assert (ack.status, ack.output, ack.terminal) == (HermesStatus.STOPPING, None, False)
    assert requests.get_nowait()[:2] == ("POST", f"/v1/runs/{RUN}/stop")
    receipt = await client.stop(RUN)
    assert (receipt.status, receipt.output, receipt.terminal) == (HermesStatus.CANCELLED, None, True)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["waiting_for_approval", "failed", "incomplete", "interrupted", "cancelled"])
async def test_poll_never_uses_output_from_noncompleted_runs(gateway, status):
    port, replies, _ = gateway
    replies.put(Reply(200, run_status(status, output=BEARER, error=BEARER)))
    result = await HermesRunsClient(port, BEARER).poll(RUN)
    assert result.status == status
    assert result.output is None
    assert BEARER not in repr(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", [
    Reply(200, run_status("complete")),
    Reply(200, run_status("completed", output="No completion flags")),
    Reply(200, run_status("completed", completed=True, partial=True, interrupted=False, output="Partial result")),
    Reply(200, run_status("completed", completed=True, partial=False, interrupted=True, output="Interrupted result")),
    Reply(200, run_status("completed", completed=True, partial=False, interrupted=False, output=BEARER)),
    Reply(200, run_status("completed", completed=True, partial=False, interrupted=False, output="é" * 13000)),
    Reply(200, {"object": "hermes.run", "run_id": OTHER_RUN, "status": "running"}),
    Reply(200, run_status("running"), {"Content-Type": "text/html"}),
    Reply(200, run_status("running"), {"Content-Encoding": "gzip"}),
    Reply(200, b"{" * (129 * 1024)),
    Reply(200, b'{"status":"running","status":"completed"}'),
    Reply(200, b"not JSON"),
])
async def test_poll_rejects_ambiguous_malformed_mismatched_or_unbounded_receipts(gateway, reply):
    port, replies, _ = gateway
    replies.put(reply)
    with pytest.raises(HermesRunsError) as raised:
        await HermesRunsClient(port, BEARER).poll(RUN)
    assert raised.value.outcome_unknown
    assert raised.value.category == "protocol-error"
    assert BEARER not in repr(raised.value)


@pytest.mark.asyncio
async def test_does_not_follow_redirect_even_to_same_gateway(gateway):
    port, replies, requests = gateway
    replies.put(Reply(307, {"error": BEARER}, {"Location": "/sensitive-redirect"}))
    with pytest.raises(HermesRunsError, match="^protocol-error$"):
        await HermesRunsClient(port, BEARER).create(JOB, "Synthetic fixture")
    assert requests.get_nowait()[:2] == ("POST", "/v1/runs")
    assert requests.empty()


@pytest.mark.asyncio
async def test_distinguishes_refused_admission_from_unknown_existing_run(gateway):
    port, replies, _ = gateway
    for status in (429, 409, 404):
        replies.put(Reply(status, {"error": BEARER}))
    client = HermesRunsClient(port, BEARER)
    with pytest.raises(HermesRunsError, match="^busy$") as rejected:
        await client.create(JOB, "Synthetic fixture")
    assert not rejected.value.outcome_unknown
    with pytest.raises(HermesRunsError, match="^conflict$") as conflict:
        await client.create(JOB, "Different synthetic fixture")
    assert conflict.value.outcome_unknown
    with pytest.raises(HermesRunsError, match="^run-unavailable$") as missing:
        await client.stop(RUN)
    assert missing.value.outcome_unknown


@pytest.mark.asyncio
async def test_request_deadline_bounds_stream_that_keeps_sending_bytes(gateway):
    port, replies, requests = gateway
    replies.put(Reply(202, {"run_id": RUN, "status": "started", "replayed": False}, drip=True))
    client = HermesRunsClient(port, BEARER, timeout_seconds=0.5)
    async with asyncio.timeout(2):
        with pytest.raises(HermesRunsError, match="^timeout$") as raised:
            await client.create(JOB, "Synthetic fixture")
    assert raised.value.outcome_unknown
    assert requests.get_nowait()[:2] == ("POST", "/v1/runs")
    assert requests.empty()


@pytest.mark.asyncio
async def test_rejects_unsafe_paths_and_oversized_inputs_before_network(gateway):
    port, _, requests = gateway
    client = HermesRunsClient(port, BEARER)
    with pytest.raises(ValueError, match="identifier"):
        await client.stop(f"{RUN}/../sensitive")
    with pytest.raises(ValueError, match="size limit"):
        await client.create(JOB, "é" * 4097)
    with pytest.raises(ValueError, match="size limit") as rejected:
        await client.create(JOB, f"Fixture with a reflected credential: {BEARER}")
    assert BEARER not in str(rejected.value)
    assert requests.empty()


@pytest.mark.parametrize("port, bearer, timeout", [
    ("https://example.test", BEARER, 1), (80, BEARER, 1), (8642, "short", 1),
    (8642, BEARER + "\r\nInjected", 1), (8642, BEARER, float("inf")), (8642, "a" * 32, 1),
])
def test_rejects_remote_or_invalid_runtime_configuration(port, bearer, timeout):
    with pytest.raises(ValueError) as raised:
        HermesRunsClient(port, bearer, timeout_seconds=timeout)
    assert BEARER not in str(raised.value)
