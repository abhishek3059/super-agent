# Frontend local streaming code review

| Field | Value |
| --- | --- |
| Date | 2026-11-10 |
| Reviewer | Separate `reviewer-free` subagent; returned its report without modifying files |
| Scope | Uncommitted frontend slice in PH-01 PR #24; initial 24-case, corrected 37-case, and final 39-case snapshots |
| Contract | [Streaming design](../design/voice-streaming-slice.md) revision 2, CT-11 to CT-15 |
| Reviewer verdict | Final PASS, 39 service cases and 8 epoch cases reproduced, average 8.8 |
| Parent disposition | Frontend code-review quality gate cleared; overall slice still waits for backend completion and required acceptance |
| Gate effect | None. Not independent security acceptance, hardware evidence, or PH-01 completion |

The parent saved this report from the reviewer's returned response. Backend
source and tests were excluded. The reviewer did not read or change the user's
Angular CLI analytics setting. Nothing was staged, committed, or pushed.

## Reproduced checks

The reviewer ran the existing epoch test (8 cases), actual-service test
(24 cases), and repository check. All passed. The repository check reported
75 Markdown files, 170 scanned files, 1100 local links, 259 fragment links,
and zero errors. The reviewer did not run the build, audit, backend tests,
microphone tests, or provider calls. The parent independently ran the build
and audit as recorded in the [implementation record](../implementation/voice-streaming-slice.md).

## Findings and required corrections

Line references below describe the reviewed source, before corrections.

| ID | Reviewer severity | Finding | Parent action |
| --- | --- | --- | --- |
| F-01 | MINOR, severity flagged for second opinion | `voice-session.service.ts:328`: a rejected or synchronously throwing `AudioContext.close()` can abort the cleanup tail, leave Start disabled, and produce an unhandled rejection. No regression test covered it. | Required correction: detach resources and publish final state deterministically; handle close errors without raw details; test rejection, throw, restart, and old-close isolation. |
| F-02 | MINOR, severity flagged for second opinion | `voice-session.service.ts:226-229`: context is not tracked until after two fallible audio-node factories. A factory exception can leak an audio context. | Required correction: register each owned resource before later fallible work; test both factory exceptions and recoverable cleanup. |
| F-03 | MINOR | The service tests do not invoke old socket handlers after Stop and replacement, although code inspection supports the guards. | Required regression: invoke captured old handlers and verify both identity guards and handler detachment. |
| F-04 | MINOR, flagged for second opinion | `voice-session.service.ts:53-61,331-332`: a muted session followed by deferred cleanup and immediate restart can retain frontend mute while the backend defaults to unmuted. | Required correction: reset mute for each valid new session and test muted restart while old close is pending. Invalid or busy Start must not mutate a current session. |
| F-05 | MINOR, flagged for second opinion | No suspended-state or `AudioContext.resume()` handling exists. A suspended context can appear to be listening without producing PCM. Real target-browser reachability was not established offline. | Required correction within the existing capture lifecycle: resume suspended contexts, guard async results, fail recoverably on rejection, and test Stop/restart during pending resume. |
| N-01 | NIT | Frontend output says cleanup detaches epochs, but the tracker is actually replaced in `start()`. | Correct the evidence wording. |
| N-02 | NIT | Mute is enabled during connecting and error, where the operation can silently do nothing. | Align the button's enabled states with an active capture session. |

The reviewer considered the generation/socket scheme, redaction allowlist,
per-session epoch reset, per-frame rate, stale-frame filtering, provisional
level meter, and existing barge-in tests sound. It reported no confirmed major
finding. The parent nevertheless treats the concrete cleanup and lifecycle
cases above as required work, not waived risks. Browser-specific likelihood
and severity are not asserted as measured facts.

Additional noted test gaps: error or interruption during pending microphone
permission, old playback before permission resolves, and handler teardown.
The correction assignment includes an error-during-permission regression.
Early audio dropping is disclosed behavior, not native-provider acceptance.

## Reviewer quality scores

| Correctness | Security | Honesty | Scope | Clarity | Average |
| --- | --- | --- | --- | --- | --- |
| 8 | 8 | 9 | 9 | 9 | 8.6 |

Security is a code-review score, not an independent security PASS. The review
and scores apply to the original 24-case frontend snapshot. Corrections and
their new tests require a fresh verdict before delivery.

## Correction status

The parent assigned these corrections to the same free frontend developer.
The correction round has returned, with 13 added service regressions. The
parent independently reproduced 37 passing service cases, 8 passing epoch
cases, a successful 115.94 kB frontend build, and zero audit findings. See the
[implementation record](../implementation/voice-streaming-slice.md) for the
real outputs. A fresh review is pending; the original PASS and scores above
do not certify this new snapshot. No acceptance item is newly ticked.

## Re-review of the 37-case correction snapshot

The same separate free reviewer reran all 37 service cases and 8 epoch cases.
It returned PASS for the corrected code: F-01 to F-05 and N-01/N-02 were
resolved, all 13 new cases were present, and the original 24 were not weakened.
It did not rerun build, audit, backend tests, or repository checks.

Two new minor honesty findings remained:

- The frontend output says a hung close is caught. It is not: rejection and
  throw are caught, while a hang is tolerated because UI state was finalized
  before the await. The browser resource may remain open.
- The local run instructions say Stop fully closes the audio context. The
  code attempts closure; failure or a hung promise cannot be claimed as
  successful release.

The reviewer also noted an empty heading, a stale 24-case count, inconsistent
F-03/F-04 numbering, and two transient ready-state labels. The parent assigned
correction of the prose and IDs, an OPEN-socket check after pending permission,
and preservation of `speaking` when playback exists as capture setup finishes.
The latter two get focused tests. This assignment does not add a provider or
change capture authority.

| Correctness | Security | Honesty | Scope | Clarity | Average |
| --- | --- | --- | --- | --- | --- |
| 9 | 8 | 7 | 9 | 8 | 8.2 |

Despite the code PASS, this average is below the delivery threshold. The
parent's disposition remains HOLD until the new corrections and fresh scores.

## Final frontend verdict (2026-11-10)

The free developer returned the final prose, ID, heading, and count fixes,
plus the two state-label guards with regression tests. The parent reproduced
39 passing service cases, 8 passing epoch cases, a successful 116.00 kB build,
and zero audit findings. The two added cases cover late permission on a
closing socket and preservation of speaking during deferred context resume.
The same separate free reviewer returned PASS for this final snapshot. It
reproduced 39 passing service cases, 8 passing epoch cases, and the repository
check (78 Markdown files, 1145 local links, zero errors, roadmap self-test
passed). It did not rerun the build or audit; those were independently run by
the parent as recorded above.

The reviewer verified the fixed cleanup claims, restored heading, historical
case counts, F-01 to F-05 meanings, post-await OPEN-socket guard, and speaking
state preservation during deferred resume. All previous findings were
resolved, and the two added tests genuinely exercise the corresponding code
changes. No blocker or major finding remained.

Two cosmetic nits remained in the output record: one shortened `F1 to F5`
reference and a non-sequential F-04/F-03 bullet order. The parent corrected
both without changing application code or test assertions.

| Correctness | Security | Honesty | Scope | Clarity | Average |
| --- | --- | --- | --- | --- | --- |
| 9 | 8 | 9 | 9 | 9 | 8.8 |

This clears the frontend code-review quality threshold. Security remains a
code-review score, not R-01.6 acceptance. Backend completion, independent
security and credential reviews, hardware evidence, and PH-01 gates remain
separate and open. No roadmap tick, commit, push, or merge accompanies this
verdict.
