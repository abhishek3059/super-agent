# RT-003 — Native voice session

| Field | Value |
| --- | --- |
| Task ID | RT-003 |
| Status | not started |
| Execution evidence | none |

## Scope

Single manually activated native voice adapter and thin UI with indicators, backend control ownership, mic/playback stops, consent and failure behavior measured. No task workers or silent fallback.

## Non-goals

No task workers, no silent transport/provider fallback, no assumed native model access.

## Future owner

Implementation owner after RT-002 plus approved runtime grant.

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

None. Future task status is `not started`; no execution evidence exists.

## Navigation

- [Task index](README.md)
- [Phases](../phases.md)
- [Decisions](../descisions.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)
