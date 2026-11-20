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


def full(task):
    return policy.TOOL_SCOPE[task] | policy.TIER1_FILE_TOOLS[task] | policy.TIER1_APP_TOOLS[task] | policy.MEMORY_TOOLS[task]


def untouched():
    return ledger.list_jobs() == []


# --- limits ---------------------------------------------------------------

def test_default_limits_match_the_design_table():
    d = Limits()
    assert (d.steps_per_job, d.step_deadline_s, d.job_deadline_s, d.retries_per_step, d.model_calls_per_job,
            d.model_input_chars, d.step_output_chars, d.concurrent_jobs, d.queued_jobs, d.instruction_chars) == (
        8, 30, 300, 1, 12, 8000, 4000, 2, 5, 1000)


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
    assert a.tools == full("answer")
    assert s.tools == full("summarize")
    assert isinstance(a.tools, frozenset)


def test_no_scope_contains_a_write_tool():
    from super_agent_voice import memory
    from super_agent_voice import tools
    every = set().union(*policy.TOOL_SCOPE.values(), *policy.TIER1_FILE_TOOLS.values(),
                        *policy.TIER1_APP_TOOLS.values(), *policy.MEMORY_TOOLS.values())
    assert not every & memory.WRITES
    base = {t["function"]["name"] for t in tools.TOOLS} | {t["name"] for t in tools.GEMINI_FUNCTIONS}
    assert set().union(*policy.TOOL_SCOPE.values()) <= base


def test_scope_tables_cover_exactly_the_task_types():
    assert set(policy.TOOL_SCOPE) == set(policy.TIER1_FILE_TOOLS) == set(policy.TIER1_APP_TOOLS) == set(policy.MEMORY_TOOLS) == set(policy.TASK_TYPES)


def test_personal_tools_are_real_tool_names():
    from super_agent_voice import memory, tier1
    known = tier1.T1_NAMES | memory.NAMES
    files = set().union(*policy.TIER1_FILE_TOOLS.values())
    apps = set().union(*policy.TIER1_APP_TOOLS.values())
    groups = {schema["function"]["name"]: group for group, schema in tier1._TOOLS}
    assert files | apps <= tier1.T1_NAMES
    assert {groups[n] for n in files} == {"files"}
    assert "files" not in {groups[n] for n in apps}
    assert files | apps == tier1.T1_NAMES
    assert set().union(*policy.MEMORY_TOOLS.values()) <= memory.NAMES
    assert set().union(*policy.MEMORY_TOOLS.values()) <= known


# --- data-class rule ------------------------------------------------------

@pytest.mark.parametrize("local,dc,mem_synth,t1_synth",
                         list(itertools.product([True, False], ["synthetic", "personal"], [True, False], [True, False])))
def test_data_class_truth_table(local, dc, mem_synth, t1_synth):
    spec = {**GOOD, "data_class": dc}
    if not local and dc == "personal":
        assert code(go, spec, local=local, memory_is_synthetic=mem_synth,
                    tier1_is_synthetic=t1_synth) == "personal_data_cloud_planner"
        assert untouched()
        return
    out = go(spec, local=local, memory_is_synthetic=mem_synth, tier1_is_synthetic=t1_synth)
    want = set(policy.TOOL_SCOPE["answer"])
    if local or t1_synth:
        want |= policy.TIER1_FILE_TOOLS["answer"]
    if local:
        want |= policy.TIER1_APP_TOOLS["answer"]
    if local or mem_synth:
        want |= policy.MEMORY_TOOLS["answer"]
    assert out.tools == want
    assert out.memory_context is (local or mem_synth)


def test_a_spec_claiming_synthetic_cannot_by_itself_obtain_personal_tools_from_a_cloud_planner():
    out = go({**GOOD, "data_class": "synthetic"}, local=False)
    assert out.tools == policy.TOOL_SCOPE["answer"]
    assert not out.tools & (policy.TIER1_FILE_TOOLS["answer"] | policy.TIER1_APP_TOOLS["answer"]
                            | policy.MEMORY_TOOLS["answer"])
    assert out.memory_context is False


def test_trusted_flags_grant_each_source_separately():
    t1 = go(local=False, tier1_is_synthetic=True, key="a").tools
    mem = go(local=False, memory_is_synthetic=True, key="b").tools
    assert t1 == policy.TOOL_SCOPE["answer"] | policy.TIER1_FILE_TOOLS["answer"]
    assert mem == policy.TOOL_SCOPE["answer"] | policy.MEMORY_TOOLS["answer"]


@pytest.mark.parametrize("task", ["answer", "summarize"])
def test_synthetic_flag_never_grants_calendar_notes_or_mail_to_a_cloud_planner(task):
    out = go({**GOOD, "task_type": task}, local=False, tier1_is_synthetic=True, memory_is_synthetic=True)
    assert not out.tools & {"calendar_events", "recent_notes", "search_notes", "recent_emails"}
    assert {"list_files", "read_file", "search_files"} <= out.tools
    local = go({**GOOD, "task_type": task}, local=True, key="loc")
    assert policy.TIER1_APP_TOOLS[task] <= local.tools


def test_app_tools_are_the_calendar_notes_and_mail_tools():
    assert policy.TIER1_APP_TOOLS["answer"] == {"calendar_events", "recent_notes", "search_notes", "recent_emails"}
    assert policy.TIER1_APP_TOOLS["summarize"] == {"recent_notes", "search_notes"}
    assert policy.TIER1_FILE_TOOLS["answer"] == policy.TIER1_FILE_TOOLS["summarize"] == {
        "list_files", "read_file", "search_files"}


@pytest.mark.parametrize("local", [None, 1, 0, "true", "", [], 1.0])
@pytest.mark.parametrize("dc", ["synthetic", "personal"])
def test_locality_must_be_exactly_a_bool(local, dc):
    assert code(go, {**GOOD, "data_class": dc}, local=local) == "planner_locality_invalid"
    assert untouched()


def test_missing_locality_argument_is_a_type_error_not_an_allow():
    with pytest.raises(TypeError):
        admit(GOOD, "k", limits=Limits(), ledger=ledger, now=NOW)


@pytest.mark.parametrize("flag", [None, 1, "yes"])
@pytest.mark.parametrize("name", ["memory_is_synthetic", "tier1_is_synthetic"])
def test_trusted_synthetic_flags_must_be_bools(flag, name):
    assert code(go, local=False, **{name: flag}) == "memory_flag_invalid"
    assert untouched()


def test_spec_cannot_claim_locality_or_memory():
    for extra in ({"planner_local": True}, {"memory_is_synthetic": True}, {"tier1_is_synthetic": True}):
        assert code(go, {**GOOD, "data_class": "personal", **extra}, local=False) == "spec_invalid"
        assert untouched()


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


def test_retries_above_two_cannot_be_built_and_a_third_retry_is_refused():
    code(Limits, retries_per_step=3)
    lim = Limits(retries_per_step=2)
    assert policy.check_retry("read_tool", 1, lim) is True
    assert code(policy.check_retry, "read_tool", 2, lim) == "retries_exhausted"


def test_step_started_in_the_future_is_a_clock_error():
    assert code(policy.check_step_deadline, NOW + timedelta(seconds=1), NOW, Limits()) == "clock_invalid"
    assert policy.check_step_deadline(NOW, NOW, Limits()) is True


def test_deadline_overflow_writes_nothing():
    assert code(go, now=datetime.max.replace(tzinfo=UTC)) == "clock_invalid"
    assert untouched()


@pytest.mark.parametrize("key", ["k\ud800", "\ud800"])
def test_key_that_does_not_encode_is_refused_before_the_ledger(key):
    assert code(go, key=key) == "idempotency_key_invalid"
    assert untouched()


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


# --- spec size as the ledger stores it, and a repeat's deadline -----------

@pytest.mark.parametrize("char,count", [("\U0001F600", 700), ("é", 1400), ("中", 1400)])
def test_instruction_too_large_as_stored_is_instruction_invalid(char, count):
    assert code(go, {**GOOD, "instruction": char * count}, limits=Limits(instruction_chars=1500)) == "instruction_invalid"
    assert untouched()


def test_non_ascii_instruction_that_fits_is_admitted():
    assert go({**GOOD, "instruction": "é" * 500}).job.state == "queued"


def test_repeat_keeps_the_original_deadline():
    first = go()
    later = go(now=NOW + timedelta(hours=2))
    assert later.job.id == first.job.id
    # the repeat's deadline comes from the ledger's creation stamp, never from the later `now`
    assert later.deadline == datetime.fromisoformat(first.job.created_at) + timedelta(seconds=Limits().job_deadline_s)
    assert later.deadline != NOW + timedelta(hours=2, seconds=Limits().job_deadline_s)


def test_repeat_with_unparseable_created_at_is_refused(monkeypatch):
    go()
    real = ledger.create_job
    monkeypatch.setattr(ledger, "create_job", lambda *a: dataclasses.replace(real(*a), created_at="junk"))
    assert code(go) == "ledger_error"


@pytest.mark.parametrize("data", [float("nan"), 7, None, "x" * 9000, "other"])
def test_bad_data_class_is_reported_as_data_class_invalid(data):
    assert code(go, {**GOOD, "data_class": data}) == "data_class_invalid"
    assert untouched()


# --- decide: the turn-level gate ---------------------------------------------

ON = frozenset({"delegate_task", "calculate", "current_time", "list_memory", *policy.MEMORY_WRITES, *policy.ASKED})


def _turn(heard="please remember my cat", read=False, on=ON):
    return policy.Turn(heard, read, on)


@pytest.mark.parametrize("tool, turn, verdict, why", [
    ("delegate_task", _turn(), "allow", None),
    ("delegate_task", _turn(read=True), "deny", "untrusted_read_in_turn"),
    ("remember_fact", _turn(), "allow", None),
    ("remember_fact", _turn(read=True), "deny", "untrusted_read_in_turn"),
    ("remember_fact", _turn("what time is it"), "deny", "not_asked"),
    ("remember_fact", _turn("what time is it", read=True), "deny", "untrusted_read_in_turn"),
    ("remember_fact", _turn(None), "allow", None),  # not a voice turn: no transcript to check
    ("add_reminder", _turn("Remind me at noon"), "allow", None),
    ("add_reminder", _turn("hello"), "deny", "not_asked"),
    ("forget", _turn("delete that"), "allow", None),
    ("forget", _turn("hello"), "deny", "not_asked"),
    ("complete_reminder", _turn("hello"), "allow", None),  # a write with no asked pattern, as today
    ("complete_reminder", _turn(read=True), "deny", "untrusted_read_in_turn"),
    ("list_memory", _turn("hello", read=True), "allow", None),  # reads are not writes
    ("calculate", _turn("hello", read=True), "allow", None),  # an enabled read passes
    ("anything_else", _turn(), "deny", "tool_disabled"),  # slice 2: unknown names deny
    ("delegate_task", _turn(on=ON - {"delegate_task"}), "deny", "tool_disabled"),
    ("remember_fact", _turn(on=frozenset()), "deny", "tool_disabled"),
    ("list_memory", _turn(on=frozenset({"calculate"})), "deny", "tool_disabled"),
    # a switched-off tool is "no such tool" even in a turn that read untrusted text
    ("delegate_task", _turn(read=True, on=frozenset()), "deny", "tool_disabled"),
])
def test_decide_table(tool, turn, verdict, why):
    assert policy.decide(tool, turn) == policy.Decision(verdict, why)


@pytest.mark.parametrize("tool, turn", [
    (None, _turn()), (3, _turn()), (b"forget", _turn()), (["forget"], _turn()),
    ("forget", None), ("forget", "turn"), ("forget", {"heard": "x"}),
    ("forget", policy.Turn(5, False, ON)),
    ("forget", policy.Turn("forget", 1, ON)),
    ("forget", policy.Turn("forget", None, ON)),
    ("forget", policy.Turn("forget", False, None)),
    ("forget", policy.Turn("forget", False, {"forget"})),  # a mutable set is not a trusted fact
    ("forget", policy.Turn("forget", False, frozenset({1}))),
    ("forget", policy.Turn("forget", False, "forget")),
])
def test_decide_bad_input_fails_closed(tool, turn):
    assert policy.decide(tool, turn) == policy.Decision("deny", "input_invalid")


def test_decide_never_returns_confirm_and_its_codes_are_known():
    names = ["delegate_task", "calculate", *policy.MEMORY_WRITES, *policy.ASKED, None, 1]
    for name, heard, read in itertools.product(names, ["", "remember it", "hello", None], [False, True]):
        d = policy.decide(name, policy.Turn(heard, read, ON))
        assert d.verdict in ("allow", "deny")
        assert (d.code is None) == (d.verdict == "allow") and d.code in REASONS | {None}


# --- slice 3: job-side checks as pure gate functions --------------------------

@pytest.mark.parametrize("granted_local, model_local, ok", [
    (False, False, True), (False, True, True), (True, True, True),
    (True, False, False), (True, None, False), (True, 1, False), (True, "yes", False),
    (1, False, False), (None, False, False),  # a grant flag that is not exactly False needs a local model
])
def test_check_planner_locality(granted_local, model_local, ok):
    if ok:
        assert policy.check_planner_locality(granted_local, model_local) is True
    else:
        with pytest.raises(PolicyError, match="planner_locality_invalid"):
            policy.check_planner_locality(granted_local, model_local)


def test_offered_tools_narrows_the_grant_by_the_live_switches():
    granted = frozenset({"calculate", "read_file", "recent_notes", "list_memory"})
    assert policy.offered_tools(granted, frozenset({"read_file"}), True) == {"calculate", "read_file", "list_memory"}
    assert policy.offered_tools(granted, frozenset(), False) == {"calculate"}
    assert policy.offered_tools(granted, frozenset({"read_file", "recent_notes"}), False) == granted - {"list_memory"}


@pytest.mark.parametrize("admitted, t1, mem", [
    ({"calculate"}, frozenset(), True), (frozenset({"calculate"}), {"read_file"}, True),
    (frozenset({"calculate"}), frozenset(), 1), (None, frozenset(), True), (frozenset({1}), frozenset(), True),
])
def test_offered_tools_bad_input_offers_nothing(admitted, t1, mem):
    assert policy.offered_tools(admitted, t1, mem) == frozenset()


def test_the_gate_knows_every_tier1_name():
    from super_agent_voice import tier1
    assert policy.TIER1_NAMES == tier1.T1_NAMES


# --- slice 4: the distiller asks the gate -------------------------------------

@pytest.mark.parametrize("learn, mem, local, user, verdict, why", [
    (True, True, True, True, "allow", None),
    (False, True, True, True, "deny", "tool_disabled"),
    (True, False, True, True, "deny", "tool_disabled"),
    (True, True, False, True, "deny", "planner_locality_invalid"),
    (True, True, True, False, "deny", "input_invalid"),  # only the user's own words are learned from
    (1, True, True, True, "deny", "input_invalid"),
    (True, None, True, True, "deny", "input_invalid"),
    (True, True, "yes", True, "deny", "input_invalid"),
])
def test_may_distill(learn, mem, local, user, verdict, why):
    assert policy.may_distill(learn, mem, local, user) == policy.Decision(verdict, why)
