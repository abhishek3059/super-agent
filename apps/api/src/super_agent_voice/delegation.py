"""delegate_task for the conversation loop (agent-backend design, section 10 item 6).

One Service owns one Runner built with graph.make_work. `delegate` admits a job and returns a receipt at
once; it never waits for the job. The conversation model supplies only `task_type` and `instruction`.
The data class, the idempotency key, the locality flag, the limits and the tools all come from trusted
code here. Every refusal is a fixed PolicyError code, never exception text or any part of the spec.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

from . import graph, ledger, memory, policy, tier1, tools
from .policy import PolicyError
from .runner import Runner

# Defence in depth: admission and plan validation already keep every other name out.
READ_TOOLS = frozenset({"calculate", "current_time"}) | tier1.T1_NAMES | (memory.NAMES - memory.WRITES)
_NO_TOOL = "error: no such tool."

TOOL = {"type": "function", "function": {
    "name": "delegate_task",
    "description": "Hand a bounded read-only task to a background helper. It returns a job number at once; "
                   "you never get the result in this conversation.",
    "parameters": {"type": "object", "required": ["task_type", "instruction"], "properties": {
        "task_type": {"type": "string", "enum": sorted(policy.TASK_TYPES)},
        "instruction": {"type": "string"}}}}}


def run_read_tool(name: object, args: object) -> str:
    """The `run_tool` the graph calls, from a worker thread. Results are untrusted data and pass unchanged."""
    if not isinstance(name, str) or name not in READ_TOOLS:
        return _NO_TOOL
    if name in tier1.T1_NAMES:
        return asyncio.run(tier1.run_t1(name, args))  # no loop runs in a graph thread, so it gets its own
    return memory.run(name, args) if name in memory.NAMES else tools.run_tool(name, args)


class Service:
    def __init__(self, model=None, *, data_class: str = "personal", limits: policy.Limits | None = None):
        if not isinstance(data_class, str) or data_class not in policy.DATA_CLASSES:
            raise PolicyError("data_class_invalid")
        self._model, self._data_class, self._closed = model, data_class, False
        self._limits = policy.Limits() if limits is None else limits
        self._clock = lambda: datetime.now(UTC)
        self._runner = Runner(ledger, self._limits,
                              graph.make_work(ledger, model, run_read_tool, self._limits, self._clock), self._clock)
        try:  # nothing schedules the purge after this
            self._runner.recover()
            ledger.purge(self._clock())
        except BaseException:
            self._runner.close()
            raise

    def delegate(self, task_type: object, instruction: object, call_key: object) -> dict:
        """A receipt {job_id, state, revision}, or {"refused": <PolicyError code>}."""
        try:
            if self._closed or self._model is None:
                raise PolicyError("delegation_unavailable")
            try:
                local = self._model.is_local is True
            except Exception:  # a broken flag is not local
                local = False
            spec = {"task_type": task_type, "instruction": instruction, "data_class": self._data_class}
            adm = policy.admit(spec, call_key, local, self._limits, ledger, self._clock())
            self._runner.submit(adm)
        except PolicyError as err:
            return {"refused": err.code}
        except Exception:
            return {"refused": "delegation_unavailable"}
        return {"job_id": adm.job.id, "state": adm.job.state, "revision": adm.job.revision}

    def handle(self, arguments: object) -> str:
        """The tool call. The key is fresh per call, so a retried tool call is a new job."""
        if not isinstance(arguments, dict) or set(arguments) != {"task_type", "instruction"}:
            return "error: not delegated (spec_invalid)."
        result = self.delegate(arguments["task_type"], arguments["instruction"], uuid.uuid4().hex)
        if "refused" in result:
            return f"error: not delegated ({result['refused']})."
        return json.dumps({"job_id": result["job_id"], "state": result["state"]})  # never job output

    def close(self) -> None:
        self._closed = True
        self._runner.close()
