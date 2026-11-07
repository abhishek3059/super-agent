# Super-agent — phased plan and approvals

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Revision | 4 |
| Status | Future phases initially `not started`; documentation milestone separate from measured runtime acceptance |
| Revision 2 note | Corrections applied 2026-11-07 for independent review finding R-02 (see [docs/reviews/super-agent.md](docs/reviews/super-agent.md)): entry prerequisites and exit/acceptance gates are now stated separately per phase; no gate is asserted to have passed. |
| Revision 4 note | Status metadata updated 2026-11-07: actual independent reports now exist at [docs/reviews/super-agent.md](docs/reviews/super-agent.md) (design review, opens PASS for the revision-3 correction set) and [docs/security/super-agent.md](docs/security/super-agent.md) (design-stage security, opens PASS, findings LOW-01 and INFO-01–03, for signed design revision 1 plus that set); see [progress](progress.md). No future-phase gate is claimed passed and no runtime work has started; PH-DOC status is a status-revision clarification, not a final acceptance. |

This document orders future phases and tasks. It is part of the documentation pack and authorizes nothing at runtime. For every phase below, **entry prerequisites** (what must already exist before the phase may begin) are stated separately from **exit/acceptance gates** (the evidence the phase's own work must produce). No status other than the initial `not started` value is asserted.

## Navigation

- [Signed design](docs/design/super-agent.md)
- [Delivery status](docs/delivery/super-agent.md)
- [Discovery brief](docs/delivery/super-agent-brief.md)
- [Council deliberation](docs/delivery/council.md)
- [Requirements](prd.md)
- [Architecture](architecture.md)
- [Decisions](descisions.md)
- [Progress](progress.md)
- [Build](build.md)
- [Flow](flow.md)
- [Tasks](taks/README.md)
- [Council meetings](council%20meetings/README.md)
- [Implementation report](docs/implementation/super-agent.md)

## Phase register

### PH-DOC

Current documentation pack; DOC-001–DOC-012 below.

- **Entry prerequisites:** the signed design and the two delivery sources. No runtime authorization of any kind.
- **Exit/acceptance gates:** DOC-A01–DOC-A06; the delivery manager's independent design-review and design-stage security assessment dispositions for the assessed revision. Documentation authoring alone does not close the review gate.
- **Status:** documentation pack authored; the previously assessed revisions hold actual independent design review PASS ([docs/reviews/super-agent.md](docs/reviews/super-agent.md)) and design-stage security PASS ([docs/security/super-agent.md](docs/security/super-agent.md)); this revision-4 status-clarification snapshot awaits its independent re-review and the delivery manager's recorded final acceptance; see [progress](progress.md).

Future task links: none.

### PH-00

Runtime eligibility, consent, real-task selection, host, budgets, retention, and implementation authorization; RT-G00 authority and feasibility.

- **Entry prerequisites:** a separate authorization permitting feasibility/setup *decision work* (not runtime execution); the signed design and completed independent-review dispositions of PH-DOC for the assessed revision. No scaffold is required and none is assumed.
- **Exit/acceptance gates:** [RT-001](taks/001-runtime-consent-and-feasibility.md) producing a truthful dated setup decision, and [RT-G00](prd.md#rt-g00) resolved: explicit runtime consent and named microphone/context recipients; confirmed provider eligibility and native access; actual account/region/quota access and disclosed terms; disclosed retention windows; confirmed host; user-selected first real task pair; approved monetary/resource budgets. No consent/access fact may be fabricated.
- **Status:** `not started`.

Task links: [RT-001](taks/001-runtime-consent-and-feasibility.md).

### PH-01

Separately approved local scaffold/boundary and manually activated native voice connection.

- **Entry prerequisites:** [RT-G00](prd.md#rt-g00) resolved (runtime consent, eligibility, host, task selection, budgets/retention) **and** an explicit new implementation/scaffold authorization for a new implementation request. No scaffold or native connection exists yet when the phase begins — producing them is the phase's work, not its prerequisite.
- **Exit/acceptance gates:** [RT-002](taks/002-local-scaffold-and-boundary.md) and [RT-003](taks/003-native-voice-session.md) complete, and [RT-G01](prd.md#rt-g01) evidenced: actually reviewed scaffold/commands, deployed authentication/Host/Origin/CORS/WS/CSRF controls, backend-only secrets, and measured native media and backend event/control connection with manual activation, stop controls, visible states, and fail-closed transport behavior.
- **Status:** `not started`.

Task links: [RT-002](taks/002-local-scaffold-and-boundary.md), [RT-003](taks/003-native-voice-session.md).

### PH-02

Ledger/policy and two deterministic trusted synthetic workers.

- **Entry prerequisites:** [RT-G01](prd.md#rt-g01) evidenced — an approved local scaffold/boundary and the measured manually activated native connection exist.
- **Exit/acceptance gates:** [RT-004](taks/004-task-ledger-and-policy.md) and [RT-005](taks/005-fixed-sample-workers.md) complete, and [RT-G02](prd.md#rt-g02) evidenced: two trusted read-only synthetic workers with bounded inputs, receipts, off-loop execution, authoritative ledger states, externally enforced resource limits, and continued native conversation during overlap; no arbitrary-code/host-shell/plugin/external-action exposure.
- **Status:** `not started`.

Task links: [RT-004](taks/004-task-ledger-and-policy.md), [RT-005](taks/005-fixed-sample-workers.md).

### PH-03

Steering/stops, recovery/retention, and measured negative and performance validation.

- **Entry prerequisites:** [RT-G02](prd.md#rt-g02) evidenced / [RT-005](taks/005-fixed-sample-workers.md) complete (the fixed-worker slice exists and is accepted as its gate defines).
- **Exit/acceptance gates:** [RT-006](taks/006-steering-and-stop-controls.md) and [RT-007](taks/007-recovery-and-retention.md) complete with [RT-G03](prd.md#rt-g03) evidenced (revisions, all stop semantics, cancellation races/unknown outcomes, stale commands/audio/notifications, duplicates, lost events, restart without blind replay); plus [RT-008](taks/008-runtime-validation.md) with [RT-G04](prd.md#rt-g04) evidenced (RT-A01–RT-A06 measurements, actual distributions/failures, retention/budget behavior, negative security tests, independent implementation review/security assessment of the actual revision).
- **Status:** `not started`.

Task links: [RT-006](taks/006-steering-and-stop-controls.md), [RT-007](taks/007-recovery-and-retention.md), [RT-008](taks/008-runtime-validation.md).

### PH-04

Useful bounded planner for the approved real task pair.

- **Entry prerequisites:** the fixed slice accepted ([RT-G04](prd.md#rt-g04)), a **user-selected and separately approved real task pair**, and separately approved worker/recipient capabilities for it. Approval of the planner capability itself is the extension gate the phase works toward, not its entry condition.
- **Exit/acceptance gates:** [RT-009](taks/009-bounded-real-task-planner.md) complete with bounded-planner evidence: typed bounded steps, checkpointed steering, verifier evidence, and comparative usefulness against fixed baselines; no new authority granted by voice (extension evidence under [RT-G05](prd.md#rt-g05)).
- **Status:** `not started`.

Task links: [RT-009](taks/009-bounded-real-task-planner.md).

### PH-05

Optional OS-contained OpenCode worker adapter.

- **Entry prerequisites:** a separately approved capability request and an independent security design for OS containment/credentials/egress; accepted fixed-slice evidence ([RT-G04](prd.md#rt-g04)) showing the system the adapter would join. The containment/egress/child-scope **results** are this phase's output, not prerequisites.
- **Exit/acceptance gates:** [RT-010](taks/010-contained-opencode-adapter.md) complete with evidence of demonstrated OS containment, least privilege, restricted credentials/egress, independent child-scope enforcement, event-gap reconciliation, and version/capability tests (extension evidence under [RT-G05](prd.md#rt-g05)).
- **Status:** `not started` (optional phase).

Task links: [RT-010](taks/010-contained-opencode-adapter.md).

### PH-06

Optional desktop/wake/locked-screen/always-on host feasibility.

- **Entry prerequisites:** a separate explicit device/host/security/power UX/deployment consent decision; privacy/identity analysis needed before such work. Feasibility **findings** are the phase's output, not prerequisites.
- **Exit/acceptance gates:** [RT-011](taks/011-always-on-and-desktop-feasibility.md) complete as a feasibility/decision record for desktop activation, wake gating, locked-screen identity/privacy, sleep/power behavior, or an approved always-on host; no always-on promise is made (extension evidence under [RT-G05](prd.md#rt-g05)).
- **Status:** `not started` (optional phase).

Task links: [RT-011](taks/011-always-on-and-desktop-feasibility.md).

### PH-07

Optional genuinely native private audio feasibility/migration.

- **Entry prerequisites:** a separate private-runtime/hardware approval from the user; confirmed candidate OS/hardware to test against. An always-on or private-native **outcome** is the phase's finding, not its prerequisite.
- **Exit/acceptance gates:** [RT-012](taks/012-private-native-audio-feasibility.md) complete with confirmed hardware compatibility, quality/latency measurements, and denied-egress tests; a migration decision — not a promise that the observed laptop supports private native voice (extension evidence under [RT-G05](prd.md#rt-g05)).
- **Status:** `not started` (optional phase).

Task links: [RT-012](taks/012-private-native-audio-feasibility.md).

## Phase ordering summary

| Phase ID | Entry prerequisites | Exit/acceptance gates | Task links | Status |
| --- | --- | --- | --- | --- |
| PH-DOC | Signed design + delivery sources. | DOC-A01–DOC-A06; manager-recorded independent review/security dispositions. | None. | Pack authored; earlier assessed revisions hold design review PASS and design-stage security PASS; revision-4 status clarifications pending independent re-review and manager-recorded final acceptance (see [progress](progress.md)). |
| PH-00 | Separate authorization for feasibility/setup decision work; PH-DOC dispositions. | RT-001 dated setup decision; RT-G00 resolved. | [RT-001](taks/001-runtime-consent-and-feasibility.md) | `not started` |
| PH-01 | RT-G00 resolved **and** explicit new scaffold authorization. | RT-002 + RT-003 complete; RT-G01 evidenced. | [RT-002](taks/002-local-scaffold-and-boundary.md), [RT-003](taks/003-native-voice-session.md) | `not started` |
| PH-02 | RT-G01 evidenced. | RT-004 + RT-005 complete; RT-G02 evidenced. | [RT-004](taks/004-task-ledger-and-policy.md), [RT-005](taks/005-fixed-sample-workers.md) | `not started` |
| PH-03 | RT-G02 evidenced / RT-005 complete. | RT-006 + RT-007 complete; RT-G03 evidenced; RT-008 complete; RT-G04 evidenced. | [RT-006](taks/006-steering-and-stop-controls.md), [RT-007](taks/007-recovery-and-retention.md), [RT-008](taks/008-runtime-validation.md) | `not started` |
| PH-04 | Fixed slice accepted (RT-G04); user-approved real task pair and worker/recipient capabilities. | RT-009 complete; RT-G05 bounded-planner evidence. | [RT-009](taks/009-bounded-real-task-planner.md) | `not started` |
| PH-05 (optional) | Separate capability request and security design; accepted fixed-slice evidence. | RT-010 complete; RT-G05 containment/egress/child-scope evidence. | [RT-010](taks/010-contained-opencode-adapter.md) | `not started` |
| PH-06 (optional) | Separate device/host/security/power consent decision. | RT-011 complete; RT-G05 feasibility/decision evidence. | [RT-011](taks/011-always-on-and-desktop-feasibility.md) | `not started` |
| PH-07 (optional) | Separate private-runtime/hardware approval; confirmed candidate OS/hardware. | RT-012 complete; RT-G05 benchmark/denied-egress evidence. | [RT-012](taks/012-private-native-audio-feasibility.md) | `not started` |

These dependencies match the task-level prerequisites in the signed design (`docs/design/super-agent.md:349-362`): no phase makes its own exit gate a prerequisite, and no phase asserts that a gate has already passed.

## Milestone separation

The documentation milestone (PH-DOC) is separate from measured runtime acceptance. A signed documentation contract, a completed pack, or development-model permission cannot close any runtime gate.

See [progress](progress.md) for the dated documentation-only milestone and [build](build.md) for the no-runnable-build position.
