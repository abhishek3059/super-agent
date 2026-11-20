# R-02.F3 record: one ledger truth

| Field | Value |
| --- | --- |
| Date | 2026-11-20 |
| Branch | `feat/ph02-ledger-policy`, stacked on PR 64 |
| Host | macOS, Python 3.12, SQLite ledger, synthetic data, no network |
| Suite result | `apps/api`: 1387 passed, 2 skipped (macOS, Python 3.12, commit `a789e9c`). `npm run check`: 0 errors. |

R-02.F3 asks that the SQLite owner ledger be the one application-owned
truth, and that the PostgreSQL seam and the Hermes worker definitions from
PR 55 either sit behind it with the same states, idempotency and policy
admission, or be removed. Both now sit behind it. Nothing was removed.

## PostgreSQL seam

The seam is not a second ledger. It is a storage switch inside `ledger.py`:
the same `create_job`, `transition`, `_move` compare-and-set and `NEXT`
table run on either backend, and `policy.admit` writes through the same
`create_job`. So states, revisions and idempotency are the same code.

Two gaps were found and closed in `ledger.py`:

| Gap | Fix | Tests (`tests/test_ledger.py`) |
| --- | --- | --- |
| The generic `DATABASE_URL`, which other apps set, silently moved the owner ledger | Only `SUPER_AGENT_DATABASE_URL` is read | `test_the_generic_database_url_does_not_select_the_ledger` |
| Any host was accepted, so job specs and receipts could leave the machine | `_pg_url` allows only `postgres` or `postgresql` on `127.0.0.1`, `localhost` or `::1`, with no libpq multi-host, `host`, `hostaddr` or `service` override. Anything else raises `LedgerError` before any connection, never echoes the URL, and does not fall back to SQLite, so there is never a second truth | `test_a_ledger_database_off_this_machine_fails_closed` (9 cases), `test_a_loopback_ledger_database_is_used` (3 cases) |

A hosted database (Neon, Supabase) is therefore refused. It would send job
instructions, which can hold personal data, to a cloud service (REQ-13). The
[path map](../design/jarvis-path-map.svg) now says so.

Not covered: no test runs a real PostgreSQL server. The seam's SQL is
covered by the existing `test_postgres_seam_query_formatting` with a fake
driver. A Unix-socket PostgreSQL URL is refused (no hostname); allowing one
needs its own check.

## Hermes worker definitions

`runner.HERMES_WORKERS` holds five read-only tool profiles. Since R-02.F1
(PR 64), `Runner.claim_and_run` passes every claimed job through
`policy.admit_claimed`, which runs the same spec checks as `admit` and cuts
the worker's tools down to the task type's scope. The runner then narrows
them again by the live switches (`policy.offered_tools`, governance slice 3).

So a worker definition can only remove tools, never add one. The workers in
R-02.4 are the two task types, `answer` and `summarize`. The five profiles
are not extra workers with their own authority.

| Claim | Tests |
| --- | --- |
| A profile never adds a tool beyond the task scope, for every task type and locality, and holds no memory write | `tests/test_runner.py::test_a_hermes_worker_can_only_narrow_the_task_scope` |
| A claimed job that fails the checks is failed with `executed: false` | `tests/test_runner.py::test_claim_and_run_goes_through_admit` |
| No admitted tool, for any profile, can write or reach the network | `tests/test_delegation.py::test_no_admitted_tool_can_write_or_reach_network` |
