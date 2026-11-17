"""Client for the loopback Hermes Runs API. Model text remains untrusted."""

from __future__ import annotations

import asyncio
import json
import math
import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

import httpx


_MAX_PROMPT_BYTES = 8 * 1024
_MAX_OUTPUT_BYTES = 24 * 1024
_MAX_RESPONSE_BYTES = 128 * 1024
_RUN_ID = re.compile(r"run_[0-9a-f]{32}")
_RUNTIME_ID = re.compile(r"[A-Za-z0-9_.:/-]{1,120}")


class HermesStatus(StrEnum):
    QUEUED = "queued"
    STARTED = "started"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    STOPPING = "stopping"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


_TERMINAL = frozenset({
    HermesStatus.COMPLETED, HermesStatus.INCOMPLETE, HermesStatus.FAILED,
    HermesStatus.CANCELLED, HermesStatus.INTERRUPTED,
})


@dataclass(frozen=True, slots=True)
class HermesRun:
    run_id: str
    status: HermesStatus
    output: str | None = None
    replayed: bool = False
    provider: str | None = None
    model: str | None = None

    @property
    def terminal(self) -> bool:
        return self.status in _TERMINAL


class HermesRunsError(Exception):
    """A fixed category with no upstream error message, request or credential."""

    def __init__(self, category: str, *, outcome_unknown: bool = True) -> None:
        super().__init__(category)
        self.category = category
        self.outcome_unknown = outcome_unknown


class HermesRunsClient:
    def __init__(self, port: int, api_key: str, *, timeout_seconds: float = 5.0) -> None:
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Hermes port must be an unprivileged TCP port")
        if (
            not isinstance(api_key, str) or not 32 <= len(api_key) <= 256
            or len(set(api_key)) < 16 or any(not 33 <= ord(char) <= 126 for char in api_key)
        ):
            raise ValueError("Hermes API bearer must be 32 to 256 printable ASCII characters with 16 distinct characters")
        if (
            type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 30
            or not math.isfinite(timeout_seconds)
        ):
            raise ValueError("Hermes request deadline must be in (0, 30] seconds")
        self._base_url = f"http://127.0.0.1:{port}"
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def create(self, job_id: UUID, prompt: str) -> HermesRun:
        if not isinstance(job_id, UUID):
            raise ValueError("Hermes admission requires a Jarvis job UUID")
        if not _bounded_text(prompt, _MAX_PROMPT_BYTES) or self._api_key in prompt:
            raise ValueError("Hermes job input must be nonempty UTF-8 within the size limit")
        response = await self._request(
            "POST", "/v1/runs", 202,
            payload={"input": prompt}, idempotency_key=str(job_id),
        )
        run_id, status = self._identity(response)
        replayed = response.get("replayed")
        if not isinstance(replayed, bool) or (not replayed and status is not HermesStatus.STARTED):
            raise HermesRunsError("protocol-error")
        # A replay may report a terminal status. Polling its receipt still owns the result.
        return HermesRun(run_id, status, replayed=replayed)

    async def poll(self, run_id: str) -> HermesRun:
        response = await self._request("GET", _run_path(run_id), 200)
        return self._receipt(response, run_id)

    async def stop(self, run_id: str) -> HermesRun:
        response = await self._request("POST", _run_path(run_id) + "/stop", 200)
        _, status = self._identity(response, run_id)
        if status is HermesStatus.STOPPING:
            return HermesRun(run_id, status)
        if status not in _TERMINAL:
            raise HermesRunsError("protocol-error")
        return self._receipt(response, run_id)

    def _receipt(self, response: dict[str, object], expected_id: str) -> HermesRun:
        run_id, status = self._identity(response, expected_id)
        if response.get("object") != "hermes.run":
            raise HermesRunsError("protocol-error")
        if status is not HermesStatus.COMPLETED:
            return HermesRun(run_id, status)
        output = response.get("output")
        if (
            response.get("completed") is not True or response.get("partial") is not False
            or response.get("interrupted") is not False or not _bounded_text(output, _MAX_OUTPUT_BYTES)
            or self._api_key in output
        ):
            raise HermesRunsError("protocol-error")
        runtime = response.get("runtime")
        provider = self._runtime_id(runtime.get("provider")) if isinstance(runtime, dict) else None
        model = self._runtime_id(runtime.get("model")) if isinstance(runtime, dict) else None
        return HermesRun(run_id, status, output=output, provider=provider, model=model)

    def _runtime_id(self, value: object) -> str | None:
        if isinstance(value, str) and _RUNTIME_ID.fullmatch(value) and self._api_key not in value:
            return value
        return None

    @staticmethod
    def _identity(response: dict[str, object], expected_id: str | None = None) -> tuple[str, HermesStatus]:
        run_id = response.get("run_id")
        try:
            status = HermesStatus(response.get("status"))
        except ValueError:
            raise HermesRunsError("protocol-error") from None
        if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
            raise HermesRunsError("protocol-error")
        if expected_id is not None and run_id != expected_id:
            raise HermesRunsError("protocol-error")
        return run_id, status

    async def _request(
        self, method: str, path: str, expected_status: int, *,
        payload: dict[str, str] | None = None, idempotency_key: str | None = None,
    ) -> dict[str, object]:
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept-Encoding": "identity"}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        try:
            async with asyncio.timeout(self._timeout):
                async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=self._timeout) as client:
                    async with client.stream(method, self._base_url + path, headers=headers, json=payload) as response:
                        if response.status_code != expected_status:
                            raise _http_failure(response.status_code, admitting=idempotency_key is not None)
                        return await _read_json(response)
        except (TimeoutError, httpx.TimeoutException):
            raise HermesRunsError("timeout") from None
        except httpx.HTTPError:
            raise HermesRunsError("unavailable") from None


def _run_path(run_id: str) -> str:
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid Hermes run identifier")
    return f"/v1/runs/{run_id}"


def _bounded_text(value: object, max_bytes: int) -> bool:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return False
    try:
        return len(value.encode("utf-8")) <= max_bytes
    except UnicodeError:
        return False


def _http_failure(status: int, *, admitting: bool) -> HermesRunsError:
    if status in (401, 403):
        return HermesRunsError("access-denied", outcome_unknown=not admitting)
    if status == 404:
        return HermesRunsError("run-unavailable")
    if status == 409:
        # Create conflict may mean the UUID is already attached to other work.
        return HermesRunsError("conflict")
    if status in (400, 422, 429):
        return HermesRunsError("busy" if status == 429 else "request-rejected", outcome_unknown=not admitting)
    return HermesRunsError("unavailable" if status >= 500 else "protocol-error")


async def _read_json(response: httpx.Response) -> dict[str, object]:
    if (
        response.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json"
        or response.headers.get("content-encoding", "identity").strip().lower() != "identity"
    ):
        raise HermesRunsError("protocol-error")
    body = bytearray()
    async for chunk in response.aiter_raw():
        if len(body) + len(chunk) > _MAX_RESPONSE_BYTES:
            raise HermesRunsError("protocol-error")
        body.extend(chunk)
    try:
        decoded = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        raise HermesRunsError("protocol-error") from None
    if not isinstance(decoded, dict):
        raise HermesRunsError("protocol-error")
    return decoded


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ValueError("Ambiguous response object")
    return fields
