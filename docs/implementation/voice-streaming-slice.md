# Local voice streaming slice: implementation record

| Field | Value |
| --- | --- |
| Date | Started 2026-11-10; final local code review 2026-11-11 |
| Phase / PR | PH-01 / PR #24 on `docs/ph-00-close` |
| Authority | [Operator current-phase direction](../approvals/ph-01-current-phase-work.md) |
| Contract | [Local streaming technical design](../design/voice-streaming-slice.md) |
| State | Local fake streaming implementation and code review complete; backend 66 cases and frontend 39 cases pass; phase not accepted |
| Review | Backend final PASS, average 8.52; frontend PASS, average 8.8; credential and independent security acceptance open |

## Scope

This is the local streaming foundation, not the Gemini adapter. The assigned
work replaces the request/response seam with `start`, `enqueue_audio`,
`interrupt`, `events`, and `close`, and a concurrent bounded backend bridge.
The browser work covers per-frame playback rate, a silence floor, an honest
input-level meter, automatic interruption, and session lifecycle regression
tests. No new SDK, dependency, provider call, or microphone egress is included.

## Execution status

The parent drafted the first code changes. A free architect inspected that
draft and signed a technical contract. The first `developer-free` pass reached
its step limit before completing the slice. It reported a partial FAIL, with
four backend test failures and unfinished browser corrections and self-tests.

The backend continuation and browser work were assigned to separate free
developers with non-overlapping file ownership. The browser developer has
returned its [frontend output record](voice-streaming-frontend-output.md).
The parent independently reran its self-tests, build, and audit successfully.
The backend developer also returned its [output record](voice-streaming-backend-output.md),
and the parent independently ran all 46 backend tests successfully. Separate
free reviewers then assessed both scopes. The frontend correction round added
13 service regressions, and parent verification passed all 37 service cases,
8 epoch cases, build, and audit.

The [frontend re-review](../reviews/voice-streaming-frontend.md) and
[backend review](../reviews/voice-streaming-backend.md) both returned code PASS,
but each quality average was 8.2, below the repository delivery threshold.
The parent required further corrections. The frontend developer has returned
the honesty and transient-state fixes; the parent independently verified all
39 service cases, 8 epoch cases, build, and audit. The final frontend review
returned PASS with an 8.8 average, clearing that scope's quality threshold.
The backend developer drafted the [bounded-teardown addendum](../design/voice-streaming-teardown.md)
revision 2 implementation and reached its step limit. The parent fixed the
timing-dependent overflow test and cleanup bookkeeping; the backend API file
passes. The free developer returned the agreed teardown unit tests. Parent
combined verification on 2026-11-11 passes all 66 backend cases. The consolidated
final review returned PASS at 8.52 with no confirmed blocker or major finding.
Uncertain cases are
logged in the [uncertainty record](../reviews/voice-streaming-uncertain-findings.md)
rather than automatically expanding implementation scope.
No pending test is treated as a PASS. The operator requested a local commit of
this implementation for PR #24. Publishing it and merging contributions require
separate push and merge approvals. No phase acceptance or roadmap tick is claimed.

## Evidence so far

| Check | Result / source |
| --- | --- |
| Backend before the streaming draft | Parent ran pytest: 11 passed |
| Existing playback epoch self-test before the draft | Parent ran `npm run test:epoch --prefix apps/web`: PASS, 8 cases |
| First developer backend unit file | Developer reported 12 passed |
| First developer backend API file | Developer reported 19 passed, 4 failed; not delivery evidence |
| Earlier backend failures | Resolved in the continuation; the earlier partial FAIL remains historical, not the current test result |
| Full backend run before bounded-teardown correction | Parent ran all backend tests: 46 passed in 2.58 s; amended teardown not yet verified |
| Full backend run after bounded-teardown correction | Parent ran all backend tests on 2026-11-11: 66 passed in 3.96 s; [saved output](evidence/voice-streaming-backend-2026-11-11.txt) |
| Pre-commit verification (2026-11-11) | Root `npm ci --ignore-scripts` passed with 0 vulnerabilities; backend rerun: 66 passed in 6.27 s on Python 3.14.4; voice service: 39 cases PASS; playback epoch: 8 cases PASS |
| Browser service self-test after first review corrections | Parent rerun: PASS, 37 cases; historical first-correction result |
| Browser service self-test after final frontend corrections | Parent rerun: `npm run test:voice --prefix apps/web`, PASS, 39 cases |
| Existing epoch self-test on the frontend rewrite | Parent rerun: `npm run test:epoch --prefix apps/web`, PASS, 8 cases |
| Frontend build after final frontend corrections | Parent rerun with `NG_CLI_ANALYTICS=false`: PASS, 116.00 kB initial total |
| Frontend audit | Parent rerun: `npm audit --prefix apps/web`, found 0 vulnerabilities |
| Repository checks after final review record | Parent ran `npm run check` on 2026-11-11: PASS, 0 errors; roadmap self-test passed |
| Whitespace check after final review record | Parent ran `git diff --check` on 2026-11-11: PASS, line-ending advisories only |
| Completed-code review | Backend final PASS with 8.52 average; frontend PASS with 8.8 average; both code-review quality thresholds cleared |
| Mac hardware acceptance | Old-scaffold evidence merged via PR #25 against `4f51e00`; R-01.3 is ticked, but that evidence is not evidence for the new streaming code |
| Local microphone acceptance | Inconclusive operator report at the time; superseded by the [R-01.4 record](../approvals/r01-4-microphone-test.md) of 2026-11-12 |
| Native provider test | Not run; no Gemini adapter in this slice |

### Parent frontend verification (2026-11-10)

These commands ran after the frontend developer returned. The build timestamp
in the real output is `2026-11-10T16:11:42.360Z`.

```text
npm run test:voice --prefix apps/web
voice-session self-test: PASS (24 cases)

npm run test:epoch --prefix apps/web
playback-epoch self-test: PASS (8 cases)

$env:NG_CLI_ANALYTICS='false'
npm run build --prefix apps/web
Initial total: 115.40 kB
Application bundle generation complete. [11.478 seconds]

npm audit --prefix apps/web
found 0 vulnerabilities
```

All four commands exited successfully. These offline checks are not hardware
microphone evidence, an independent review verdict, or RT-G01 acceptance.

The parent then ran `npm run check` and `git diff --check`, both with exit 0.
The repository check reported:

```text
"markdown_files": 73,
"files_scanned": 168,
"local_links_checked": 1098,
"fragment_links_checked": 259,
"errors": 0
roadmap self-test: all checks passed
```

The whitespace check emitted LF-to-CRLF advisories, not whitespace errors.
These checks cover that working-tree snapshot, not future backend or review
corrections. The roadmap was reread and no new item was ticked.

### Parent verification after frontend corrections (2026-11-10)

The initial 24-case and 115.40 kB results above are retained as history. After
the free developer returned the correction round, the parent ran:

```text
npm run test:voice --prefix apps/web
voice-session self-test: PASS (37 cases)

npm run test:epoch --prefix apps/web
playback-epoch self-test: PASS (8 cases)

$env:NG_CLI_ANALYTICS='false'
npm run build --prefix apps/web
Initial total: 115.94 kB
Application bundle generation complete. [7.752 seconds]
Build timestamp: 2026-11-10T16:54:25.111Z

npm audit --prefix apps/web
found 0 vulnerabilities
```

All four commands exited with 0. These results do not substitute for the
subsequently required corrections and fresh review. A hung browser context-close promise cannot be forcibly
settled by this code; the correction makes local state and track/socket
detachment finish without waiting for it. Browser audio-context release must
not be claimed when that close did not complete.

## Limitations and acceptance blockers

### Parent verification of final frontend corrections (2026-11-10)

```text
npm run test:voice --prefix apps/web
voice-session self-test: PASS (39 cases)

npm run test:epoch --prefix apps/web
playback-epoch self-test: PASS (8 cases)

$env:NG_CLI_ANALYTICS='false'
npm run build --prefix apps/web
Initial total: 116.00 kB
Application bundle generation complete. [1.956 seconds]
Build timestamp: 2026-11-10T17:41:32.838Z

npm audit --prefix apps/web
found 0 vulnerabilities
```

All four commands exited with 0. These 39-case results supersede the earlier
24-case and 37-case snapshots for the latest frontend test evidence. The final
frontend reviewer subsequently reproduced the tests and returned PASS at 8.8.
These commands do not validate the
backend teardown correction, verified separately by the 2026-11-11 run.

### Parent backend verification (2026-11-10)

```text
$voicePython = Join-Path $env:LOCALAPPDATA 'Temp\super-agent-voice-venv\Scripts\python.exe'
& $voicePython -m pytest apps/api -v
platform win32 -- Python 3.14.4, pytest-9.1.1, pluggy-1.7.0
collected 46 items
apps\api\tests\test_stream_units.py ............                         [ 26%]
apps\api\tests\test_voice_api.py ..................................      [100%]
46 passed in 2.58s
```

The command exited with 0. The developer diagnosed cancellation during
teardown, invalid follow-up TestClient lifetimes, oversized-frame error/close
ordering, a Windows pytest parameter-name limit, and a reused closed adapter.
Its first product fix moved teardown into a shielded task. The independent
review then reproduced unbounded-worker and final-send waits. The bounded-
teardown correction was subsequently implemented and verified with 66 tests.
These earlier 46 tests do not
prove the amended behavior or every task and transport failure.

### Remaining blockers

- Local code review is complete: backend PASS at 8.52 and frontend PASS at
  8.8. Hardware, credential, independent security, and native-provider
  acceptance remain separate and open.
- The teardown addendum explicitly supersedes unconditional gate release on
  cleanup failure: unresolved workers or unconfirmed adapter closure retain
  the slot. A failed close permits at most one non-overlapping idempotent
  retry. Permanent failure requires operator recovery. This is specified local
  fail-closed behavior, not an implemented or approved native-provider claim.

- This slice is only part of R-01.7. R-01.7 cannot be ticked without the Gemini
  adapter and its required coverage.
- A level floor is not speech recognition or validated voice activity detection.
  Neither audio quality nor automatic barge-in is accepted on hardware yet.
- Provider stale-event quarantine and native interruption behavior remain
  unverified until the provider implementation and synthetic live evidence.
- Credentials retain the existing development token flow. Expiry, revocation,
  throttling, and independent credential review are not delivered here.
- R-01.3, R-01.4, R-01.5, R-01.6, R-01.8, R-01.9, and R-01.10 remained open when this slice was written; see [roadmap.md](../../roadmap.md) for current state.
- No phase or runtime gate is closed by this record.
- The existing local Angular CLI analytics change is user work. It is not part
  of this implementation and must not be committed with it.
