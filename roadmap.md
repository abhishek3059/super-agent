# Super-agent roadmap (checklist of record)

| Field | Value |
| --- | --- |
| Date | 2026-11-11 |
| Current phase | PH-01 |
| Current phase PR | [#24 PH-01 real voice console](https://github.com/abhishek3059/super-agent/pull/24) (open work bundle; details in [phase PR log](docs/implementation/phase-prs.md)) |
| Gate definitions | [phases.md](phases.md) (entry prerequisites and exit gates stay defined there) |
| Task records | [tasks/](tasks/README.md) |
| Enforced by | `npm run check` ([scripts/check-roadmap.mjs](scripts/check-roadmap.mjs), form only), code-owner review ([.github/CODEOWNERS](.github/CODEOWNERS)), and [AGENTS.md](AGENTS.md) section 11 |

This is the path. Every agent and every human follows it in order. The phase
IDs are the same as in [phases.md](phases.md); this file adds the checkboxes.
It authorizes nothing at runtime and closes no gate by itself.

## Rules for ticking

1. **Read this file** at the start of a session, and again after finishing any piece of work. Then do the next unticked item of the current phase, in order.
2. **Tick only with evidence.** Change `[ ]` to `[x]` and replace the line's ending `Evidence: none yet` with `Evidence: [label](target)`, where the target is a record under `docs/`, `spikes/`, `tasks/`, `apps/`, `scripts/` or `.github/`, a root policy file, or a merged pull request, commit, or Actions run of this repository. `README.md` and this file are not evidence. No evidence, no tick.
3. **Keep one phase or work-bundle PR open until its approved scope is complete.** Put implementation, tests, evidence records, documentation, and ticks in that PR when the evidence is a repository record in the same PR or is already merged. Do not open bookmark or bookkeeping PRs for each status update. Use a follow-up only when evidence can exist only after merge or the operator explicitly requests one. Never tick an unsupported claim.
4. **If a check fails or a tick cannot be made, fix that first.** Add a fix item under the same phase (`R-xx.Fn`), solve the bug, tick the fix, tick the original item, and only then move on.
5. **Stay on the path.** Do not start items of a later phase while the current phase has unticked required items. A deliberate exception needs `[exception: [label](docs/approvals/...)]` on the item, pointing to an approvals or review record that both maintainers have approved.
6. **`[human]` items** need a person. An agent may tick one only when the person says so in chat or in a reviewed PR, and the evidence must include a record under `docs/approvals/` that says who decided and when.
7. **Phase status** is `not started`, `in progress`, or `done`. A phase is `done` only when every item in it is ticked and its exit gate in [phases.md](phases.md) is evidenced. Then update `Current phase` above.
8. If the roadmap itself needs to change, change it in its own PR with the reason, and update [phases.md](phases.md) too if a gate moves.

9. **The check tests form, not truth.** It rejects missing or malformed evidence, out-of-order ticks, a `[human]` tick without a record under `docs/approvals/`, and any item added, deleted, or re-flagged without the same change in [scripts/roadmap-ids.txt](scripts/roadmap-ids.txt). It cannot tell whether evidence is honest, so changes to this file need review from a code owner ([.github/CODEOWNERS](.github/CODEOWNERS)), and reviewers must open the evidence. Adding or removing an item means editing both files in one roadmap PR.

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

**Status:** in progress

Maps to [RT-002](tasks/002-local-scaffold-and-boundary.md), [RT-003](tasks/003-native-voice-session.md), and RT-G01. Design: [voice foundation](docs/design/voice-foundation.md). Item order below follows the [PH-01 sequencing record](docs/approvals/ph-01-sequencing.md); every item is still required to close PH-01.

- [x] R-01.1 [exception: [confirmation record](docs/approvals/voice-foundation-confirmation.md)] Offline voice scaffold (fake adapter, no provider, no tools) merged. Evidence: [PR 13](https://github.com/abhishek3059/super-agent/pull/13)
- [x] R-01.2 [exception: [confirmation record](docs/approvals/voice-foundation-confirmation.md)] Voice workflow green on `develop` for Windows and macOS. Evidence: [voice-foundation run on develop](https://github.com/abhishek3059/super-agent/actions/runs/42574431372)
- [x] R-01.3 [human] Mac offline checks run with real output recorded. Evidence: [macOS evidence and owner confirmation](docs/approvals/r01-3-macos-evidence.md)
- [x] R-01.5 Credential design written and independently reviewed: high-entropy device or session credentials, storage, expiry, revocation, throttling (RT-A05 obligation). Evidence: [credential design review](docs/reviews/r01-5-credential-design.md)
- [x] R-01.7 Gemini Live adapter behind the replaceable seam, covered by offline tests with the fake. Evidence: [R-01.7 implementation record](docs/implementation/r01-7-gemini-adapter.md)
- [x] R-01.F1 Fix the misleading console state found in the [R-01.4 observations](docs/implementation/r01-4-microphone-observations.md): input level shown separately from model speech, silent frames never set `speaking`, and conversational barge-in (not the Interrupt button) is the tested path, with offline tests for silence, playback, interruption, stale output, mute, and stop. Evidence: [streaming slice record](docs/implementation/voice-streaming-slice.md), [frontend test output](docs/implementation/voice-streaming-frontend-output.md)
- [ ] R-01.4 [human] Local microphone test (start, mute, conversational barge-in, stop) recorded on the revised scaffold after R-01.F1; no audio leaves the machine. Evidence: none yet
- [ ] R-01.6 Independent security review accepted for the implemented boundary: deployed authentication, Host, Origin, CORS, WebSocket, and CSRF controls, and backend-only secrets. Evidence: none yet
- [ ] R-01.8 Opt-in synthetic-audio live command built (key from process environment only, excluded from default tests and CI, logs timing and state only). Evidence: none yet
- [ ] R-01.9 Synthetic live test run and recorded; unsupported transport fails closed. Evidence: none yet
- [ ] R-01.10 RT-002 and RT-003 records complete and RT-G01 evidenced. Evidence: none yet

## PH-02: ledger, policy, and two fixed workers

**Status:** not started

Maps to [RT-004](tasks/004-task-ledger-and-policy.md), [RT-005](tasks/005-fixed-sample-workers.md), and RT-G02.

- [ ] R-02.1 Job ledger with the eight canonical states, receipts, and application-owned truth. Evidence: none yet
- [ ] R-02.2 Idempotency keys, task revisions, and stale-session rejection. Evidence: none yet
- [ ] R-02.3 Policy limits enforced outside the model (schemas, sizes, deadlines, steps, retries, budget). Evidence: none yet
- [ ] R-02.4 Two trusted read-only workers over synthetic data, with no arbitrary-code, host-shell, plugin, or external-action exposure. Evidence: none yet
- [ ] R-02.5 Worker execution off the voice event loop; conversation continues during overlap (RT-A02, RT-A03). Evidence: none yet
- [ ] R-02.6 RT-004 and RT-005 records complete and RT-G02 evidenced. Evidence: none yet

## PH-03: steering, stops, recovery, and validation

**Status:** not started

Maps to [RT-006](tasks/006-steering-and-stop-controls.md), [RT-007](tasks/007-recovery-and-retention.md), [RT-008](tasks/008-runtime-validation.md), RT-G03, and RT-G04.

- [ ] R-03.1 Steer and cancel a named job; the distinct stop controls (speech, mic upload, job, emergency stop). Evidence: none yet
- [ ] R-03.2 Duplicate, stale, and lost-event handling; cancellation races and unknown outcomes; native replacement sessions; restart without blind replay; sleep and off limits disclosed (RT-A04). Evidence: none yet
- [ ] R-03.3 Retention and deletion policy implemented and tested (RT-A06). Evidence: none yet
- [ ] R-03.4 Negative security tests for the local boundary pass (RT-A05). Evidence: none yet
- [ ] R-03.5 Measured latency and barge-in results reported against targets (RT-A02). Evidence: none yet
- [ ] R-03.6 Independent implementation review and security assessment of the actual revision. Evidence: none yet
- [ ] R-03.7 RT-006, RT-007, RT-008 records complete; RT-G03 and RT-G04 evidenced. Evidence: none yet

## PH-04: bounded real-task planner

**Status:** not started

Maps to [RT-009](tasks/009-bounded-real-task-planner.md). Entry needs the approved real task pair.

- [ ] R-04.1 [human] Real task pair and worker or recipient capabilities approved for the planner. Evidence: none yet
- [ ] R-04.2 Clarifying-question flow turns a vague request into a reviewable task specification. Evidence: none yet
- [ ] R-04.3 Typed bounded steps with checkpointed steering and verifier evidence. Evidence: none yet
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
- [ ] R-R.4 [human] Branch protection on `main` and `develop` agreed and set, including required code-owner review for `roadmap.md` and `phases.md`. Evidence: none yet
- [ ] R-R.5 [human] Dependabot alerts, CodeQL, and secret scanning enabled. Evidence: none yet
- [x] R-R.6 README links to the learnings folder (the roadmap link is already there). Evidence: [PR 21](https://github.com/abhishek3059/super-agent/pull/21)

## Parallel track C: community and launch

Starts after the PH-03 exit, except R-C.1 and R-C.2, which can happen any time.

- [ ] R-C.1 [human] Talk to 15 to 20 people who run coding agents; record results in `docs/learnings/`. Evidence: none yet
- [ ] R-C.2 [human] Legal read of the Gemini terms (consumer-use and EEA, Swiss, UK clauses) before any public distribution. Evidence: none yet
- [ ] R-C.3 [human] Free versus paid tiers decided. Evidence: none yet
- [ ] R-C.4 First tagged release `v0.1.0` after the PH-03 exit. Evidence: none yet
