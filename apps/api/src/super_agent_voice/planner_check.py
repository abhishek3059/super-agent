r"""Opt-in live check of the Gemini planner with one synthetic task (agent-backend slice 7).

    GEMINI_API_KEY=... python -m super_agent_voice.planner_check --send-synthetic-task

The key comes from the process environment (or a prompt). The model name comes from SUPER_AGENT_PLANNER_MODEL.
Not collected by pytest and never run by CI. It prints state, reason code, step types, timings and the model
name only: no key, prompt, plan or result text. Free-tier inputs may be used by Google for training, so the
task is a fixed synthetic constant (REQ-13). The ledger lives in a temporary folder deleted at exit.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from . import delegation, ledger
from .gemini_planner import GeminiPlanner

INSTRUCTION = "What is 17 times 23? Use the calculator, then state the answer."
DEFAULT_MODEL = "gemini-2.5-flash"  # unverified for this key and the free tier; see the implementation record
WAIT_S = 60


def run_check(model, model_name: str) -> dict:
    """One job on a temporary ledger. Returns the printable summary; the exit code is the caller's."""
    real_path, started = ledger.DB_PATH, time.monotonic()
    with tempfile.TemporaryDirectory() as folder:
        ledger.DB_PATH = Path(folder) / "ledger.db"
        service = delegation.Service(model, data_class="synthetic")
        try:
            receipt = service.delegate("answer", INSTRUCTION, "planner-check")
            summary = {"model": model_name, "state": receipt.get("state", "refused"), "reason": receipt.get("refused", "")}
            if "job_id" in receipt:
                job = ledger.get_job(receipt["job_id"])
                while job.state not in ledger.TERMINAL and time.monotonic() - started < WAIT_S:
                    time.sleep(0.05)
                    job = ledger.get_job(job.id)
                events = ledger.list_events(job.id)
                steps = [e.receipt for e in events if e.reason == "step"]
                summary.update(state=job.state, reason="" if job.state == "succeeded" else events[-1].reason,
                               step_count=len(steps), step_types=[s["type"] for s in steps])
        finally:
            service.close()  # waits for the worker before the temporary ledger goes away
            ledger.DB_PATH = real_path
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
