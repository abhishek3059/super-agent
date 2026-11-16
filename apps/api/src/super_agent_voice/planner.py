"""Planner model seam and plan validation (agent-backend design, sections 4 and 6).

The model is untrusted. `request_plan` is trusted code around exactly one model call: the
call budget and input size are checked before it, and the reply is treated as hostile data
and validated into an immutable plan, or refused with a PolicyError carrying a fixed code.
No error ever holds model text or exception text. No network, no real model, no runner.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from . import policy
from .policy import Admission, Limits, PolicyError

MODEL_ERRORS = ("unavailable", "timeout", "malformed")  # the seam's closed set of failure kinds
# Sizes are characters of ensure_ascii JSON text (a non-BMP character is 12). Fixed here: Limits has no field that fits.
MAX_ARGS_CHARS, MAX_QUESTION_CHARS = 1000, 300
# Worst valid plan: 31 ask_user steps with a 300 non-BMP question (3,600 escaped) and a full `after`, plus finish,
# measures 114,882; read_tool steps at the args cap are far smaller. A bigger reply is not a plan.
MAX_REPLY_CHARS = 120_000
_KEYS = {  # allowed keys per step type; every key but "after" is required
    "read_tool": {"type", "tool", "args", "after"}, "summarize": {"type", "after"},
    "ask_user": {"type", "question", "after"}, "finish": {"type", "after"},
}


class ModelError(Exception):
    """The one failure a model seam raises. Carries a code, never provider text."""

    def __init__(self, code: str):
        super().__init__(code if code in MODEL_ERRORS else "unavailable")
        self.code = str(self.args[0])


class PlannerModel(Protocol):
    is_local: bool  # trusted code passes this to policy.admit(planner_is_local=...)

    def complete(self, prompt: str) -> object:
        """Return the reply as parsed JSON, or raise ModelError. No response schema yet: no consumer."""

    def complete_text(self, prompt: str) -> object:
        """Return the reply as text for a summarize step, or raise ModelError. The caller treats it as hostile."""


class ScriptedModel:
    """Fake for tests and evaluation tier A: replays queued replies, or raises queued ModelErrors."""

    def __init__(self, replies: list, is_local: bool = True, texts: list | None = None):
        self._replies, self.is_local, self.prompts = list(replies), is_local, []
        self._texts, self.text_prompts = list(texts or []), []

    def complete(self, prompt: str) -> object:
        self.prompts.append(prompt)
        if not self._replies:
            raise ModelError("unavailable")
        reply = self._replies.pop(0)
        if isinstance(reply, ModelError):
            raise reply
        return reply

    def complete_text(self, prompt: str) -> object:
        self.text_prompts.append(prompt)
        if not self._texts:
            raise ModelError("unavailable")
        reply = self._texts.pop(0)
        if isinstance(reply, ModelError):
            raise reply
        return reply


@dataclass(frozen=True)
class Step:
    type: str
    after: tuple[int, ...] = ()
    tool: str | None = None
    args: str = ""  # canonical JSON text, so the plan stays immutable
    question: str = ""


@dataclass(frozen=True)
class Plan:
    steps: tuple[Step, ...]


def _bad() -> PolicyError:
    return PolicyError("plan_invalid")


def _after(value: object, index: int) -> tuple[int, ...]:
    # Only earlier steps may be named, so a cycle is impossible by construction.
    if type(value) is not list or any(type(i) is not int or not 0 <= i < index for i in value):
        raise _bad()
    if len(set(value)) != len(value):
        raise _bad()
    return tuple(value)


def _step(raw: object, index: int, admission: Admission) -> Step:
    if type(raw) is not dict:
        raise _bad()
    kind = raw.get("type")
    if type(kind) is not str or kind not in policy.STEP_TYPES:
        raise PolicyError("step_type_unknown")
    keys = set(raw)
    if not _KEYS[kind] - {"after"} <= keys <= _KEYS[kind]:
        raise _bad()
    after = _after(raw.get("after", []), index)
    if kind in ("summarize", "finish") and not after:  # finish collects the result, so it must name its inputs
        raise _bad()
    if kind == "ask_user":
        q = raw["question"]
        try:
            ok = type(q) is str and q.strip() and len(q) <= MAX_QUESTION_CHARS and q.encode("utf-8")
        except UnicodeError:
            ok = False
        if not ok:
            raise _bad()
        return Step(kind, after, question=q)
    if kind != "read_tool":
        return Step(kind, after)
    tool = raw["tool"]
    if type(tool) is not str or tool not in admission.tools:
        raise PolicyError("tool_out_of_scope")  # args are only bounded here; graph.py validates them before any step runs
    try:
        if type(raw["args"]) is not dict:
            raise _bad()
        json.dumps(raw["args"], ensure_ascii=False, allow_nan=False).encode("utf-8")  # lone surrogate: UnicodeError
        text = json.dumps(raw["args"], sort_keys=True, allow_nan=False)
        if len(text) > MAX_ARGS_CHARS:
            raise _bad()
    except Exception:  # TypeError, ValueError, RecursionError
        raise _bad() from None
    return Step(kind, after, tool=tool, args=text)


def _normalize(reply: object) -> object:
    """A JSON round trip leaves only dict, list, str, int, float, bool and None, so subclasses and
    exotic objects cannot reach the checks. Any failure, including RecursionError, is a bad plan."""
    try:
        text = json.dumps(reply, allow_nan=False)
        if len(text) > MAX_REPLY_CHARS:
            raise _bad()
        return json.loads(text)
    except Exception:
        raise _bad() from None


def request_plan(model: PlannerModel, prompt: str, admission: Admission, limits: Limits,
                 calls_used: int) -> Plan:
    if type(prompt) is not str:
        raise PolicyError("input_invalid")
    # An admission granted to a local planner carries real personal-data tools; a cloud model must not use it.
    if admission.planner_is_local:
        try:
            local = model.is_local is True
        except Exception:  # a broken flag is not local
            local = False
        if not local:
            raise PolicyError("planner_locality_invalid")
    policy.check_model_call(calls_used, len(prompt), limits)
    try:
        reply = model.complete(prompt)
    except Exception:
        raise PolicyError("model_error") from None
    try:
        return _validate(_normalize(reply), admission, limits)
    except PolicyError:
        raise
    except Exception:  # a bug here must still fail closed
        raise _bad() from None


def _validate(reply: object, admission: Admission, limits: Limits) -> Plan:
    if type(reply) is not dict or set(reply) != {"steps"} or type(reply["steps"]) is not list:
        raise _bad()
    raw = reply["steps"]
    if not raw:
        raise _bad()
    policy.check_step_index(len(raw) - 1, limits)
    steps = tuple(_step(item, i, admission) for i, item in enumerate(raw))
    if [s.type for s in steps].count("finish") != 1 or steps[-1].type != "finish":
        raise _bad()
    return Plan(steps)
