r"""Opt-in live check of the Gemini planner with one synthetic task (agent-backend slice 7).

    GEMINI_API_KEY=... python -m super_agent_voice.planner_check --send-synthetic-task

The key comes from the process environment (or a prompt). The model name comes from SUPER_AGENT_PLANNER_MODEL.
Not collected by pytest and never run by CI. It prints state, reason code, step types, timings and the model
name only: no key, prompt, plan or result text. Free-tier inputs may be used by Google for training, so the
task is a fixed synthetic constant (REQ-13). The ledger lives in a temporary folder, deleted once the worker has exited.
"""
from __future__ import annotations

import argparse
import contextlib
import getpass
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

from . import delegation, ledger
from .gemini_planner import GeminiPlanner

INSTRUCTION = "What is 17 times 23? Use the calculator, then state the answer."
DEFAULT_MODEL = "gemini-2.5-flash"  # unverified for this key and the free tier; see the implementation record
WAIT_S = 60
GRACE_S = 35  # a blocked model call ends at its own 20 s timeout, so the worker is gone by then


def _drained(service) -> bool:
    """True once every worker thread has exited. Runner.close does not wait, so join the pool here, bounded."""
    service.close()
    joiner = threading.Thread(target=service._runner._pool.shutdown, kwargs={"wait": True}, daemon=True)
    joiner.start()
    joiner.join(GRACE_S)
    return not joiner.is_alive()


def run_check(model, model_name: str) -> dict:
    """One job on a temporary ledger. Returns the printable summary; the exit code is the caller's.

    The real ledger path is restored only after the worker has exited, because a live worker's next ledger
    call would otherwise create the real ~/.super-agent/ledger.db. If it has not exited within GRACE_S, the
    path stays on the temporary folder (fail closed) and the state is `worker_unfinished`."""
    if ledger._is_postgres():
        return {"model": model_name, "state": "refused", "reason": "postgres_configured", "total_ms": 0}

    real_path, started = ledger.DB_PATH, time.monotonic()
    folder = tempfile.mkdtemp(prefix="planner-check-")
    ledger.DB_PATH = Path(folder) / "ledger.db"
    service, summary = None, {"model": model_name, "state": "refused", "reason": ""}
    try:
        service = delegation.Service(model, data_class="synthetic")
        receipt = service.delegate("answer", INSTRUCTION, "planner-check")
        summary.update(state=receipt.get("state", "refused"), reason=receipt.get("refused", ""))
        if "job_id" in receipt:
            job = ledger.get_job(receipt["job_id"])
            while job.state not in ledger.TERMINAL and time.monotonic() - started < WAIT_S:
                time.sleep(0.05)
                job = ledger.get_job(job.id)
            waited_out = job.state not in ledger.TERMINAL
            if waited_out:
                with contextlib.suppress(Exception):  # a stop request; the worker ends at its next step
                    service._runner.cancel(job.id)
            events = ledger.list_events(job.id)
            steps = [e.receipt for e in events if e.reason == "step"]
            summary.update(state=ledger.get_job(job.id).state,
                           reason="wait_timeout" if waited_out else "" if job.state == "succeeded" else events[-1].reason,
                           step_count=len(steps), step_types=[s["type"] for s in steps])
    finally:
        if service is None or _drained(service):
            ledger.DB_PATH = real_path
            shutil.rmtree(folder, ignore_errors=True)
        else:
            summary.update(state="worker_unfinished", reason="worker_unfinished")
    summary["total_ms"] = round((time.monotonic() - started) * 1000)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Synthetic-task check of the Gemini planner.")
    parser.add_argument("--send-synthetic-task", action="store_true", required=True,
                        help="confirm that the task is synthetic and may be sent to Google")
    parser.parse_args(argv)
    api_key = os.environ.get("GEMINI_API_KEY") or getpass.getpass("Gemini API key: ")
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set")
    name = os.environ.get("SUPER_AGENT_PLANNER_MODEL") or DEFAULT_MODEL
    summary = run_check(GeminiPlanner(api_key, name), name)
    print(json.dumps(summary), flush=True)
    sys.exit(0 if summary["state"] == "succeeded" else 1)


if __name__ == "__main__":
    main()
