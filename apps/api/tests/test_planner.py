import dataclasses
import json
import sys
from datetime import UTC, datetime

import pytest

from super_agent_voice import ledger, memory, policy
from super_agent_voice.planner import ModelError, Plan, ScriptedModel, request_plan
from super_agent_voice.policy import REASONS, Limits, PolicyError

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
SPEC = {"task_type": "answer", "instruction": "What is 2 plus 2?", "data_class": "synthetic"}
LIM = Limits()
READ = {"type": "read_tool", "tool": "calculate", "args": {"expression": "2+2"}}
SUM = {"type": "summarize", "after": [0]}
FIN = {"type": "finish", "after": [1]}
GOOD = {"steps": [READ, SUM, FIN]}


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "DB_PATH", tmp_path / "led" / "ledger.db")


def adm(local=True):
    return policy.admit(SPEC, "k1", local, LIM, ledger, NOW)


def plan(reply, local=True, prompt="p", calls=0, limits=LIM):
    model = ScriptedModel([reply])
    return request_plan(model, prompt, adm(local), limits, calls)


def code(reply, **kw):
    with pytest.raises(PolicyError) as err:
        plan(reply, **kw)
    assert err.value.code in REASONS and str(err.value) == err.value.code
    return err.value.code


def steps(*items):
    return {"steps": list(items)}


def test_valid_plan_round_trips_into_a_typed_plan():
    got = plan(GOOD)
    assert isinstance(got, Plan) and [s.type for s in got.steps] == ["read_tool", "summarize", "finish"]
    assert got.steps[0].tool == "calculate" and json.loads(got.steps[0].args) == {"expression": "2+2"}
    assert got.steps[1].after == (0,) and got.steps[0].after == ()


def test_plan_is_immutable():
    got = plan(GOOD)
    with pytest.raises(dataclasses.FrozenInstanceError):
        got.steps[0].tool = "read_file"
    with pytest.raises(dataclasses.FrozenInstanceError):
        got.steps = ()
    assert isinstance(got.steps, tuple) and isinstance(got.steps[0].args, str)


def test_ask_user_step_is_allowed():
    got = plan(steps({"type": "ask_user", "question": "Which one?"}, {"type": "finish", "after": [0]}))
    assert got.steps[0].question == "Which one?"


def test_unknown_step_type():
    assert code(steps({"type": "shell"}, FIN)) == "step_type_unknown"
    assert code(steps({"type": 7}, FIN)) == "step_type_unknown"


def test_tool_outside_the_admitted_set():
    assert code(steps({**READ, "tool": "rm_rf"}, {"type": "finish"})) == "tool_out_of_scope"
    assert code(steps({**READ, "tool": 5}, {"type": "finish"})) == "tool_out_of_scope"


@pytest.mark.parametrize("tool", ["read_file", "recent_emails", "list_memory"])
def test_real_tool_not_granted_to_a_cloud_planner(tool):
    assert code(steps({**READ, "tool": tool, "args": {}}, {"type": "finish"}), local=False) == "tool_out_of_scope"


def test_memory_write_tool_is_refused_even_for_a_local_planner():
    for tool in memory.WRITES:
        assert code(steps({**READ, "tool": tool}, {"type": "finish"})) == "tool_out_of_scope"


def bump(index, **extra):
    """GOOD with one step carrying one extra key, valid in every other way."""
    items = [dict(x) for x in GOOD["steps"]]
    items[index].update(extra)
    return {"steps": items}


@pytest.mark.parametrize("reply", [
    {**GOOD, "tools": ["read_file"]},
    {**GOOD, "limits": {"steps_per_job": 99}},
    *[bump(i, **{key: value}) for i in range(3)
      for key, value in (("tools", ["x"]), ("limits", {}), ("scope", "all"), ("deadline", 9999))],
])
def test_extra_keys_are_refused(reply):
    assert code(reply) == "plan_invalid"


@pytest.mark.parametrize("reply", [
    {},
    {"steps": GOOD["steps"], "steps2": 1},
    {"steps": [{"type": "read_tool", "tool": "calculate"}, SUM, FIN]},  # no args
    {"steps": [{"type": "read_tool", "args": {}}, SUM, FIN]},  # no tool
    {"steps": [READ, SUM, {"after": [1]}]},  # no type
    {"steps": [READ, SUM, {"type": "ask_user", "after": [1]}, {"type": "finish", "after": [2]}]},  # no question
])
def test_missing_keys_are_refused(reply):
    assert code(reply) in {"plan_invalid", "step_type_unknown"}


@pytest.mark.parametrize("after", [[1], [5], [0, 0], [-1], [True], [0.0], ["0"], 0, None, [[0]]])
def test_bad_after(after):
    assert code(steps(READ, {"type": "summarize", "after": after}, {"type": "finish", "after": [1]})) in {
        "plan_invalid"}


def test_summarize_needs_a_dependency():
    assert code(steps(READ, {"type": "summarize"}, {"type": "finish"})) == "plan_invalid"
    assert code(steps(READ, {"type": "summarize", "after": []}, {"type": "finish"})) == "plan_invalid"


def test_step_count_limits():
    assert code(steps()) == "plan_invalid"
    many = [READ] * LIM.steps_per_job + [{"type": "finish"}]
    assert code({"steps": many}) == "step_limit"
    ok = [READ] * (LIM.steps_per_job - 1) + [{"type": "finish"}]
    assert len(plan({"steps": ok}).steps) == LIM.steps_per_job


@pytest.mark.parametrize("items", [
    [READ],
    [READ, {"type": "finish"}, {"type": "finish"}],
    [{"type": "finish"}, READ],
])
def test_finish_must_be_exactly_one_and_last(items):
    assert code({"steps": items}) == "plan_invalid"


@pytest.mark.parametrize("args", [[], "x", 5, None, {"a": "x" * 2000}, {"a": float("nan")}, {"a": "\ud800"}])
def test_bad_args(args):
    assert code(steps({**READ, "args": args}, {"type": "finish"})) == "plan_invalid"


@pytest.mark.parametrize("question", ["", "   ", 5, None, "q" * 301, "\ud800", ["a"]])
def test_bad_question(question):
    assert code(steps({"type": "ask_user", "question": question}, {"type": "finish"})) == "plan_invalid"


@pytest.mark.parametrize("reply", [[], "text", None, 5, {"steps": "x"}, {"steps": {"0": READ}},
                                    {"steps": [READ, "finish"]}, {"steps": float("nan")},
                                    {"steps": [{**READ, "tool": float("nan")}, {"type": "finish"}]}])
def test_reply_of_the_wrong_shape(reply):
    assert code(reply) in {"plan_invalid", "tool_out_of_scope"}


def test_seam_error_becomes_a_fixed_code():
    for err in ("unavailable", "timeout", "malformed"):
        with pytest.raises(PolicyError) as e:
            request_plan(ScriptedModel([ModelError(err)]), "p", adm(), LIM, 0)
        assert e.value.code == "model_error"


def test_arbitrary_model_exception_text_is_dropped():
    class Boom:
        is_local = True

        def complete(self, prompt):
            raise RuntimeError("secret personal text")

    with pytest.raises(PolicyError) as e:
        request_plan(Boom(), "p", adm(), LIM, 0)
    assert e.value.code == "model_error" and "secret" not in repr(e.value) and e.value.__cause__ is None


def test_scripted_model_records_prompts_and_runs_out():
    model = ScriptedModel([GOOD])
    request_plan(model, "hello", adm(), LIM, 0)
    assert model.prompts == ["hello"]
    with pytest.raises(PolicyError) as e:
        request_plan(model, "again", adm(), LIM, 1)
    assert e.value.code == "model_error"


def test_budget_and_size_are_checked_before_the_model_is_called():
    model = ScriptedModel([GOOD])
    for prompt, calls, want in [("p", LIM.model_calls_per_job, "model_call_limit"),
                                ("x" * (LIM.model_input_chars + 1), 0, "input_too_large"),
                                (b"bytes", 0, "input_invalid"), ("p", True, "input_invalid")]:
        with pytest.raises(PolicyError) as e:
            request_plan(model, prompt, adm(), LIM, calls)
        assert e.value.code == want
    assert model.prompts == []


def test_model_locality_is_readable_for_admission():
    assert ScriptedModel([], is_local=False).is_local is False and ScriptedModel([]).is_local is True


# --- hostile objects: only PolicyError may escape, with a fixed code ----------

def nested(depth, leaf=None):
    x = leaf
    for _ in range(depth):
        x = [x]
    return x


class LyingStr(str):
    """Claims to be an admitted tool in hash and equality, but its value is another tool."""

    def __hash__(self):
        return hash("calculate")

    def __eq__(self, other):
        return other == "calculate"


class Hostile:
    def __repr__(self):
        raise RuntimeError("secret repr")

    def __hash__(self):
        raise RuntimeError("secret hash")


def deep_loads(depth):
    try:
        return json.loads("[" * depth + "]" * depth)
    except RecursionError:  # the parser itself refuses; the object loop below covers the deeper case
        return nested(depth)


@pytest.mark.parametrize("reply", [
    {"steps": [{**READ, "args": {"a": nested(20000)}}, {"type": "finish"}]},
    {"steps": [{**READ, "args": {"a": deep_loads(900)}}, {"type": "finish"}]},
    {"steps": nested(20000)},
    {"steps": [READ, {"type": "finish"}], "x": deep_loads(900)},
    {"steps": [{"type": "finish", "after": [10 ** 5000]}]},
    {"steps": [READ, {"type": "summarize", "after": [Hostile()]}, {"type": "finish", "after": [1]}]},
    {"steps": [{**READ, "tool": Hostile()}, {"type": "finish"}]},
    {"steps": [{**READ, "args": {"a": Hostile()}}, {"type": "finish"}]},
    {"steps": [{**READ, "args": {(1, 2): 3}}, {"type": "finish"}]},
    {1: "x", 2: "y"},
    {"steps": [{1: "x"}, {"type": "finish"}]},
    {"steps": [READ, {"type": "finish", "note": "x" * 100_000}]},
])
def test_hostile_replies_raise_only_a_fixed_policy_error(reply):
    with pytest.raises(PolicyError) as err:
        plan(reply)
    assert err.value.code in {"plan_invalid", "step_type_unknown"}
    assert str(err.value) == err.value.code and "secret" not in repr(err.value)


def test_str_subclass_cannot_smuggle_a_tool():
    assert code(steps({**READ, "tool": LyingStr("read_file")}, {"type": "finish"}), local=False) == "tool_out_of_scope"
    got = plan(steps({**READ, "tool": LyingStr("calculate")}, {"type": "finish"}))
    assert type(got.steps[0].tool) is str and got.steps[0].tool == "calculate"


def test_recursion_limit_is_unchanged_after_a_deep_reply():
    before = sys.getrecursionlimit()
    code({"steps": nested(20000)})
    assert sys.getrecursionlimit() == before


# --- the model's locality must match the admission ----------------------------

def test_cloud_model_with_a_local_admission_is_refused_before_the_call():
    model = ScriptedModel([GOOD], is_local=False)
    with pytest.raises(PolicyError) as err:
        request_plan(model, "p", adm(local=True), LIM, 0)
    assert err.value.code == "planner_locality_invalid" and model.prompts == []


@pytest.mark.parametrize("flag", [None, 1, "yes"])
def test_non_bool_locality_is_not_local(flag):
    model = ScriptedModel([GOOD])
    model.is_local = flag
    with pytest.raises(PolicyError) as err:
        request_plan(model, "p", adm(local=True), LIM, 0)
    assert err.value.code == "planner_locality_invalid" and model.prompts == []


def test_local_model_with_a_cloud_admission_is_allowed():
    assert plan(GOOD, local=False).steps[0].tool == "calculate"


def test_admission_records_the_locality_it_was_granted_under():
    assert adm(local=True).planner_is_local is True and adm(local=False).planner_is_local is False


# --- sizes are measured as escaped JSON text, and the ceiling plan fits -------

def args_of(n):
    return {"a": "x" * (n - 9)}  # '{"a": "' + x... + '"}' is n characters of JSON text


@pytest.mark.parametrize("size,ok", [(1000, True), (1001, False)])
def test_args_cap_is_exact(size, ok):
    assert len(json.dumps(args_of(size))) == size
    reply = steps({**READ, "args": args_of(size)}, {"type": "finish"})
    if ok:
        assert plan(reply).steps[0].args
    else:
        assert code(reply) == "plan_invalid"


def test_non_bmp_args_count_as_escaped_text():
    emoji = {"a": "\U0001F600" * 83}  # 12 characters each once escaped: 1,005 in all
    assert code(steps({**READ, "args": emoji}, {"type": "finish"})) == "plan_invalid"
    assert plan(steps({**READ, "args": {"a": "\U0001F600" * 82}}, {"type": "finish"}))


def test_worst_valid_plan_at_the_ceiling_is_accepted():
    lim = Limits(steps_per_job=32)
    question = "\U0001F600" * 300
    items = [{"type": "ask_user", "question": question, "after": list(range(i))} for i in range(31)]
    items.append({"type": "finish", "after": list(range(31))})
    reply = {"steps": items}
    assert 100_000 < len(json.dumps(reply)) <= 120_000
    assert len(plan(reply, limits=lim).steps) == 32
    mixed = [{**READ, "tool": "calendar_events", "args": args_of(1000), "after": list(range(i))} for i in range(31)]
    assert len(plan({"steps": mixed + [{"type": "finish"}]}, limits=lim).steps) == 32


# --- a broken is_local flag is "not local" -------------------------------------

class RaisingFlag:
    @property
    def is_local(self):
        raise RuntimeError("secret flag")

    def complete(self, prompt):
        raise AssertionError("must not be called")


class NoFlag:
    def complete(self, prompt):
        raise AssertionError("must not be called")


@pytest.mark.parametrize("model", [RaisingFlag(), NoFlag()])
def test_broken_locality_flag_with_a_local_admission_is_refused(model):
    with pytest.raises(PolicyError) as err:
        request_plan(model, "p", adm(local=True), LIM, 0)
    assert err.value.code == "planner_locality_invalid" and "secret" not in repr(err.value)
    assert err.value.__cause__ is None


def test_broken_locality_flag_with_a_cloud_admission_does_not_matter():
    class Cloud(ScriptedModel):
        @property
        def is_local(self):
            raise RuntimeError("secret flag")

        @is_local.setter
        def is_local(self, value):
            pass

    assert len(request_plan(Cloud([GOOD]), "p", adm(local=False), LIM, 0).steps) == 3
