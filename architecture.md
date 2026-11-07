# Super-agent — proposed architecture (documentation pack)

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Revision | 1 |
| Status | Proposed future architecture; no component exists |
| Signed design | [docs/design/super-agent.md](docs/design/super-agent.md), revision 1 |

This document describes a proposed future logical architecture. It asserts no existing API, component, control, or test.

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

## Scope and evidence classes

All components below are provisional. Proposed field responsibilities are conceptual contracts, not existing APIs or code signatures.

## Proposed logical components

| Logical component | Owns | Does not own / boundary |
| --- | --- | --- |
| Browser audio/control UI | Manual activation, browser permission, native media tracks, listening/cloud indicator, player gating, speech epochs, accessible stop/mic/emergency controls. | No long-lived keys, grant creation by voice, host tools, authoritative job state, or recording persistence. |
| Native transport adapter | Verified native media/session configuration, provider lifecycle/events, backend control-channel health, usage observations, translation to conceptual conversation events. | No action authorization, worker execution, or assumed cross-provider failover. Exact vendor event mapping is untested. |
| Conversation coordinator | Ephemeral native transcript context where required, task/delegation correlation, turn/playback bookkeeping, bounded factual status requests, notification scheduling. | No durable conversational transcript or authority based on spoken "yes"; model narration is not execution evidence. |
| Policy/admission broker | Authenticated subject/grants; typed proposal validation; fixed dataset/tool scope; egress, size, deadline, step/retry/concurrency/spend checks; revocation and emergency admission latch. | No trust in prompts as enforcement, and no approvals of initially disabled consequential capabilities. |
| Task service and tiny ledger | Job IDs, current revisions/states, request/action deduplication, intent/receipt records, leases, budget reservations/usage, cancellation truth, reconciliation, retention and purge metadata. | Not a general scheduler/agent fleet or guaranteed execution when the host sleeps. |
| Bounded trusted worker executor | Only approved fixed functions, finite inputs, cooperative cancellation, isolated CPU execution from the audio/control event loop, structured receipts. | A worker thread/process used for responsiveness is not an arbitrary-code security sandbox. No generated code, plugins, unrestricted shell, or external actions. |
| Result verifier / notification coordinator | Check worker evidence against the task specification/revision; persist outcomes; send concise allowed facts when conversation policy permits; track publication versus playback separately. | No successful-job assertion from model confidence, an append acknowledgment, or a late superseded result. |
| Future bounded planner / contained adapters | Later typed multi-step proposals, checkpointed reasoning, and individually approved worker capabilities, through the same broker/ledger. | Not part of the deterministic proof; no capability expansion through delegation. OpenCode remains optional and disabled until OS containment is independently tested. |

## Data paths

- **Native audio:** after authenticated setup and named consent, browser microphone media goes to the approved native provider and native output returns to the browser player. No obligatory text reasoning service or TTS lies in this audio path.
- **Control/tasks:** backend-owned native events and authenticated local control requests become untrusted proposals; broker validation precedes ledger admission; executor receipts are verified and journaled; only minimized factual summaries return to the native conversation.

Browser-direct media egress and backend/worker context egress are distinct recipient/consent boundaries.

## Conceptual records and interfaces

| Conceptual record | Minimum contents / invariants |
| --- | --- |
| Authenticated grant | Subject/device session, allowed fixed capability/dataset IDs, named recipients, grant/policy version, expiry, budget scope, and revocation status. Credentials are external references, never secret values. Voice cannot expand it. |
| Task proposal | Client intent/request ID, authenticated subject, originating session epoch, desired fixed operation, bounded structured arguments, target job/current revision for steering, required scope, and deadline/budget request. Provider delegation ID is correlation metadata, not authorization. |
| Task record | Stable job ID, request ID, current revision, state, minimal approved input/specification, grant/policy references, timestamps/deadline/lease, reservations/usage and limits, cancellation request/acknowledgment, outcome/evidence reference, retention metadata. No raw transcript, audio, secret, or full model reasoning. |
| Action/attempt record | Stable action ID and bounded attempt number tied to job/revision; validated operation and argument digest; pre-dispatch intent; worker receipt; observed outcome and partial-effect information; retry/reconciliation disposition. |
| Worker receipt | Job/revision/action IDs, executed fixed function, actual start/finish/stop observations, bounded structured output, verification evidence, failure/partial-effect/cancellation facts. Treat it as untrusted until checked against the admitted action. |
| Notification record | Job and revision, verified state/evidence reference, recipient/session epoch, publication ID, whether announced or held/interrupted, and observed playback disposition where available. "Published" and "heard" are different facts. |

Conceptual operations include start native session, propose/create task, read task snapshot, revise/steer task, request job cancellation, stop speech, stop microphone upload, emergency stop, and reconcile/purge.

## Distinct stop semantics

- Stop speech advances the playback epoch and gates/drops stale output only; it does not change job state, and a provider interruption acknowledgment is not proof that the user heard silence or that jobs ended.
- Cancel a named job records `cancel_requested` and resolves `cancelled`, a raced terminal outcome, or `unknown` only from durable evidence; it does not undo effects completed before the stop.
- Stop microphone upload immediately stops local transmission/capture and discards unsent buffers; provider-side muting alone is insufficient, and jobs continue only within independently valid background grants.
- Emergency stop latches admission/dispatch off, revokes applicable execution grants, stops microphone transmission and playback, closes the native transport, requests and verifies all-job cancellation, and requires manual authenticated re-arm.

For native delegation flows, the backend sideband is the sole execution and result-update owner; browser event echoes are captions/control requests, not a second worker executor or trusted task-state writer. Attach/control access and client permissions need deployed verification, and execution fails closed if the required backend control channel is not healthy.

## Canonical job states

Eight canonical states are defined. `architecture.md` owns this canonical state table; `flow.md` and the task files link to it.

| State | Definition | Allowed next states and evidence |
| --- | --- | --- |
| `queued` | Validated bounded job admitted with a reservation; no worker has been dispatched yet. | `running` after atomic lease/admission recheck; `cancel_requested` on cancellation; `failed` on a verified admission/deadline failure; `waiting_for_approval` only at a configured authenticated grant checkpoint. |
| `running` | A leased approved action is executing against the current job revision. | `succeeded` / `failed` with verified receipts; `cancel_requested`; `unknown` if lease/connection loss makes execution outcome uncertain; `waiting_for_approval` only after a safe checkpoint with no further dispatch. |
| `waiting_for_approval` | Work is blocked at an explicitly configured authenticated checkpoint; no further effects may execute. | `queued` only after valid exact approval/grant revalidation; `cancel_requested` on withdrawal; `failed` on denial/expiry. No queued action is implicitly approved by reconnect or ambient speech. |
| `cancel_requested` | A cancellation intent is durably recorded; worker stop is not yet proven. | `cancelled` after evidence of non-execution or acknowledged stop; `succeeded` / `failed` if verified terminal work won the race; `unknown` if the outcome cannot be established. |
| `succeeded` | Current-revision required results are verified. Existing completed effects remain facts even if speech was interrupted. | Terminal for that revision. A changed request uses a new explicitly admitted revision/job, not rewriting history. |
| `failed` | Verified failure/deadline/policy outcome, with any known partial effects disclosed. Failure does not mean all effects were rolled back. | Terminal for that revision; a permitted retry is separately journaled and bounded, not an untracked rerun. |
| `cancelled` | Future work stopped or never ran, supported by evidence. Preserve/report any work or effects completed before the stop. | Terminal for that revision. Cancellation is not automatic rollback. |
| `unknown` | The application cannot prove execution/stop/outcome. Block unsafe further dispatch and say that uncertainty plainly. | `succeeded`, `failed`, or `cancelled` only on reconciliation evidence. Recovery to `queued` requires a journaled policy decision proving non-execution or safe read-only/idempotent retry, valid grants and budget; never blindly replay an uncertain mutation. |

### Queued

Validated bounded job admitted with a reservation; no worker has been dispatched yet.

### Running

A leased approved action is executing against the current job revision.

### Waiting for approval

Work is blocked at an explicitly configured authenticated checkpoint; no further effects may execute.

### Cancel requested

A cancellation intent is durably recorded; worker stop is not yet proven.

### Succeeded

Current-revision required results are verified. Existing completed effects remain facts even if speech was interrupted.

### Failed

Verified failure/deadline/policy outcome, with any known partial effects disclosed.

### Cancelled

Future work stopped or never ran, supported by evidence. Preserve/report any work or effects completed before the stop.

### Unknown

The application cannot prove execution/stop/outcome. Block unsafe further dispatch and say that uncertainty plainly.

## Idempotency, revisions, and uncertainty

1. Bind client intent IDs to subject, validated specification, and a bounded retry window. Reject the same ID with changed parameters.
2. Enforce unique request/action IDs in the ledger. Repeated create, revise, and cancellation requests return current recorded disposition.
3. Increment job revision on accepted steering. Before each step/result commit, compare current revision, grant/policy version, deadline, emergency latch, and lease.
4. A voice-session epoch is not a job ID or task revision. Reject delayed commands from stale/closed sessions.
5. Chargeable session creation also needs local intent deduplication and conservative uncertain-start handling.
6. On backend restart, re-read records and reconcile previously `running` / `cancel_requested` work before scheduling it. The ledger preserves evidence, not the executing process. Terminal receipt and cancellation races are resolved by facts, not by whichever narration arrives last.
7. A voice-session epoch is not a job ID or task revision. Old audio/notification epochs never resume playback after a barge-in, stop, or replacement session, and delayed commands from stale/closed sessions are rejected.
8. Do not assume a provider honors an idempotency header or that SDK automatic retries are safe. Verify the deployed provider contract before enabling retries; otherwise report uncertain startup/charges instead of repeatedly creating sessions.

## Security, budgets, retention, and limits

- Serve the first UI and API from one deliberately chosen loopback origin. Authenticate setup using a locally established device/session credential outside project documents.
- Restrict listener addresses and accepted Host values to configured loopback hosts/ports. Check exact allowed Origin for browser mutations and WebSocket handshakes; apply CSRF defense to cookie-authenticated mutations and authenticate/authorize WebSocket messages as well as their upgrade.
- No permanent secrets in URLs, browser storage, provider/model prompts, task records, telemetry, or repository files. Future backend credentials come from an OS vault or externally injected environment.
- Validate message/schema/content type, sizes, rates, fixed capability and dataset IDs, deadlines, request revisions, and recipient scope. Initial workers accept synthetic dataset identifiers, not model-selected arbitrary paths or URLs.
- Deny worker/tool network egress by default. Initial fixed sample workers have no network capability.
- Keep the browser frontend thin, without unnecessary third-party scripts/content.
- Trusted worker bugs remain a risk; "fixed function" is a narrowed reviewed capability, not protection against arbitrary code with host authority.
- External budgets and admission limits (aggregate concurrency, steps, retries, deadlines, and spend) are enforced by the broker and ledger outside models; numeric targets remain provisional until approved/measured, and provider usage/finalization uncertainty is recorded and conservatively blocks further spending rather than claiming perfect billing control.

## Deferred adapter seams

- OpenCode V2 may later be an OS-contained worker adapter, not the assumed voice transport or sandbox.
- Future private inference must be genuinely native and enforce egress boundaries.
