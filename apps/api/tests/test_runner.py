import asyncio
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest

from super_agent_voice import ledger, memory, policy, tier1
from super_agent_voice.runner import HERMES_WORKERS, Runner, get_worker, list_workers

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

    def __call__(self, job, adm, should_stop):
        self.calls.append((job, adm))
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
    runner, adm = made(lambda j, a, s: work(j, a, lambda: False)), admit()
    runner.submit(adm)
    wait_state(adm.job, "running")
    runner.cancel(adm.job.id)
    work.release.set()
    wait_state(adm.job, "succeeded")


def test_cancel_unknown_or_terminal_job_is_refused(made):
    runner, adm = made(lambda j, a, s: {"ok": 1}), admit()
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
    def boom(job, adm, should_stop):
        raise RuntimeError("secret personal text")

    runner, adm = made(boom), admit()
    runner.submit(adm)
    wait_state(adm.job, "failed")
    events = ledger.list_events(adm.job.id)
    assert events[-1].reason == "work_error"
    assert "secret" not in repr(events)


def test_work_receives_the_admission_with_filtered_tools(made, monkeypatch):
    monkeypatch.setattr(tier1, "enabled_tools", lambda: [])
    work = Hold()
    work.release.set()
    runner, adm = made(work), admit()
    runner.submit(adm)
    wait_state(adm.job, "succeeded")
    got = work.calls[0][1]
    assert got.deadline == adm.deadline and got.planner_is_local is adm.planner_is_local
    assert got.tools < adm.tools and not got.tools & tier1.T1_NAMES


def test_policy_error_code_is_recorded_as_a_fixed_code(made):
    def refuse(job, adm, should_stop):
        raise policy.PolicyError("plan_invalid")

    runner, adm = made(refuse), admit()
    runner.submit(adm)
    wait_state(adm.job, "failed")
    last = ledger.list_events(adm.job.id)[-1]
    assert last.reason == "work_error" and last.receipt == {"error": "work_error", "code": "plan_invalid"}


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
    runner, adm = made(lambda j, a, s: receipt), admit()
    runner.submit(adm)
    wait_state(adm.job, "failed")
    assert ledger.list_events(adm.job.id)[-1].reason == "bad_receipt"


def test_disabled_tier1_tools_are_removed(made, monkeypatch):
    monkeypatch.setenv("SUPER_AGENT_MEMORY", "on")
    monkeypatch.setattr(tier1, "enabled_tools", lambda: [{"function": {"name": "list_files"}}])
    work = Hold()
    work.release.set()
    runner, adm = made(work), admit()
    assert "read_file" in adm.tools and "calendar_events" in adm.tools
    runner.submit(adm)
    wait_state(adm.job, "succeeded")
    assert work.calls[0][1].tools == policy.TOOL_SCOPE["answer"] | {"list_files"} | policy.MEMORY_TOOLS["answer"]


@pytest.mark.parametrize("setting", [None, "off", "maybe"])
def test_memory_tools_are_removed_unless_memory_is_on(made, monkeypatch, setting):
    if setting is None:
        monkeypatch.delenv("SUPER_AGENT_MEMORY", raising=False)
    else:
        monkeypatch.setenv("SUPER_AGENT_MEMORY", setting)
    work = Hold()
    work.release.set()
    runner, adm = made(work), admit()
    assert adm.tools & memory.NAMES and adm.memory_context
    runner.submit(adm)
    wait_state(adm.job, "succeeded")
    assert not work.calls[0][1].tools & memory.NAMES and work.calls[0][1].memory_context is False


def test_tier1_config_error_removes_all_tier1_tools(made, monkeypatch):
    def bad():
        raise RuntimeError("bad config")

    monkeypatch.setattr(tier1, "enabled_tools", bad)
    work = Hold()
    work.release.set()
    runner, adm = made(work), admit()
    runner.submit(adm)
    wait_state(adm.job, "succeeded")
    assert not work.calls[0][1].tools & tier1.T1_NAMES


def test_one_terminal_event_and_each_transition_once(made):
    runner = made(lambda j, a, s: {"ok": 1})
    adms = [admit(f"k{i}") for i in range(4)]
    for a in adms:
        runner.submit(a)
    for a in adms:
        wait_state(a.job, "succeeded")
        assert [e.to_state for e in ledger.list_events(a.job.id)] == ["queued", "running", "succeeded"]


def test_recover_marks_running_unknown_and_fails_queued(made):
    ran = []
    runner = made(lambda j, a, s: ran.append(j) or {"ok": 1})
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
        Runner(ledger, bad, lambda j, a, s: {}, lambda: NOW)
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


def test_refused_success_write_is_not_recorded_as_a_bad_receipt():
    class RefuseOnce(Flaky):
        def transition(self, job_id, to_state, *a, **kw):
            if to_state == "succeeded":
                raise ledger.LedgerError("ledger storage failed")
            return ledger.transition(job_id, to_state, *a, **kw)

    runner = Runner(RefuseOnce(), policy.Limits(), lambda j, a, s: {"ok": 1}, lambda: NOW)
    adm = admit()
    try:
        runner.submit(adm)
        wait_state(adm.job, "unknown")
    finally:
        runner.close()
    last = ledger.list_events(adm.job.id)[-1]
    assert last.reason == "terminal_write_failed"
    assert "bad_receipt" not in repr(ledger.list_events(adm.job.id))


def test_deeply_nested_receipt_is_a_bad_receipt_not_a_failed_write(made):
    deep = {}
    for _ in range(20000):
        deep = {"a": deep}
    runner, adm = made(lambda j, a, s: deep), admit()
    runner.submit(adm)
    wait_state(adm.job, "failed")
    assert ledger.list_events(adm.job.id)[-1].reason == "bad_receipt"


def test_hermes_worker_definitions():
    workers = list_workers()
    assert len(workers) == 5
    names = {w.name for w in workers}
    assert names == {"researcher", "coder", "secretary", "librarian", "ops"}

    for name in names:
        worker = get_worker(name)
        assert worker is not None
        assert worker.name == name
        assert len(worker.role) > 0
        assert len(worker.description) > 0


def test_claim_and_run_executes_claimed_job(made):
    executed = []
    def work(job, adm, should_stop):
        executed.append((job.id, adm.tools))
        return {"result": f"processed_{job.id}"}

    runner = made(work)
    # create a job directly in queued state
    job = ledger.create_job(dict(SPEC), "k-runner-claim-1")

    claimed = runner.claim_and_run("researcher")
    assert claimed is not None
    assert claimed.id == job.id

    wait_state(job, "succeeded")
    assert len(executed) == 1
    assert executed[0][0] == job.id
    assert "calculate" in executed[0][1]

    # Empty claim returns None
    assert runner.claim_and_run("coder") is None



def test_claim_and_run_goes_through_admit(made):
    ran = []
    runner = made(lambda job, adm, stop: ran.append(adm.tools) or {"result": "x"})
    bad = ledger.create_job({"task": "no schema"}, "k-bad")
    assert runner.claim_and_run("researcher").id == bad.id
    personal = ledger.create_job({**SPEC, "data_class": "personal"}, "k-personal")  # cloud planner by default
    assert runner.claim_and_run("researcher").id == personal.id
    for job in (bad, personal):
        assert state(job) == "failed"
        assert ledger.list_events(job.id)[-1].receipt["executed"] is False
    assert ledger.list_events(personal.id)[-1].reason == "policy_personal_data_cloud_planner"
    assert ran == []
    ok = ledger.create_job(dict(SPEC), "k-ok")
    runner.claim_and_run("librarian")  # memory reads are outside the answer scope for a cloud planner
    wait_state(ok, "succeeded")
    assert ran == [frozenset()]
    local = Runner(ledger, policy.Limits(), lambda job, adm, stop: ran.append(adm.tools) or {"r": 1}, lambda: NOW, True)
    mine = ledger.create_job({**SPEC, "data_class": "personal"}, "k-mine")
    local.claim_and_run("librarian")
    wait_state(mine, "succeeded")
    assert ran[-1] == frozenset({"list_memory", "list_reminders"}) - (memory.NAMES if not memory.enabled() else set())
    local.close()


def test_a_hermes_worker_can_only_narrow_the_task_scope():
    """R-02.F3: the five Hermes definitions sit behind admission. A worker never adds a tool."""
    for n, (task_type, local) in enumerate([(t, l) for t in policy.TASK_TYPES for l in (False, True)]):
        job = ledger.create_job({"task_type": task_type, "instruction": "x", "data_class": "synthetic"}, f"k-{n}")
        scope = policy.admit_claimed(job, frozenset({"calculate", "current_time", *tier1.T1_NAMES, *memory.NAMES}),
                                     local, policy.Limits()).tools
        for worker in HERMES_WORKERS.values():
            assert policy.admit_claimed(job, frozenset(worker.allowed_tools), local, policy.Limits()).tools <= scope
            assert not set(worker.allowed_tools) & memory.WRITES
