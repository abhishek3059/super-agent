# Super-agent — workflows and state transitions (documentation pack)

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Revision | 4 |
| Status | Documentation-only workflow contract; no runtime workflow exists |
| Revision 4 note | Documentation-acceptance traceability and privacy clarifications applied 2026-11-07, acting on the design review PASS and the design-stage security PASS for the previously assessed revision: WF-01 additionally cites [RT-A05](prd.md#rt-a05) (security report INFO-02), and WF-07 explicitly clears locally held ephemeral transcript context at session end (INFO-03). No workflow semantics, job states, or runtime claims are changed. |

This document expands the signed design's workflow contract into numbered Markdown workflows. State tables are used rather than generated assets or diagram artifacts.

## Navigation

- [Signed design](docs/design/super-agent.md)
- [Delivery status](docs/delivery/super-agent.md)
- [Discovery brief](docs/delivery/super-agent-brief.md)
- [Council deliberation](docs/delivery/council.md)
- [Requirements](prd.md)
- [Architecture](architecture.md)
- [Decisions](descisions.md)
- [Phases](phases.md)
- [Progress](progress.md)
- [Build](build.md)
- [Flow](flow.md)
- [Tasks](tasks/README.md)
- [Council meetings](council%20meetings/README.md)
- [Implementation report](docs/implementation/super-agent.md)

## How to read the workflows

Each workflow names: actor, input, policy preconditions, ledger transition, output, failure path, and acceptance links.

Canonical job states are owned by [architecture](architecture.md); this document applies them.

## Workflow register

### WF-01 Setup and manual activation

User/device authentication, named native/provider/context consent, eligibility/access/cost/retention review and grants precede session creation. User manually permits microphone and activates the browser session. Controls/health checks are ready before upload.

Any failed prerequisite keeps microphone transmission off; no alternate cloud or text-voice fallback.

- Actor: user, performing device/session authentication and manual activation.
- Policy preconditions: named native/provider/context consent; eligibility/access/cost/retention review and grants precede session creation; user manually permits microphone.
- Ledger transition: none; no job is created during setup.
- Output: a manually activated authenticated browser session; controls/health checks ready before microphone upload.
- Failure path: any failed prerequisite keeps microphone transmission off; no alternate cloud or text-voice fallback.
- Acceptance references: [RT-A01](prd.md#rt-a01) (native and consent), [RT-A02](prd.md#rt-a02) (responsiveness and playback), [RT-A05](prd.md#rt-a05) (authority and local attack surface).

### WF-02 Native conversation and two sample jobs

Native input/output continues directly. Backend assembles conservative transient task context, validates a fixed proposal, reserves limits, journals it, returns job IDs, and dispatches bounded workers off the audio/control loop. Results are verified and committed before concise completion facts are sent at an appropriate idle boundary.

- Actor: user speaking; backend conversation coordinator, policy/admission broker, task service, and fixed worker executor.
- Policy preconditions: active authenticated native session with named consent; proposal validated against fixed capability/dataset scope; limits and budgets available to reserve.
- Ledger transition: validated proposal admitted as a durable queued job with stable request/job IDs and a reservation; then `running` while a leased approved action executes.
- Output: job IDs returned promptly; verified results committed to the ledger before concise completion facts are spoken at an appropriate idle boundary.
- Failure path: invalid or unadmittable proposals fail closed without dispatch (WF-09); uncertain or unverified outcomes are never spoken as success.
- Acceptance references: [RT-A02](prd.md#rt-a02) (responsiveness and playback), [RT-A03](prd.md#rt-a03) (task truth and bounded work).

### WF-03 Barge-in stop speech

Detect/accept the interruption, advance speech epoch, gate/drop stale player output, and invoke verified conversational interruption semantics. Job state is unchanged.

A provider acknowledgment is not proof that the user heard silence or that jobs stopped.

- Actor: user interrupting; browser player/controls and native transport adapter.
- Policy preconditions: active session with ongoing speech or playback; interruption actually requested/accepted rather than merely detected by the provider.
- Ledger transition: none; job state is unchanged by stopping speech.
- Output: stale player output gated/dropped; playback/voice epoch advanced; verified conversational interruption invoked through the provider adapter.
- Failure path: a provider acknowledgment is not proof of silence or job stop; stale output must not replay after the new epoch.
- Acceptance references: [RT-A02](prd.md#rt-a02) (responsiveness and playback).

### WF-04 Steer a named job

Resolve an unambiguous job/revision; clarify ambiguous references. Admit only bounded changes within the existing grant. Record a new revision and retire/cancel superseded execution safely.

Late old results cannot become new-revision answers.

- Actor: user steering; conversation coordinator, broker, and task service.
- Policy preconditions: unambiguously named job and current revision; ambiguous references are clarified first; changes bounded within the existing grant.
- Ledger transition: atomically record a new job revision for admitted changes; superseded execution is retired or cancelled safely.
- Output: revised task continues under the new revision; old-revision results preserved as evidence but never presented as current answers.
- Failure path: stale, conflicting, or out-of-scope changes are rejected; completed effects are not claimed to be undone; in-flight replacement may require cancellation/reconciliation first.
- Acceptance references: [RT-A04](prd.md#rt-a04) (duplicates, races and recovery).

### WF-05 Cancel a named job

Record `cancel_requested`, signal/check the worker, then establish `cancelled`, a raced terminal outcome, or `unknown` from evidence. Speak "cancellation requested" before stop confirmation, not "cancelled" prematurely.

- Actor: user cancelling a named job; task service and bounded worker executor.
- Policy preconditions: unambiguous job identified; duplicate cancellation requests are harmless.
- Ledger transition: `cancel_requested` durably recorded against the current revision; worker stop signalled and checked.
- Output: `cancelled`, a raced terminal `succeeded`/`failed` outcome, or `unknown`, established from evidence.
- Failure path: without stop/non-execution evidence the outcome is not established; speech says "cancellation requested" before any confirmation, never "cancelled" prematurely.
- Acceptance references: [RT-A04](prd.md#rt-a04) (duplicates, races and recovery).

### WF-06 Mic-stop pause

Local UI immediately stops microphone transmission and discards unsent audio. Provider muting alone is insufficient.

Job grants, audio output, and worker/model-context egress have separate controls; disclose which remain active.

- Actor: user; browser audio/control UI.
- Policy preconditions: active microphone transmission within an authenticated session; truthful listening/cloud state visible.
- Ledger transition: none required; any jobs that continue do so only within independently valid background grants, and this is disclosed.
- Output: local capture/transmission stops and unsent buffers are discarded before provider-side effects; truthful disconnected/paused status is shown.
- Failure path: provider-side muting alone is insufficient; resume requires current authenticated consent and deliberate activation; paused speech is not buffered for later upload.
- Acceptance references: [RT-A02](prd.md#rt-a02) (responsiveness and playback), [RT-A06](prd.md#rt-a06) (privacy, budgets and lifecycle).

### WF-07 Emergency stop

Local controls stop microphone/playback even if the backend/provider is unhealthy. Backend latches off new sessions/jobs/steps, revokes execution grants, cancels running work, and reconciles.

Session-end privacy: ending the native transport also clears locally held ephemeral transcript/conversation context, applying the same rules as [WF-10](#wf-10-retention-session-end-and-host-lifecycle). Local stopping and clearing take effect even while offline; backend/provider-side cleanup cannot be confirmed while the backend is unreachable, and no provider log deletion is claimed. This stop introduces no new recording, retention, or authority.

Keep uncertain outcomes explicit.

- Actor: user; local UI, then backend broker/task service.
- Policy preconditions: authenticated local controls; the latch and revocation proceed even when the backend/provider connection is unhealthy.
- Ledger transition: admission/dispatch latched off; applicable execution grants revoked; running work cancellation requested and then reconciled.
- Output: microphone transmission and playback stop locally, and locally held ephemeral transcript context is cleared; all-job cancellation requested, outcomes and uncertainties verified/reported.
- Failure path: uncertain outcomes stay explicit; no spoken "yes" clears the latch or grants new power; manual authenticated re-arm is required. Even offline, local stopping and context clearing apply, while backend/provider-side cleanup cannot then be confirmed and no provider log deletion is claimed.
- Acceptance references: [RT-A05](prd.md#rt-a05) (authority and local attack surface).

### WF-08 Disconnect, replacement session, and restart

Freeze stale-session commands/output; persist job truth; invalidate interrupted approvals. Reconcile a scoped snapshot and current grants before any resumed task work.

New native session gets minimized current facts and only allowed transient history, not raw persisted transcripts or repeated actions.

- Actor: backend task service and native transport adapter during disconnect/session replacement or backend restart.
- Policy preconditions: stale/closed session detected; a new session must be recreated, not silently continued.
- Ledger transition: job truth preserved in the ledger; interrupted approvals invalidated; backend restart reconciles previously running/cancel_requested work before scheduling it; recovery to queued only via a journaled safe decision.
- Output: a reconciled scoped snapshot and current grants resume work; the new native session receives minimized current facts and only allowed transient history.
- Failure path: stale-session commands and output are rejected, superseded outputs cannot become current answers, and re-subscription is not replay, replay of actions, or guaranteed acoustic continuity.
- Acceptance references: [RT-A04](prd.md#rt-a04) (duplicates, races and recovery).

### WF-09 Denied scope, injection, or exhausted budget

Malformed/oversized/out-of-scope/expired/over-budget proposals fail closed without dispatch.

Treat audio, native transcripts, documents, pages, and worker output as data, not grant instructions.

- Actor: policy/admission broker on behalf of the task service.
- Policy preconditions: any submitted proposal is untrusted until validated against schema, size, scope, grant/policy version, revision, expiry, and budget.
- Ledger transition: no dispatch and no admission; denial metadata is recorded.
- Output: the denial is explained without inventing a completed task; failing closed is the success path of this workflow.
- Failure path: audio, native transcripts, documents, pages, and worker output are treated as data, not grant instructions; injected content never elevates authority or bypasses external limits.
- Acceptance references: [RT-A05](prd.md#rt-a05) (authority and local attack surface).

### WF-10 Retention, session end, and host lifecycle

End native audio and clear ephemeral transcript context; keep only bounded approved task evidence. Purge content and eventually dedup metadata under explicit windows; reject expired retries.

Record unfinished shutdown/usage reconciliation honestly.

- Actor: backend task service and retention policy at session end or on a retention window.
- Policy preconditions: explicit approved retention/deletion windows exist before durable runtime content can be retained; local defaults keep recordings/transcripts off.
- Ledger transition: ephemeral transcript context cleared; content and eventually dedup metadata purged under explicit windows; expired retries rejected after purge instead of treated as new intent.
- Output: only bounded approved task evidence remains; unfinished shutdown/usage reconciliation is recorded honestly, not claimed clean.
- Failure path: purge cannot erase provider-retained content; sleep/off stops local execution and an approved always-on host is a different deployment decision, not a property of this workflow.
- Acceptance references: [RT-A06](prd.md#rt-a06) (privacy, budgets and lifecycle).

## State and transition summary

See the canonical job states in [architecture](architecture.md).

States include `queued`, `running`, `waiting_for_approval`, `cancel_requested`, `succeeded`, `failed`, `cancelled`, and `unknown`.

Stop and cancellation semantics:

- Stopping speech does not cancel jobs.
- Cancelling a job records `cancel_requested` and resolves only from evidence.
- Unknown outcomes block unsafe further dispatch and are not blindly replayed.

Host lifecycle: sleep/off stops local execution; durable records do not promise execution during sleep/off.


