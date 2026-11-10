# Backend local streaming code review

| Field | Value |
| --- | --- |
| Date | Initial review 2026-11-10; final review 2026-11-11 |
| Reviewer | Separate `reviewer-free` subagents; final session `ses_e393b248cffeZd4diyZw3cWW2T` |
| Scope | PH-01 PR #24: original 46-test snapshot and corrected 66-test snapshot; existing frontend PASS retained |
| Reviewed contract | [Streaming contract](../design/voice-streaming-slice.md) revision 4 and [teardown addendum](../design/voice-streaming-teardown.md) revision 2 for the final review |
| Reviewer verdict | Final PASS, no confirmed blocker or major finding; average 8.52 |
| Parent disposition | Local slice code-review quality threshold cleared; phase acceptance and independent security review remain open |
| Gate effect | None. Not independent security acceptance, hardware evidence, or PH-01 completion |

The parent saved this report from the reviewer's returned response. The
reviewer read backend source, tests, and its output record only. It did not
write files, review frontend source, stage, commit, approve, or merge.

## Verified evidence

The following sections preserve the original review. They are superseded by
the final verdict at the end, not current unresolved delivery findings.

The reviewer reran all 46 backend tests successfully and reported four
controlled inline asyncio probes. Those probes were not saved as runnable
repository tests, so they motivate the required regression coverage rather
than substituting for it.

- Cancellation during teardown: repeated cancellations were absorbed by the
  original shielded cleanup, and cooperative workers and adapter finished.
- Blocked final wire send: adapter cleanup and gate release completed, but the
  session handler remained alive past 2.5 seconds. A second session could
  authenticate while that final send remained blocked.
- Cancellation-resistant worker: the unbounded gather prevented adapter
  cleanup and gate release until the worker actually finished.
- Hanging but cancellation-cooperative close: the original two-second timeout
  preserved the known `invalid-control` category and eventually released the
  gate. The repository lacked a regression for this path.

Current fake workers are cancellation-cooperative. The parent treats the
observed indefinite waits as a structural delivery gap against code-enforced
bounds, not as proof of native-provider behavior or an accepted vulnerability
in an unimplemented provider.

## Findings and disposition

Line references describe the reviewed snapshot, before correction.

| ID | Reviewer severity | Finding | Required action |
| --- | --- | --- | --- |
| B-01 | MINOR | `test_voice_api.py:456-462` lacks an adapter `AudioChunk(data=b'')` case, although the validation branch rejects it. | Add an adapter-side empty-frame regression for fixed `invalid-audio`. |
| B-02 | MINOR, second opinion requested | `app.py:263` awaits cancelled workers without a timeout before adapter close and gate release. A resistant worker can hold the handler indefinitely. | Bounded presence waits; quarantine unresolved ownership rather than allowing replacement sessions. |
| B-03 | MINOR, second opinion requested | `app.py:277,280,284` final error/state/close operations are unbounded. The shield loop can keep a blocked connection task alive indefinitely. | Shared bounded deadline, owned pending operations, and no later wire operation while an earlier one is unresolved. |
| B-04 | MINOR | The suite tests raising close but not a hanging close or its claimed bound. | Add hanging and cancellation-resistant close regressions with honest closure confirmation. |
| B-05 | MINOR | Control overflow is tested at queue level, not through session failure and cleanup. | Add session-level overflow coverage and verify serialized final messages. |
| B-06 | MINOR | The CT-05 acceptance table does not explicitly state the intended pre-authentication session-slot placement. | Add the dated acceptance-table clarification, preserving the auth/total deadlines and 1013 behavior. |
| B-07 | MINOR, honesty | Backend output says the parent model was unavailable, although the parent remained active. | Record the selected free developer profile without an unverified outage claim. |

The reviewer found the auth-before-factory ordering, Host/Origin checks,
constant-time comparison, PCM validation, fixed error categories, per-frame
rates, sender ownership recheck, queue bounds, fake lifecycle, and existing
tests sound for their current scope. No confirmed major finding was reported.

## Quality scores

| Correctness | Security | Honesty | Scope | Clarity | Average |
| --- | --- | --- | --- | --- | --- |
| 8 | 8 | 8 | 9 | 8 | 8.2 |

These are the reviewer's original scores, not the parent's claim of a passing
delivery gate. Security is a code-review score only. Revise and re-review are
required by AGENTS.md section 9.

## Signed correction and remaining work

The free architect produced the [bounded-teardown addendum](../design/voice-streaming-teardown.md)
revision 2 and the streaming contract's revision 4 alignment. This explicitly
amends the original cleanup rule: a replacement session is not allowed while
worker ownership or successful adapter closure remains unresolved. A single
owned residual supervisor retains that gate, without retry fan-out or a
false claim that cancellation forcibly kills a coroutine.

The design distinguishes a settled close attempt from confirmed successful
closure. A failed attempt permits at most one non-overlapping idempotent
retry; permanent failure stays fail closed. It preserves the original error
category and bounds handler waits while documenting potentially unresolved
resource lifetime. Repeated cancellation must not reintroduce the original
cleanup bug.

This is a technical amendment in the same local-only slice, not maintainer
approval or a roadmap gate change. The correction and regressions are now
implemented; the final review below supersedes the earlier HOLD.

## Final consolidated verdict (2026-11-11)

**PASS.** The reviewer independently ran `pytest apps/api -q`: 66 dots, exit 0,
matching the parent's [saved 66-test output](../implementation/evidence/voice-streaming-backend-2026-11-11.txt).
No confirmed blocker or major finding remained.

The focused review traced cleanup ownership, exactly-once gate release,
deadline preservation until cleanup settles, non-overlapping close attempts,
the one-retry limit, serialized final writes, preserved first cancellation,
and auth-before-adapter ordering. It found no logical failure in these paths.
The existing [frontend PASS](voice-streaming-frontend.md) remains valid; no
new frontend review cycle was opened.

| Correctness | Security | Honesty | Scope | Clarity | Average |
| --- | --- | --- | --- | --- | --- |
| 8.6 | 7.5 | 9.0 | 9.0 | 8.5 | 8.52 |

The reviewer logged three non-blocking observations: no direct assertion that
the completed-supervisor list drains, a wall-clock separator in the hanging-
close integration test, and no injected test of the supervisor's generic
exception path. These are recorded as U-07 to U-09 in the
[uncertainty log](voice-streaming-uncertain-findings.md), not new requirements.
The reported post-deadline cleanup resumption was examined: ownership is
retained and gate conditions are derived after the owning task settles.
The claimed Windows-specific cause remains unverified.

Within the focused review budget, not every API test body was read. No
hardware, live provider, build, or dependency audit was rerun by this reviewer.
Security is a code-review score, not R-01.6 acceptance. This verdict closes
the local code-review hold only; it is not PH-01 completion or ship approval.
