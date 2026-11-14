# Super-agent — runtime task index (`tasks/`)

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Revision | 2 |
| Status | RT-001 complete; RT-002 and RT-003 in progress; RT-004 and later tasks `not started` |

This index covers runtime implementation tasks. It does not cover the authoring
of the original documentation pack.

Creating a task Markdown file does not start or authorize implementation.

## Navigation

- [Signed design](../docs/design/super-agent.md)
- [Delivery status](../docs/delivery/super-agent.md)
- [Discovery brief](../docs/delivery/super-agent-brief.md)
- [Council deliberation](../docs/delivery/council.md)
- [Requirements](../prd.md)
- [Decisions](../descisions.md)
- [Architecture](../architecture.md)
- [Phases](../phases.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Council meetings](../council%20meetings/README.md)
- [Implementation report](../docs/implementation/super-agent.md)

## Task index

| Task ID | Exact file | Scope | Phase / requirements / decisions | Status |
| --- | --- | --- | --- | --- |
| [RT-001](001-runtime-consent-and-feasibility.md) | 001-runtime-consent-and-feasibility.md | Dated setup decision covering candidate eligibility/native access, account/region/quota/data/cost, named egress, budget, host, retention, and first real task pair; separate implementation authorization. No consent/access fabrication. | REQ-13, REQ-14, REQ-17; DEC-06, DEC-10, DEC-16; RT-G00 | complete |
| [RT-002](002-local-scaffold-and-boundary.md) | 002-local-scaffold-and-boundary.md | Reviewed local streaming scaffold, dependency/command contract, credentials, and loopback HTTP/WS boundary; final task and gate acceptance remain open. | RT-001 and explicit scaffold authority; REQ-11, REQ-12; DEC-03, DEC-11, DEC-16 | in progress, not accepted |
| [RT-003](003-native-voice-session.md) | 003-native-voice-session.md | Gemini adapter, synthetic live check, and local microphone evidence exist. Browser-provider integration and native-path acceptance remain incomplete. | RT-002 plus approved runtime grant; REQ-01-REQ-03, REQ-15; DEC-02, DEC-03, DEC-06, DEC-08 | in progress, not accepted |
| [RT-004](004-task-ledger-and-policy.md) | 004-task-ledger-and-policy.md | Small durable state/admission/idempotency/revision/budget contract with synthetic tests; no arbitrary tools or provider dependencies required for ledger tests. | RT-002; REQ-05, REQ-06, REQ-09, REQ-10; DEC-04, DEC-07, DEC-09, DEC-12 | not started |
| [RT-005](005-fixed-sample-workers.md) | 005-fixed-sample-workers.md | Two trusted bounded read-only synthetic workers, finite input/output, off-loop CPU execution, structured receipts/verification and overlap demonstration. | RT-003-RT-004; REQ-04, REQ-08; DEC-05, DEC-12 | not started |
| [RT-006](006-steering-and-stop-controls.md) | 006-steering-and-stop-controls.md | Named-job revisions/cancellation plus distinct speech/mic/emergency semantics, cancellation races and partial-result reporting, held notifications and stale output checks. | RT-005; REQ-03, REQ-07, REQ-09; DEC-07-DEC-09 | not started |
| [RT-007](007-recovery-and-retention.md) | 007-recovery-and-retention.md | Reconciliation after event loss/disconnect/restart; stale commands/approvals rejected; no blind effects replay; bounded content/metadata purge and lost-context disclosure. | RT-006; REQ-05, REQ-06, REQ-14, REQ-18; DEC-09, DEC-10, DEC-15 | not started |
| [RT-008](008-runtime-validation.md) | 008-runtime-validation.md | Measured native/overlap/control/negative/security/privacy/budget evidence for the fixed slice, actual distributions/failures, and independent implementation review/security assessment. | RT-007; RT-A01-RT-A06; REQ-17; DEC-11, DEC-12 | not started |
| [RT-009](009-bounded-real-task-planner.md) | 009-bounded-real-task-planner.md | Separately approved planner/worker increment for one real task pair; typed bounded steps, checkpointed steering, verifier evidence and comparative usefulness versus fixed baselines. No high-risk authority by voice. | Accepted fixed-slice evidence, real-task/capability/recipient grants; REQ-09, REQ-10, REQ-16; DEC-07, DEC-13 | not started |
| [RT-010](010-contained-opencode-adapter.md) | 010-contained-opencode-adapter.md | Optional V2 adapter only inside demonstrated OS containment with least privilege, restricted credentials/egress, independent child-scope enforcement, event-gap reconciliation and version/capability tests. | Separate capability request and security design; REQ-06, REQ-08-REQ-12, REQ-15; DEC-14 | not started |
| [RT-011](011-always-on-and-desktop-feasibility.md) | 011-always-on-and-desktop-feasibility.md | Optional feasibility/decision record for desktop activation, wake gating, locked-screen identity/privacy, sleep/power behavior or an approved always-on host; no always-on promise. | Separate UX/deployment consent; REQ-02, REQ-17, REQ-18; DEC-15 | not started |
| [RT-012](012-private-native-audio-feasibility.md) | 012-private-native-audio-feasibility.md | Optional measurement and migration decision for genuinely native local/private audio with confirmed OS/hardware, quality/latency and denied-egress tests; no downloads from this request. | Separate private-runtime/hardware approval; REQ-01, REQ-14, REQ-15, REQ-17; DEC-10, DEC-15 | not started |

## Ordering and dependencies

- RT-001 → RT-002 → RT-003 (voice path).
- RT-004 depends on RT-002 (parallel ledger after scaffold).
- RT-005 depends on RT-003 and RT-004.
- RT-006 → RT-007 → RT-008 (controls, recovery, measured validation).
- RT-009 after accepted fixed-slice evidence/acceptance.
- RT-010 optional contained OpenCode.
- RT-011 optional always-on/desktop feasibility.
- RT-012 optional private native audio feasibility.

## Task template fields

Each task file contains its exact task ID, status, execution evidence, owner,
scope and non-goals, prerequisites, inputs, deliverable, acceptance checks,
failure considerations, and evidence.

Initially all future tasks were **not started** with no execution evidence.
RT-001 is complete. RT-002 and RT-003 are in progress. RT-004 and every later
task remain `not started`.
