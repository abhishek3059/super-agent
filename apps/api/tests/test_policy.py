import dataclasses
import itertools
from datetime import UTC, datetime, timedelta

import pytest

from super_agent_voice import ledger, policy
from super_agent_voice.policy import REASONS, Limits, PolicyError, admit

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
GOOD = {"task_type": "answer", "instruction": "What is 2 plus 2?", "data_class": "synthetic"}


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "DB_PATH", tmp_path / "led" / "ledger.db")


def go(spec=GOOD, key="k1", local=True, limits=None, now=NOW, **kw):
    return admit(spec, key, local, limits or Limits(), ledger, now, **kw)


def code(fn, *a, **kw):
    with pytest.raises(PolicyError) as err:
        fn(*a, **kw)
    assert err.value.code in REASONS and str(err.value) == err.value.code
    return err.value.code


def untouched():
    return ledger.list_jobs() == []


# --- limits ---------------------------------------------------------------

def test_default_limits_match_the_design_table():
    d = Limits()
    assert (d.steps_per_job, d.step_deadline_s, d.job_deadline_s, d.retries_per_step, d.model_calls_per_job,
            d.model_input_chars, d.step_output_chars, d.concurrent_jobs, d.queued_jobs) == (
        8, 30, 300, 1, 12, 8000, 4000, 2, 5)


def test_limits_are_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Limits().steps_per_job = 99


@pytest.mark.parametrize("field", [f.name for f in dataclasses.fields(Limits)])
@pytest.mark.parametrize("bad", [0, -1, True, False, 1.0, "3", None, 10**9])
def test_invalid_limits_cannot_be_built(field, bad):
    with pytest.raises(PolicyError) as err:
        Limits(**{field: bad})
    assert err.value.code == "limits_invalid"


@pytest.mark.parametrize("field", [f.name for f in dataclasses.fields(Limits)])
def test_ceiling_is_allowed_and_one_above_is_not(field):
    top = policy.CEILING[field]
    assert getattr(Limits(**{field: top}), field) == top
    code(Limits, **{field: top + 1})


def test_non_limits_object_is_rejected():
    assert code(go, limits={"steps_per_job": 99}) == "limits_invalid"
    assert untouched()


# --- spec -----------------------------------------------------------------

@pytest.mark.parametrize("spec,reason", [
    (None, "spec_invalid"), ([], "spec_invalid"), ("x", "spec_invalid"),
    ({}, "spec_invalid"),
    ({"task_type": "answer", "instruction": "x"}, "spec_invalid"),
    ({**GOOD, "tools": ["read_file"]}, "spec_invalid"),
    ({**GOOD, "limits": {"steps_per_job": 99}}, "spec_invalid"),
    ({**GOOD, "task_type": "shell"}, "task_type_invalid"),
    ({**GOOD, "task_type": 1}, "task_type_invalid"),
    ({**GOOD, "task_type": ["answer"]}, "task_type_invalid"),
    ({**GOOD, "instruction": ""}, "instruction_invalid"),
    ({**GOOD, "instruction": "   "}, "instruction_invalid"),
    ({**GOOD, "instruction": 5}, "instruction_invalid"),
    ({**GOOD, "instruction": {"a": {1, 2}}}, "instruction_invalid"),
    ({**GOOD, "instruction": b"x"}, "instruction_invalid"),
    ({**GOOD, "instruction": "bad \ud800 surrogate"}, "instruction_invalid"),
    ({**GOOD, "instruction": "x" * 1001}, "instruction_invalid"),
    ({**GOOD, "data_class": "secret"}, "data_class_invalid"),
    ({**GOOD, "data_class": True}, "data_class_invalid"),
    ({**GOOD, "data_class": None}, "data_class_invalid"),
])
def test_bad_specs_fail_closed(spec, reason):
    assert code(go, spec) == reason
    assert untouched()


def test_instruction_limit_follows_limits_object():
    assert go({**GOOD, "instruction": "x" * 1000}).job
    assert code(go, {**GOOD, "instruction": "x" * 11}, key="k2",
                limits=Limits(instruction_chars=10)) == "instruction_invalid"


def test_free_text_never_reaches_the_error():
    secret = "TOPSECRET-" + "x" * 2000
    for spec in ({**GOOD, "instruction": secret}, {**GOOD, "task_type": secret}, {**GOOD, "data_class": secret},
                 {**GOOD, secret: 1}):
        with pytest.raises(PolicyError) as err:
            go(spec)
        assert "TOPSECRET" not in str(err.value) and "TOPSECRET" not in repr(err.value)
        assert err.value.code in REASONS


@pytest.mark.parametrize("key", ["", None, 5, True, "k" * 129])
def test_bad_idempotency_key(key):
    assert code(go, key=key) == "idempotency_key_invalid"
    assert untouched()


# --- tool scope -----------------------------------------------------------

def test_tools_come_from_the_task_type_only():
    a = go(key="a")
    s = go({**GOOD, "task_type": "summarize"}, key="b")
    assert a.tools == policy.TOOL_SCOPE["answer"] | policy.PERSONAL_TOOLS["answer"]
    assert s.tools == policy.TOOL_SCOPE["summarize"] | policy.PERSONAL_TOOLS["summarize"]
    assert isinstance(a.tools, frozenset)


def test_no_scope_contains_a_write_tool():
    from super_agent_voice import memory
    every = set().union(*policy.TOOL_SCOPE.values(), *policy.PERSONAL_TOOLS.values())
    assert not every & memory.WRITES
    assert {"calculate", "current_time"} >= set().union(*policy.TOOL_SCOPE.values())


def test_scope_tables_cover_exactly_the_task_types():
    assert set(policy.TOOL_SCOPE) == set(policy.PERSONAL_TOOLS) == set(policy.TASK_TYPES)


def test_personal_tools_are_real_tool_names():
    from super_agent_voice import memory, tier1
    known = tier1.T1_NAMES | memory.NAMES
    assert set().union(*policy.PERSONAL_TOOLS.values()) <= known


# --- data-class rule ------------------------------------------------------

@pytest.mark.parametrize("local,dc,mem_synth",
                         list(itertools.product([True, False], ["synthetic", "personal"], [True, False])))
def test_data_class_table(local, dc, mem_synth):
    spec = {**GOOD, "data_class": dc}
    if not local and dc == "personal":
        assert code(go, spec, local=local, memory_is_synthetic=mem_synth) == "personal_data_cloud_planner"
        assert untouched()
        return
    out = go(spec, local=local, memory_is_synthetic=mem_synth)
    assert out.tools == policy.TOOL_SCOPE["answer"] | policy.PERSONAL_TOOLS["answer"]
    assert out.memory_context is (local or mem_synth)


@pytest.mark.parametrize("local", [None, 1, 0, "true", "", [], 1.0])
@pytest.mark.parametrize("dc", ["synthetic", "personal"])
def test_locality_must_be_exactly_a_bool(local, dc):
    assert code(go, {**GOOD, "data_class": dc}, local=local) == "planner_locality_invalid"
    assert untouched()


def test_missing_locality_argument_is_a_type_error_not_an_allow():
    with pytest.raises(TypeError):
        admit(GOOD, "k", limits=Limits(), ledger=ledger, now=NOW)


@pytest.mark.parametrize("flag", [None, 1, "yes"])
def test_memory_synthetic_flag_must_be_a_bool(flag):
    assert code(go, local=False, memory_is_synthetic=flag) == "memory_flag_invalid"
    assert untouched()


def test_spec_cannot_claim_locality_or_memory():
    for extra in ({"planner_local": True}, {"memory_is_synthetic": True}):
        assert code(go, {**GOOD, "data_class": "personal", **extra}, local=False) == "spec_invalid"


# --- admission, queue and ledger ------------------------------------------

def test_admission_creates_the_job_and_computes_the_deadline():
    out = go()
    assert out.job.state == "queued" and out.job.spec == GOOD
    assert out.deadline == NOW + timedelta(seconds=300)
    assert [e.reason for e in ledger.list_events(out.job.id)] == ["created"]


def test_deadline_uses_limits_not_the_spec():
    assert go(limits=Limits(job_deadline_s=60)).deadline == NOW + timedelta(seconds=60)


def test_same_key_same_spec_returns_the_same_job():
    a, b = go(), go()
    assert a.job.id == b.job.id and len(ledger.list_jobs()) == 1


def test_same_key_other_spec_is_rejected():
    go()
    assert code(go, {**GOOD, "instruction": "other"}) == "ledger_rejected"
    assert len(ledger.list_jobs()) == 1


@pytest.mark.parametrize("now", [None, "now", 5, datetime(2026, 1, 1)])
def test_clock_must_be_timezone_aware(now):
    assert code(go, now=now) == "clock_invalid"
    assert untouched()


def test_queue_cap_rejects_and_writes_nothing():
    lim = Limits(concurrent_jobs=1, queued_jobs=2)
    for i in range(3):
        go(key=f"k{i}", limits=lim)
    events = sum(len(ledger.list_events(j.id)) for j in ledger.list_jobs())
    assert code(go, key="over", limits=lim) == "queue_full"
    assert len(ledger.list_jobs()) == 3
    assert sum(len(ledger.list_events(j.id)) for j in ledger.list_jobs()) == events


def test_terminal_jobs_do_not_count_toward_the_cap():
    lim = Limits(concurrent_jobs=1, queued_jobs=1)
    a, _ = go(key="a", limits=lim), go(key="b", limits=lim)
    assert code(go, key="c", limits=lim) == "queue_full"
    ledger.transition(a.job.id, "failed", a.job.revision, "t", {"ok": False})
    assert go(key="c", limits=lim).job


def test_repeat_of_an_admitted_key_still_works_when_the_queue_is_full():
    lim = Limits(concurrent_jobs=1, queued_jobs=1)
    a = go(key="a", limits=lim)
    go(key="b", limits=lim)
    assert go(key="a", limits=lim).job.id == a.job.id


def test_ledger_failure_becomes_a_policy_error():
    class Broken:
        LedgerError = ledger.LedgerError

        def list_jobs(self, state=None):
            raise ledger.LedgerError("x")
    assert code(admit, GOOD, "k", True, Limits(), Broken(), NOW) == "ledger_error"


# --- step-level checks ----------------------------------------------------

@pytest.mark.parametrize("i", [0, 7])
def test_step_index_within_limit(i):
    assert policy.check_step_index(i, Limits()) is True


@pytest.mark.parametrize("i", [8, 9, -1])
def test_step_index_breach(i):
    assert code(policy.check_step_index, i, Limits()) == "step_limit"


@pytest.mark.parametrize("i", [True, 1.0, "1", None])
def test_step_index_bad_type(i):
    assert code(policy.check_step_index, i, Limits()) == "input_invalid"


def test_retry_only_for_idempotent_read_only_steps_within_limit():
    assert policy.check_retry("read_tool", 0, Limits()) is True
    assert code(policy.check_retry, "read_tool", 1, Limits()) == "retries_exhausted"
    assert policy.check_retry("read_tool", 1, Limits(retries_per_step=2)) is True
    assert code(policy.check_retry, "read_tool", 2, Limits(retries_per_step=2)) == "retries_exhausted"
    for step in ("summarize", "ask_user", "finish"):
        assert code(policy.check_retry, step, 0, Limits()) == "retry_not_allowed"
    assert code(policy.check_retry, "shell", 0, Limits()) == "step_type_unknown"
    assert code(policy.check_retry, ["read_tool"], 0, Limits()) == "step_type_unknown"


@pytest.mark.parametrize("n", [True, -1, 1.0, None])
def test_retry_count_bad_type(n):
    assert code(policy.check_retry, "read_tool", n, Limits()) == "input_invalid"


def test_retry_ceiling_is_two():
    assert policy.CEILING["retries_per_step"] == 2


def test_step_deadline():
    lim = Limits()
    assert policy.check_step_deadline(NOW, NOW + timedelta(seconds=30), lim) is True
    assert code(policy.check_step_deadline, NOW, NOW + timedelta(seconds=31), lim) == "step_deadline"


def test_job_deadline():
    d = NOW + timedelta(seconds=300)
    assert policy.check_job_deadline(d, d) is True
    assert code(policy.check_job_deadline, d, d + timedelta(microseconds=1)) == "job_deadline"


@pytest.mark.parametrize("bad", [None, "x", 5, datetime(2026, 1, 1)])
def test_deadline_inputs_fail_closed(bad):
    assert code(policy.check_job_deadline, bad, NOW) == "input_invalid"
    assert code(policy.check_job_deadline, NOW, bad) == "input_invalid"
    assert code(policy.check_step_deadline, bad, NOW, Limits()) == "input_invalid"
    assert code(policy.check_step_deadline, NOW, bad, Limits()) == "input_invalid"


def test_model_call_and_size_budgets():
    lim = Limits()
    assert policy.check_model_call(11, 8000, lim) is True
    assert code(policy.check_model_call, 12, 10, lim) == "model_call_limit"
    assert code(policy.check_model_call, 0, 8001, lim) == "input_too_large"
    assert code(policy.check_model_call, True, 10, lim) == "input_invalid"
    assert code(policy.check_model_call, 0, -1, lim) == "input_invalid"
    assert policy.check_step_output(4000, lim) is True
    assert code(policy.check_step_output, 4001, lim) == "output_too_large"
    assert code(policy.check_step_output, True, lim) == "input_invalid"


def test_step_checks_reject_a_non_limits_object():
    assert code(policy.check_step_index, 0, None) == "limits_invalid"
    assert code(policy.check_retry, "read_tool", 0, {}) == "limits_invalid"
