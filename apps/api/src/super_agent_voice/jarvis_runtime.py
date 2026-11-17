"""Bounded in-memory coordination for Jarvis's five worker slots."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import UUID

from .hermes_runs import HermesRun, HermesRunsError, HermesStatus


_WORKERS = {
    "research": ("Researcher", "Find and verify information"),
    "developer": ("Developer", "Inspect and implement code"),
    "writer": ("Writer", "Draft and revise documents"),
    "operator": ("Operator", "Work in a scoped browser or desktop"),
    "reviewer": ("Reviewer", "Check results and flag gaps"),
}
_MAX_JOBS = 128
_MAX_PROMPT_BYTES = 2 * 1024
_MAX_RESULT_BYTES = 8 * 1024

JobStatus = Literal[
    "queued", "running", "waiting_for_approval", "cancel_requested",
    "succeeded", "failed", "cancelled", "unknown",
]
_ACTIVE = frozenset({"queued", "running", "waiting_for_approval", "cancel_requested"})
_TERMINAL: dict[HermesStatus, JobStatus] = {
    HermesStatus.INCOMPLETE: "failed", HermesStatus.FAILED: "failed",
    HermesStatus.CANCELLED: "cancelled", HermesStatus.INTERRUPTED: "unknown",
}


class WorkerTransport(Protocol):
    async def create(self, job_id: UUID, prompt: str) -> HermesRun: ...
    async def poll(self, run_id: str) -> HermesRun: ...
    async def stop(self, run_id: str) -> HermesRun: ...


@dataclass(slots=True)
class _Job:
    id: str
    worker_id: str
    prompt: str
    status: JobStatus = "queued"
    result: str | None = None
    receipt: dict[str, object] | None = None
    cancel_requested: asyncio.Event = field(default_factory=asyncio.Event)


class JarvisRuntime:
    def __init__(
        self, workers: Mapping[str, WorkerTransport] | None = None, *,
        poll_interval_seconds: float = 0.25, job_timeout_seconds: float = 120.0,
        stop_timeout_seconds: float = 5.0,
    ) -> None:
        self._clients = dict(workers or {})
        if self._clients.keys() - _WORKERS.keys():
            raise ValueError("Unknown Jarvis worker configuration")
        for value, maximum in ((poll_interval_seconds, 5), (job_timeout_seconds, 300), (stop_timeout_seconds, 30)):
            if type(value) not in (int, float) or not 0 < value <= maximum:
                raise ValueError("Invalid Jarvis timing configuration")
        self._poll_interval = poll_interval_seconds
        self._job_timeout = job_timeout_seconds
        self._stop_timeout = stop_timeout_seconds
        self._jobs: dict[str, _Job] = {}
        self._occupied: dict[str, str] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._closed = False

    def snapshot(self) -> dict[str, list[dict[str, object]]]:
        workers: list[dict[str, object]] = []
        for worker_id, (name, role) in _WORKERS.items():
            status = "offline" if self._closed or worker_id not in self._clients else "ready"
            if worker_id in self._occupied:
                status = "busy"
            workers.append({"id": worker_id, "name": name, "role": role, "status": status})
        jobs: list[dict[str, object]] = []
        occupied = set(self._occupied.values())
        remaining = len(_WORKERS) - len(occupied)
        completed = [job_id for job_id in self._jobs if job_id not in occupied]
        visible = occupied | (set(completed[-remaining:]) if remaining else set())
        for job_id, job in self._jobs.items():
            if job_id not in visible:
                continue
            row: dict[str, object] = {
                "id": job.id, "workerId": job.worker_id, "status": job.status, "prompt": job.prompt,
            }
            if job.result is not None:
                row["result"] = job.result
            if job.receipt is not None:
                row["receipt"] = dict(job.receipt)
            jobs.append(row)
        return {"workers": workers, "jobs": jobs}

    def submit(self, worker_id: str, prompt: str, request_id: UUID) -> str:
        if not isinstance(worker_id, str) or worker_id not in _WORKERS:
            raise ValueError("Unknown Jarvis worker")
        if not isinstance(request_id, UUID):
            raise ValueError("Jarvis requires a request UUID")
        if not _prompt_bytes(prompt):
            raise ValueError("Jarvis prompt must be nonempty UTF-8 under 2 KiB")
        job_id = str(request_id)
        previous = self._jobs.get(job_id)
        if previous is not None:
            if (previous.worker_id, previous.prompt) != (worker_id, prompt):
                raise ValueError("Request UUID belongs to a different job")
            return job_id
        if self._closed or worker_id not in self._clients:
            raise RuntimeError("Jarvis worker is offline")
        if worker_id in self._occupied:
            raise RuntimeError("Jarvis worker is busy")
        if len(self._jobs) >= _MAX_JOBS:
            # Keep UUIDs for this runtime lifetime so a replay cannot create more work.
            raise RuntimeError("Jarvis job history is full")
        loop = asyncio.get_running_loop()
        job = self._jobs[job_id] = _Job(job_id, worker_id, prompt)
        self._occupied[worker_id] = job_id
        task = loop.create_task(self._execute(job, request_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job_id

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id) if isinstance(job_id, str) else None
        if job is None or job.status not in _ACTIVE:
            return False
        job.status = "cancel_requested"
        job.cancel_requested.set()
        return True

    async def close(self) -> None:
        self._closed = True
        for job_id in self._occupied.values():
            self.cancel(job_id)
        if self._tasks:
            await asyncio.gather(*self._tasks)

    async def _execute(self, job: _Job, request_id: UUID) -> None:
        started = False
        try:
            if job.cancel_requested.is_set():
                job.status = "cancelled"
                return
            started = True
            await self._drive(job, request_id, self._clients[job.worker_id])
        except asyncio.CancelledError:
            job.status = "unknown" if started else "cancelled"
            raise
        finally:
            if job.status != "unknown":
                self._occupied.pop(job.worker_id, None)

    async def _drive(self, job: _Job, request_id: UUID, client: WorkerTransport) -> None:
        run_id = None
        try:
            async with asyncio.timeout(self._job_timeout):
                admission = await client.create(request_id, job.prompt)
                _validate_admission(admission)
                run_id = admission.run_id
                job.receipt = _receipt(admission)
                while not job.cancel_requested.is_set():
                    result = await client.poll(run_id)
                    if _apply_receipt(job, result, run_id):
                        return
                    await self._wait_for_cancel(job)
        except HermesRunsError as error:
            if run_id is None:
                job.status = "unknown" if error.outcome_unknown else "failed"
                return
        except Exception:
            if run_id is None:
                job.status = "unknown"
                return
        await self._stop(job, client, run_id)

    async def _wait_for_cancel(self, job: _Job) -> None:
        try:
            await asyncio.wait_for(job.cancel_requested.wait(), timeout=self._poll_interval)
        except TimeoutError:
            pass

    async def _stop(self, job: _Job, client: WorkerTransport, run_id: str) -> None:
        job.status = "cancel_requested"
        try:
            async with asyncio.timeout(self._stop_timeout):
                try:
                    if _apply_receipt(job, await client.stop(run_id), run_id, stopping=True):
                        return
                except HermesRunsError:
                    # The stop response can be lost while its effect still happens.
                    pass
                while True:
                    if _apply_receipt(job, await client.poll(run_id), run_id, stopping=True):
                        return
                    await asyncio.sleep(self._poll_interval)
        except Exception:
            # Quarantine this worker rather than starting a second remote job.
            job.status = "unknown"


def _prompt_bytes(prompt: object) -> bool:
    if not isinstance(prompt, str) or not 0 < len(prompt) <= _MAX_PROMPT_BYTES or not prompt.strip() or "\0" in prompt:
        return False
    try:
        return len(prompt.encode("utf-8")) <= _MAX_PROMPT_BYTES
    except UnicodeError:
        return False


def _validate_admission(run: HermesRun) -> None:
    if (
        not isinstance(run, HermesRun) or not isinstance(run.run_id, str) or not run.run_id
        or not isinstance(run.status, HermesStatus) or (not run.replayed and run.status is not HermesStatus.STARTED)
    ):
        raise HermesRunsError("protocol-error")


def _receipt(run: HermesRun) -> dict[str, object]:
    receipt: dict[str, object] = {"runId": run.run_id, "status": run.status.value}
    if run.provider is not None:
        receipt["provider"] = run.provider
    if run.model is not None:
        receipt["model"] = run.model
    return receipt


def _apply_receipt(job: _Job, run: HermesRun, expected_id: str, *, stopping: bool = False) -> bool:
    if not isinstance(run, HermesRun) or run.run_id != expected_id or not isinstance(run.status, HermesStatus):
        raise HermesRunsError("protocol-error")
    receipt = _receipt(run)
    if run.status is HermesStatus.COMPLETED:
        output = run.output
        if not isinstance(output, str) or not output.strip() or "\0" in output:
            raise HermesRunsError("protocol-error")
        try:
            encoded = output.encode("utf-8")
        except UnicodeError:
            raise HermesRunsError("protocol-error") from None
        job.result = encoded[:_MAX_RESULT_BYTES].decode("utf-8", errors="ignore")
        if len(encoded) > _MAX_RESULT_BYTES:
            receipt["resultTruncated"] = True
        job.status = "succeeded"
    elif run.status in _TERMINAL:
        job.status = _TERMINAL[run.status]
    elif stopping or job.cancel_requested.is_set() or run.status is HermesStatus.STOPPING:
        job.status = "cancel_requested"
    elif run.status is HermesStatus.WAITING_FOR_APPROVAL:
        job.status = "waiting_for_approval"
    else:
        job.status = "running"
    job.receipt = receipt
    return run.terminal
