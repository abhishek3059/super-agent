# RT-003 — Native voice session

| Field | Value |
| --- | --- |
| Task ID | RT-003 |
| Status | in progress; adapter, synthetic live check, and opt-in console wiring implemented, native measurements through the application missing |
| Execution evidence | [Gemini adapter record](../docs/implementation/r01-7-gemini-adapter.md), [synthetic live-check record](../docs/implementation/r01-8-live-check.md), [local microphone test](../docs/approvals/r01-4-microphone-test.md), [criteria table](../docs/implementation/r01-10-acceptance.md#criteria-and-evidence), [offline re-run, 2026-11-15](../docs/implementation/evidence/r01-10-offline-suites-20261115.txt) |

## Scope

The Gemini Live adapter, offline tests, and one standalone synthetic real-service
run exist. Since [PR #41](https://github.com/abhishek3059/super-agent/pull/41)
the browser console can construct the adapter with `SUPER_AGENT_ADAPTER=gemini`,
for maintainer testing under the
[testing exception](../docs/approvals/gemini-live-testing-exception.md); the
fake adapter stays the default. No saved measurement covers the native path
through the console. The target remains a manually activated path with
indicators, backend control ownership, mic/playback stops, and no task workers
or silent fallback.

## Non-goals

No task workers, no silent transport/provider fallback, no assumed native model access.

## Owner

PH-01 implementation owner under the approved sequencing record. Final
acceptance still depends on RT-002 and RT-G01.

## Prerequisites

- [RT-002](002-local-scaffold-and-boundary.md) plus approved runtime grant.

## Inputs

Approved runtime grant, native transport adapter, backend control channel design, mic/playback stop semantics.

## Deliverable

Single manually activated native voice adapter and thin UI with indicators, backend control ownership, mic/playback stops, consent and failure behavior measured; no task workers or silent fallback.

## Acceptance

- Single manually activated native voice adapter and thin UI delivered with indicators, backend control ownership, mic/playback stops, consent and failure behavior measured; no task workers or silent fallback: [REQ-01](../prd.md#req-01) through [REQ-03](../prd.md#req-03), [REQ-15](../prd.md#req-15); [DEC-02](../descisions.md#dec-02), [DEC-03](../descisions.md#dec-03), [DEC-06](../descisions.md#dec-06), [DEC-08](../descisions.md#dec-08).
- Native audio path requires manual setup then active hands-free interaction within an authenticated session; no mandatory external STT/chat/TTS chain and no silent provider fallback: [REQ-02](../prd.md#req-02).

## Failure considerations

No silent transport/provider fallback; no assumed native model access; no task workers.

## Evidence

The Gemini Live adapter, offline tests, and one synthetic real-service run are
recorded above. The R-01.4 test covers the earlier local console at `a790530`
with the fake adapter. The operator reported a live Gemini session through the
console in the PR #41 description; the output was not saved, so it is not
counted. The [R-01.10 record](../docs/implementation/r01-10-acceptance.md)
holds the criterion-by-criterion table:

- Met offline: no silent fallback (unknown adapter or missing key refuses to
  start), fail-closed unsupported model, provider-mismatch refusal, local stop
  and interruption ordering at the bridge.
- Missing: native stop, interruption, and visible-state behavior measured
  through the application, and the revised synthetic live run with barge-in.

Task completion and RT-G01 remain open.

## Navigation

- [Task index](README.md)
- [Phases](../phases.md)
- [Decisions](../descisions.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)
