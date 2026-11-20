# RT-005 — Fixed sample workers

| Field | Value |
| --- | --- |
| Task ID | RT-005 |
| Status | in progress |
| Execution evidence | [PH-02 evidence record](../docs/implementation/ph02-ledger-evidence.md) |

## Scope

Two trusted bounded read-only synthetic workers, finite input/output, off-loop CPU execution, structured receipts/verification and overlap demonstration.

## Non-goals

Not an arbitrary-code security sandbox: worker threads/processes are a scheduling isolation, not host containment. No generated code, plugins, unrestricted shell, external actions, or real personal data; samples are illustrative only.

## Future owner

Implementation owner after RT-003 and RT-004.

## Prerequisites

- [RT-003](003-native-voice-session.md) and [RT-004](004-task-ledger-and-policy.md).

## Inputs

Two trusted fixed sample functions over a bundled synthetic dataset, with receipt/verification and overlap requirements.

## Deliverable

Two trusted bounded read-only synthetic workers, finite input/output, off-loop CPU execution, structured receipts/verification and overlap demonstration.

## Acceptance

- Two trusted bounded read-only synthetic workers with finite input/output, off-loop CPU execution, structured receipts/verification and overlap demonstration delivered: [REQ-04](../prd.md#req-04), [REQ-08](../prd.md#req-08); [DEC-05](../descisions.md#dec-05), [DEC-12](../descisions.md#dec-12).

## Failure considerations

Trusted fixed function is not an arbitrary-code sandbox; compute isolation is not credential/filesystem/network containment.

## Evidence

In progress. Evidence so far is in the [PH-02 evidence record](../docs/implementation/ph02-ledger-evidence.md). It is not complete: the real-model run for R-02.5 is pending. R-02.F3 is closed in its [record](../docs/implementation/r02-f3-ledger-paths.md).

## Navigation

- [Task index](README.md)
- [Phases](../phases.md)
- [Decisions](../descisions.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)
