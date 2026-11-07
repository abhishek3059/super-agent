# RT-007 — Recovery and retention

| Field | Value |
| --- | --- |
| Task ID | RT-007 |
| Status | not started |
| Execution evidence | none |

## Scope

Reconciliation after event loss/disconnect/restart; stale commands/approvals rejected; no blind effects replay; bounded content/metadata purge and lost-context disclosure.

## Non-goals

No blind replay of effects under expired or superseded requests; retention purge stays within approved windows; no promise that durable records keep jobs running during host sleep/off.

## Future owner

Implementation owner after RT-006.

## Prerequisites

- [RT-006](006-steering-and-stop-controls.md).

## Inputs

Event loss/disconnect/restart, stale session/approval, retention, and reconciliation requirements.

## Deliverable

Reconciliation and retention behaviour for the future fixed slice.

## Acceptance

- Reconciliation after event loss/disconnect/restart delivered; stale commands/approvals rejected; no blind effects replay; bounded content/metadata purge and lost-context disclosure: [REQ-05](../prd.md#req-05), [REQ-06](../prd.md#req-06), [REQ-14](../prd.md#req-14), [REQ-18](../prd.md#req-18); [DEC-09](../descisions.md#dec-09), [DEC-10](../descisions.md#dec-10), [DEC-15](../descisions.md#dec-15).

## Failure considerations

Unknown outcomes must not be blindly replayed; retention windows must be approved before durable runtime starts.

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
