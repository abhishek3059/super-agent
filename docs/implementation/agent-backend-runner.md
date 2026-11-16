# Agent backend slice 3: runner

Date: 2026-11-16. Branch `feat/agent-backend`. Build step 3 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
This is code only. It is not wired into `app.py`, and no roadmap item is ticked.

## What was built

- `apps/api/src/super_agent_voice/runner.py`: standard library only
  (`concurrent.futures.ThreadPoolExecutor`). No model, no network, no LangGraph.
- `apps/api/tests/test_runner.py`: 27 tests (the bad-receipt test runs 4 cases, the invalid-limits test 3).
- `Runner(ledger, limits, work, clock)`. `ledger` is the ledger module, `limits` a
  `policy.Limits`, `clock` a zero-argument callable returning an aware `datetime`.
  `work(job, admission, should_stop) -> dict` is the graph seam: trusted code
  that returns a receipt and is expected to poll `should_stop()`. The admission is
  the one submitted, with `tools` replaced by the set the runner kept after its tier 1
  filter (slice 5 changed this from passing the bare tool set, so the work also sees
  the deadline and `planner_is_local`).
- `submit(admission)` returns at once. The pool has `limits.concurrent_jobs`
  threads, so a job stays `queued` until a thread picks it up. This is the
  concurrent-jobs limit that admission left to the runner.
- `cancel(job_id)`, `recover()`, `close()`.

## Outcomes

| Situation | Ledger result | Reason | Receipt |
| --- | --- | --- | --- |
| Work returns a dict | `succeeded` | `work_done` | the work's receipt |
| Work raises | `failed` | `work_error` | `{"error": "work_error"}`, plus `"code"` when it raised a `PolicyError` (a fixed code from `policy.REASONS`, slice 5) |
| Job deadline passed when work returns | `failed` | `job_deadline` | `{"error": "job_deadline"}` |
| Cancel requested, work saw `should_stop()` | `cancelled` | `cancel_stopped` | `{"stopped": true}` |
| Work saw `should_stop()` true but no cancel is confirmed (failed ledger read, or state unreadable after work) | `failed` | `stop_unconfirmed` | `{"error": "stop_unconfirmed"}` |
| Cancel requested, work never polled and returned | `succeeded` | `work_done` | the work's receipt |
| Receipt not a dict, too large, or not JSON (judged from the receipt itself, with the ledger's cap and encoding; a very deeply nested receipt counts as not JSON) | `failed` | `bad_receipt` | `{"error": "bad_receipt"}` |
| No terminal write possible | `unknown` | `terminal_write_failed` | none |
| `cancel` on a queued job | `cancel_requested` then `cancelled` | `user_cancel`, `cancelled_before_start` | `{"executed": false}` |
| `cancel` on a running job | `cancel_requested` | `user_cancel` | none |
| `recover` finds `running` or `cancel_requested` | `unknown` | `restart_running`, `restart_cancel_requested` | none |
| `recover` finds `queued` | `failed` | `restart_queued` | `{"executed": false}` |

Reasons and error receipts are fixed strings in code, and exception text is never
stored, because it could carry model or personal data. A `succeeded` receipt is
whatever the trusted work function returned, so once the graph replaces the stub it
can carry model output. Once `should_stop()` has returned true for a job, `succeeded`
is never written. If the clock raises any exception, the job counts as past its deadline and
ends `failed` with `job_deadline`. If choosing the outcome itself raises, no outcome is
planned and the runner goes straight to the `unknown` attempt. A valid receipt whose
`succeeded` write the ledger refuses is never recorded as `bad_receipt`; it falls
through to `unknown` with `terminal_write_failed`.

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
  `bad_receipt`, `stop_unconfirmed`, `terminal_write_failed`, `user_cancel`,
  `cancelled_before_start`, `restart_queued`) and the receipt shapes are my choice.
- `should_stop()` is true when the job is `cancel_requested`, when the job
  deadline has passed, or when it cannot read the ledger (fail closed). A job
  becomes `cancelled` only if work saw a true value and the ledger still reads
  `cancel_requested` when work returns. Work that saw a true value with no
  confirmed cancel ends `failed` with `stop_unconfirmed`. A returned result is
  `succeeded` only if `should_stop()` never returned true for that job; that
  includes work that never polled while a cancel was requested, as the ledger allows.
- A passed deadline fails the job even if work returned a result. The deadline
  is checked when work returns, not by interrupting it.
- A bad receipt is `failed` with `bad_receipt`, then `unknown`. A good receipt whose
  write is refused goes to `unknown`, never to `bad_receipt`. Success is never a fallback.
- `recover()` returns the number of jobs moved (running or cancel requested to
  `unknown`, plus queued to `failed`).
- `Runner` accepts only a `policy.Limits`; anything else raises `PolicyError("limits_invalid")`, never a silent fallback to defaults.
- The per-day provider request counter is not part of this slice.

## Known limits

- Threads cannot be killed. A work function that never polls `should_stop`
  holds its pool slot until it returns, and a cancel or deadline only takes
  effect when it does. Step deadlines inside work are enforced by [the graph](agent-backend-graph.md), which can only check them after a step returns.
- `Admission` (tools, deadline) is in memory only. After a restart queued jobs
  are failed, not replayed, and `running` jobs become `unknown`.
- `close()` does not wait for running work. Queued jobs dropped by `close()` stay
  `queued` in the ledger until the next `recover()`.
- If `cancel` moves a queued job to `cancel_requested` and the follow-up write to
  `cancelled` fails, the job stays `cancel_requested` with no worker, and `recover()`
  later marks it `unknown` although it provably never ran.
- `cancel` raises `LedgerError` if the job is unknown or not `queued` or
  `running` (so a `cancel_requested` job cannot be cancelled again), and
  `StaleRevision` if it loses the race twice.
- `should_stop()` reads SQLite on each call, so work should not poll in a tight loop.
- If the ledger stays down during the terminal write, the job can stay `running`
  or `cancel_requested` until `recover()` marks it `unknown`.
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
error, one terminal event per job, `recover`, a failed poll and an unreadable
state after cancel (neither ends `succeeded`), a raising clock, invalid limits
(3 cases), a refused success write that is not recorded as `bad_receipt`, and a very deeply
nested receipt (`bad_receipt`, not a refused write). Real result: see the commit
report; it is not copied here so this file cannot go stale.

## Not built

Per-day provider request counter, wiring into `app.py`, and any roadmap tick. The graph is built in
[slice 5](agent-backend-graph.md). `recover()` now has a caller: the [delegation service](agent-backend-delegation.md) (slice 6) calls it once at creation.
