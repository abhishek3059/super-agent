# Super-agent roadmap (checklist of record)

| Field | Value |
| --- | --- |
| Date | 2026-11-19 |
| Current phase | PH-02 |
| Current phase PR | [PR #58](https://github.com/abhishek3059/super-agent/pull/58) closed PH-01 (R-01.F9, R-01.F10, R-01.10) on 2026-11-19. PH-02 starts. Details: [phase PR log](docs/implementation/phase-prs.md). |
| Gate definitions | [phases.md](phases.md) (entry prerequisites and exit gates stay defined there) |
| Task records | [tasks/](tasks/README.md) |
| Enforced by | `npm run check` ([scripts/check-roadmap.mjs](scripts/check-roadmap.mjs), form only), the shared reviewer ([.claude/agents/reviewer.md](.claude/agents/reviewer.md), [DEC-19](descisions.md#dec-19)), and [AGENTS.md](AGENTS.md) section 11 |

This is the path. Every agent and every human follows it in order. The phase
IDs are the same as in [phases.md](phases.md); this file adds the checkboxes.
It authorizes nothing at runtime and closes no gate by itself.

## Rules for ticking

1. **Read this file** at the start of a session, and again after finishing any piece of work. Then do the next unticked item of the current phase, in order.
2. **Tick only with evidence.** Change `[ ]` to `[x]` and replace the line's ending `Evidence: none yet` with `Evidence: [label](target)`, where the target is a record under `docs/`, `spikes/`, `tasks/`, `apps/`, `scripts/` or `.github/`, a root policy file, or a merged pull request, commit, or Actions run of this repository. `README.md` and this file are not evidence. No evidence, no tick.
3. **Keep one phase or work-bundle PR open until its approved scope is complete.** Put implementation, tests, evidence records, documentation, and ticks in that PR when the evidence is a repository record in the same PR or is already merged. Do not open bookmark or bookkeeping PRs for each status update. Use a follow-up only when evidence can exist only after merge or the operator explicitly requests one. Never tick an unsupported claim.
4. **If a check fails or a tick cannot be made, fix that first.** Add a fix item under the same phase (`R-xx.Fn`), solve the bug, tick the fix, tick the original item, and only then move on.
5. **Stay on the path.** Do not start items of a later phase while the current phase has unticked required items. A deliberate exception needs `[exception: [label](docs/approvals/...)]` on the item, pointing to an approvals or review record that a maintainer has approved ([DEC-21](descisions.md#dec-21)).
6. **`[human]` items** need a person. An agent may tick one only when the person says so in chat or in a reviewed PR, and the evidence must include a record under `docs/approvals/` that says who decided and when.
7. **Phase status** is `not started`, `in progress`, or `done`. A phase is `done` only when every item in it is ticked and its exit gate in [phases.md](phases.md) is evidenced. Then update `Current phase` above.
8. If the roadmap itself needs to change, change it in its own PR with the reason, and update [phases.md](phases.md) too if a gate moves.

9. **The check tests form, not truth.** It rejects missing or malformed evidence, out-of-order ticks, a `[human]` tick without a record under `docs/approvals/`, and any item added, deleted, or re-flagged without the same change in [scripts/roadmap-ids.txt](scripts/roadmap-ids.txt). It cannot tell whether evidence is honest, so the shared reviewer ([AGENTS.md](AGENTS.md) section 9) opens the evidence for every change to this file. Adding or removing an item means editing both files in one roadmap PR.

Item format (one line, starting at column 0): `- [ ] R-<phase>.<n> [tags] Description. Evidence: none yet`

## PH-DOC: documentation pack and repository tooling

**Status:** done

- [x] R-DOC.1 Documentation pack authored and cross-linked. Evidence: [delivery record](docs/delivery/super-agent.md)
- [x] R-DOC.2 Independent design review passed. Evidence: [design review](docs/reviews/super-agent.md)
- [x] R-DOC.3 Design-stage security assessment passed. Evidence: [security assessment](docs/security/super-agent.md)
- [x] R-DOC.4 Repository checks, hooks, CI, and PR template in place. Evidence: [CONTRIBUTING.md](CONTRIBUTING.md)
- [x] R-DOC.5 Task folder typo fixed (`taks/` to `tasks/`). Evidence: [tasks/README.md](tasks/README.md)
- [x] R-DOC.6 MIT license added. Evidence: [LICENSE](LICENSE)
- [x] R-DOC.7 Agent rulebook added. Evidence: [AGENTS.md](AGENTS.md)
- [x] R-DOC.8 Spikes A2 (permission hook) and A3 (Gemini Live latency) run and recorded. Evidence: [spike A2](spikes/a2-permission-hook/README.md), [spike A3](spikes/a3-gemini-live/README.md)
- [x] R-DOC.9 Documentation stage accepted by the delivery manager on 2026-11-07 for the documentation and design stage only (later revisions are covered by the delivery record; no runtime gate). Evidence: [delivery status](docs/delivery/super-agent.md)

## PH-00: runtime eligibility, consent, and setup decisions

**Status:** done

Maps to [RT-001](tasks/001-runtime-consent-and-feasibility.md) and RT-G00. Nothing in PH-01 may start (beyond the offline scaffold already merged) until RT-G00 is resolved.

- [x] R-00.1 [human] Both maintainers record approval of the first-cycle scope. Evidence: [voice-foundation confirmation](docs/approvals/voice-foundation-confirmation.md)
- [x] R-00.2 Gemini account verification recorded: provider eligibility, native transport and model access, region, quota, billing. Evidence: [verification record](docs/implementation/gemini-account-verification.md)
- [x] R-00.3 [human] First real task pair chosen and approved. Evidence: [PH-00 setup decisions](docs/approvals/ph-00-setup-decisions.md)
- [x] R-00.4 [human] Named runtime recipients and data boundary approved, including that personal microphone audio stays local. Evidence: [PH-00 setup decisions](docs/approvals/ph-00-setup-decisions.md)
- [x] R-00.5 [human] Hosts confirmed (Mac and Windows) and retention and retry windows approved. Evidence: [PH-00 setup decisions](docs/approvals/ph-00-setup-decisions.md)
- [x] R-00.6 [human] Monetary and resource limits approved and recorded ($0 cap, no paid fallback). Evidence: [PH-00 setup decisions](docs/approvals/ph-00-setup-decisions.md)
- [x] R-00.7 RT-001 dated setup decision record written. Evidence: [PH-00 setup decisions](docs/approvals/ph-00-setup-decisions.md)
- [x] R-00.8 [human] Explicit implementation authorization for PH-01 beyond the offline scaffold. Evidence: [PH-00 setup decisions](docs/approvals/ph-00-setup-decisions.md)
- [x] R-00.9 External secret setup done and documented: keys in the process environment or an OS vault, never in the repo, browser, URLs, or logs. Evidence: [PH-00 setup decisions](docs/approvals/ph-00-setup-decisions.md)
- [x] R-00.10 Provider terms, retention, and recipients disclosed in a dated record. Evidence: [Gemini verification](docs/implementation/gemini-account-verification.md)
- [x] R-00.11 RT-G00 evidenced and resolved. Evidence: [PR 23](https://github.com/abhishek3059/super-agent/pull/23)

## PH-01: local boundary and native voice connection

**Status:** done

Maps to [RT-002](tasks/002-local-scaffold-and-boundary.md), [RT-003](tasks/003-native-voice-session.md), and RT-G01. Design: [voice foundation](docs/design/voice-foundation.md). Item order below follows the [PH-01 sequencing record](docs/approvals/ph-01-sequencing.md); every item is still required to close PH-01.

- [x] R-01.1 [exception: [confirmation record](docs/approvals/voice-foundation-confirmation.md)] Offline voice scaffold (fake adapter, no provider, no tools) merged. Evidence: [PR 13](https://github.com/abhishek3059/super-agent/pull/13)
- [x] R-01.2 [exception: [confirmation record](docs/approvals/voice-foundation-confirmation.md)] Voice workflow green on `develop` for Windows and macOS. Evidence: [voice-foundation run on develop](https://github.com/abhishek3059/super-agent/actions/runs/42574431372)
- [x] R-01.3 [human] Mac offline checks run with real output recorded. Evidence: [macOS evidence and owner confirmation](docs/approvals/r01-3-macos-evidence.md)
- [x] R-01.5 Credential design written and independently reviewed: high-entropy device or session credentials, storage, expiry, revocation, throttling (RT-A05 obligation). Evidence: [credential design review](docs/reviews/r01-5-credential-design.md)
- [x] R-01.7 Gemini Live adapter behind the replaceable seam, covered by offline tests with the fake. Evidence: [R-01.7 implementation record](docs/implementation/r01-7-gemini-adapter.md)
- [x] R-01.F1 Fix the misleading console state found in the [R-01.4 observations](docs/implementation/r01-4-microphone-observations.md): input level shown separately from model speech, silent frames never set `speaking`, and conversational barge-in (not the Interrupt button) is the tested path, with offline tests for silence, playback, interruption, stale output, mute, and stop. Evidence: [streaming slice record](docs/implementation/voice-streaming-slice.md), [frontend test output](docs/implementation/voice-streaming-frontend-output.md)
- [x] R-01.F2 Make the POSIX token-symlink security test portable so unprivileged Windows test runs skip the POSIX-only fixture instead of failing before the assertion. Evidence: [R-01.F2 implementation record](docs/implementation/r01-f2-windows-symlink-test.md)
- [x] R-01.F3 Make the exact browser Origin requirement and backend-unavailable failure actionable without widening the reviewed Origin allowlist. Evidence: [R-01.F3 implementation record](docs/implementation/r01-f3-origin-diagnostic.md)
- [x] R-01.F4 Add one Windows launcher that starts the locked backend and frontend from its own checkout path and cleans up the backend when the frontend exits. Evidence: [R-01.F4 implementation record](docs/implementation/r01-f4-windows-launcher.md)
- [x] R-01.4 [human] Local microphone test (start, mute, conversational barge-in, stop) recorded on the revised scaffold after R-01.F1; no audio leaves the machine. Evidence: [operator's microphone test record](docs/approvals/r01-4-microphone-test.md)
- [x] R-01.6 Independent security review accepted for the implemented boundary: deployed authentication, Host, Origin, CORS, WebSocket, and CSRF controls, and backend-only secrets. Evidence: [security review](docs/reviews/r01-6-security-review.md), [F2 risk acceptance](docs/approvals/r01-6-f2-risk-acceptance.md)
- [x] R-01.8 Opt-in synthetic-audio live command built (key from process environment only, excluded from default tests and CI, logs timing and state only). Evidence: [R-01.8 and R-01.9 record](docs/implementation/r01-8-live-check.md)
- [x] R-01.9 Synthetic live test run and recorded; unsupported transport fails closed. Evidence: [saved live output](docs/implementation/evidence/r01-9-live-check-output-20261112T000230Z.txt), [R-01.8 and R-01.9 record](docs/implementation/r01-8-live-check.md)
- [x] R-01.F5 Prevent queued and late native audio from resuming playback after a local interrupt. Evidence: [PH-01 acceptance record](docs/implementation/r01-10-acceptance.md#offline-fixes)
- [x] R-01.F6 Require a clean SDK exit before reporting an established Gemini session closed. Evidence: [PH-01 acceptance record](docs/implementation/r01-10-acceptance.md#offline-fixes)
- [x] R-01.F7 Refuse an unexpected or missing provider before the local echo console requests microphone capture. Evidence: [browser verification](docs/implementation/r01-10-acceptance.md#browser-verification)
- [x] R-01.F8 Keep the synthetic Live adapter on the approved Gemini Developer API destination. Evidence: [provider destination check](docs/implementation/r01-10-acceptance.md#provider-destination)
- [x] R-01.F9 Make the server prove it holds the session token before the console sends any credential, so a process squatting the port cannot capture it (review finding B1, old F5). Evidence: [R-01.F9 record](docs/implementation/r01-f9-handshake-proof.md)
- [x] R-01.F10 Keep a connected console session alive while muted and report a stalled microphone instead of idling into the 60-second timeout, found in the R-01.10 console run. Evidence: [R-01.F10 record](docs/implementation/r01-f10-idle-keepalive.md)
- [x] R-01.10 RT-002 and RT-003 records complete and RT-G01 evidenced. Evidence: [R-01.10 acceptance record](docs/implementation/r01-10-acceptance.md), [decisions record](docs/approvals/r01-10-decisions.md)

## PH-02: ledger, policy, and two fixed workers

**Status:** not started

Maps to [RT-004](tasks/004-task-ledger-and-policy.md), [RT-005](tasks/005-fixed-sample-workers.md), and RT-G02.

- [ ] R-02.1 [exception: [agent backend exception](docs/approvals/agent-backend-exception.md)] Job ledger with the eight canonical states, receipts, and application-owned truth. Evidence: none yet
- [ ] R-02.2 [exception: [agent backend exception](docs/approvals/agent-backend-exception.md)] Idempotency keys, task revisions, and stale-session rejection. Evidence: none yet
- [ ] R-02.3 [exception: [agent backend exception](docs/approvals/agent-backend-exception.md)] Policy limits enforced outside the model (schemas, sizes, deadlines, steps, retries, budget). Evidence: none yet
- [ ] R-02.4 [exception: [agent backend exception](docs/approvals/agent-backend-exception.md)] Two trusted read-only workers over synthetic data, with no arbitrary-code, host-shell, plugin, or external-action exposure. Evidence: none yet
- [ ] R-02.5 [exception: [agent backend exception](docs/approvals/agent-backend-exception.md)] Worker execution off the voice event loop; conversation continues during overlap (RT-A02, RT-A03). Evidence: none yet
- [ ] R-02.7 Governance gate per [governance design](docs/design/governance.md): `policy.decide` is the single allow, deny, or confirm decision for turn-level checks, fail closed, moved in slices 1 to 4 with no behaviour change except GR-1 (emotional or social turns never start a task). OD-G1 (`policy.py` is the gate) is approved in the [decisions record](docs/approvals/governance-decisions.md); OD-G2 to OD-G4 are decided in the same record; OD-G5 (how intent and emotional meaning are understood) is a precondition of slice 2b only; OD-G6 is answered in the [decisions record](docs/approvals/governance-decisions.md) (PH-02, no exception). Evidence: none yet
- [ ] R-02.F1 Fix the admission bypass in `Runner.claim_and_run`: it must call `policy.admit`, use the job's own admitted tools, and stop offering `memory_recall` and `memory_save`, which do not exist, or the method is removed (review finding B4). Evidence: none yet
- [ ] R-02.F3 Reconcile the two ledger paths: the SQLite owner ledger is the one application-owned truth, and the PostgreSQL seam and the Hermes worker definitions from PR #55 either sit behind it with the same states, idempotency, and policy admission, or are removed. Evidence: none yet
- [ ] R-02.F4 Close F2 (accept-before-auth denial of service) by handshake-time authentication before any of: R-A.2 allows real voice to a cloud provider beyond maintainer testing; a multi-user, shared, always-on, or remote host; job control reachable from a voice session ([decisions](docs/approvals/r01-10-decisions.md), [risk acceptance](docs/approvals/r01-6-f2-risk-acceptance.md)). Evidence: none yet
- [ ] R-02.6 RT-004 and RT-005 records complete and RT-G02 evidenced. Evidence: none yet

## PH-03: steering, stops, recovery, and validation

**Status:** not started

Maps to [RT-006](tasks/006-steering-and-stop-controls.md), [RT-007](tasks/007-recovery-and-retention.md), [RT-008](tasks/008-runtime-validation.md), RT-G03, and RT-G04.

- [ ] R-03.1 Steer and cancel a named job; the distinct stop controls (speech, mic upload, job, emergency stop). Evidence: none yet
- [ ] R-03.2 Duplicate, stale, and lost-event handling; cancellation races and unknown outcomes; native replacement sessions; restart without blind replay; sleep and off limits disclosed (RT-A04). Evidence: none yet
- [ ] R-03.3 Retention and deletion policy implemented and tested (RT-A06). Evidence: none yet
- [ ] R-03.4 Negative security tests for the local boundary pass (RT-A05). Evidence: none yet
- [ ] R-03.F1 Fail closed when the local adapter's remote-model check cannot run (Ollama unreachable): refuse the session or re-check before the first chat request (review finding B3). Evidence: none yet
- [ ] R-03.F2 Owner-only protection on Windows for the token, memory, and ledger files (ACL or documented equivalent), and make the failing `test_memory.py` file-mode test pass or skip correctly on Windows (review finding B5). Evidence: none yet
- [ ] R-03.F3 Enforce the 127.0.0.1 bind in code, not only in the launch commands (review finding B6). Evidence: none yet
- [ ] R-03.F4 Bound the Gemini adapter queues in code and make the tool-call cap apply per user reply, not per provider turn (review finding B7). Evidence: none yet
- [ ] R-03.5 Measured latency and barge-in results reported against targets (RT-A02). Evidence: none yet
- [ ] R-03.6 Independent implementation review and security assessment of the actual revision. Evidence: none yet
- [ ] R-03.7 RT-006, RT-007, RT-008 records complete; RT-G03 and RT-G04 evidenced. Evidence: none yet

## PH-04: bounded real-task planner

**Status:** not started

Maps to [RT-009](tasks/009-bounded-real-task-planner.md). Entry needs the approved real task pair.

- [ ] R-04.1 [human] Real task pair and worker or recipient capabilities approved for the planner. Evidence: none yet
- [ ] R-04.2 [exception: [agent backend exception](docs/approvals/agent-backend-exception.md)] Clarifying-question flow turns a vague request into a reviewable task specification. Evidence: none yet
- [ ] R-04.3 [exception: [agent backend exception](docs/approvals/agent-backend-exception.md)] Typed bounded steps with checkpointed steering and verifier evidence. Evidence: none yet
- [ ] R-04.4 Planner shown more useful than the fixed baselines; no new authority granted by voice. Evidence: none yet
- [ ] R-04.5 RT-009 record complete. Evidence: none yet

## PH-05: contained coding-agent adapter (optional)

**Status:** not started

Maps to [RT-010](tasks/010-contained-opencode-adapter.md). Spike A2 is only prior art.

- [ ] R-05.1 [human] Capability request approved and an independent security design for containment, credentials, and egress reviewed. Evidence: none yet
- [ ] R-05.2 Adapter built with OS containment, least privilege, restricted credentials and egress, and child-scope enforcement; event gaps reconciled; version and capability tests pass. Evidence: none yet
- [ ] R-05.3 RT-010 record complete. Evidence: none yet

## PH-06: desktop, wake, and always-on feasibility (optional)

**Status:** not started

Maps to [RT-011](tasks/011-always-on-and-desktop-feasibility.md).

- [ ] R-06.1 [human] Device, host, security, and power consent decision. Evidence: none yet
- [ ] R-06.2 Feasibility and decision record written; no always-on promise made. Evidence: none yet

## PH-07: private native audio feasibility (optional)

**Status:** not started

Maps to [RT-012](tasks/012-private-native-audio-feasibility.md).

- [ ] R-07.1 [human] Private-runtime and hardware approval; candidate hardware confirmed. Evidence: none yet
- [ ] R-07.2 Quality, latency, and denied-egress measurements recorded; migration decision made. Evidence: none yet

## Parallel track R: repository and release readiness

These do not gate any phase, but they are on the path and must be ticked.

- [x] R-R.1 PRs #14 (voice CI fix), #15 (status docs), and #16 (Gemini verification and learnings) merged. Evidence: [PR 14](https://github.com/abhishek3059/super-agent/pull/14), [PR 15](https://github.com/abhishek3059/super-agent/pull/15), [PR 16](https://github.com/abhishek3059/super-agent/pull/16)
- [ ] R-R.2 Release PR from `develop` to `main` merged with a merge commit, so both maintainers appear on the Contributors graph. Evidence: none yet
- [ ] R-R.3 [human] Private vulnerability reporting enabled on GitHub. Evidence: none yet
- [ ] R-R.4 [human] Branch protection on `main` and `develop` agreed and set: required **Repository checks** and no force pushes or deletions on both; on `develop`, the shared AI reviewer as the review gate instead of a required human review ([DEC-19](descisions.md#dec-19)); on `main`, a required human review. Evidence: none yet
- [ ] R-R.5 [human] Dependabot alerts, CodeQL, and secret scanning enabled. Evidence: none yet
- [x] R-R.6 README links to the learnings folder (the roadmap link is already there). Evidence: [PR 21](https://github.com/abhishek3059/super-agent/pull/21)

## Parallel track M: memory and brain

Design input: [brain overview](docs/design/brain/overview.md) and [memory design](docs/design/brain/memory.md). This track gates no phase and moves no gate. R-M.1 can happen any time. No item is built before the items it needs are ticked. The clarifying-question build stays in R-04.2 and the T0 persona in R-A.3. Work record: [roadmap record](docs/implementation/roadmap-brain-memory-governance.md).

- [ ] R-M.1 [human] A maintainer approves the brain and memory design and records every open decision in [brain overview](docs/design/brain/overview.md) section 10, including the persistent-memory approval under RT-G05. Evidence: none yet
- [ ] R-M.2 Local model measurement spike on the tool and step schemas; model and licence recorded (needs R-M.1). Evidence: none yet
- [ ] R-M.3 Context assembler and model router with data-class enforcement and session memory only, with tests (needs R-02.3, R-M.2, R-A.2, R-02.F4). Evidence: none yet
- [ ] R-M.4 System 1 tools `delegate_task`, `query_ledger`, and `cancel_task` wired to the ledger, tested with a scripted model (needs R-02.1, R-02.2, R-M.3, R-02.F4). Evidence: none yet
- [ ] R-M.5 `steer_task` wired to revisions (needs R-03.1, R-M.4). Evidence: none yet
- [ ] R-M.6 Profile store: remember, correct, and export as ledger jobs, with an inspect screen and the confirmation paths; synthetic data only until R-M.7 is ticked (needs R-02.1 to R-02.3, R-M.1, R-M.4). Evidence: none yet
- [ ] R-M.7 Forgetting and retention purge, with the residue tests passing; the profile store may hold real data only after this item (needs R-03.3, R-M.6). Evidence: none yet
- [ ] R-M.8 Day book written from verified receipts (needs R-02.6, R-M.7, OD-3 recorded). Evidence: none yet
- [ ] R-M.9 Advice-only recommendations with cited evidence (needs R-M.6, R-M.8, R-A.3). Evidence: none yet
- [ ] R-M.10 Library layer built behind the policy layer (needs R-A.4, R-A.5, R-M.7). Evidence: none yet
- [ ] R-M.11 Evaluation suite run on the built layers and recorded. Evidence: none yet
- [ ] R-M.12 [exception: [distiller exception](docs/approvals/memory-distiller-exception.md)] Memory distiller that learns the user: a `memory.distill` job with origin `session_end`, local model only, `inferred` records, episodes and decisions stores, the "What I learned" screen, trip scenario EV-A1 to EV-A10 as acceptance; needs its exception record `docs/approvals/memory-distiller-exception.md` before it starts (needs R-M.7, R-M.8, OD-15 to OD-18, IR-9, IR-10). Evidence: none yet
- [ ] R-M.13 Explicit facts and reminders (`remember`, `add_reminder`, `forget`, `undo_forget`; SQLite, opt-in, secrets refused), merged in commit 774bca4 under the [local memory exception](docs/approvals/local-memory-exception.md); tick only with later evidence. Evidence: none yet
- [ ] R-M.14 [human] Decide how contradictions and outdated facts are handled: a one-off is not a habit, a newer record supersedes an older one, the old one is kept for a set time, and the user can see why. Evidence: none yet
- [ ] R-M.15 Contradiction handling built and tested as decided in R-M.14 (needs R-M.12, R-M.14). Evidence: none yet
- [ ] R-M.16 Decay of unreinforced `inferred` records and forget with a receipt, including skipping distillation of any session that contains a forget request, tested (needs R-M.12). Evidence: none yet
- [ ] R-M.17 Result handler subagent: job results reach the conversation model only through a handler that returns a brief at the turn boundary, never raw worker output, with tests (needs R-02.5, R-M.4). Evidence: none yet
- [ ] R-M.19 Butler and etiquette rules BR-1 to BR-8 applied: short replies, ask once, discretion, good timing, not reciting stored facts, report only ledger truth, with tests; persona per OD-11 (needs R-M.1, R-M.4, R-A.3; persona name and tone come from the OD-11 record in R-M.1). Evidence: none yet

## Parallel track A: capability ladder (DEC-18)

Tiers are defined in [DEC-18](descisions.md#dec-18). R-A.1 and R-A.2 can happen any time. R-A.3 starts after PH-01 is done and R-A.1 and R-A.2 are ticked. R-A.4 and R-A.5 start after RT-G02 (PH-02 exit). R-A.6 to R-A.9 start after RT-G03 (PH-03 exit). Each tier is built only after its design item is ticked. This track gates no phase and moves no gate.

- [x] R-A.1 [human] Both maintainers approve DEC-18 and the matching REQ-08 and AGENTS.md section 5 edits. Evidence: [approval record](docs/approvals/capability-ladder-decision.md), [PR 35](https://github.com/abhishek3059/super-agent/pull/35)
- [ ] R-A.2 [human] Data-boundary and cost decision for real voice and personal data sent to a cloud provider (REQ-13, free-tier training, the $0 cap). Evidence: none yet
- [ ] R-A.3 T0 advice-only conversation persona shipped with tests; no tools, no personal data access, no new authority. Evidence: none yet
- [ ] R-A.4 [human] T1 read-only connector design (scopes, allowlists, injection handling) approved after independent security review. Evidence: none yet
- [ ] R-A.5 T1 read-only connectors built behind the policy layer, with negative tests. Evidence: none yet
- [ ] R-A.6 [human] T2 reversible-write design (logging, undo path, sandbox folder) approved after independent security review. Evidence: none yet
- [ ] R-A.7 T2 reversible writes built behind the policy layer, with negative tests. Evidence: none yet
- [ ] R-A.8 [human] T3 consequential-action design (on-device approval, shell and recipient allowlists, kill switch) approved after independent security review. Evidence: none yet
- [ ] R-A.9 T3 consequential actions built behind the policy layer, with negative tests. Evidence: none yet

## Parallel track H: Jarvis HQ local team (DEC-23)

`apps/hq` is an experimental local multi-bot workspace built at a maintainer's direction under [DEC-23](descisions.md#dec-23). Its workers run inside the macOS sandbox, outside the capability ladder, as a [bounded exception approved by a maintainer](docs/approvals/jarvis-hq-dec-23-approval.md). This track gates no phase and moves no gate. Every item must be ticked before any release to `main` users or any public distribution of the app.

- [x] R-H.1 [human] A maintainer approves DEC-23, the AGENTS.md section 5 exception and the OpenAI voice spend. Evidence: [maintainer approval in chat, 2026-11-17](docs/approvals/jarvis-hq-dec-23-approval.md)
- [x] R-H.2 `apps/hq` merged with its self-checks green in CI. Evidence: [PR 56](https://github.com/abhishek3059/super-agent/pull/56), [Jarvis HQ run on develop](https://github.com/abhishek3059/super-agent/actions/runs/44607953074)
- [x] R-H.3 Live voice run recorded with synthetic speech: connect, tool call handed to a bot, spoken result, interrupt, end. Evidence: [voice check record](docs/implementation/jarvis-hq-voice-check.md#live-run-2026-11-19), [saved output](docs/implementation/evidence/rh3-voice-check-output-20261119.txt)
- [x] R-H.4 Independent security review of `apps/hq`: loopback boundary, screen relay, the sandbox profile, credentials copied into bot homes, internet egress. Evidence: [security review and closure](docs/reviews/jarvis-hq-security-review.md)
- [x] R-H.5 Workers contained so one bot cannot read the operator's files (beyond folders the operator opts in to under DEC-23 rule 2, R-H.6), the session secret or another bot's folder. Evidence: [containment run and attacks through the server](docs/implementation/jarvis-hq-local-run.md#containment), [self-checks](apps/hq/server/test/hq.test.ts)
- [ ] R-H.6 Desktop page and browser bar for each bot's computer, ChatGPT sign-in through OpenAI's page and an Anthropic API key field for a dedicated Hermes seed, read-only access to operator-listed folders and skill folders, a shared skills folder and a fixed `system_info` tool, all in `apps/hq` under DEC-23, with an independent security review of the new access. Evidence: none yet
- [ ] R-H.7 Run HQ on Windows through WSL2 with a Linux containment backend (bubblewrap) that enforces the same rules as the macOS sandbox, with Linux Chrome discovery and a WSL launcher; per the [Windows and memory decision](docs/approvals/jarvis-hq-windows-memory-decision.md). Evidence: none yet
- [ ] R-H.8 Per-bot semantic memory in a local PostgreSQL with pgvector, embedded locally by Ollama, with `memory_save` and `memory_search` tools that cite stored entries and answer "not in memory" when nothing matches; per the [Windows and memory decision](docs/approvals/jarvis-hq-windows-memory-decision.md). Evidence: none yet
- [ ] R-H.9 Add an on-screen Jarvis companion inside HQ using original skins, saved appearance, and the existing chat and voice controls. Verify keyboard navigation, small screens, and reduced motion. No new tool permissions or provider connections. Evidence: none yet
- [ ] R-H.10 Add an HQ companion walkthrough that highlights known app controls and waits for the operator, and an opt-in explanation display that renders bounded text-only flow cards through existing chat. Scope is inside HQ without desktop capture or automated clicks. Evidence: none yet

## Parallel track C: community and launch

Starts after the PH-03 exit, except R-C.1 and R-C.2, which can happen any time.

- [ ] R-C.1 [human] Talk to 15 to 20 people who run coding agents; record results in `docs/learnings/`. Evidence: none yet
- [ ] R-C.2 [human] Legal read of the Gemini terms (consumer-use and EEA, Swiss, UK clauses) before any public distribution. Evidence: none yet
- [ ] R-C.3 [human] Free versus paid tiers decided. Evidence: none yet
- [ ] R-C.4 First tagged release `v0.1.0` after the PH-03 exit. Evidence: none yet
