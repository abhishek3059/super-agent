import os
import sqlite3
import stat
import sys
from datetime import UTC, datetime, timedelta

import pytest

from super_agent_voice import ledger
from super_agent_voice.ledger import LedgerError

RECEIPT = {"ok": True}
ALLOWED = [
    ("queued", "running"), ("queued", "cancel_requested"), ("queued", "failed"),
    ("queued", "waiting_for_approval"),
    ("running", "succeeded"), ("running", "failed"), ("running", "cancel_requested"),
    ("running", "unknown"), ("running", "waiting_for_approval"),
    ("waiting_for_approval", "queued"), ("waiting_for_approval", "cancel_requested"),
    ("waiting_for_approval", "failed"),
    ("cancel_requested", "cancelled"), ("cancel_requested", "succeeded"),
    ("cancel_requested", "failed"), ("cancel_requested", "unknown"),
    ("unknown", "succeeded"), ("unknown", "failed"), ("unknown", "cancelled"),
]
# One route from queued to every state, used to put a job in a given state.
ROUTE = {
    "queued": [], "running": ["running"], "waiting_for_approval": ["waiting_for_approval"],
    "cancel_requested": ["cancel_requested"], "unknown": ["running", "unknown"],
    "succeeded": ["running", "succeeded"], "failed": ["failed"],
    "cancelled": ["cancel_requested", "cancelled"],
}


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "DB_PATH", tmp_path / "led" / "ledger.db")


def mk(state="queued", key=None, spec=None):
    job = ledger.create_job(spec or {"task": "x"}, key or f"k-{state}-{os.urandom(4).hex()}")
    for step in ROUTE[state]:
        job = ledger.transition(job.id, step, job.revision, "test",
                                RECEIPT if step in ("succeeded", "failed", "cancelled") else None)
    return job


@pytest.mark.parametrize("src,dst", ALLOWED)
def test_allowed_transitions(src, dst):
    job = mk(src)
    out = ledger.transition(job.id, dst, job.revision, "r", RECEIPT if dst in ("succeeded", "failed", "cancelled") else None)
    assert out.state == dst and out.revision == job.revision + 1


@pytest.mark.parametrize("src", list(ROUTE))
@pytest.mark.parametrize("dst", list(ROUTE))
def test_every_other_transition_is_rejected(src, dst):
    if (src, dst) in ALLOWED:
        return
    job = mk(src)
    with pytest.raises(LedgerError):
        ledger.transition(job.id, dst, job.revision, "r", RECEIPT)
    assert ledger.get_job(job.id) == job


def test_unknown_state_rejected():
    job = mk()
    with pytest.raises(LedgerError):
        ledger.transition(job.id, "bogus", job.revision, "r")


def test_stale_revision_rejected():
    job = mk()
    ledger.transition(job.id, "running", job.revision, "r")
    with pytest.raises(ledger.StaleRevision):
        ledger.transition(job.id, "cancel_requested", job.revision, "r")
    assert ledger.get_job(job.id).state == "running"


def test_lost_update_is_caught_in_sql(monkeypatch):
    job = mk()
    real = ledger._stamp

    def racer(*a, **k):
        # another process wins between our read and our write
        monkeypatch.setattr(ledger, "_stamp", real)
        con = sqlite3.connect(ledger.DB_PATH)
        con.execute("UPDATE jobs SET revision = revision + 1 WHERE id = ?", (job.id,))
        con.commit()
        con.close()
        return real(*a, **k)

    monkeypatch.setattr(ledger, "_stamp", racer)
    with pytest.raises(ledger.StaleRevision):
        ledger.transition(job.id, "running", job.revision, "r")
    after = ledger.get_job(job.id)
    assert after.state == "queued" and after.revision == job.revision + 1
    assert len(ledger.list_events(job.id)) == 1


def test_corrupt_spec_is_a_ledger_error():
    job = mk()
    con = sqlite3.connect(ledger.DB_PATH)
    con.execute("UPDATE jobs SET spec = '{not json' WHERE id = ?", (job.id,))
    con.commit()
    con.close()
    with pytest.raises(LedgerError):
        ledger.get_job(job.id)


@pytest.mark.parametrize("stored", ["5", "[1]", "null", '"x"'])
def test_stored_spec_that_is_not_an_object_is_a_ledger_error(stored):
    job = mk()
    con = sqlite3.connect(ledger.DB_PATH)
    con.execute("UPDATE jobs SET spec = ? WHERE id = ?", (stored, job.id))
    con.commit()
    con.close()
    with pytest.raises(LedgerError):
        ledger.get_job(job.id)


@pytest.mark.parametrize("stored", ["5", "[1]", '"x"'])
def test_stored_receipt_that_is_not_an_object_is_a_ledger_error(stored):
    job = mk("failed")
    con = sqlite3.connect(ledger.DB_PATH)
    con.execute("UPDATE events SET receipt = ? WHERE job_id = ? AND receipt IS NOT NULL", (stored, job.id))
    con.commit()
    con.close()
    with pytest.raises(LedgerError):
        ledger.list_events(job.id)


@pytest.mark.parametrize("bad", [["x"], {"a": 1}, 5, "nope"])
def test_list_jobs_bad_state_is_a_ledger_error(bad):
    with pytest.raises(LedgerError):
        ledger.list_jobs(bad)


def test_key_that_does_not_encode_is_a_ledger_error():
    with pytest.raises(LedgerError):
        ledger.create_job({"task": "x"}, "k\ud800")
    assert ledger.list_jobs() == []


@pytest.mark.parametrize("bad", [["running"], {"a": 1}, None, 5])
def test_non_string_state_is_a_ledger_error(bad):
    job = mk()
    with pytest.raises(LedgerError):
        ledger.transition(job.id, bad, job.revision, "r")


@pytest.mark.parametrize("bad", [True, 1.0, "1", None])
def test_revision_must_be_a_real_int(bad):
    job = mk()
    assert job.revision == 1
    with pytest.raises(LedgerError):
        ledger.transition(job.id, "running", bad, "r")
    assert ledger.get_job(job.id) == job


def test_missing_job_rejected():
    with pytest.raises(LedgerError):
        ledger.transition("nope", "running", 1, "r")
    assert ledger.get_job("nope") is None


@pytest.mark.parametrize("dst,src", [("succeeded", "running"), ("failed", "running"),
                                     ("cancelled", "cancel_requested"), ("cancelled", "unknown")])
def test_receipt_required(dst, src):
    job = mk(src)
    for bad in (None, "text", {"x": object()}, {"big": "a" * 9000}):
        with pytest.raises(LedgerError):
            ledger.transition(job.id, dst, job.revision, "r", bad)
    assert ledger.get_job(job.id) == job


def test_receipt_stored_in_event_and_terminal_stamp():
    job = mk("running")
    out = ledger.transition(job.id, "succeeded", job.revision, "done", {"n": 1})
    assert out.terminal_at is not None and mk().terminal_at is None
    last = ledger.list_events(job.id)[-1]
    assert (last.from_state, last.to_state, last.reason, last.receipt) == ("running", "succeeded", "done", {"n": 1})


def test_events_follow_every_change():
    job = mk("running")
    ev = ledger.list_events(job.id)
    assert [(e.from_state, e.to_state, e.revision) for e in ev] == [
        (None, "queued", 1), ("queued", "running", 2)]


def test_event_and_state_change_are_atomic(monkeypatch):
    job = mk()
    real = ledger._append_event

    def boom(*a, **k):
        raise sqlite3.OperationalError("disk")

    monkeypatch.setattr(ledger, "_append_event", boom)
    with pytest.raises(LedgerError):
        ledger.transition(job.id, "running", job.revision, "r")
    monkeypatch.setattr(ledger, "_append_event", real)
    assert ledger.get_job(job.id) == job
    assert len(ledger.list_events(job.id)) == 1


def test_idempotent_create():
    a = ledger.create_job({"task": "x"}, "same")
    b = ledger.create_job({"task": "x"}, "same")
    assert a == b and len(ledger.list_jobs()) == 1 and len(ledger.list_events(a.id)) == 1


def test_same_key_different_spec_is_error():
    ledger.create_job({"task": "x"}, "same")
    with pytest.raises(LedgerError):
        ledger.create_job({"task": "y"}, "same")
    assert len(ledger.list_jobs()) == 1


def test_key_order_in_spec_does_not_matter():
    a = ledger.create_job({"a": 1, "b": 2}, "k")
    assert ledger.create_job({"b": 2, "a": 1}, "k") == a


@pytest.mark.parametrize("spec", [None, "s", [1], {"a": object()}, {"a": float("nan")},
                                  {"a": "x" * ledger.MAX_SPEC_BYTES}])
def test_bad_spec_rejected(spec):
    with pytest.raises(LedgerError):
        ledger.create_job(spec, "k")
    assert ledger.list_jobs() == []


@pytest.mark.parametrize("key", [None, "", 5, "k" * 200])
def test_bad_key_rejected(key):
    with pytest.raises(LedgerError):
        ledger.create_job({"a": 1}, key)


def test_list_by_state():
    a, b = mk(), mk("running")
    assert [j.id for j in ledger.list_jobs("running")] == [b.id]
    assert {j.id for j in ledger.list_jobs()} == {a.id, b.id}
    with pytest.raises(LedgerError):
        ledger.list_jobs("bogus")


def test_restart_recovery_never_replays():
    run, cancel, queued, wait = mk("running"), mk("cancel_requested"), mk(), mk("waiting_for_approval")
    done = mk("succeeded")
    assert ledger.recover_after_restart() == 2
    assert ledger.get_job(run.id).state == "unknown"
    assert ledger.get_job(cancel.id).state == "unknown"
    assert ledger.get_job(queued.id).state == "queued"
    assert ledger.get_job(wait.id).state == "waiting_for_approval"
    assert ledger.get_job(done.id).state == "succeeded"
    assert ledger.list_events(run.id)[-1].reason == "restart_running"
    assert ledger.list_events(cancel.id)[-1].reason == "restart_cancel_requested"
    assert ledger.recover_after_restart() == 0


def test_purge_boundary_and_non_terminal_survive():
    done, failed, cancelled = mk("succeeded"), mk("failed"), mk("cancelled")
    live = [mk(s) for s in ("queued", "running", "waiting_for_approval", "cancel_requested", "unknown")]
    stamp = datetime.fromisoformat(ledger.get_job(done.id).terminal_at)
    day14 = timedelta(days=14)
    assert ledger.purge(stamp + day14 - timedelta(seconds=1)) == 0
    assert ledger.get_job(done.id) is not None
    assert ledger.purge(datetime.now(UTC) + day14 + timedelta(seconds=1)) == 3
    for j in (done, failed, cancelled):
        assert ledger.get_job(j.id) is None and ledger.list_events(j.id) == []
    assert all(ledger.get_job(j.id) is not None for j in live)
    assert all(ledger.list_events(j.id) for j in live)
    with pytest.raises(LedgerError):
        ledger.purge(datetime.now())  # naive clock refused


def test_purge_exact_edge_is_purged():
    done = mk("succeeded")
    stamp = datetime.fromisoformat(ledger.get_job(done.id).terminal_at)
    assert ledger.purge(stamp + timedelta(days=14) - timedelta(microseconds=1)) == 0
    assert ledger.purge(stamp + timedelta(days=14)) == 1
    assert ledger.get_job(done.id) is None


def test_db_error_is_a_ledger_error(monkeypatch):
    def boom(*a, **k):
        raise sqlite3.OperationalError("locked")

    monkeypatch.setattr(ledger.sqlite3, "connect", boom)
    with pytest.raises(LedgerError):
        ledger.list_jobs()


def test_schema_version_set():
    ledger.create_job({"a": 1}, "k")
    con = sqlite3.connect(ledger.DB_PATH)
    assert con.execute("PRAGMA user_version").fetchone()[0] == 1
    con.close()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes do not exist on Windows")
def test_files_are_private_even_when_they_already_existed():
    old = os.umask(0)
    try:
        ledger.create_job({"a": 1}, "k")
        assert stat.S_IMODE(ledger.DB_PATH.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(ledger.DB_PATH.stat().st_mode) == 0o600
        ledger.DB_PATH.chmod(0o644)
        ledger.list_jobs()
        assert stat.S_IMODE(ledger.DB_PATH.stat().st_mode) == 0o600
    finally:
        os.umask(old)


def test_deeply_nested_receipt_is_a_ledger_error_not_a_recursion_error():
    deep = {}
    for _ in range(20000):
        deep = {"a": deep}
    job = ledger.create_job({"a": 1}, "deep")
    with pytest.raises(ledger.LedgerError):
        ledger.transition(job.id, "running", job.revision, "start", deep)


@pytest.mark.parametrize("state", ["running", "cancel_requested"])
def test_append_note_adds_an_event_without_changing_state_or_revision(state):
    job = mk(state)
    before = ledger.get_job(job.id)
    ledger.append_note(job.id, "step", {"step": 0})
    after = ledger.get_job(job.id)
    assert (after.state, after.revision, after.updated_at) == (before.state, before.revision, before.updated_at)
    last = ledger.list_events(job.id)[-1]
    assert (last.from_state, last.to_state, last.revision) == (state, state, before.revision)
    assert (last.reason, last.receipt) == ("step", {"step": 0})


@pytest.mark.parametrize("state", ["queued", "waiting_for_approval", "unknown", "succeeded", "failed", "cancelled"])
def test_append_note_refused_unless_running_or_cancel_requested(state):
    job = mk(state)
    count = len(ledger.list_events(job.id))
    with pytest.raises(LedgerError):
        ledger.append_note(job.id, "step", {"step": 0})
    assert len(ledger.list_events(job.id)) == count


@pytest.mark.parametrize("reason,receipt", [
    ("", {"a": 1}), ("x" * 65, {"a": 1}), (None, {"a": 1}), ("step", None), ("step", "text"),
    ("step", {"big": "x" * 5000}), ("step", {"n": float("nan")}),
])
def test_append_note_validates_like_other_receipts(reason, receipt):
    job = mk("running")
    count = len(ledger.list_events(job.id))
    with pytest.raises(LedgerError):
        ledger.append_note(job.id, reason, receipt)
    assert len(ledger.list_events(job.id)) == count


def test_append_note_unknown_job_is_a_ledger_error():
    with pytest.raises(LedgerError):
        ledger.append_note("nope", "step", {"a": 1})


def test_notes_do_not_break_a_later_transition_on_the_same_revision():
    job = mk("running")
    ledger.append_note(job.id, "step", {"step": 0})
    done = ledger.transition(job.id, "succeeded", job.revision, "done", RECEIPT)
    assert done.state == "succeeded"


def test_claim_next_job_empty_returns_none():
    assert ledger.claim_next_job("bot-1") is None


def test_claim_next_job_claims_queued_in_fifo_order():
    j1 = ledger.create_job({"task": "first"}, "k-fifo-1")
    j2 = ledger.create_job({"task": "second"}, "k-fifo-2")

    claimed1 = ledger.claim_next_job("bot-alpha")
    assert claimed1 is not None
    assert claimed1.id == j1.id
    assert claimed1.state == "running"
    assert claimed1.revision == 2

    # Verify event recorded
    events1 = ledger.list_events(j1.id)
    assert any(e.to_state == "running" and e.reason == "claimed_bot-alpha" for e in events1)

    claimed2 = ledger.claim_next_job("bot-beta")
    assert claimed2 is not None
    assert claimed2.id == j2.id
    assert claimed2.state == "running"

    assert ledger.claim_next_job("bot-gamma") is None


def test_claim_next_job_validates_inputs():
    with pytest.raises(LedgerError):
        ledger.claim_next_job("")
    with pytest.raises(LedgerError):
        ledger.claim_next_job("x" * 65)
    with pytest.raises(LedgerError):
        ledger.claim_next_job(123)
    with pytest.raises(LedgerError):
        ledger.claim_next_job("bot", state="invalid_state")


def test_postgres_seam_query_formatting(monkeypatch):
    executed = []

    class DummyCursor:
        def __init__(self):
            self.rowcount = 1
        def execute(self, sql, params=()):
            executed.append((sql, params))
        def fetchone(self):
            return ("test-id", "test-key", '{"t": 1}', "queued", 1, "2026-11-16T00:00:00.000000+00:00", "2026-11-16T00:00:00.000000+00:00", None)
        def fetchall(self):
            return []
        def close(self):
            pass

    class DummyConn:
        def cursor(self):
            return DummyCursor()
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            pass

    dummy_driver = type("DummyDriver", (), {"connect": lambda url: DummyConn()})
    monkeypatch.setattr(ledger, "DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
    monkeypatch.setattr(ledger, "psycopg2", dummy_driver)
    monkeypatch.setattr(ledger, "_pg_initialized", True)

    claimed = ledger.claim_next_job("pg-worker")
    assert claimed is not None
    assert claimed.id == "test-id"
    # Ensure parameter placeholder ? was replaced with %s and SKIP LOCKED was used
    assert any("FOR UPDATE SKIP LOCKED" in sql and "%s" in sql for sql, _ in executed)

