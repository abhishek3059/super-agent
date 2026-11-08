# RT-006 — Steering and stop controls

| Field | Value |
| --- | --- |
| Task ID | RT-006 |
| Status | not started |
| Execution evidence | none |

## Scope

Named-job revisions/cancellation plus distinct speech/mic/emergency semantics, cancellation races and partial-result reporting, held notifications and stale output checks.

## Non-goals

Stopping speech, cancelling a job, stopping microphone upload, and emergency stop remain distinct operations; cancellation does not undo completed effects, and these controls do not create new authority or enable high-risk tools.

## Future owner

Implementation owner after RT-005.

## Prerequisites

- [RT-005](005-fixed-sample-workers.md).

## Inputs

Named-job steering/cancellation requirements plus distinct stop semantics.

## Deliverable

Named-job revisions/cancellation plus distinct speech/mic/emergency semantics, cancellation races and partial-result reporting, held notifications and stale output checks.

## Acceptance

- Named-job revisions/cancellation plus distinct speech/mic/emergency semantics, cancellation races and partial-result reporting, held notifications and stale output checks delivered: [REQ-03](../prd.md#req-03), [REQ-07](../prd.md#req-07), [REQ-09](../prd.md#req-09); [DEC-07](../descisions.md#dec-07), [DEC-08](../descisions.md#dec-08), [DEC-09](../descisions.md#dec-09).

## Failure considerations

Stopping speech cannot undo completed effects; provider mute is not a local mic-stop.

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
