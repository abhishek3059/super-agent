"""Background job runner (agent-backend design, section 10 item 3).

Jobs run on a small thread pool, off the conversation event loop. The pool size is the
"concurrent jobs" limit, so a job stays queued in the ledger until a thread picks it up.
`work(job, admission, should_stop)` is trusted code; its admission carries only the tools still enabled. Every state change goes through the
ledger's revision compare-and-set, so a cancel and a start race to exactly one winner.
Reasons and error receipts are fixed strings chosen here, never exception text. A success
receipt is whatever the trusted work function returned.
No model, no network, no replay.
"""
from __future__ import annotations

import dataclasses
import json
from concurrent.futures import ThreadPoolExecutor

from . import memory, policy, tier1
from .ledger import MAX_RECEIPT_BYTES, TERMINAL, Job, LedgerError, StaleRevision


@dataclasses.dataclass(frozen=True)
class HermesWorkerDefinition:
    name: str
    role: str
    description: str
    allowed_tools: tuple[str, ...]


HERMES_WORKERS: dict[str, HermesWorkerDefinition] = {
    "researcher": HermesWorkerDefinition(
        name="researcher",
        role="Web & Knowledge Researcher",
        description="Autonomous web research, documentation analysis, fact retrieval, and cited synthesis",
        allowed_tools=("calculate", "current_time"),
    ),
    "coder": HermesWorkerDefinition(
        name="coder",
        role="Software Engineer",
        description="Source code reading, editing, test execution, syntax diagnostics, and git commits",
        allowed_tools=("current_time",),
    ),
    "secretary": HermesWorkerDefinition(
        name="secretary",
        role="Executive Secretary & Scheduler",
        description="Calendar coordination, appointment reminders, email drafting, and agenda summaries",
        allowed_tools=("current_time",),
    ),
    "librarian": HermesWorkerDefinition(
        name="librarian",
        role="Memory & Profile Librarian",
        description="User preference tracking, fact persistence, memory recall, and contextual indexing",
        allowed_tools=("memory_recall", "memory_save"),
    ),
    "ops": HermesWorkerDefinition(
        name="ops",
        role="Systems & Desktop Operations",
        description="Host environment diagnostics, disk and network metrics, approved Mac desktop application launches",
        allowed_tools=("current_time",),
    ),
}


def get_worker(name: str) -> HermesWorkerDefinition | None:
    return HERMES_WORKERS.get(name)


def list_workers() -> list[HermesWorkerDefinition]:
    return list(HERMES_WORKERS.values())


def _storable(receipt: object) -> bool:
    """True if the ledger would accept this as a receipt (same rules as ledger._json)."""
    try:
        text = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        return False
    return isinstance(receipt, dict) and len(text.encode()) <= MAX_RECEIPT_BYTES


class Runner:
    def __init__(self, ledger, limits, work, clock):
        self._ledger, self._work, self._clock = ledger, work, clock
        if not isinstance(limits, policy.Limits):
            raise policy.PolicyError("limits_invalid")  # never fall back to defaults on a limit
        self._limits = limits
        self._pool = ThreadPoolExecutor(max_workers=self._limits.concurrent_jobs,
                                        thread_name_prefix="job-runner")

    def submit(self, admission: policy.Admission) -> None:
        self._pool.submit(self._run, admission)

    def claim_and_run(self, worker_id: str = "default") -> Job | None:
        """Atomically claim the next queued task from the ledger and submit it to the pool."""
        job = self._ledger.claim_next_job(worker_id)
        if job is None:
            return None
        tools = frozenset(HERMES_WORKERS[worker_id].allowed_tools) if worker_id in HERMES_WORKERS else frozenset()
        from datetime import timedelta
        adm = policy.Admission(
            job=job,
            tools=tools,
            memory_context=False,
            deadline=self._clock() + timedelta(seconds=self._limits.job_deadline_s),
            planner_is_local=True,
        )
        self._pool.submit(self._run_claimed, adm, worker_id)
        return job

    def _run_claimed(self, adm: policy.Admission, worker_id: str) -> None:
        job = adm.job
        saw_stop = []

        def should_stop() -> bool:
            try:
                stop = self._late(adm) or self._ledger.get_job(job.id).state == "cancel_requested"
            except Exception:
                stop = True
            if stop:
                saw_stop.append(True)
            return stop

        code = None
        try:
            offered = dataclasses.replace(adm, tools=self._tools(adm.tools))
            receipt, failed = self._work(job, offered, should_stop), False
        except Exception as err:
            receipt, failed = None, True
            code = err.code if isinstance(err, policy.PolicyError) else None

        try:
            if failed:
                plan = [("failed", "work_error", {"error": "work_error", **({"code": code} if code else {})})]
            elif self._late(adm):
                plan = [("failed", "job_deadline", {"error": "job_deadline"})]
            elif not saw_stop:
                plan = ([("succeeded", f"work_done_{worker_id}", receipt)] if _storable(receipt)
                        else [("failed", "bad_receipt", {"error": "bad_receipt"})])
            elif self._state(job.id) == "cancel_requested":
                plan = [("cancelled", "cancel_stopped", {"stopped": True})]
            else:
                plan = [("failed", "stop_unconfirmed", {"error": "stop_unconfirmed"})]
        except Exception:
            plan = []
        plan.append(("unknown", "terminal_write_failed", None))
        for to, reason, body in plan:
            if self._finish(job.id, to, reason, body):
                return

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def cancel(self, job_id: str) -> Job:
        """Request a stop. A job that never started is cancelled at once, with proof it did not run."""
        for _ in range(2):
            job = self._ledger.get_job(job_id)
            if job is None or job.state not in ("queued", "running"):
                raise LedgerError("job cannot be cancelled")
            try:
                moved = self._ledger.transition(job_id, "cancel_requested", job.revision, "user_cancel")
            except StaleRevision:  # a worker started it, or it ended, since we read it
                continue
            if job.state == "queued":  # the worker's start now fails its own compare-and-set
                return self._ledger.transition(job_id, "cancelled", moved.revision, "cancelled_before_start",
                                               {"executed": False})
            return moved
        raise StaleRevision("stale revision")

    def recover(self) -> int:
        """Startup. The Admission (tools, deadline) did not survive, so queued jobs are failed, not replayed."""
        moved = self._ledger.recover_after_restart()
        for job in self._ledger.list_jobs("queued"):
            if "hq_role" in job.spec:
                continue
            self._ledger.transition(job.id, "failed", job.revision, "restart_queued", {"executed": False})
            moved += 1
        return moved

    def _tools(self, admitted: frozenset[str]) -> frozenset[str]:
        """Tier 1 tools are offered only while their group is enabled, memory tools only while memory is on;
        a bad config offers none."""
        try:
            enabled = {schema["function"]["name"] for schema in tier1.enabled_tools()}
        except Exception:
            enabled = set()
        remembering = memory.enabled()
        return frozenset(t for t in admitted if (t not in tier1.T1_NAMES or t in enabled)
                         and (remembering or t not in memory.NAMES))

    def _run(self, adm: policy.Admission) -> None:
        try:
            job = self._ledger.transition(adm.job.id, "running", adm.job.revision, "runner_start")
        except LedgerError:  # cancelled while queued, or the ledger is unreachable: do not run
            return
        saw_stop = []

        def should_stop() -> bool:
            try:
                stop = self._late(adm) or self._ledger.get_job(job.id).state == "cancel_requested"
            except Exception:
                stop = True  # fail closed
            if stop:
                saw_stop.append(True)
            return stop

        code = None  # a PolicyError code is a fixed string; any other exception contributes nothing
        try:
            offered = dataclasses.replace(adm, tools=self._tools(adm.tools),
                                          memory_context=adm.memory_context and memory.enabled())
            receipt, failed = self._work(job, offered, should_stop), False
        except Exception as err:
            receipt, failed = None, True
            code = err.code if isinstance(err, policy.PolicyError) else None
        try:
            if failed:
                plan = [("failed", "work_error", {"error": "work_error", **({"code": code} if code else {})})]
            elif self._late(adm):
                plan = [("failed", "job_deadline", {"error": "job_deadline"})]
            elif not saw_stop:
                # judged from the receipt itself, so a refused write of a good one is never called bad
                plan = ([("succeeded", "work_done", receipt)] if _storable(receipt)
                        else [("failed", "bad_receipt", {"error": "bad_receipt"})])
            elif self._state(job.id) == "cancel_requested":
                plan = [("cancelled", "cancel_stopped", {"stopped": True})]
            else:  # work stopped early but no cancel is confirmed: its receipt is partial, never a success
                plan = [("failed", "stop_unconfirmed", {"error": "stop_unconfirmed"})]
        except Exception:
            plan = []
        plan.append(("unknown", "terminal_write_failed", None))  # last resort, never a success
        for to, reason, body in plan:
            if self._finish(job.id, to, reason, body):
                return

    def _late(self, adm: policy.Admission) -> bool:
        try:
            return not policy.check_job_deadline(adm.deadline, self._clock())
        except Exception:  # PolicyError, or a broken clock: fail closed
            return True

    def _state(self, job_id: str) -> str | None:
        try:
            return self._ledger.get_job(job_id).state
        except Exception:
            return None

    def _finish(self, job_id: str, to: str, reason: str, receipt: dict | None) -> bool:
        """One terminal write on the current revision, retried once if a cancel landed. False if refused."""
        for _ in range(2):
            try:
                job = self._ledger.get_job(job_id)
                if job is None or job.state in TERMINAL:
                    return job is not None
                self._ledger.transition(job_id, to, job.revision, reason, receipt)
                return True
            except StaleRevision:
                continue
            except LedgerError:
                return False
        return False
