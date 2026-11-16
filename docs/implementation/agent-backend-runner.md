# Agent backend slice 3: runner

Date: 2026-11-16. Branch `feat/agent-backend`. Build step 3 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
This is code only. It is not wired into `app.py`, and no roadmap item is ticked.

## What was built

- `apps/api/src/super_agent_voice/runner.py`: standard library only
  (`concurrent.futures.ThreadPoolExecutor`). No model, no network, no LangGraph.
- `apps/api/tests/test_runner.py`: 20 tests (the bad-receipt test runs 4 cases, the invalid-limits test 3).
- `Runner(ledger, limits, work, clock)`. `ledger` is the ledger module, `limits` a
  `policy.Limits`, `clock` a zero-argument callable returning an aware `datetime`.
  `work(job, tools, should_stop) -> dict` is the stub graph seam: trusted code
  that returns a receipt and is expected to poll `should_stop()`.
- `submit(admission)` returns at once. The pool has `limits.concurrent_jobs`
  threads, so a job stays `queued` until a thread picks it up. This is the
  concurrent-jobs limit that admission left to the runner.
- `cancel(job_id)`, `recover()`, `close()`.

## Outcomes

| Situation | Ledger result | Reason | Receipt |
| --- | --- | --- | --- |
| Work returns a dict | `succeeded` | `work_done` | the work's receipt |
| Work raises | `failed` | `work_error` | `{"error": "work_error"}` |
| Job deadline passed when work returns | `failed` | `job_deadline` | `{"error": "job_deadline"}` |
| Cancel requested, work saw `should_stop()` | `cancelled` | `cancel_stopped` | `{"stopped": true}` |
| Cancel requested, work never polled and returned | `succeeded` | `work_done` | the work's receipt |
| Receipt not a dict, too large, or not JSON | `failed` | `bad_receipt` | `{"error": "bad_receipt"}` |
| No terminal write possible | `unknown` | `terminal_write_failed` | none |
| `cancel` on a queued job | `cancel_requested` then `cancelled` | `user_cancel`, `cancelled_before_start` | `{"executed": false}` |
| `cancel` on a running job | `cancel_requested` | `user_cancel` | none |
| `recover` finds `running` or `cancel_requested` | `unknown` | `restart_running`, `restart_cancel_requested` | none |
| `recover` finds `queued` | `failed` | `restart_queued` | `{"executed": false}` |

Reasons and error receipts are fixed strings in code. Exception text is never
stored, because it could carry model or personal data.

## How races resolve

Every write uses the ledger's revision compare-and-set. A worker starts a job
from the revision admission returned. If `cancel` moved a queued job first, the
start raises `StaleRevision`, the work is never called, and nothing more is
written. If the worker starts first, `cancel` sees a stale revision, re-reads
once, and cancels the now `running` job. The terminal write re-reads the job and
retries once on `StaleRevision`, so a cancel landing during the write is not lost.
A job already terminal is left alone, so each job gets one terminal event.

## Tier 1 tools

The runner removes any tier 1 tool (`tier1.T1_NAMES`) that is not in
`tier1.enabled_tools()` from what `work` receives. Other tools pass through. If
`enabled_tools()` raises (bad `SUPER_AGENT_T1` setting, or a non macOS host with
groups set), no tier 1 tool is offered.

## Choices where the design was unclear

- Reason strings (`runner_start`, `work_done`, `work_error`, `cancel_stopped`,
  `bad_receipt`, `terminal_write_failed`, `user_cancel`, `cancelled_before_start`,
  `restart_queued`) and the receipt shapes are my choice.
- `should_stop()` is true when the job is `cancel_requested`, when the job
  deadline has passed, or when it cannot read the ledger (fail closed). A job
  becomes `cancelled` only if work actually saw a true value while cancel was
  requested; otherwise a returned result is `succeeded`, as the ledger allows.
- A passed deadline fails the job even if work returned a result. The deadline
  is checked when work returns, not by interrupting it.
- A bad receipt falls back to `failed`, then `unknown`. Success is never a fallback.
- `recover()` returns the number of jobs moved (running or cancel requested to
  `unknown`, plus queued to `failed`).
- `Runner` accepts only a `policy.Limits`; anything else raises `PolicyError("limits_invalid")`, never a silent fallback to defaults.
- The per-day provider request counter is not part of this slice.

## Known limits

- Threads cannot be killed. A work function that never polls `should_stop`
  holds its pool slot until it returns, and a cancel or deadline only takes
  effect when it does. Step deadlines inside work are the graph slice's job.
- `Admission` (tools, deadline) is in memory only. After a restart queued jobs
  are failed, not replayed, and `running` jobs become `unknown`.
- `close()` does not wait for running work. Queued jobs dropped by `close()` stay
  `queued` in the ledger until the next `recover()`.
- `cancel` raises `LedgerError` if the job is unknown or not `queued` or
  `running` (so a `cancel_requested` job cannot be cancelled again), and
  `StaleRevision` if it loses the race twice.
- `should_stop()` reads SQLite on each call, so work should not poll in a tight loop.
- If the ledger itself fails during the terminal write, the job can stay
  `running` until `recover()` marks it `unknown`.
- Not run: any concurrency stress beyond the test suite, and the tier 1 filter on
  a real macOS host with groups enabled (tests monkeypatch `enabled_tools`).

## Tests and result

Command (venv built from `apps/api/requirements.lock`):

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest apps/api -p no:cacheprovider
```

Covered: the asyncio loop answering while a job runs, `submit` not blocking,
cancel of a running and of a queued job, work that ignores cancel, cancel of an
unknown or ended job, the concurrency cap (2 running, 1 queued, third starts after
release), a raising work function with no text leaked, a passed deadline with a
fake clock, four bad receipts, the tier 1 filter and its fail-closed config
error, one terminal event per job, and `recover`. Real result: see the commit
report; it is not copied here so this file cannot go stale.

## Not built

Model seam, graph, step catalog schemas, per-day provider request counter,
wiring into `app.py`, and any roadmap tick.
