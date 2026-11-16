import dataclasses
import json
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


@pytest.mark.parametrize("reply", [
    {"steps": [READ, FIN], "tools": ["read_file"]},
    {"steps": [READ, FIN], "limits": {"steps_per_job": 99}},
    {"steps": [{**READ, "tools": ["x"]}, FIN]},
    {"steps": [{**READ, "limits": {}}, FIN]},
    {"steps": [{**READ, "scope": "all"}, FIN]},
    {"steps": [READ, {**FIN, "deadline": 9999}]},
    {"steps": [{**SUM, "tool": "calculate"}, FIN]},
    {"steps": [{"type": "read_tool", "tool": "calculate"}, FIN]},
    {},
])
def test_extra_or_missing_keys_are_refused(reply):
    assert code(reply) == "plan_invalid"


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
