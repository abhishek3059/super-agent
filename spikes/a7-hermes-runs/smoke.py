"""Optional smoke against installed Hermes gateways and a local synthetic model."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import httpx

from super_agent_voice.hermes_runs import HermesRunsClient
from super_agent_voice.jarvis_runtime import JarvisRuntime

WORKERS = ("research", "developer", "writer", "operator", "reviewer")
ANSWER = "Omar owns the mute check."


class FixtureModel(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 1_000_000:
            self.send_error(413)
            return
        data = json.loads(self.rfile.read(size))
        envelope = {"id": "chatcmpl-jarvis-fixture", "created": int(time.time()), "model": "jarvis-fixture"}
        message = {"role": "assistant", "content": ANSWER}
        if data.get("stream"):
            def frame(delta: dict, finish: str | None) -> str:
                packet = {
                    **envelope, "object": "chat.completion.chunk",
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
                }
                return "data: " + json.dumps(packet) + "\n\n"

            wire = frame(message, None) + frame({}, "stop") + "data: [DONE]\n\n"
            content_type = "text/event-stream"
        else:
            wire = json.dumps({
                **envelope, "object": "chat.completion",
                "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            })
            content_type = "application/json"
        payload = wire.encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args) -> None:
        pass


def unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def terminate(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def start_gateway(executable: Path, profile: Path, model_port: int, stack: ExitStack) -> tuple[int, HermesRunsClient, subprocess.Popen]:
    profile.mkdir(mode=0o700)
    port = unused_port()
    credential = secrets.token_urlsafe(32)
    (profile / "config.yaml").write_text(f"""model:
  provider: custom
  default: jarvis-fixture
  api_mode: chat_completions
  base_url: http://127.0.0.1:{model_port}/v1
platform_toolsets:
  api_server: []
memory:
  memory_enabled: false
  user_profile_enabled: false
gateway:
  api_server:
    enabled: true
    host: 127.0.0.1
    port: {port}
""")
    env_file = profile / ".env"
    env_file.write_text(f"API_SERVER_KEY={credential}\nOPENAI_API_KEY=synthetic-jarvis-fixture\n")
    env_file.chmod(0o600)
    env = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "TMPDIR", "SYSTEMROOT") if key in os.environ}
    env.update(HERMES_HOME=str(profile), DO_NOT_TRACK="1")
    with (profile / "gateway.log").open("w") as log:
        process = subprocess.Popen([str(executable), "gateway", "run"], cwd=profile, env=env, stdout=log, stderr=log)
    stack.callback(terminate, process)
    return port, HermesRunsClient(port, credential), process


async def wait_for_health(port: int, process: subprocess.Popen) -> None:
    async with asyncio.timeout(90), httpx.AsyncClient(trust_env=False, timeout=0.5) as client:
        while process.poll() is None:
            try:
                response = await client.get(f"http://127.0.0.1:{port}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.25)
    raise RuntimeError("Hermes gateway exited before becoming ready")


async def exercise(gateways: dict[str, tuple[int, HermesRunsClient, subprocess.Popen]]) -> None:
    await asyncio.gather(*(wait_for_health(port, process) for port, _, process in gateways.values()))
    runtime = JarvisRuntime({name: client for name, (_, client, _) in gateways.items()})
    try:
        for name in gateways:
            request = uuid4()
            prompt = f"Jarvis synthetic fixture for {name}. Say who owns the mute check."
            job_id = runtime.submit(name, prompt, request)
            assert runtime.submit(name, prompt, request) == job_id
        async with asyncio.timeout(90):
            while True:
                jobs = runtime.snapshot()["jobs"]
                if any(job["status"] in {"cancelled", "failed", "unknown"} for job in jobs):
                    raise RuntimeError("A Hermes fixture job failed or has unknown outcome")
                if all(job["status"] == "succeeded" for job in jobs):
                    break
                await asyncio.sleep(0.25)
        run_ids = {job["receipt"]["runId"] for job in jobs if job.get("result") == ANSWER}
        if len(run_ids) != len(gateways):
            raise RuntimeError("Missing or duplicate Hermes receipts")
        print(json.dumps({"gateways": len(gateways), "verified_receipts": len(run_ids), "local_fixture": True}))
    finally:
        await runtime.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-executable", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=range(1, 6), default=1)
    args = parser.parse_args()
    executable = args.hermes_executable.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="jarvis-hermes-fixture-") as directory, ExitStack() as stack:
        model = stack.enter_context(ThreadingHTTPServer(("127.0.0.1", 0), FixtureModel))
        threading.Thread(target=model.serve_forever, daemon=True).start()
        stack.callback(model.shutdown)
        root = Path(directory)
        gateways = {
            name: start_gateway(executable, root / name, model.server_port, stack)
            for name in WORKERS[: args.workers]
        }
        asyncio.run(exercise(gateways))


if __name__ == "__main__":
    main()
