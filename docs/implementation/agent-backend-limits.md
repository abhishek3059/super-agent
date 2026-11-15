# Agent backend slice 2: limits and admission

Date: 2026-11-16. Branch `feat/agent-backend`. Build step 2 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
This is code only. It is not wired into `app.py`, and no roadmap item is ticked.

## What was built

- `apps/api/src/super_agent_voice/policy.py`: standard library only. No model,
  no network, no clock of its own.
- `apps/api/tests/test_policy.py`: 199 tests.
- `Limits`: a frozen dataclass. Every field must be exactly `int` (a bool is
  refused), above 0 and at or below a hard ceiling in `CEILING`. A bad value
  raises `PolicyError("limits_invalid")`, so an invalid object cannot exist.
  The spec has no way to reach it.
- `admit(spec, idempotency_key, planner_is_local, limits, ledger, now, *, memory_is_synthetic=False)`
  returns an `Admission` (job, scoped tool set, memory-context flag, absolute
  deadline). `ledger` is the `ledger` module (anything with `list_jobs` and
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
is the PH-00 rule. The ceilings are my choice, not measured. 1,500 characters
is at most 6,000 UTF-8 bytes, inside the ledger's 8,000-byte spec cap.

## Task spec, scope, queue

- The spec must be a dict with exactly `task_type`, `instruction`,
  `data_class`. Task types: `answer` and `summarize` (the design names no
  types, so these are mine). Data class: `synthetic` or `personal`. The
  instruction must be a non-blank string within `instruction_chars` that
  encodes as UTF-8 and serializes as JSON.
- Tool scope is fixed tables keyed by task type: base tools (`TOOL_SCOPE`:
  `answer` gets `calculate` and `current_time`, `summarize` gets
  `current_time`), tier 1 read tools (`TIER1_TOOLS`) and memory read tools
  (`MEMORY_TOOLS`: `list_memory`, `list_reminders`, `answer` only). Tier 1
  tools are added only if the planner is local or `tier1_is_synthetic` is
  True. Memory tools and memory context are added only if the planner is local
  or `memory_is_synthetic` is True. Both flags are keyword-only, default False,
  and come from trusted code (deployment configuration). The spec's
  `data_class` can only make admission stricter. No scope holds a memory write
  tool (tested against `memory.WRITES`).
- Queue cap: non-terminal jobs in the ledger must be below
  `concurrent_jobs + queued_jobs` (7 by default). A repeat of an already
  admitted key skips the cap, so a retry of a lost response still returns the
  same job. A refusal writes nothing.

## Data-class decision table

`planner_is_local`, `memory_is_synthetic` and `tier1_is_synthetic` come from
trusted code and must be exactly `bool`, else refusal (`planner_locality_invalid`,
`memory_flag_invalid`). The spec's `data_class` is model-controlled, so it
never grants anything.

| Planner | Spec data class | Tier 1 tools | Memory tools and context |
| --- | --- | --- | --- |
| local | either | granted | granted |
| cloud | personal | refused: `personal_data_cloud_planner` | refused |
| cloud | synthetic | only if `tier1_is_synthetic` | only if `memory_is_synthetic` |

Base tools are always granted. The tests run the full table over planner,
data class and both flags.

## Reason codes

`limits_invalid`, `clock_invalid`, `idempotency_key_invalid`,
`planner_locality_invalid`, `memory_flag_invalid`, `spec_invalid`,
`task_type_invalid`, `instruction_invalid`, `data_class_invalid`,
`personal_data_cloud_planner`, `queue_full`, `ledger_error` (ledger could not
be read), `ledger_rejected` (ledger refused the create, for example the same
key with a different spec), `input_invalid`, `step_limit`, `step_type_unknown`,
`retry_not_allowed`, `retries_exhausted`, `step_deadline`, `job_deadline`,
`model_call_limit`, `input_too_large`, `output_too_large`. The set is closed in
code (`REASONS`); the error message is only the code.

## Tests and result

Command (venv built from `apps/api/requirements.lock`):

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest apps/api -p no:cacheprovider
```

Real result on this host (Windows): `573 passed, 110 skipped in 25.26s` for
`apps/api`. `npm run check`
result is recorded in the commit report, not here.

Covered: every limit breach and boundary, bool and wrong-type inputs, every
locality and data-class combination, unknown or extra spec keys (a spec cannot
name tools, limits, locality or the memory flag), free text never in an error,
ledger untouched after any refusal, idempotent re-admission.

## Choices where the design was unclear

- Task type names and the personal-tool sets per type.
- Section 5 lists "concurrent jobs 2" and "jobs queued 5". Admission uses
  their sum as the cap on non-terminal jobs. The runner slice must enforce the
  concurrent part when it picks jobs to start.
- "Retries per step 1" is the default; the PH-00 maximum of 2 is the ceiling.
- A cloud-planner job gets tier 1 or memory tools only through the trusted
  flags, because the conversation model writes the spec and could label a job
  `synthetic`.
- `instruction_chars` and the ceilings are additions to the section 5 table.

## Known limits

- The cap check and the create are two ledger calls, not one transaction. Two
  concurrent admissions can both pass at the cap edge, so the queue can exceed
  the cap by the number of simultaneous callers. Closing that needs a ledger
  change.
- The trusted flags are statements by deployment configuration. Admission
  cannot check that the folders or the memory file really hold synthetic data.
- A model-call count and per-step state are the caller's to keep; the checks
  are pure.

## Not built

The runner, model seam, graph, step catalog schemas, per-day provider request
counter, wiring into `app.py`, and any roadmap tick.
