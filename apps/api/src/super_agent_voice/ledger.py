"""Job ledger: the application-owned record of every background job.

One SQLite file beside memory.db. The ledger owns state, revision and
receipts; no model or worker decides them. Transitions follow the canonical
table in architecture.md, each one bumps the revision and appends an event in
the same transaction, and every error raises LedgerError with nothing
half-written. No model, no network, no replay: nothing returns to queued
except by an allowed transition the caller requests.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

DB_PATH = Path.home() / ".super-agent" / "ledger.db"
# Only our own variable: a generic DATABASE_URL belongs to some other app and must not move the owner ledger.
DATABASE_URL: str | None = os.environ.get("SUPER_AGENT_DATABASE_URL") or None
_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})

try:
    import psycopg2
except ImportError:
    try:
        import psycopg as psycopg2
    except ImportError:
        psycopg2 = None

MAX_SPEC_BYTES, MAX_RECEIPT_BYTES, MAX_KEY, MAX_REASON = 8000, 4000, 128, 64
RETENTION = timedelta(days=14)  # DEC after 2026-11-15, see docs/design/agent-backend.md

# architecture.md "Canonical job states". `unknown -> queued` needs a journaled
# policy decision that this slice does not have, so it is not allowed here.
NEXT = {
    "queued": {"running", "cancel_requested", "failed", "waiting_for_approval"},
    "running": {"succeeded", "failed", "cancel_requested", "unknown", "waiting_for_approval"},
    "waiting_for_approval": {"queued", "cancel_requested", "failed"},
    "cancel_requested": {"cancelled", "succeeded", "failed", "unknown"},
    "unknown": {"succeeded", "failed", "cancelled"},
    "succeeded": set(), "failed": set(), "cancelled": set(),
}
TERMINAL = {"succeeded", "failed", "cancelled"}
NEEDS_RECEIPT = {"succeeded", "failed", "cancelled"}  # cancelled needs proof of stop or non-execution


class LedgerError(Exception):
    """Any validation or database failure. Messages never echo caller data."""


class StaleRevision(LedgerError):
    """The caller acted on an old revision of the job."""


@dataclass(frozen=True)
class Job:
    id: str
    idempotency_key: str
    spec: dict
    state: str
    revision: int
    created_at: str
    updated_at: str
    terminal_at: str | None


@dataclass(frozen=True)
class Event:
    job_id: str
    from_state: str | None
    to_state: str
    revision: int
    reason: str
    receipt: dict | None
    at: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  spec TEXT NOT NULL,
  state TEXT NOT NULL,
  revision INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  terminal_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  from_state TEXT,
  to_state TEXT NOT NULL,
  revision INTEGER NOT NULL,
  reason TEXT NOT NULL,
  receipt TEXT,
  at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_job ON events (job_id, seq);
PRAGMA user_version = 1;
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  spec TEXT NOT NULL,
  state TEXT NOT NULL,
  revision INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  terminal_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
  seq BIGSERIAL PRIMARY KEY,
  job_id TEXT NOT NULL,
  from_state TEXT,
  to_state TEXT NOT NULL,
  revision INTEGER NOT NULL,
  reason TEXT NOT NULL,
  receipt TEXT,
  at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_job ON events (job_id, seq);
"""

_lock = threading.Lock()  # callers use worker threads
_pg_initialized = False


def _is_postgres() -> bool:
    return bool(DATABASE_URL)  # any value selects the database path, which then fails closed if it is not loopback


def _connect_postgres():
    """The owner ledger stays on this machine: PostgreSQL on loopback only. The error never echoes the URL."""
    try:
        parts = urlsplit(DATABASE_URL)
        host = parts.hostname
        query = {key.lower() for key, _ in parse_qsl(parts.query, keep_blank_values=True)}
        ok = (parts.scheme in ("postgres", "postgresql") and host in _LOOPBACK
              and "," not in parts.netloc and not query & {"host", "hostaddr", "service"})
    except (TypeError, ValueError):
        ok = False
    if not ok:
        raise LedgerError("ledger database must be PostgreSQL on 127.0.0.1")
    # An inherited libpq address must never override the validated hostname.
    return psycopg2.connect(DATABASE_URL, hostaddr="::1" if host == "::1" else "127.0.0.1")


class _PgConn:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params=()):
        cur = self._raw.cursor()
        pg_sql = sql.replace("?", "%s")
        cur.execute(pg_sql, params)
        return cur

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()


def _stamp(when: datetime | None = None) -> str:
    """UTC with fixed-width microseconds, so strings compare in time order."""
    return (when or datetime.now(UTC)).astimezone(UTC).isoformat(timespec="microseconds")


@contextmanager
def _db() -> Iterator[sqlite3.Connection | _PgConn]:
    """One connection per call under lock. Commits on success, rolls back on any error."""
    global _pg_initialized
    if _is_postgres():
        if psycopg2 is None:
            raise LedgerError("PostgreSQL driver (psycopg2) not installed")
        con = None
        try:
            raw = _connect_postgres()
            con = _PgConn(raw)
            with _lock:
                if not _pg_initialized:
                    cur = raw.cursor()
                    cur.execute(_PG_SCHEMA)
                    raw.commit()
                    cur.close()
                    _pg_initialized = True
            yield con
            con.commit()
        except LedgerError:
            if con:
                con.rollback()
            raise
        except Exception as err:
            if con:
                con.rollback()
            raise LedgerError("ledger storage failed") from err
        finally:
            if con:
                con.close()
    else:
        with _lock:
            con = None
            try:
                DB_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                os.close(os.open(DB_PATH, os.O_RDWR | os.O_CREAT, 0o600))  # born 0600, no window
                os.chmod(DB_PATH, 0o600)  # and tightened if it already existed
                con = sqlite3.connect(DB_PATH)
                con.executescript(_SCHEMA)
                yield con
                con.commit()
            except LedgerError:
                if con:
                    con.rollback()
                raise
            except (sqlite3.Error, OSError) as err:
                if con:
                    con.rollback()
                raise LedgerError("ledger storage failed") from err
            except BaseException:
                if con:
                    con.rollback()
                raise
            finally:
                if con:
                    con.close()


def _json(value: object, limit: int, what: str) -> str:
    """Canonical JSON text of a dict, or LedgerError. Rejects NaN and oversize."""
    if not isinstance(value, dict):
        raise LedgerError(f"{what} must be an object")
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as err:  # RecursionError: absurdly deep nesting
        raise LedgerError(f"{what} is not valid JSON") from err
    if len(text.encode()) > limit:
        raise LedgerError(f"{what} is too large")
    return text


def _load(text: str) -> dict:
    try:
        value = json.loads(text)
    except ValueError as err:
        raise LedgerError("stored record is corrupt") from err
    if not isinstance(value, dict):  # specs and receipts are objects
        raise LedgerError("stored record is corrupt")
    return value


def _job(row: sqlite3.Row | tuple) -> Job:
    return Job(row[0], row[1], _load(row[2]), *row[3:])


_COLS = "id, idempotency_key, spec, state, revision, created_at, updated_at, terminal_at"


def _append_event(db, job_id, from_state, to_state, revision, reason, receipt_text, at) -> None:
    db.execute("INSERT INTO events (job_id, from_state, to_state, revision, reason, receipt, at) "
               "VALUES (?, ?, ?, ?, ?, ?, ?)",
               (job_id, from_state, to_state, revision, reason, receipt_text, at))


def create_job(spec: dict, idempotency_key: str) -> Job:
    if not isinstance(idempotency_key, str) or not 0 < len(idempotency_key) <= MAX_KEY:
        raise LedgerError("idempotency key must be 1 to 128 characters")
    try:
        idempotency_key.encode("utf-8")  # a lone surrogate would raise inside sqlite
    except UnicodeError:
        raise LedgerError("idempotency key must be valid text") from None
    text = _json(spec, MAX_SPEC_BYTES, "task spec")
    with _db() as db:
        row = db.execute(f"SELECT {_COLS} FROM jobs WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        if row:
            if row[2] != text:
                raise LedgerError("idempotency key already used with a different task spec")
            return _job(row)
        job_id, now = uuid.uuid4().hex, _stamp()
        db.execute(f"INSERT INTO jobs ({_COLS}) VALUES (?, ?, ?, 'queued', 1, ?, ?, NULL)",
                   (job_id, idempotency_key, text, now, now))
        _append_event(db, job_id, None, "queued", 1, "created", None, now)
        return _job(db.execute(f"SELECT {_COLS} FROM jobs WHERE id = ?", (job_id,)).fetchone())


def _move(db, row, to_state: str, reason: str, receipt: dict | None) -> None:
    """Apply one allowed transition to a fetched job row, with its event. Caller has validated."""
    now, rev = _stamp(), row[4] + 1
    receipt_text = None if receipt is None else _json(receipt, MAX_RECEIPT_BYTES, "receipt")
    # compare-and-set: a concurrent writer that bumped the revision makes this match no row
    cur = db.execute("UPDATE jobs SET state = ?, revision = ?, updated_at = ?, terminal_at = ? "
                     "WHERE id = ? AND revision = ?",
                     (to_state, rev, now, now if to_state in TERMINAL else None, row[0], row[4]))
    if cur.rowcount != 1:
        raise StaleRevision("stale revision")
    _append_event(db, row[0], row[3], to_state, rev, reason, receipt_text, now)


def transition(job_id: str, to_state: str, expected_revision: int, reason: str,
               receipt: dict | None = None) -> Job:
    if not isinstance(reason, str) or not 0 < len(reason) <= MAX_REASON:
        raise LedgerError("reason must be 1 to 64 characters")
    if not isinstance(to_state, str) or to_state not in NEXT:
        raise LedgerError("unknown state")
    if type(expected_revision) is not int:
        raise LedgerError("revision must be an integer")
    if to_state in NEEDS_RECEIPT and receipt is None:
        raise LedgerError("this state needs a receipt")
    if receipt is not None:
        _json(receipt, MAX_RECEIPT_BYTES, "receipt")
    with _db() as db:
        row = db.execute(f"SELECT {_COLS} FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise LedgerError("no such job")
        if row[4] != expected_revision:
            raise StaleRevision("stale revision")
        if to_state not in NEXT[row[3]]:
            raise LedgerError("transition not allowed")
        _move(db, row, to_state, reason, receipt)
        return _job(db.execute(f"SELECT {_COLS} FROM jobs WHERE id = ?", (job_id,)).fetchone())


def append_note(job_id: str, reason: str, receipt: dict) -> None:
    """Append an event to a running job without changing its state or revision.

    Workers that run in parallel write these, so they must not race the runner's revision
    compare-and-set. The event carries the current revision and from_state equal to to_state."""
    if not isinstance(reason, str) or not 0 < len(reason) <= MAX_REASON:
        raise LedgerError("reason must be 1 to 64 characters")
    text = _json(receipt, MAX_RECEIPT_BYTES, "receipt")
    with _db() as db:
        row = db.execute(f"SELECT {_COLS} FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise LedgerError("no such job")
        if row[3] not in ("running", "cancel_requested"):
            raise LedgerError("job is not running")
        _append_event(db, job_id, row[3], row[3], row[4], reason, text, _stamp())


def get_job(job_id: str) -> Job | None:
    with _db() as db:
        row = db.execute(f"SELECT {_COLS} FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _job(row) if row else None


def list_jobs(state: str | None = None) -> list[Job]:
    if state is not None and (not isinstance(state, str) or state not in NEXT):
        raise LedgerError("unknown state")
    with _db() as db:
        sql = f"SELECT {_COLS} FROM jobs" + ("" if state is None else " WHERE state = ?") + " ORDER BY created_at, id"
        return [_job(r) for r in db.execute(sql, () if state is None else (state,))]


def list_events(job_id: str) -> list[Event]:
    with _db() as db:
        rows = db.execute("SELECT job_id, from_state, to_state, revision, reason, receipt, at "
                          "FROM events WHERE job_id = ? ORDER BY seq", (job_id,))
        return [Event(r[0], r[1], r[2], r[3], r[4], None if r[5] is None else _load(r[5]), r[6])
                for r in rows]


def recover_after_restart() -> int:
    """Startup: no worker survived, so no running or cancel_requested job has proof of stop.
    Both become unknown. Nothing is replayed. Returns how many jobs moved."""
    with _db() as db:
        rows = db.execute(f"SELECT {_COLS} FROM jobs WHERE state IN ('running', 'cancel_requested')").fetchall()
        for row in rows:
            _move(db, row, "unknown", f"restart_{row[3]}", None)
        return len(rows)


def purge(now: datetime) -> int:
    """Delete terminal jobs, and their events, RETENTION after they ended. Returns jobs deleted."""
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise LedgerError("purge needs a timezone-aware time")
    cutoff = _stamp(now - RETENTION)
    with _db() as db:
        ids = [r[0] for r in db.execute("SELECT id FROM jobs WHERE terminal_at IS NOT NULL AND terminal_at <= ?",
                                        (cutoff,))]
        for job_id in ids:
            db.execute("DELETE FROM events WHERE job_id = ?", (job_id,))
            db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return len(ids)


def claim_next_job(worker_id: str = "default", state: str = "queued") -> Job | None:
    """Atomically claim the next queued job for a worker.

    In PostgreSQL, uses SELECT ... FOR UPDATE SKIP LOCKED to prevent concurrent worker contention.
    In SQLite, serializes under the process thread lock with compare-and-set.
    Transitions the job to 'running', bumps revision, and records a claim event.
    Returns None if no matching job is available.
    """
    if not isinstance(worker_id, str) or not 0 < len(worker_id) <= MAX_REASON:
        raise LedgerError("worker_id must be 1 to 64 characters")
    if not isinstance(state, str) or state not in NEXT:
        raise LedgerError("unknown state")
    with _db() as db:
        if _is_postgres():
            cur = db.execute(
                f"SELECT {_COLS} FROM jobs WHERE state = ? ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED",
                (state,),
            )
            row = cur.fetchone()
            if not row:
                return None
            _move(db, row, "running", f"claimed_{worker_id}", None)
            res = db.execute(f"SELECT {_COLS} FROM jobs WHERE id = ?", (row[0],)).fetchone()
            return _job(res)
        else:
            row = db.execute(
                f"SELECT {_COLS} FROM jobs WHERE state = ? ORDER BY created_at, id LIMIT 1",
                (state,),
            ).fetchone()
            if not row:
                return None
            _move(db, row, "running", f"claimed_{worker_id}", None)
            return _job(db.execute(f"SELECT {_COLS} FROM jobs WHERE id = ?", (row[0],)).fetchone())

