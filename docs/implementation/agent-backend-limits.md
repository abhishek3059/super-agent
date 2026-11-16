# Agent backend slice 2: limits and admission

Date: 2026-11-16. Branch `feat/agent-backend`. Build step 2 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
This is code only. It is not wired into `app.py`, and no roadmap item is ticked.

## What was built

- `apps/api/src/super_agent_voice/policy.py`: standard library only. No model,
  no network, no clock of its own.
- `apps/api/tests/test_policy.py`: 217 tests.
- `Limits`: a frozen dataclass. Every field must be exactly `int` (a bool is
  refused), above 0 and at or below a hard ceiling in `CEILING`. A bad value
  raises `PolicyError("limits_invalid")`, so an invalid object cannot exist.
  The spec has no way to reach it.
- `admit(spec, idempotency_key, planner_is_local, limits, ledger, now, *, memory_is_synthetic=False,
  tier1_is_synthetic=False)`
  returns an `Admission` (job, scoped tool set, memory-context flag, absolute
  deadline, and `planner_is_local`, the locality it was granted under; the
  [planner](agent-backend-planner.md) refuses a non-local model for a local grant). `ledger` is the `ledger` module (anything with `list_jobs` and
  `create_job`).
- Step checks, pure, each returns `True` or raises: `check_step_index`,
  `check_retry`, `check_step_deadline`, `check_job_deadline`,
  `check_model_call`, `check_step_output`.

## Limits as implemented

| Field | Default | Hard ceiling |
| --- | --- | --- |
| `steps_per_job` | 8 | 32 |
| `step_deadline_s` | 30 | 600 |
| `job_deadline_s` | 300 | 3600 |
| `retries_per_step` | 1 | 2 |
| `model_calls_per_job` | 12 | 100 |
| `model_input_chars` | 8000 | 32000 |
| `step_output_chars` | 4000 | 16000 |
| `concurrent_jobs` | 2 | 8 |
| `queued_jobs` | 5 | 50 |
| `instruction_chars` | 1000 | 1500 |

Defaults are the provisional design table (unmeasured). The retry ceiling of 2
is the PH-00 rule. The ceilings are my choice, not measured. A character cap
does not bound stored bytes: the ledger stores JSON with `ensure_ascii`, so a
non-ASCII character costs 6 bytes and an emoji 12. `_spec` therefore also
measures the whole spec exactly as the ledger stores it and refuses with
`instruction_invalid` when it exceeds the ledger's `MAX_SPEC_BYTES`. What is
guaranteed: a spec that passes `_spec` is within the ledger's spec cap.

## Task spec, scope, queue

- The spec must be a dict with exactly `task_type`, `instruction`,
  `data_class`. Task types: `answer` and `summarize` (the design names no
  types, so these are mine). Data class: `synthetic` or `personal`. The
  instruction must be a non-blank string within `instruction_chars` that
  encodes as UTF-8 and serializes as JSON.
- Tool scope is fixed tables keyed by task type: base tools (`TOOL_SCOPE`:
  `answer` gets `calculate` and `current_time`, `summarize` gets
  `current_time`), tier 1 file tools (`TIER1_FILE_TOOLS`: `list_files`,
  `read_file`, `search_files`, which read the allowlisted folders), tier 1 app
  tools (`TIER1_APP_TOOLS`: `calendar_events`, `recent_notes`, `search_notes`,
  `recent_emails`, which read the user's real Calendar, Notes and Mail apps;
  `summarize` gets only the two notes tools) and memory read tools
  (`MEMORY_TOOLS`: `list_memory`, `list_reminders`, `answer` only). File tools
  are added only if the planner is local or `tier1_is_synthetic` is True. App
  tools are added only if the planner is local: no flag vouches for app data.
  Memory tools and memory context are added only if the planner is local
  or `memory_is_synthetic` is True. Both flags are keyword-only, default False,
  and come from trusted code (deployment configuration). The spec's
  `data_class` can only make admission stricter. No scope holds a memory write
  tool (tested against `memory.WRITES`).
- Queue cap: non-terminal jobs in the ledger must be below
  `concurrent_jobs + queued_jobs` (7 by default). A repeat of an already
  admitted key skips the cap, so a retry of a lost response still returns the
  same job. A refusal writes nothing.
- A repeat keeps the job's original deadline: it is the ledger's `created_at`
  plus `job_deadline_s`, so a retry cannot extend the budget. An unparseable
  stamp is `ledger_error`, an overflow `clock_invalid`. The two deadlines come
  from two clocks: the injected `now` for a new job, the ledger's own stamp for
  a repeat. Tools on a repeat are recomputed from the current trusted flags
  (deployment configuration, not spec input).

## Data-class decision table

`planner_is_local`, `memory_is_synthetic` and `tier1_is_synthetic` come from
trusted code and must be exactly `bool`, else refusal (`planner_locality_invalid`,
`memory_flag_invalid`). The spec's `data_class` is model-controlled, so it
never grants anything.

| Planner | Spec data class | Tier 1 file tools | Tier 1 app tools | Memory tools and context |
| --- | --- | --- | --- | --- |
| local | either | granted | granted | granted |
| cloud | personal | refused: `personal_data_cloud_planner` | refused | refused |
| cloud | synthetic | only if `tier1_is_synthetic` | never | only if `memory_is_synthetic` |

Base tools are always granted. The tests run the full table over planner,
data class and both flags.

## Tier 1 groups are not checked here

`Admission.tools` does not look at which `SUPER_AGENT_T1` groups are enabled.
`tier1.run_t1` refuses a disabled group at run time, so a disabled tool in the
admitted set fails when called, and is never made to work. The runner
([record](agent-backend-runner.md)) intersects the admitted set with
`tier1.enabled_tools()` before it offers tools to the planner.

## Reason codes

`limits_invalid`, `clock_invalid` (clock not timezone-aware, deadline overflow, or a step
start in the future), `idempotency_key_invalid` (also a key that does not
encode as UTF-8),
`planner_locality_invalid`, `memory_flag_invalid`, `spec_invalid`,
`task_type_invalid`, `instruction_invalid`, `data_class_invalid`,
`personal_data_cloud_planner`, `queue_full`, `ledger_error` (ledger could not
be read), `ledger_rejected` (ledger refused the create, for example the same
key with a different spec), `input_invalid`, `step_limit`, `step_type_unknown`,
`retry_not_allowed`, `retries_exhausted`, `step_deadline`, `job_deadline`,
`model_call_limit`, `input_too_large`, `output_too_large`, and three added by the
[planner slice](agent-backend-planner.md): `plan_invalid`, `tool_out_of_scope`,
`model_error`. The set is closed in
code (`REASONS`); the error message is only the code.

## Tests and result

Command (venv built from `apps/api/requirements.lock`):

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest apps/api -p no:cacheprovider
```

Real result on this host (Windows): `728 passed, 110 skipped` for
`apps/api` (`test_policy.py` 217, `test_runner.py` 25, `test_planner.py` 99, `test_ledger.py` 135 passed and 1 skipped). `npm run check`
result is recorded in the commit report, not here.

Covered: every limit breach and boundary, bool and wrong-type inputs, every
locality, data-class and trusted-flag combination, the app-tool rule, deadline
overflow, a future step start, unknown or extra spec keys (a spec cannot
name tools, limits, locality or the trusted flags), free text never in an error,
ledger untouched after any refusal, idempotent re-admission.

## Choices where the design was unclear

- Task type names and the personal-tool sets per type.
- Section 5 lists "concurrent jobs 2" and "jobs queued 5". Admission uses
  their sum as the cap on non-terminal jobs. The runner
  ([record](agent-backend-runner.md)) enforces the concurrent part with its pool size.
- "Retries per step 1" is the default; the PH-00 maximum of 2 is the ceiling.
- Classification of tier 1 tools, from `tier1.py` groups: `files` group
  (`list_files`, `read_file`, `search_files`) are file tools; `calendar`
  (`calendar_events`), `notes` (`recent_notes`, `search_notes`) and `mail`
  (`recent_emails`) are app tools. A test checks this against `tier1._TOOLS`.
- A cloud-planner job gets tier 1 file or memory tools only through the trusted
  flags, because the conversation model writes the spec and could label a job
  `synthetic`.
- `instruction_chars` and the ceilings are additions to the section 5 table.

## Known limits

- The cap check and the create are two ledger calls, not one transaction. Two
  concurrent admissions can both pass at the cap edge, so the queue can exceed
  the cap by the number of simultaneous callers. Closing that needs a ledger
  change.
- `check_job_deadline` takes only a deadline and a time, so it has no start
  time to compare and no future-start check; `check_step_deadline` does.
- A concurrent first admission of the same key can still get a fresh, `now`-based
  deadline for its repeat (the same non-atomic window as the queue cap).
- The trusted flags are statements by deployment configuration. Admission
  cannot check that the folders or the memory file really hold synthetic data.
- A model-call count and per-step state are the caller's to keep; the checks
  are pure.

## Not built

The graph, step execution, per-day provider request counter, wiring into `app.py`, and any roadmap tick.
