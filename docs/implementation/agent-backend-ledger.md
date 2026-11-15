# Agent backend slice 1: job ledger

Date: 2026-11-15. Branch `feat/agent-backend`. Build step 1 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
This is code only. It is not wired into `app.py`, and no roadmap item is ticked.

## What was built

- `apps/api/src/super_agent_voice/ledger.py`: standard-library `sqlite3` only.
- `apps/api/tests/test_ledger.py`: 135 tests: 134 passed and 1 skipped on this host (the first
  version had 122 passed and 1 skipped; slice 2 review fixes added 12).
- Storage: `~/.super-agent/ledger.db` beside `memory.db`, directory 0700, file
  0600, same `DB_PATH` override convention as `memory.py`. No WAL (memory.py
  does not use it). Schema version is `PRAGMA user_version = 1`. Tables:
  `jobs` (id, unique idempotency key, canonical spec JSON, state, revision,
  created, updated, terminal timestamps in UTC) and an append-only `events`
  table (job id, from, to, revision, reason code, receipt JSON or null, time).
- `create_job(spec, key)`: spec must be a JSON-safe dict of at most 8,000
  bytes. A repeated key with the same spec returns the existing job; with a
  different spec it raises.
- `transition(job_id, to_state, expected_revision, reason, receipt=None)`: a
  stale revision raises `StaleRevision`; a disallowed move raises; `succeeded`
  `failed` and `cancelled` need a receipt (dict, at most 4,000 bytes, stored and not
  interpreted). Revision bump, state change and event are one transaction.
- `get_job`, `list_jobs(state=None)`, `list_events(job_id)`.
- `recover_after_restart()`: `running` and `cancel_requested` become
  `unknown` (reason `restart_running` or `restart_cancel_requested`). Nothing
  returns to `queued`.
- `purge(now)`: deletes terminal jobs and their events once
  `terminal_at <= now - 14 days`. `now` must be timezone-aware. Jobs that are
  not terminal, including `unknown`, are never purged.
- Every database, file or validation failure raises `LedgerError`, including
  a corrupt stored spec or receipt, a non-string state, and a revision that is
  not a plain int (a bool is refused).

## Transition table as implemented

From [architecture.md](../../architecture.md#canonical-job-states).

| From | Allowed to |
| --- | --- |
| `queued` | `running`, `cancel_requested`, `failed`, `waiting_for_approval` |
| `running` | `succeeded`, `failed`, `cancel_requested`, `unknown`, `waiting_for_approval` |
| `waiting_for_approval` | `queued`, `cancel_requested`, `failed` |
| `cancel_requested` | `cancelled`, `succeeded`, `failed`, `unknown` |
| `unknown` | `succeeded`, `failed`, `cancelled` |
| `succeeded`, `failed`, `cancelled` | none |

## Choices where architecture.md is not exact

- `unknown` to `queued` needs "a journaled policy decision proving
  non-execution", which does not exist yet, so it is not allowed. A later
  slice adds it with that decision.
- Restart moves `cancel_requested` to `unknown`: the table allows it and a
  restart is no proof of stop.
- The table's "only at a verified checkpoint" and "only after valid approval
  revalidation" conditions are the caller's duty. The ledger checks the edge,
  not the evidence.
- `cancelled` needs a receipt, because architecture.md reaches it only "after
  evidence of non-execution or acknowledged stop". The ledger stores the
  receipt and does not judge it.
- `failed` always needs a receipt, including an admission failure from
  `queued`.
- `unknown` is not terminal, so it keeps no terminal timestamp and is not
  purged.

## Verification

Run on Windows, Python 3.14.4, in a virtual environment under the system temp
directory, installed from `apps/api/requirements.lock` with `--only-binary=:all:`.

- `python -m pytest apps/api`: 374 passed, 110 skipped, 1 warning (existing).
  `test_ledger.py` alone: 122 passed, 1 skipped.
- The skips include the ledger file-mode test and the whole of `test_memory.py`
  (no time zone database on this host). The 0700 and 0600 mode test did not run
  here, because Windows has no POSIX modes. It is not verified.
- `npm run check`: 0 errors.

## Known limits

- One process lock. The transition is a compare-and-set in SQL
  (`UPDATE ... WHERE id = ? AND revision = ?`, stale if no row matched, then
  rolled back), tested by simulating a rival write inside one process. Real
  two-process behaviour is still not tested.
- No unique-violation race handling beyond the lock: the check and insert run
  under one lock and one transaction.
- Sizes are provisional and not yet tied to the limits table in the design.

## Not built yet

Limits and admission (step 2), runner, model seam, graph, `delegate_task`,
Gemini text model, evaluation set. No call site uses the ledger, so
`recover_after_restart` and `purge` are not yet called at startup.
