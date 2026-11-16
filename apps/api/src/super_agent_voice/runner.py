"""Background job runner (agent-backend design, section 10 item 3).

Jobs run on a small thread pool, off the conversation event loop. The pool size is the
"concurrent jobs" limit, so a job stays queued in the ledger until a thread picks it up.
`work` is trusted code (a stub now, the graph later). Every state change goes through the
ledger's revision compare-and-set, so a cancel and a start race to exactly one winner.
Reasons and error receipts are fixed strings chosen here, never exception text. A success
receipt is whatever the trusted work function returned.
No model, no network, no replay.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from . import policy, tier1
from .ledger import TERMINAL, Job, LedgerError, StaleRevision


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
            self._ledger.transition(job.id, "failed", job.revision, "restart_queued", {"executed": False})
            moved += 1
        return moved

    def _tools(self, admitted: frozenset[str]) -> frozenset[str]:
        """Tier 1 tools are offered only while their group is enabled; a bad config offers none."""
        try:
            enabled = {schema["function"]["name"] for schema in tier1.enabled_tools()}
        except Exception:
            enabled = set()
        return frozenset(t for t in admitted if t not in tier1.T1_NAMES or t in enabled)

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

        try:
            receipt, failed = self._work(job, self._tools(adm.tools), should_stop), False
        except Exception:
            receipt, failed = None, True
        try:
            if failed:
                plan = [("failed", "work_error", {"error": "work_error"})]
            elif self._late(adm):
                plan = [("failed", "job_deadline", {"error": "job_deadline"})]
            elif not saw_stop:
                plan = [("succeeded", "work_done", receipt),
                        ("failed", "bad_receipt", {"error": "bad_receipt"})]
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
