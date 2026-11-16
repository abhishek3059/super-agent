import asyncio
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest

from super_agent_voice import ledger, policy, tier1
from super_agent_voice.runner import Runner

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
SPEC = {"task_type": "answer", "instruction": "What is 2 plus 2?", "data_class": "synthetic"}
WAIT = 5.0


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "DB_PATH", tmp_path / "led" / "ledger.db")


@pytest.fixture
def made():
    runners = []

    def make(work, limits=None, clock=lambda: NOW):
        r = Runner(ledger, limits or policy.Limits(), work, clock)
        runners.append(r)
        return r
    yield make
    for r in runners:
        r.close()


def admit(key="k1", local=True):
    return policy.admit(SPEC, key, local, policy.Limits(), ledger, NOW)


def wait_for(predicate, timeout=WAIT):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.005)
    raise AssertionError("timed out")


def state(job):
    return ledger.get_job(job.id).state


def wait_state(job, want):
    wait_for(lambda: state(job) == want)


class Hold:
    """Work that records its calls and blocks until released."""

    def __init__(self, result=None):
        self.started, self.release, self.calls = threading.Event(), threading.Event(), []
        self.stops, self.result = [], result if result is not None else {"answer": "4"}

    def __call__(self, job, tools, should_stop):
        self.calls.append((job, tools))
        self.started.set()
        assert self.release.wait(WAIT)
        self.stops.append(should_stop())
        return self.result


def test_event_loop_answers_while_a_job_runs(made):
    work = Hold()
    runner, adm = made(work), admit()

    async def main():
        loop = asyncio.get_running_loop()
        runner.submit(adm)
        await loop.run_in_executor(None, work.started.wait, WAIT)
        assert await asyncio.sleep(0, "answered") == "answered"
        assert state(adm.job) == "running"
        work.release.set()
        await loop.run_in_executor(None, wait_state, adm.job, "succeeded")

    asyncio.run(main())
    assert ledger.list_events(adm.job.id)[-1].receipt == {"answer": "4"}


def test_submit_returns_before_the_work_finishes(made):
    work = Hold()
    runner, adm = made(work), admit()
    runner.submit(adm)
    assert not work.release.is_set() and state(adm.job) in {"queued", "running"}
    work.release.set()
    wait_state(adm.job, "succeeded")


def test_cancel_running_job_stops_it(made):
    work = Hold()
    runner, adm = made(work), admit()
    runner.submit(adm)
    wait_state(adm.job, "running")
    assert runner.cancel(adm.job.id).state == "cancel_requested"
    assert state(adm.job) == "cancel_requested"
    work.release.set()
    wait_state(adm.job, "cancelled")
    assert work.stops == [True]
    assert ledger.list_events(adm.job.id)[-1].receipt == {"stopped": True}


def test_cancel_queued_job_never_runs(made):
    work = Hold()
    runner = made(work, policy.Limits(concurrent_jobs=1))
    first, second = admit("a"), admit("b")
    runner.submit(first)
    wait_state(first.job, "running")
    runner.submit(second)
    assert runner.cancel(second.job.id).state == "cancelled"
    work.release.set()
    wait_state(first.job, "succeeded")
    assert [c[0].id for c in work.calls] == [first.job.id]
    assert ledger.list_events(second.job.id)[-1].receipt == {"executed": False}
    assert [e.to_state for e in ledger.list_events(second.job.id)] == ["queued", "cancel_requested", "cancelled"]


def test_work_that_ignores_cancel_may_succeed(made):
    work = Hold()
    runner, adm = made(lambda j, t, s: work(j, t, lambda: False)), admit()
    runner.submit(adm)
    wait_state(adm.job, "running")
    runner.cancel(adm.job.id)
    work.release.set()
    wait_state(adm.job, "succeeded")


def test_cancel_unknown_or_terminal_job_is_refused(made):
    runner, adm = made(lambda j, t, s: {"ok": 1}), admit()
    with pytest.raises(ledger.LedgerError):
        runner.cancel("nope")
    runner.submit(adm)
    wait_state(adm.job, "succeeded")
    with pytest.raises(ledger.LedgerError):
        runner.cancel(adm.job.id)


def test_concurrency_cap(made):
    work = Hold()
    runner = made(work, policy.Limits(concurrent_jobs=2))
    adms = [admit(f"k{i}") for i in range(3)]
    for a in adms:
        runner.submit(a)
    wait_for(lambda: len(ledger.list_jobs("running")) == 2)
    time.sleep(0.1)  # give a wrongly started third job time to show itself
    assert len(ledger.list_jobs("running")) == 2 and len(ledger.list_jobs("queued")) == 1
    work.release.set()
    wait_for(lambda: len(ledger.list_jobs("succeeded")) == 3)


def test_work_error_fails_without_leaking_text(made):
    def boom(job, tools, should_stop):
        raise RuntimeError("secret personal text")

    runner, adm = made(boom), admit()
    runner.submit(adm)
    wait_state(adm.job, "failed")
    events = ledger.list_events(adm.job.id)
    assert events[-1].reason == "work_error"
    assert "secret" not in repr(events)


def test_deadline_passed_fails_the_job(made):
    clock = [NOW]
    work = Hold()
    runner, adm = made(work, clock=lambda: clock[0]), admit()
    runner.submit(adm)
    wait_state(adm.job, "running")
    clock[0] = NOW + timedelta(seconds=policy.Limits().job_deadline_s + 1)
    work.release.set()
    wait_state(adm.job, "failed")
    assert work.stops == [True]
    assert ledger.list_events(adm.job.id)[-1].reason == "job_deadline"


@pytest.mark.parametrize("receipt", ["text", None, {"big": "x" * 5000}, {"n": float("nan")}])
def test_bad_receipt_fails_instead_of_sticking(made, receipt):
    runner, adm = made(lambda j, t, s: receipt), admit()
    runner.submit(adm)
    wait_state(adm.job, "failed")
    assert ledger.list_events(adm.job.id)[-1].reason == "bad_receipt"


def test_disabled_tier1_tools_are_removed(made, monkeypatch):
    monkeypatch.setattr(tier1, "enabled_tools", lambda: [{"function": {"name": "list_files"}}])
    work = Hold()
    work.release.set()
    runner, adm = made(work), admit()
    assert "read_file" in adm.tools and "calendar_events" in adm.tools
    runner.submit(adm)
    wait_state(adm.job, "succeeded")
    assert work.calls[0][1] == policy.TOOL_SCOPE["answer"] | {"list_files"} | policy.MEMORY_TOOLS["answer"]


def test_tier1_config_error_removes_all_tier1_tools(made, monkeypatch):
    def bad():
        raise RuntimeError("bad config")

    monkeypatch.setattr(tier1, "enabled_tools", bad)
    work = Hold()
    work.release.set()
    runner, adm = made(work), admit()
    runner.submit(adm)
    wait_state(adm.job, "succeeded")
    assert not work.calls[0][1] & tier1.T1_NAMES


def test_one_terminal_event_and_each_transition_once(made):
    runner = made(lambda j, t, s: {"ok": 1})
    adms = [admit(f"k{i}") for i in range(4)]
    for a in adms:
        runner.submit(a)
    for a in adms:
        wait_state(a.job, "succeeded")
        assert [e.to_state for e in ledger.list_events(a.job.id)] == ["queued", "running", "succeeded"]


def test_recover_marks_running_unknown_and_fails_queued(made):
    ran = []
    runner = made(lambda j, t, s: ran.append(j) or {"ok": 1})
    running, queued = admit("a"), admit("b")
    ledger.transition(running.job.id, "running", 1, "test")
    assert runner.recover() == 2
    assert state(running.job) == "unknown" and state(queued.job) == "failed"
    last = ledger.list_events(queued.job.id)[-1]
    assert (last.reason, last.receipt) == ("restart_queued", {"executed": False})
    assert ran == []


@pytest.mark.parametrize("bad", [None, {"concurrent_jobs": 2}, 2])
def test_runner_refuses_invalid_limits(bad):
    with pytest.raises(policy.PolicyError) as err:
        Runner(ledger, bad, lambda j, t, s: {}, lambda: NOW)
    assert err.value.code == "limits_invalid"


class Flaky:
    """The ledger module with one get_job call made to fail, counted from arm()."""

    def __init__(self):
        self.calls, self.fail_on = 0, None

    def arm(self, n):
        self.calls, self.fail_on = 0, n

    def get_job(self, job_id):
        self.calls += 1
        if self.calls == self.fail_on:
            raise ledger.LedgerError("ledger storage failed")
        return ledger.get_job(job_id)

    def __getattr__(self, name):
        return getattr(ledger, name)


def test_failed_poll_never_records_success(store):
    flaky, work = Flaky(), Hold({"partial": True})
    runner = Runner(flaky, policy.Limits(), work, lambda: NOW)
    adm = admit()
    try:
        runner.submit(adm)
        wait_state(adm.job, "running")
        flaky.arm(1)  # the poll inside work
        work.release.set()
        wait_state(adm.job, "failed")
    finally:
        runner.close()
    last = ledger.list_events(adm.job.id)[-1]
    assert (last.reason, last.receipt) == ("stop_unconfirmed", {"error": "stop_unconfirmed"})
    assert "partial" not in repr(ledger.list_events(adm.job.id))


def test_cancel_with_unreadable_state_never_records_success(store):
    flaky, work = Flaky(), Hold({"partial": True})
    runner = Runner(flaky, policy.Limits(), work, lambda: NOW)
    adm = admit()
    try:
        runner.submit(adm)
        wait_state(adm.job, "running")
        runner.cancel(adm.job.id)
        flaky.arm(2)  # poll is call 1, the post-work state read is call 2
        work.release.set()
        wait_for(lambda: state(adm.job) not in {"running", "cancel_requested"})
    finally:
        runner.close()
    assert state(adm.job) == "failed"
    assert "partial" not in repr(ledger.list_events(adm.job.id))


def test_clock_that_raises_does_not_leave_the_job_running(made):
    broken, work = [], Hold()

    def clock():
        if broken:
            raise RuntimeError("clock down")
        return NOW

    runner, adm = made(work, clock=clock), admit()
    runner.submit(adm)
    wait_state(adm.job, "running")
    broken.append(True)
    work.release.set()
    wait_state(adm.job, "failed")
    assert ledger.list_events(adm.job.id)[-1].reason == "job_deadline"
