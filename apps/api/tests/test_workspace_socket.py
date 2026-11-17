from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from super_agent_voice.app import create_app
from super_agent_voice.config import VoiceConfig
from super_agent_voice.hermes_runs import HermesRun, HermesStatus
from super_agent_voice.jarvis_runtime import JarvisRuntime
from voice_auth_helpers import auth_proof, begin_auth, send_auth

TOKEN = "workspace-fixture-token-with-extra-entropy-381"
ORIGIN = "http://127.0.0.1:4200"
HEADERS = {"host": "127.0.0.1:8000", "origin": ORIGIN}


class WorkerFixture:
    def __init__(self, result: str | None):
        self.output = result
        self.created = 0

    async def create(self, job_id, prompt):
        self.created += 1
        assert prompt == "Read release-brief.md"
        return HermesRun("run_" + job_id.hex, HermesStatus.STARTED)

    async def poll(self, run_id):
        if self.output is None:
            return HermesRun(run_id, HermesStatus.RUNNING)
        return HermesRun(run_id, HermesStatus.COMPLETED, output=self.output)

    async def stop(self, run_id):
        return HermesRun(run_id, HermesStatus.CANCELLED)


def connect(client):
    return client.websocket_connect("/ws/workspace", headers=HEADERS)


def submit(socket, worker):
    request_id = str(uuid4())
    command = {"type": "workspace.submit", "requestId": request_id,
               "workerId": worker, "prompt": "Read release-brief.md"}
    socket.send_json(command)
    assert socket.receive_json() == {"type": "workspace.admitted", "jobId": request_id}
    socket.receive_json()
    return command


def snapshot(socket):
    socket.send_json({"type": "workspace.snapshot"})
    return socket.receive_json()


def test_workspace_requires_its_own_proof_and_allows_reconnect_without_mic():
    with TestClient(create_app(VoiceConfig(local_token=TOKEN)), base_url=ORIGIN) as client:
        with connect(client) as socket:
            nonce, challenge = begin_auth(socket)
            socket.send_json({"type": "session.auth", "proof": auth_proof(TOKEN, "client", nonce, challenge["serverNonce"])})
            with pytest.raises(WebSocketDisconnect) as error:
                socket.receive_json()
            assert error.value.code == 1008
        with connect(client) as socket:
            send_auth(socket, TOKEN, purpose="workspace")
            state = socket.receive_json()
            assert state["type"] == "workspace.snapshot" and state["jobs"] == []
            assert len(state["workers"]) == 5 and {worker["status"] for worker in state["workers"]} == {"offline"}


def test_two_jobs_can_overlap_and_only_verified_completion_is_shown():
    reporter, operator = WorkerFixture("Omar, 19 November"), WorkerFixture(None)
    workspace = JarvisRuntime({"research": reporter, "operator": operator}, poll_interval_seconds=0.01)
    with TestClient(create_app(VoiceConfig(local_token=TOKEN), workspace=workspace), base_url=ORIGIN) as client:
        with connect(client) as socket:
            send_auth(socket, TOKEN, purpose="workspace")
            socket.receive_json()
            operator_request = submit(socket, "operator")
            reporter_request = submit(socket, "research")
            socket.send_json(reporter_request)
            assert socket.receive_json()["jobId"] == reporter_request["requestId"]
            socket.receive_json()
            rows = snapshot(socket)["jobs"]
            running, complete = rows
            assert running["status"] == "running" and "result" not in running
            assert complete["status"] == "succeeded" and complete["result"] == "Omar, 19 November"
            assert complete["receipt"]["status"] == "completed"
            socket.send_json({"type": "workspace.cancel", "jobId": operator_request["requestId"]})
            socket.receive_json()
            client.portal.call(asyncio.sleep, 0.02)
            assert snapshot(socket)["jobs"][0]["status"] == "cancelled"
        with connect(client) as socket:
            send_auth(socket, TOKEN, purpose="workspace")
            assert [row["status"] for row in socket.receive_json()["jobs"]] == ["cancelled", "succeeded"]
    assert reporter.created == operator.created == 1


def test_recent_completions_do_not_hide_a_running_job():
    async def exercise():
        worker = WorkerFixture("Omar, 19 November")
        workspace = JarvisRuntime({"research": worker, "operator": WorkerFixture(None)}, poll_interval_seconds=0.01)
        try:
            active = workspace.submit("operator", "Read release-brief.md", uuid4())
            for _ in range(6):
                workspace.submit("research", "Read release-brief.md", uuid4())
                await asyncio.sleep(0)
            jobs = workspace.snapshot()["jobs"]
            assert len(jobs) == 5
            assert jobs[0]["id"] == active and jobs[0]["status"] == "running"
            assert all(job["status"] == "succeeded" for job in jobs[1:])
            assert workspace.cancel(active)
        finally:
            await workspace.close()

    asyncio.run(exercise())
