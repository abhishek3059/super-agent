# RT-003 — Native voice session

| Field | Value |
| --- | --- |
| Task ID | RT-003 |
| Status | in progress; adapter and synthetic live check implemented, browser integration and acceptance incomplete |
| Execution evidence | [Gemini adapter record](../docs/implementation/r01-7-gemini-adapter.md); [synthetic live-check record](../docs/implementation/r01-8-live-check.md) |

## Scope

The Gemini Live adapter, offline tests, and one standalone synthetic real-service
run exist. The browser console still constructs the fake adapter, so the full
native path and its acceptance measurements are incomplete. The target remains
a manually activated path with indicators, backend control ownership,
mic/playback stops, and no task workers or silent fallback.

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
recorded above. The application still defaults to the fake adapter. R-01.4,
task completion, and RT-G01 remain open.

## Navigation

- [Task index](README.md)
- [Phases](../phases.md)
- [Decisions](../descisions.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)
