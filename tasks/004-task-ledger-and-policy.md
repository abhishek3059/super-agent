# RT-004 — Task ledger and policy

| Field | Value |
| --- | --- |
| Task ID | RT-004 |
| Status | not started |
| Execution evidence | none |

## Scope

Small durable state/admission/idempotency/revision/budget contract with synthetic tests; no arbitrary tools or provider dependencies required for ledger tests.

## Non-goals

No arbitrary or generated code, unrestricted shell, external actions, or provider dependency is added or claimed here; ledger tests run on synthetic data only, and a ledger is not asserted to guarantee execution while the host sleeps.

## Future owner

Implementation owner after RT-002.

## Prerequisites

- [RT-002](002-local-scaffold-and-boundary.md).

## Inputs

Eight canonical job states plus idempotency, revision, budget, admission, and verified-receipt requirements.

## Deliverable

Small durable state/admission/idempotency/revision/budget contract with synthetic tests; no arbitrary tools or provider dependencies required for ledger tests.

## Acceptance

- Small durable state/admission/idempotency/revision/budget contract with synthetic tests delivered; no arbitrary tools or provider dependencies required for ledger tests: [REQ-05](../prd.md#req-05), [REQ-06](../prd.md#req-06), [REQ-09](../prd.md#req-09), [REQ-10](../prd.md#req-10); [DEC-04](../descisions.md#dec-04), [DEC-07](../descisions.md#dec-07), [DEC-09](../descisions.md#dec-09), [DEC-12](../descisions.md#dec-12).
- Application-owned ledger and verified receipts determine job progress and terminal outcomes, including cancellation and uncertainty: [REQ-05](../prd.md#req-05).

## Failure considerations

Ledger must not become a general scheduler; budgets must not be reset by revisions or steering.

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
