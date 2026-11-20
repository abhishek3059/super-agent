"""R-02.F3: the ledger on a real loopback PostgreSQL. Opt-in: set SUPER_AGENT_PG_TEST_URL to a throwaway
database on 127.0.0.1. Every test drops the ledger tables first, so never point it at data you keep."""
import os
from datetime import UTC, datetime

import pytest

from super_agent_voice import ledger, policy
from super_agent_voice.ledger import LedgerError

URL = os.environ.get("SUPER_AGENT_PG_TEST_URL")
pytestmark = pytest.mark.skipif(not URL or ledger.psycopg2 is None, reason="needs SUPER_AGENT_PG_TEST_URL and psycopg2")
SPEC = {"task_type": "answer", "instruction": "what is 2+2", "data_class": "synthetic"}


@pytest.fixture(autouse=True)
def pg(monkeypatch):
    monkeypatch.setattr(ledger, "DATABASE_URL", URL)
    monkeypatch.setattr(ledger, "_pg_initialized", False)
    raw = ledger.psycopg2.connect(ledger._pg_url())  # the loopback check runs before the tables are dropped
    raw.cursor().execute("DROP TABLE IF EXISTS events; DROP TABLE IF EXISTS jobs")
    raw.commit()
    raw.close()


def test_same_states_revisions_and_receipts_as_sqlite():
    job = ledger.create_job({"task": "x"}, "k1")
    assert ledger.create_job({"task": "x"}, "k1") == job  # idempotent
    with pytest.raises(LedgerError):
        ledger.create_job({"task": "y"}, "k1")  # same key, other spec
    running = ledger.transition(job.id, "running", job.revision, "r")
    with pytest.raises(ledger.StaleRevision):
        ledger.transition(job.id, "cancel_requested", job.revision, "r")
    with pytest.raises(LedgerError):
        ledger.transition(job.id, "queued", running.revision, "r")  # not in NEXT
    with pytest.raises(LedgerError):
        ledger.transition(job.id, "succeeded", running.revision, "done")  # terminal needs a receipt
    done = ledger.transition(job.id, "succeeded", running.revision, "done", {"result": 4})
    assert (done.state, done.revision) == ("succeeded", 3)
    assert [e.to_state for e in ledger.list_events(job.id)] == ["queued", "running", "succeeded"]


def test_claim_and_restart_recovery():
    first = ledger.create_job({"task": "a"}, "ka")
    ledger.create_job({"task": "b"}, "kb")
    claimed = ledger.claim_next_job("w1")
    assert claimed.id == first.id and claimed.state == "running"
    assert ledger.recover_after_restart() == 1
    assert ledger.get_job(first.id).state == "unknown"


def test_admission_writes_through_the_same_ledger():
    now = datetime.now(UTC)
    adm = policy.admit(dict(SPEC), "k-admit", False, policy.Limits(), ledger, now)
    again = policy.admit(dict(SPEC), "k-admit", False, policy.Limits(), ledger, now)
    assert adm.job.id == again.job.id and len(ledger.list_jobs()) == 1
