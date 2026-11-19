"""Limits and admission for background jobs (agent-backend design, sections 4, 5, 7).

Everything here is enforced in code, outside any model. A caller supplies the
task spec, but never the limits, the tool scope, or the planner's locality:
those come from trusted code. Every failure raises PolicyError carrying one
reason code from the closed set REASONS, never text taken from the spec.
No model, no network, no clock of its own: time comes in as an argument.
"""
from __future__ import annotations

import dataclasses
import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from .ledger import MAX_SPEC_BYTES, TERMINAL, Job, LedgerError
from .memory import WRITES as MEMORY_WRITES

REASONS = frozenset({
    "limits_invalid", "clock_invalid", "idempotency_key_invalid", "planner_locality_invalid",
    "memory_flag_invalid", "spec_invalid", "task_type_invalid", "instruction_invalid",
    "data_class_invalid", "personal_data_cloud_planner", "queue_full", "ledger_error",
    "ledger_rejected", "input_invalid", "step_limit", "step_type_unknown", "retry_not_allowed",
    "retries_exhausted", "step_deadline", "job_deadline", "model_call_limit", "input_too_large",
    "output_too_large",
    "plan_invalid", "tool_out_of_scope", "model_error",
    "tool_args_invalid", "clarify_unsupported", "tracing_enabled", "model_reply_invalid", "step_failed",
    "verify_failed", "delegation_unavailable", "untrusted_read_in_turn", "not_asked",
    "session_stale", "tool_threads_stuck", "unknown_job",
})


class PolicyError(Exception):
    """A policy refusal. The message is the fixed reason code and nothing else."""

    def __init__(self, code: str):
        if code not in REASONS:
            code = "input_invalid"
        super().__init__(code)
        self.code = code


# Hard ceilings: no Limits object can exceed these, whoever builds it.
CEILING = {
    "steps_per_job": 32, "step_deadline_s": 600, "job_deadline_s": 3600, "retries_per_step": 2,
    "model_calls_per_job": 100, "model_input_chars": 32_000, "step_output_chars": 16_000,
    "concurrent_jobs": 8, "queued_jobs": 50,
    # A character cap alone does not fit the ledger's byte cap (an emoji is 12 stored bytes);
    # _spec also measures the spec the way the ledger stores it.
    "instruction_chars": 1500,
}


@dataclass(frozen=True)
class Limits:
    """Defaults are the provisional table in docs/design/agent-backend.md section 5."""
    steps_per_job: int = 8
    step_deadline_s: int = 30
    job_deadline_s: int = 300
    retries_per_step: int = 1
    model_calls_per_job: int = 12
    model_input_chars: int = 8000
    step_output_chars: int = 4000
    concurrent_jobs: int = 2
    queued_jobs: int = 5
    instruction_chars: int = 1000

    def __post_init__(self) -> None:
        for f in dataclasses.fields(self):
            value = getattr(self, f.name)
            if type(value) is not int or not 0 < value <= CEILING[f.name]:  # type is int rejects bool
                raise PolicyError("limits_invalid")


TASK_TYPES = frozenset({"answer", "summarize"})
DATA_CLASSES = frozenset({"synthetic", "personal"})
SPEC_KEYS = frozenset({"task_type", "instruction", "data_class"})
STEP_TYPES = frozenset({"read_tool", "summarize", "ask_user", "finish"})
RETRYABLE_STEPS = frozenset({"read_tool"})  # idempotent and read-only; a model call is neither

# Tool scope by task type. The spec cannot name tools. All read-only.
TOOL_SCOPE = {
    "answer": frozenset({"calculate", "current_time"}),
    "summarize": frozenset({"current_time"}),
}
# Tools that read personal data, by source (tier1.py, memory.py reads). Granted per source only
# when trusted code says the source is synthetic or the planner is local. Never from the spec.
# File tools read the allowlisted folders, which trusted config may vouch for as synthetic. App tools read the
# user's real Calendar, Notes and Mail apps; no flag vouches for those, so only a local planner gets them.
TIER1_FILE_TOOLS = {
    "answer": frozenset({"list_files", "read_file", "search_files"}),
    "summarize": frozenset({"list_files", "read_file", "search_files"}),
}
TIER1_APP_TOOLS = {
    "answer": frozenset({"calendar_events", "recent_notes", "search_notes", "recent_emails"}),
    "summarize": frozenset({"recent_notes", "search_notes"}),
}
MEMORY_TOOLS = {"answer": frozenset({"list_memory", "list_reminders"}), "summarize": frozenset()}


@dataclass(frozen=True)
class Admission:
    job: Job
    tools: frozenset[str]
    memory_context: bool
    deadline: datetime
    planner_is_local: bool  # what the grant was made under; request_plan holds the model to it


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None


def _limits(limits: object) -> Limits:
    if not isinstance(limits, Limits):
        raise PolicyError("limits_invalid")
    return limits


def _count(value: object, low: int = 0) -> int:
    if type(value) is not int or value < low:
        raise PolicyError("input_invalid")
    return value


def _spec(spec: object, limits: Limits) -> dict:
    if not isinstance(spec, dict) or set(spec) != SPEC_KEYS:
        raise PolicyError("spec_invalid")
    task, text, data = spec["task_type"], spec["instruction"], spec["data_class"]
    if not isinstance(task, str) or task not in TASK_TYPES:
        raise PolicyError("task_type_invalid")
    if not isinstance(text, str) or not text.strip() or len(text) > limits.instruction_chars:
        raise PolicyError("instruction_invalid")
    if not isinstance(data, str) or data not in DATA_CLASSES:
        raise PolicyError("data_class_invalid")
    try:
        text.encode("utf-8")  # a lone surrogate is not storable
        # same encoding as ledger._json (ensure_ascii), so what passes here is storable
        stored = json.dumps(spec, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (UnicodeError, TypeError, ValueError):
        raise PolicyError("instruction_invalid") from None
    if len(stored.encode()) > MAX_SPEC_BYTES:
        raise PolicyError("instruction_invalid")
    return spec


def _vetted(spec: object, planner_is_local: bool, lim: Limits) -> dict:
    """The spec schema and the data-class rule. Shared by admit and the runner's claim path."""
    spec = _spec(spec, lim)
    if not planner_is_local and spec["data_class"] == "personal":
        raise PolicyError("personal_data_cloud_planner")
    return spec


def _scope(task: str, planner_is_local: bool, memory_is_synthetic: bool = False,
           tier1_is_synthetic: bool = False) -> frozenset[str]:
    tools = TOOL_SCOPE[task]
    if planner_is_local or tier1_is_synthetic:
        tools |= TIER1_FILE_TOOLS[task]
    if planner_is_local:
        tools |= TIER1_APP_TOOLS[task]
    # Memory now holds inferred records from real speech, so memory_is_synthetic must never be True for real memory.
    if planner_is_local or memory_is_synthetic:
        tools |= MEMORY_TOOLS[task]
    return tools


def _deadline_of(job: Job, lim: Limits) -> datetime:
    """The job's deadline counts from its creation, so a retry or a late claim never extends it."""
    try:
        return datetime.fromisoformat(job.created_at) + timedelta(seconds=lim.job_deadline_s)
    except ValueError:
        raise PolicyError("ledger_error") from None
    except OverflowError:
        raise PolicyError("clock_invalid") from None


_ADMIT_LOCK = threading.Lock()  # shortcut: one process only; a shared database needs its own cap, upgrade then


def admit(spec: object, idempotency_key: object, planner_is_local: object, limits: object,
          ledger, now: object, *, memory_is_synthetic: object = False,
          tier1_is_synthetic: object = False, session: str | None = None) -> Admission:
    """Validate, apply the data-class rule and queue cap, then create the job in the ledger.

    planner_is_local, memory_is_synthetic and tier1_is_synthetic come from trusted code
    (deployment configuration) and must be exactly bool; anything else is a refusal. The spec's
    data_class can only make admission stricter, never unlock a personal-data source. Refusals write nothing.
    `session` (trusted, optional) is stored beside the spec. The cap check and the job creation run under one
    lock, so concurrent admissions in this process cannot both pass the cap."""
    lim = _limits(limits)
    if not _aware(now):
        raise PolicyError("clock_invalid")
    if not isinstance(idempotency_key, str) or not 0 < len(idempotency_key) <= 128:
        raise PolicyError("idempotency_key_invalid")
    try:
        idempotency_key.encode("utf-8")
    except UnicodeError:
        raise PolicyError("idempotency_key_invalid") from None
    try:
        deadline = now + timedelta(seconds=lim.job_deadline_s)  # before any write
    except OverflowError:
        raise PolicyError("clock_invalid") from None
    if type(planner_is_local) is not bool:
        raise PolicyError("planner_locality_invalid")
    if type(memory_is_synthetic) is not bool or type(tier1_is_synthetic) is not bool:
        raise PolicyError("memory_flag_invalid")
    spec = _vetted(spec, planner_is_local, lim)
    with _ADMIT_LOCK:
        try:
            jobs = ledger.list_jobs()
            known = any(j.idempotency_key == idempotency_key for j in jobs)  # a repeat is not new load
            if not known and sum(j.state not in TERMINAL for j in jobs) >= lim.concurrent_jobs + lim.queued_jobs:
                raise PolicyError("queue_full")
        except LedgerError:
            raise PolicyError("ledger_error") from None
        try:
            job = ledger.create_job(spec if session is None else {**spec, "session": session}, idempotency_key)
        except LedgerError:
            raise PolicyError("ledger_rejected") from None
    if known:  # a repeat must not extend the job's deadline: budgets are not reset by a retry
        deadline = _deadline_of(job, lim)
    task = spec["task_type"]
    tools = _scope(task, planner_is_local, memory_is_synthetic, tier1_is_synthetic)
    return Admission(job, tools, planner_is_local or memory_is_synthetic, deadline, planner_is_local)


def admit_claimed(job: Job, allowed: frozenset[str], planner_is_local: bool, limits: Limits) -> Admission:
    """The same checks as admit for a job another path already created and claimed. The tools are the
    worker's own names cut down to the scope of the job's task type. Raises PolicyError; the caller fails the job."""
    lim = _limits(limits)
    if type(planner_is_local) is not bool:
        raise PolicyError("planner_locality_invalid")
    spec = _vetted({k: v for k, v in job.spec.items() if k != "session"}, planner_is_local, lim)
    tools = _scope(spec["task_type"], planner_is_local) & allowed
    return Admission(job, tools, False, _deadline_of(job, lim), planner_is_local)


# --- step-level checks: pure, each returns True or raises PolicyError --------

def check_step_index(index: object, limits: object) -> bool:
    lim = _limits(limits)
    if _count(index, low=-1) >= lim.steps_per_job or index < 0:
        raise PolicyError("step_limit")
    return True


def check_retry(step_type: object, retries_used: object, limits: object) -> bool:
    lim = _limits(limits)
    if not isinstance(step_type, str) or step_type not in STEP_TYPES:
        raise PolicyError("step_type_unknown")
    _count(retries_used)
    if step_type not in RETRYABLE_STEPS:
        raise PolicyError("retry_not_allowed")
    if retries_used >= lim.retries_per_step:
        raise PolicyError("retries_exhausted")
    return True


def check_step_deadline(started_at: object, now: object, limits: object) -> bool:
    lim = _limits(limits)
    if not _aware(started_at) or not _aware(now):
        raise PolicyError("input_invalid")
    if started_at > now:  # a start in the future is a clock fault, not elapsed time
        raise PolicyError("clock_invalid")
    if now - started_at > timedelta(seconds=lim.step_deadline_s):
        raise PolicyError("step_deadline")
    return True


def check_job_deadline(deadline: object, now: object) -> bool:
    if not _aware(deadline) or not _aware(now):
        raise PolicyError("input_invalid")
    if now > deadline:
        raise PolicyError("job_deadline")
    return True


def check_model_call(calls_used: object, input_chars: object, limits: object) -> bool:
    lim = _limits(limits)
    _count(calls_used), _count(input_chars)
    if calls_used >= lim.model_calls_per_job:
        raise PolicyError("model_call_limit")
    if input_chars > lim.model_input_chars:
        raise PolicyError("input_too_large")
    return True


def check_step_output(output_chars: object, limits: object) -> bool:
    if _count(output_chars) > _limits(limits).step_output_chars:
        raise PolicyError("output_too_large")
    return True


# --- turn-level gate (docs/design/governance.md section 3) --------------------

# A memory write runs only when the user's own words asked for that kind of change.
ASKED = {
    "remember_fact": re.compile(r"remember|note|save|store|memori[sz]e|keep in mind|don'?t forget"),
    "add_reminder": re.compile(r"remind|alarm|wake me|remember|don'?t (?:let me )?forget"),
    "forget": re.compile(r"forget|delete|remove|erase|clear|scratch"),
}


@dataclass(frozen=True)
class Turn:
    """Facts set by trusted code for one conversation turn. Never model claims."""
    heard: str | None      # the user's own transcript this turn, None outside a voice turn
    read_untrusted: bool   # a tier 1 read already ran this turn


@dataclass(frozen=True)
class Decision:
    verdict: Literal["allow", "deny", "confirm"]
    code: str | None


def decide(tool: object, turn: object) -> Decision:
    """Pure and total: never raises, bad input is a deny. "confirm" is never returned yet."""
    try:
        if (not isinstance(tool, str) or not isinstance(turn, Turn)
                or type(turn.read_untrusted) is not bool
                or not (turn.heard is None or isinstance(turn.heard, str))):
            return Decision("deny", "input_invalid")
        if (tool == "delegate_task" or tool in MEMORY_WRITES) and turn.read_untrusted:
            return Decision("deny", "untrusted_read_in_turn")  # file, note or mail text must not act over the user's data
        if tool in ASKED and turn.heard is not None and not ASKED[tool].search(turn.heard.casefold()):
            return Decision("deny", "not_asked")
        return Decision("allow", None)
    except Exception:
        return Decision("deny", "input_invalid")
