"""Opt-in HQ ledger boundary. Only the trusted HQ server authenticates here."""
from __future__ import annotations

import hmac
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from . import ledger, policy

MAX_BODY = 8192
CLAIM_LIFETIME = timedelta(minutes=5)
KEY = re.compile(r"[a-f0-9]{32,64}")
AUTH = re.compile(r"[A-Za-z0-9_-]{43,128}")


def _invalid() -> None:
    raise HTTPException(400, "invalid HQ request")


def _receipt(body: dict) -> dict:
    summary, artifacts = body.get("summary"), body.get("artifacts")
    if not isinstance(summary, str) or len(summary) > 600 or not isinstance(artifacts, list) or len(artifacts) > 8:
        _invalid()
    for item in artifacts:
        if (not isinstance(item, str) or not 0 < len(item) <= 160 or "\\" in item
                or PurePosixPath(item).is_absolute() or ".." in PurePosixPath(item).parts
                or not PurePosixPath(item).parts or any(ord(ch) < 32 for ch in item)):
            _invalid()
    return {"summary": summary, "artifacts": artifacts}


def _expire(job: ledger.Job) -> None:
    try:
        ledger.transition(job.id, "unknown", job.revision, "hq_claim_expired")
    except ledger.StaleRevision:
        pass


def _operate(role: str, operation: str, body: dict) -> dict:
    if ledger.DATABASE_URL:
        try:
            dsn = urlsplit(ledger.DATABASE_URL)
            hostname = dsn.hostname
        except ValueError:
            raise HTTPException(403, "HQ requires local ledger storage") from None
        if (dsn.scheme not in {"postgresql", "postgres"} or hostname != "127.0.0.1"
                or dsn.query or dsn.fragment or os.environ.get("PGHOSTADDR") or os.environ.get("PGSERVICE")):
            raise HTTPException(403, "HQ requires local ledger storage")
    if operation == "submit":
        if set(body) != {"key", "instruction"} or not isinstance(body["key"], str) or not KEY.fullmatch(body["key"]):
            _invalid()
        spec = {"task_type": "answer", "instruction": body["instruction"], "data_class": "synthetic"}
        spec = policy.validate_spec(spec, policy.Limits()) | {"hq_role": role}
        job = ledger.create_job(spec, "hq:" + body["key"], pending_limit=7)
        return {"id": job.id, "state": job.state}
    if operation == "claim":
        if body:
            _invalid()
        # Never replay an orphaned execution. A receipt for its old revision is stale.
        cutoff = datetime.now(UTC) - CLAIM_LIFETIME
        for pending in ledger.list_jobs("running"):
            if pending.spec.get("hq_role") != role or datetime.fromisoformat(pending.updated_at) >= cutoff:
                continue
            _expire(pending)
        job = ledger.claim_next_job(f"hq_{role}", hq_role=role)
        return {"job": None if job is None else {
            "id": job.id, "revision": job.revision, "instruction": job.spec["instruction"],
        }}
    if operation != "finish" or set(body) != {"id", "revision", "state", "summary", "artifacts"}:
        _invalid()
    ident, revision, state = body["id"], body["revision"], body["state"]
    if not isinstance(ident, str) or not KEY.fullmatch(ident) or type(revision) is not int or revision < 1:
        _invalid()
    if state not in ("succeeded", "failed", "unknown"):
        _invalid()
    receipt = _receipt(body)
    job = ledger.get_job(ident)
    if job is None or job.spec.get("hq_role") != role or job.spec.get("data_class") != "synthetic":
        raise HTTPException(403, "forbidden")
    if job.state == state and job.revision == revision + 1:
        last = ledger.list_events(ident)[-1]
        if last.reason == "hq_finished" and last.receipt == receipt:
            return {"id": ident, "state": state}
    if job.state != "running" or job.revision != revision:
        _invalid()
    expiry = datetime.fromisoformat(job.updated_at) + CLAIM_LIFETIME
    try:
        ledger.transition(ident, state, revision, "hq_finished", receipt, expires_at=expiry)
    except ledger.LeaseExpired:
        _expire(job)
        _invalid()
    return {"id": ident, "state": state}


def mount(app: FastAPI, allowed_host: str, token: str) -> None:
    if not AUTH.fullmatch(token) or len(set(token)) < 16:
        raise RuntimeError("Invalid HQ ledger token")
    expected = ("Bearer " + token).encode("ascii")

    @app.post("/api/jobs/{role}/{operation}")
    async def jobs(request: Request, role: str, operation: str) -> dict:
        if (request.headers.getlist("host") != [allowed_host] or "origin" in request.headers
                or not hmac.compare_digest(request.headers.get("authorization", "").encode("utf-8"), expected)):
            raise HTTPException(403, "forbidden")
        if role not in ledger.HQ_ROLES:
            _invalid()
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_BODY:
                _invalid()
            raw.extend(chunk)
        try:
            body = json.loads(raw)
        except (ValueError, RecursionError):
            _invalid()
        if not isinstance(body, dict):
            _invalid()
        try:
            return await run_in_threadpool(_operate, role, operation, body)
        except (ledger.LedgerError, policy.PolicyError, UnicodeError):
            _invalid()
