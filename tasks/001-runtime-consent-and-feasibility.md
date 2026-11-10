# RT-001 — Runtime consent and feasibility

| Field | Value |
| --- | --- |
| Task ID | RT-001 |
| Status | in progress |
| Execution evidence | [PH-00 setup decisions](../docs/approvals/ph-00-setup-decisions.md); [RT-G00 resolution](../docs/approvals/rt-g00-resolution.md) pending merge |
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

This 2026-11-07 snapshot is historical. See the 2026-11-09 progress note below for current decisions.

## Evidence note (2026-11-09)

Partial feasibility evidence now exists in the [Gemini account verification](../docs/implementation/gemini-account-verification.md): model access is verified for the maintainer's free-tier key, region support appears confirmed, and the data terms are recorded. Quota, billing, runtime consent, budget, host, and retention were still unresolved on that date. This task moved to `in progress` on 2026-11-09; see the setup decision progress note below.

## Setup decision progress (2026-11-09)

The operator recorded the PH-00 setup decisions in the
[PH-00 setup decisions](../docs/approvals/ph-00-setup-decisions.md):

- First real task pair: local document summary and action-item extraction.
- Retention: job metadata deleted 24 hours after terminal state; no raw audio,
  transcripts, or model-content logs.
- Retries: at most 2 automatic retries for idempotent read-only steps; no retry
  after an unknown outcome.
- Hosts: Windows and macOS.
- PH-01 authorization: offline work plus the Gemini Live adapter and an opt-in
  synthetic-audio test; personal microphone audio stays local.
- Secret setup: `GEMINI_API_KEY` set in an interactive PowerShell process
  environment on 2026-11-09; the variable is session-scoped and not visible to
  the agent process.
- Budget: $0 cap with no paid fallback.

This task is `in progress`. The setup decision record merged in PR #21.
RT-G00 is not resolved until the [resolution record](../docs/approvals/rt-g00-resolution.md)
merges and the follow-up roadmap evidence is added. The secret setup is
confirmed for the operator's shell; the live test must run there.

## Acceptance

When this task runs (after separate implementation authorization), its deliverable is accepted only if the dated setup decision record is truthful and complete:

- Explicit approvals/eligibility facts are recorded as user decisions with dates: named runtime microphone/context recipients; provider eligibility and actual native access; account/region/quota/cost/data terms actually verified from the account/settings; the confirmed host; the selected first real task pair; an explicitly approved monetary budget and bounded retention/retry windows.
- Any item that is unresolved, refused, or decided against must keep the gate blocked and be recorded as such — never silently treated as success. Refusals and unresolved items are documented as the block on [RT-G00](../prd.md#rt-g00), with no approval invented ([REQ-13](../prd.md#req-13)); refusing to state a budget is itself an unresolved outcome that blocks the gate.
- External budgets and limits come from approvals external to any model/pricing inference ([DEC-12](../descisions.md#dec-12)); a free tier or price list is not an approval.
- Implementation authorization is a separate approval recorded alongside, or subsequent to, the setup decision; it is not implied by completing this task or by the setup decision itself.

The sentence in the original 2026-11-07 task template that said none of these
criteria was met is historical. The merged 2026-11-09 setup decisions now
cover the criteria. Final gate resolution remains pending as stated above.

## Failure considerations

No consent, eligibility, access, budget, retention, or task-choice facts may be fabricated or asserted as existing.

## Evidence

Merged setup decision record: [PH-00 setup decisions](../docs/approvals/ph-00-setup-decisions.md).
No runtime gate is closed by this open change. Secret setup is confirmed. The
final RT-G00 resolution and follow-up roadmap evidence are still pending.

## Navigation

- [Task index](README.md)
- [Phases](../phases.md)
- [Decisions](../descisions.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)
