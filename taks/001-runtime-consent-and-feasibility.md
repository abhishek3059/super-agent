# RT-001 — Runtime consent and feasibility

| Field | Value |
| --- | --- |
| Task ID | RT-001 |
| Status | not started |
| Execution evidence | none |
| Revision 2 note | Corrections applied 2026-11-07 for independent review finding R-05 (see ../docs/reviews/super-agent.md): today's unset/unapproved values moved to a dated status note; future acceptance is now stated as truthful approval criteria. |

## Scope

Dated setup decision covering candidate eligibility/native access, account/region/quota/data/cost, named egress, budget, host, retention, and first real task pair; separate implementation authorization. No consent/access fabrication.

## Non-goals

No runtime implementation action, scaffold, or implementation authorization is granted by this task.

## Future owner

Implementation owner after separate implementation authorization; runtime gates RT-G00 remain blocking.

## Prerequisites

- Design signed: [docs/design/super-agent.md](../docs/design/super-agent.md).
- Independent review and design-stage security assessment dispositions supplied by the delivery manager.
- Separate implementation authorization.

## Inputs

Named microphone/context recipients, provider eligibility/account/region/quota/cost/data terms, retention/retry windows, host, monetary/resource limits, and first real task pair; all pending separate approval.

## Deliverable

A dated setup decision record.

## Current input and status (dated note, 2026-11-07)

As of this date: the monetary budget and bounded retention/retry limits **remain unset and unapproved**; the first real task pair is **not yet chosen**; recipients, eligibility, native access, account/region/quota/cost/data terms, and host facts are **unset and unverified**; no separate implementation authorization exists. No amount, free-tier assumption, or model-price inference authorizes runtime use. This is today's input state, not a future success criterion: it changes when the task runs, and the task is not started today.

## Acceptance

When this task runs (after separate implementation authorization), its deliverable is accepted only if the dated setup decision record is truthful and complete:

- Explicit approvals/eligibility facts are recorded as user decisions with dates: named runtime microphone/context recipients; provider eligibility and actual native access; account/region/quota/cost/data terms actually verified from the account/settings; the confirmed host; the selected first real task pair; an explicitly approved monetary budget and bounded retention/retry windows.
- Any item that is unresolved, refused, or decided against must keep the gate blocked and be recorded as such — never silently treated as success. Refusals and unresolved items are documented as the block on [RT-G00](../prd.md#rt-g00), with no approval invented ([REQ-13](../prd.md#req-13)); refusing to state a budget is itself an unresolved outcome that blocks the gate.
- External budgets and limits come from approvals external to any model/pricing inference ([DEC-12](../descisions.md#dec-12)); a free tier or price list is not an approval.
- Implementation authorization is a separate approval recorded alongside, or subsequent to, the setup decision; it is not implied by completing this task or by the setup decision itself.

Today, none of these criteria is met: the task is `not started` and no evidence exists yet. Record every acceptance item as a dated, sourced user decision in the deliverable record.

## Failure considerations

No consent, eligibility, access, budget, retention, or task-choice facts may be fabricated or asserted as existing.

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
