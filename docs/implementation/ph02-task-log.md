# PH-02 task log: ledger evidence work bundle

Dated 2026-11-20. This log records what was done on branch `feat/ph02-ledger-evidence` (PR 64).
The results are in the [evidence record](ph02-ledger-evidence.md). No roadmap item is ticked yet.

## Audit

- Base: develop at 664fd2a, suite 1071 passed, 110 skipped.
- `Runner.claim_and_run` built its own admission and skipped `policy.admit`.
- The Hermes workers listed `memory_recall` and `memory_save`, which do not exist.
- `_run` and `_run_claimed` were near duplicates.
- Deadlines were checked only between tool calls, so a hanging tool held a pool thread forever.
- The queue-cap check in `policy.admit` was not atomic.
- Jobs carried no voice session id, so stale sessions could not be rejected.
- `Service(model=None)` skips recovery. This was kept, because two tests require it and recovery could fail other workers' jobs.

## Owner decisions

- Build stale-session rejection.
- Route the Hermes workers through admission.
- Fix hung tools now, and make the fix hold on Windows.
- Build the planner first, then do the real run (so the R-02.5 real run waits for PR #65).

## Build commits

| SHA | Subject |
| --- | --- |
| 4538176 | chore(ph02): open the PH-02 ledger evidence work bundle |
| 09aa18a | fix(api): route claim_and_run through policy admission (R-02.F1) |
| 0c370e9 | feat(api): stale sessions, tool timeouts, PH-02 gap tests |
| 51a040f | docs(roadmap): add R-02.F5 and R-02.F6 |
| 72b76a4 | fix(api): close session and cap races from review |
| c571507 | fix(api): count only abandoned tool threads |
| d23cf2e | fix(api): prune finished threads before the cap check |

## Review rounds

1. Shared reviewer on 51a040f: REVISE, 7.6.
   - [Opus security review](../reviews/ph02-ledger-review.md): 0 critical or high findings, M1, M2, L1 to L4.
   - Both reviews found that the session check failed open after a close.
2. Fixes in 72b76a4:
   - Once a session has been opened, a caller must name the live one. None is refused.
   - `close_session` only ends the session whose id matches.
   - `Service.cancel` refuses unless the job's own session asks.
   - The tool-thread cap check and registration became one step under a lock.
   - The concurrent-admit test was made deterministic with 20 threads behind a barrier.
   - The subprocess audit found nothing to change. The R-02.F6 roadmap line was reworded to match.
3. Shared reviewer on 72b76a4: [PASS, 9.0](../reviews/ph02-ledger-review.md). The security re-check found two issues in the cap fix:
   - Counting every in-flight thread would fail healthy plans with five or more parallel reads.
   - `Service.cancel` reported a missing job as a stale session.
4. Fixes in c571507:
   - The cap counts only abandoned threads again. A thread joins the set only when its wait times out. Nothing is registered before `start()`.
   - `cancel` returns `unknown_job` for a missing job.
   - New tests: `test_healthy_parallel_reads_are_not_capped`, `test_the_cap_counts_abandoned_threads_across_concurrent_calls`, `test_cancel_of_an_unknown_job_is_unknown_job`.

## Result

1092 passed, 110 skipped on Windows 11. `npm run check` passes. Measured: delegate 11.3 ms, max loop gap 32.2 ms.

## Commit d23cf2e and ticks (2026-11-20)

- Commit d23cf2e prunes finished tool threads under the lock before each cap check, and drops the separate re-check after registration. Test added: `test_a_dead_thread_left_in_the_set_is_pruned`. The API suite exited 0.
- Shared-reviewer and security review record: [ph02-ledger-review.md](../reviews/ph02-ledger-review.md).
- Ticked on the roadmap with the evidence record as evidence: R-02.1, R-02.2, R-02.3, R-02.4, R-02.F1, R-02.F5, R-02.F6. R-02.5, R-02.7, R-02.F2, R-02.F3, R-02.F4 and R-02.6 are not ticked. PH-02 status moved to `in progress`.

## Next

- Merge PR #65 (local planner), then do the real run for R-02.5 and record it in the evidence record.
- R-02.F3 is closed on `feat/ph02-ledger-policy` (entry below). PR 67 proposes removing R-02.F2; it is still on the roadmap until that merges.
- R-02.5 is ticked only after the real run. The other ticks are listed in the entry above.

## `feat/ph02-ledger-policy` bundle (2026-11-20)

Stacked on PR 64 at the owner's choice, so R-02.1 to R-02.F1 are not redone.
Run on macOS with Python 3.12 and Node 22.

- R-02.7 slices 2, 3 and 4 built: [slices record](governance-gate-slices2-4.md). Slice 2b waits for OD-G5, so R-02.7 is not ticked.
- R-02.F3 ticked: [record](r02-f3-ledger-paths.md). The PostgreSQL seam is loopback only and reads only `SUPER_AGENT_DATABASE_URL`; the five Hermes definitions are tool profiles behind admission.
- R-02.F4 ticked: [record](r02-f4-handshake-auth.md). The token is proven in the WebSocket upgrade, before accept. A real browser run is not done.
- Local test runs set `HOME` to an empty folder. The per-test guard in `tests/conftest.py` walks the real `~/.super-agent`, and a large Jarvis HQ data folder there makes each test slow. CI is not affected.
- Results: `apps/api`: 1387 passed, 2 skipped (macOS, Python 3.12, commit `a789e9c`). `npm run check`: 0 errors. Web console: voice-session self-test 73 cases, ui 48, epoch 8, all PASS; `npm run build` passes; `npm audit` finds 0 vulnerabilities.
