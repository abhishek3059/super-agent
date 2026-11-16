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
MAX_ARGS_BYTES, MAX_QUESTION_CHARS = 1000, 300  # fixed here: Limits has no field that fits
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


class ScriptedModel:
    """Fake for tests and evaluation tier A: replays queued replies, or raises queued ModelErrors."""

    def __init__(self, replies: list, is_local: bool = True):
        self._replies, self.is_local, self.prompts = list(replies), is_local, []

    def complete(self, prompt: str) -> object:
        self.prompts.append(prompt)
        if not self._replies:
            raise ModelError("unavailable")
        reply = self._replies.pop(0)
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
    if not isinstance(value, list) or len(set(map(repr, value))) != len(value):
        raise _bad()
    if any(type(i) is not int or not 0 <= i < index for i in value):
        raise _bad()
    return tuple(value)


def _step(raw: object, index: int, admission: Admission) -> Step:
    if not isinstance(raw, dict):
        raise _bad()
    kind = raw.get("type")
    if not isinstance(kind, str) or kind not in policy.STEP_TYPES:
        raise PolicyError("step_type_unknown")
    keys = set(raw)
    if not _KEYS[kind] - {"after"} <= keys <= _KEYS[kind]:
        raise _bad()
    after = _after(raw.get("after", []), index)
    if kind == "summarize" and not after:
        raise _bad()
    if kind == "ask_user":
        q = raw["question"]
        try:
            ok = isinstance(q, str) and q.strip() and len(q) <= MAX_QUESTION_CHARS and q.encode("utf-8")
        except UnicodeError:
            ok = False
        if not ok:
            raise _bad()
        return Step(kind, after, question=q)
    if kind != "read_tool":
        return Step(kind, after)
    tool = raw["tool"]
    if not isinstance(tool, str) or tool not in admission.tools:
        raise PolicyError("tool_out_of_scope")  # argument validation happens when the tool runs
    try:
        if not isinstance(raw["args"], dict):
            raise _bad()
        text = json.dumps(raw["args"], sort_keys=True, ensure_ascii=False, allow_nan=False)
        if len(text.encode("utf-8")) > MAX_ARGS_BYTES:
            raise _bad()
    except (TypeError, ValueError):
        raise _bad() from None
    return Step(kind, after, tool=tool, args=text)


def request_plan(model: PlannerModel, prompt: str, admission: Admission, limits: Limits,
                 calls_used: int) -> Plan:
    if not isinstance(prompt, str):
        raise PolicyError("input_invalid")
    policy.check_model_call(calls_used, len(prompt), limits)
    try:
        reply = model.complete(prompt)
    except Exception:
        raise PolicyError("model_error") from None
    if not isinstance(reply, dict) or set(reply) != {"steps"} or not isinstance(reply["steps"], list):
        raise _bad()
    raw = reply["steps"]
    if not raw:
        raise _bad()
    policy.check_step_index(len(raw) - 1, limits)
    steps = tuple(_step(item, i, admission) for i, item in enumerate(raw))
    if [s.type for s in steps].count("finish") != 1 or steps[-1].type != "finish":
        raise _bad()
    return Plan(steps)
