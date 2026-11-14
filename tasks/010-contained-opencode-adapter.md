# RT-010 — Contained OpenCode adapter

| Field | Value |
| --- | --- |
| Task ID | RT-010 |
| Status | not started |
| Execution evidence | none |

## Scope

Optional V2 adapter only inside demonstrated OS containment with least privilege, restricted credentials/egress, independent child-scope enforcement, event-gap reconciliation and version/capability tests.

## Non-goals

Not the assumed voice transport or sandbox; not enabled before demonstrated OS containment, egress, and child-scope tests. Prompt-level permissions are not OS containment.

## Future owner

Implementation owner after separate capability request and security design.

## Prerequisites

- Separate capability request and security design.

## Inputs

Separate capability request, security design, OpenCode V2 versions and containment evidence.

## Deliverable

Optional V2 adapter inside demonstrated OS containment; least privilege, restricted credentials/egress, independent child-scope enforcement, event-gap reconciliation and version/capability tests.

## Acceptance

- Optional V2 adapter delivered only inside demonstrated OS containment with least privilege, restricted credentials/egress, independent child-scope enforcement, event-gap reconciliation and version/capability tests; not the assumed voice transport or sandbox: [REQ-06](../prd.md#req-06), [REQ-08](../prd.md#req-08) through [REQ-12](../prd.md#req-12), [REQ-15](../prd.md#req-15); [DEC-14](../descisions.md#dec-14).

## Failure considerations

OpenCode remains optional and disabled until OS containment is independently tested.

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
