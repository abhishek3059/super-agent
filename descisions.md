# Super-agent — decision register (requested spelling preserved: descisions.md)

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Revision | 2 |
| Status | Contracted design decisions; provisional, conditional, and deferred items explicitly marked per decision |
| Revision 2 note | Corrections applied 2026-11-07 for independent review findings R-01 (see [docs/reviews/super-agent.md](docs/reviews/super-agent.md)); no new decision was added and no runtime approval is asserted. |

Contracted means the design or documentation choice, not runtime authorization and not completed independent review.

## Navigation

- [Signed design](docs/design/super-agent.md)
- [Delivery status](docs/delivery/super-agent.md)
- [Discovery brief](docs/delivery/super-agent-brief.md)
- [Council deliberation](docs/delivery/council.md)
- [Requirements](prd.md)
- [Architecture](architecture.md)
- [Phases](phases.md)
- [Progress](progress.md)
- [Build](build.md)
- [Flow](flow.md)
- [Tasks](tasks/README.md)
- [Council meetings](council%20meetings/README.md)
- [Implementation report](docs/implementation/super-agent.md)

## Decision register

Each entry below carries, inline: its exact status per the signed decision register (`docs/design/super-agent.md:118-137`), rationale, alternatives and trade-offs, implications, source evidence, and reopen conditions. The status labels are the design's labels, not runtime approvals.

### DEC-01

Documentation-only delivery at the user's literal paths.

- **Status:** Contracted scope.
- **Rationale:** The brief records an initially empty project with no application, repository history, tests, or stack conventions (`docs/delivery/super-agent-brief.md:4`, `docs/delivery/super-agent-brief.md:41-42`). The current delivery is documentation only, so silently implementing a prototype or renaming requested artifacts would exceed the ask.
- **Alternatives and trade-offs:** (a) Build a scaffold/prototype now — rejected: no implementation authorization exists and runtime work requires a separate request and the §6 gates. (b) Silently correct the requested spellings (`tasks/`, `descisions.md`, `council meetings/`) to conventional `tasks/`/`decisions.md` — rejected: it would break the user's literal, explicitly preserved file names and create duplicate artifacts.
- **Implications:** Exact spelled paths are preserved across the whole pack (`tasks/`, `council meetings/`, `descisions.md`); spaces in `council meetings/` are literal filesystem characters, percent-encoded in links; no Git initialization, dependencies, scripts, or build (see [DEC-16](#dec-16)); documentation acceptance is separate from future runtime acceptance.
- **Source evidence:** [Discovery brief](docs/delivery/super-agent-brief.md):4, :41-42; design §2.1 ([docs/design/super-agent.md](docs/design/super-agent.md):22, :26); related requirement [REQ-D01](prd.md#req-d01).
- **Reopen:** Only a new explicit user/manager instruction that changes the requested taxonomy or grants implementation authorization.

### DEC-02

Native audio conversation; internal structured text and transient native transcripts are permitted.

- **Status:** Contracted UX constraint.
- **Rationale:** The user's recorded choice is hands-free native live audio, not a mandatory external STT → text-chat → TTS chain (`docs/delivery/super-agent-brief.md:12-16`; `docs/delivery/council.md:174-176`).
- **Alternatives and trade-offs:** (a) External STT/chat/TTS pipeline — cheaper and easier to control, but rejected because it silently substitutes a different conversational experience. (b) Local native model now — better privacy in principle, but unmeasured on the observed hardware, and no general local-native incompatibility on that hardware is established: the specific cited observation is Moshi's published PyTorch setup, which requires much more GPU memory and lacks official Windows support (`docs/delivery/super-agent-brief.md:43-46`; `docs/delivery/council.md:87-91`), so deferred ([DEC-15](#dec-15)).
- **Implications:** Internal structured text and transient native transcripts remain implementation details; cloud models may be used for development (`docs/delivery/super-agent-brief.md:18-22`; `docs/delivery/council.md:13-15`), but transmitting microphone or personal context to a provider at runtime is gated by [RT-G00](prd.md#rt-g00) consent ([REQ-13](prd.md#req-13)). No transport/provider fallback is silent.
- **Source evidence:** [Discovery brief](docs/delivery/super-agent-brief.md):12-16, :18-22; [Council](docs/delivery/council.md):13-15, :174-176; acceptance anchors [RT-A01](prd.md#rt-a01), [RT-A02](prd.md#rt-a02).
- **Reopen:** Explicit user scope change away from native-voice UX.

### DEC-03

Thin manually activated browser plus one local authenticated service; separate logical conversation and task/policy planes.

- **Status:** Contracted proposed shape; no stack already exists.
- **Rationale:** One backend gives execution truth a single owner and keeps long-lived credentials outside browser code (`docs/delivery/council.md:33-37`, `docs/delivery/council.md:64-75`). The conversation plane is ephemeral and manually activated; the task/policy plane is durable and externally enforced.
- **Alternatives and trade-offs:** (a) Heavy agent framework / microservices / fleet — rejected for now: operational and state surfaces without tasks that need them (`docs/delivery/council.md:186-187`). (b) Everything in the browser — smaller plumbing, but browser echoes must not define execution truth; backend-owned control protects backend credentials.
- **Implications:** The accepted shape is a deliberate single failure domain (one service, small store, SQLite-like ledger); sleep/off limits must be disclosed rather than promised ([REQ-18](prd.md#req-18)).
- **Source evidence:** [Council](docs/delivery/council.md):33-37, :64-75, :121-125, :186-187.
- **Reopen:** Measured workloads or reviewed lifecycle requirements that the one-service shape demonstrably cannot meet.

### DEC-04

Tiny authoritative local job ledger for the overlap/cancel/restart demonstration; no distributed queue or framework.

- **Status:** Conditional architecture choice.
- **Rationale:** The proposed first slice must demonstrate overlap, per-job cancellation, and safe restart reconciliation, which requires durable job truth outside any model or session (`docs/delivery/council.md:121-125`, `docs/delivery/council.md:150-151`). Durable IDs, cancellation races, and no blind replay after duplicates, disconnects, or restarts are contracted requirements ([REQ-05](prd.md#req-05), [REQ-06](prd.md#req-06)).
- **Alternatives and trade-offs:** (a) A stateless, fully disposable task demonstrator — simpler and a legitimate counterfactual for instantaneous tasks, but it cannot establish durable truth or safe reconciliation, so it fails this slice's goals; reopen evidence below is exactly this case. (b) A distributed queue/framework or recurring jobs — rejected before evidence of need: added operational/state surface with no benefit to one host and two workers (`docs/delivery/council.md:186-187`).
- **Implications:** Minimal task records still need bounded retention/delete rules ([DEC-10](#dec-10)); a ledger does not make a sleeping host process jobs (`docs/delivery/council.md:152-155`, `docs/delivery/council.md:207`).
- **Source evidence:** [Council](docs/delivery/council.md):121-125, :150-151, :186-187, :207; design §3 ([docs/design/super-agent.md](docs/design/super-agent.md):394-395); task [RT-004](tasks/004-task-ledger-and-policy.md).
- **Reopen:** If the selected first real tasks are truly instantaneous/disposable and require no recovery (no overlap/cancel/restart demonstration needed), remove the ledger to the stateless counterfactual, per the signed design.

### DEC-05

Two bounded trusted fixed sample functions initially; compute isolation from the event loop is not arbitrary-code containment.

- **Status:** Contracted boundary; arbitrary workers remain disabled.
- **Rationale:** The first experiment needs only two trusted bounded read-only synthetic workers running off the voice event loop (`docs/delivery/council.md:131-135`; [REQ-08](prd.md#req-08)).
- **Alternatives and trade-offs:** (a) Execute arbitrary/generated code in-process — rejected: threads/processes alone do not restrict host authority; OS/egress containment is a separate, later gate ([DEC-14](#dec-14), [PH-05](phases.md#ph-05)). (b) One worker — insufficient to demonstrate overlap.
- **Implications:** Workers use bundled sample data only; any deliberate timing delay is a test fixture for overlap, not evidence of reasoning.
- **Source evidence:** [Council](docs/delivery/council.md):131-135; [Discovery brief](docs/delivery/super-agent-brief.md):36-37.
- **Reopen:** A separately requested capability change plus demonstrated OS containment/egress evidence (extension gate RT-G05).

### DEC-06

Provider gate first. Investigate direct GPT-Live / WebRTC / client delegation as a provisional candidate; Realtime is another native candidate; Gemini remains eligibility-gated.

- **Status:** Provisional post-review research adoption — not a re-voted council consensus, not tested account access, and not a selection of an existing text-router model (design §2.5).
- **Rationale:** The council cross-review changed the initial provider recommendation (`docs/delivery/council.md:113-117`): Gemini must not be presumed as the personal runtime and an eligible direct OpenAI native-audio alternative should be investigated; the Researcher's terms caveat is the contributing rationale (`docs/delivery/council.md:85-87`). In meeting 3 this became the separately labeled post-review Researcher follow-up, not a new vote.
- **Alternatives and trade-offs:** (a) Gemini Live — published native streaming/barge-in capability, but developer terms describe professional/business use and warn about personal/sensitive content on unpaid services, and paid services still process/log data; eligibility must be checked, not presumed (`docs/delivery/council.md:79-91`). (b) OpenAI Realtime — another native candidate with terms/eligibility to verify. (c) GPT-Live managed Responses delegation — published and possibly useful later, but less aligned with application-owned context/routing/result review; provisionally the client-delegation shape fits independent policy and task truth. (d) Existing text-router model as transport — proves nothing about native transport.
- **Implications:** Cloud development permission is not a runtime gate pass: microphone/personal-context transmission still requires eligibility, native access, account/region/quota/cost/data terms, and named-recipient consent under [RT-G00](prd.md#rt-g00). No account is connected and no provider is approved today; candidates are compared after RT-G00 on actual capability, cost, latency, and data handling.
- **Source evidence:** [Council](docs/delivery/council.md):79-91, :105-117; design §2.5 ([docs/design/super-agent.md](docs/design/super-agent.md):139-168) and §3 (:396-397); [council meeting 3](council%20meetings/council-meeting-3.md).
- **Reopen:** Eligibility/term evidence that passes or fails any candidate re-ranks the candidates; failing eligibility for the provisional candidate makes an eligible alternative the working choice — a gated selection, not a reopened approval.

### DEC-07

Models propose; local policy grants. Voice never creates new authority. High-risk tools are absent initially.

- **Status:** Contracted safety boundary.
- **Rationale:** Voice is not identity; conversational output must not be execution authority, and ambient/replayed speech must not elevate power (`docs/delivery/council.md:188-189`; [REQ-09](prd.md#req-09)).
- **Alternatives and trade-offs:** (a) Give the voice model direct tool calls — smaller plumbing, but ambient "yes" could create authority. (b) Build the strong out-of-band/device authentication design now — deferred; high-risk actions and new authority are disabled without it.
- **Implications:** Schemas, scope, recipients, sizes, concurrency, deadlines, steps, retries, and spend are enforced outside models ([REQ-10](prd.md#req-10)); ambient "yes" cannot re-arm an emergency stop.
- **Source evidence:** [Discovery brief](docs/delivery/super-agent-brief.md):68-78; [Council](docs/delivery/council.md):50-60, :188-189.
- **Reopen:** A separately approved strong out-of-band/device-authentication design — agreed, not implied by voice use.

### DEC-08

Independent speech interruption, per-job cancellation, mic-stop, and emergency-stop controls.

- **Status:** Contracted semantics.
- **Rationale:** Barge-in must stop stale speech/playback without implicitly cancelling jobs, and job steering/cancel, speech stop, mic upload stop, and emergency stop are distinct operations (`docs/delivery/super-agent-brief.md`:63-65, :82-84; `docs/delivery/council.md`:55-58).
- **Alternatives and trade-offs:** Conflating barge-in with cancellation or a single global stop — would meet the literal words of the brief but break [REQ-03](prd.md#req-03)/[REQ-07](prd.md#req-07) and destroy recoverable work.
- **Implications:** Completed effects cannot be undone by stopping speech; non-disruptive notifications and turn-taking are measured, not assumed ([RT-A02](prd.md#rt-a02)).
- **Source evidence:** [Discovery brief](docs/delivery/super-agent-brief.md):63-67, :82-84; [Council](docs/delivery/council.md):55-58, :167-172.
- **Reopen:** Only an explicit user request to change stop semantics; any change remains subject to the same measured evidence.

### DEC-09

Durable intent/result/action IDs, task revisions, session/playback epochs, verified outcomes, and reconciliation.

- **Status:** Contracted correctness boundary; universal exactly-once external execution is not promised.
- **Rationale:** Durable dedup/reconciliation prevents blind local replay but cannot by itself guarantee external outcomes; verified receipts and honest `unknown` states are the contracted truth source (`docs/delivery/council.md`:192-204; [REQ-05](prd.md#req-05), [REQ-06](prd.md#req-06)).
- **Alternatives and trade-offs:** (a) Trust model narration or browser echoes as task evidence — rejected across the council. (b) Promise exactly-once external effects — rejected: an uncertain external outcome still requires reconciliation, provider idempotency evidence, and disclosure.
- **Implications:** Initial workers have no external effects; future tools must supply receipts and safe retry contracts; cancellation can legitimately resolve to success/failure/unknown.
- **Source evidence:** [Council](docs/delivery/council.md):44-45, :55-58, :192-204, :201; [Discovery brief](docs/delivery/super-agent-brief.md):68-70.
- **Reopen:** Evidence from future reconciliation/restart validation ([RT-007](tasks/007-recovery-and-retention.md), [RT-008](tasks/008-runtime-validation.md)) that the chosen correctness contract fails, or a real task needing an external-effect contract the ledger cannot express — both reopen the design, not the approval.

### DEC-10

Minimal local records with retention; no recordings/transcripts by default; no silent cloud fallback; private native migration is a later measured increment.

- **Status:** Contracted privacy boundary; no-training and local deletion do not mean no provider retention.
- **Rationale:** Local raw audio, persistent transcripts, model-content telemetry, and provider stored-session recording are off by default, and even minimal task content needs a bounded retention policy (`docs/delivery/super-agent-brief.md`:79-81; `docs/delivery/council.md`:136-139, :182-191; [REQ-14](prd.md#req-14)).
- **Alternatives and trade-offs:** (a) Persist raw audio always — better debugging, worse privacy and larger attack surface. (b) Claim "local database = private" — false: the client-delegation candidate needs transient text context, which can misroute work on transcript mistakes and is scoped/transient precisely to avoid persistent capture; conversational continuity is reduced (design §4). (c) Never leave cloud — the council split cloud-first only behind runtime consent and acceptable data terms (`docs/delivery/council.md`:207 area).
- **Implications:** Cloud models are permitted for development, not automatically for runtime microphone or personal-context transmission; provider retention is disclosed separately and may not expose user-facing deletion.
- **Source evidence:** [Discovery brief](docs/delivery/super-agent-brief.md):79-81, :18-22; [Council](docs/delivery/council.md):136-139, :182-193.
- **Reopen:** Explicit user opt-in to recording/transcripts with an approved bounded retention rule; or passing private-native measurements ([RT-012](tasks/012-private-native-audio-feasibility.md)) after separate approval.

### DEC-11

Backend-only external secrets; authenticated loopback with strict browser-origin and request boundaries.

- **Status:** Contracted security requirement; not a property already implemented.
- **Rationale:** Long-lived credentials stay in a backend OS vault or externally supplied environment, never in browser code, project files, URLs, logs, or model context; loopback alone is not enough because a malicious website must not be able to create sessions or jobs (`docs/delivery/council.md`:69-72, :200; [REQ-11](prd.md#req-11), [REQ-12](prd.md#req-12)).
- **Alternatives and trade-offs:** (a) Browser-held tokens — the contracted prohibition covers **long-lived provider/project/tool credentials in browser code** ([REQ-12](prd.md#req-12)), not every browser-held token: a future adapter design may propose a reviewed short-lived, scoped session credential (lower credential exposure), which still requires explicit expiry, authentication, and exposure design plus a separate security review — no browser-held token implementation is approved here (`docs/delivery/super-agent-brief.md:105-106`). (b) Trusting localhost without Host/Origin/CORS/WS/CSRF checks — rejected: cross-site and forged-control attacks target loopback servers exactly.
- **Implications:** No credential reading or vault change is authorized in this documentation delivery; compromise of the already-authenticated host/browser is a distinct threat boundary; deployed negative tests are mandatory ([RT-A05](prd.md#rt-a05)).
- **Source evidence:** [Council](docs/delivery/council.md):69-72, :200; [Discovery brief](docs/delivery/super-agent-brief.md):49-50.
- **Reopen:** A reviewed future threat model requiring a materially different boundary — a design-stage re-review, not a runtime change of scope.

### DEC-12

Externally enforced budgets and admission limits; provisional targets only; keep CPU work off audio/control processing.

- **Status:** Contracted enforcement principle; all numeric values are provisional proposals.
- **Rationale:** Budgets, admission, deadlines, steps, and retries must be enforced outside models (`docs/delivery/council.md`:57-60, :202-203), and CPU-heavy work must not block audio/control processing (`docs/delivery/council.md`:133-134).
- **Alternatives and trade-offs:** (a) Model/self-enforced budgets — not enforceable. (b) No caps until tasks demand them — unbounded spend and resource risk from the first session.
- **Implications:** Today's budget and retention values are unset and unapproved; approval belongs to the dated RT-001/RT-G00 setup decision, not to any pack author. Provider billing acknowledgments can lag, so reserves are conservative and unsafe automatic retries are disabled.
- **Source evidence:** [Council](docs/delivery/council.md):57-60, :133-134, :202-203; [Discovery brief](docs/delivery/super-agent-brief.md):71-74.
- **Reopen:** An explicitly approved change of limits, or measured evidence that provisional targets/limits are miscalibrated, reported with disposition rather than silently relaxed.

### DEC-13

Add an explicitly bounded planner only after the deterministic voice/job slice and approval of real task capabilities.

- **Status:** Deferred.
- **Rationale:** Fixed demo functions demonstrate state/safety mechanics, not useful autonomous reasoning; the planner increment requires an approved real task pair exactly so usefulness is compared against a baseline (`docs/delivery/council.md`:162-165, :219-220; [REQ-16](prd.md#req-16)).
- **Alternatives and trade-offs:** (a) Build the planner first — would claim autonomy the slice cannot prove. (b) Never add a planner — hollows out the overall purpose; the phase is deferred, not removed.
- **Implications:** [PH-04](phases.md#ph-04) requires accepted fixed-slice evidence plus user-approved real-task and recipient capabilities; a planner proposes but cannot directly execute or enlarge grants — the same admission, budget, verification, and cancellation contracts apply.
- **Source evidence:** [Council](docs/delivery/council.md):162-165, :215-220; [Discovery brief](docs/delivery/super-agent-brief.md):8-10, :29.
- **Reopen:** Activation, not a defect: the deferred work begins when the fixed slice is accepted (RT-G04) and the user separately approves the real task pair and worker/recipient capabilities (RT-009).

### DEC-14

OpenCode V2 may later be an OS-contained worker adapter, not the assumed voice transport or sandbox.

- **Status:** Deferred.
- **Rationale:** OpenCode v2.1.2 discovery returned HTTP 404 for its experimental voice route, and a reachable router port proves only port availability (`docs/delivery/super-agent-brief.md`:47-57); its permission model is not OS containment and event streams need reconciliation (`docs/delivery/super-agent-brief.md`:106-110; `docs/delivery/council.md`:159-165).
- **Alternatives and trade-offs:** (a) Use OpenCode as the voice transport now — unproven and failing that recorded route. (b) Treat prompt permissions as a sandbox — false boundary.
- **Implications:** No route/contact is claimed; version/access/child-scope/event-reconciliation evidence is required ([RT-010](tasks/010-contained-opencode-adapter.md)).
- **Source evidence:** [Discovery brief](docs/delivery/super-agent-brief.md):47-57, :106-110; [Council](docs/delivery/council.md):159-165, :234-237.
- **Reopen:** Demonstrated OS containment, least privilege, restricted credentials/egress, independent child-scope enforcement, and version/capability tests passing under a separate capability request.

### DEC-15

Defer desktop packaging, wake detection, locked-screen operation, always-on hosting, and private native deployment guarantees.

- **Status:** Deferred feasibility/authorization work.
- **Rationale:** Wake detection and locked-screen/background listening add complexity before the first experiment (`docs/delivery/council.md`:73-75, :126-139); a sleeping/off host cannot continue processing jobs merely because a ledger exists (`docs/delivery/council.md`:152-153, :207); the observed hardware's native local feasibility was never benchmarked (`docs/delivery/super-agent-brief.md`:43-46).
- **Alternatives and trade-offs:** (a) Build desktop/wake support now — richer ambient experience, added complexity and risk before the slice. (b) Promise always-on operation — requires the user's separate approval of an always-on host.
- **Implications:** First experience is hands-free within an active session only; no native-local or locked-screen/always-on guarantee ([REQ-17](prd.md#req-17), [REQ-18](prd.md#req-18)).
- **Source evidence:** [Council](docs/delivery/council.md):73-75, :126-139, :152-153; [Discovery brief](docs/delivery/super-agent-brief.md):43-46.
- **Reopen:** A separate device/host/security/power decision ([RT-011](tasks/011-always-on-and-desktop-feasibility.md)) or passing private-native hardware/quality/latency/egress benchmarks ([RT-012](tasks/012-private-native-audio-feasibility.md)), each with its own approval.

### DEC-16

No current build commands; future commands remain proposed/non-runnable until a separately approved scaffold exists. Record diagnostics without claiming they tested voice.

- **Status:** Contracted documentation honesty.
- **Rationale:** There is no application, manifest, or scaffold (`docs/delivery/super-agent-brief.md`:4, :41-42), so discovery is not deployed software; a published capability that was not run is documented/unexecuted, and the recorded OpenCode HTTP 404 is a diagnostic observation, not voice success (`docs/delivery/super-agent-brief.md`:51-57).
- **Alternatives and trade-offs:** (a) Include runnable install/test commands — would require scaffold/dependencies that are not authorized; future `npm`-style names stay proposals with prerequisites and "execution evidence: none". (b) Omit recorded diagnostics — loses the only recorded runtime-relevant evidence of the discovery phase.
- **Implications:** [build.md](build.md) records the 404/port-reachability caveats verbatim in spirit; a future successful build will not be proof of native access, safety, or latency.
- **Source evidence:** [Discovery brief](docs/delivery/super-agent-brief.md):4, :47-57; design §2.12 ([docs/design/super-agent.md](docs/design/super-agent.md):366-378).
- **Reopen:** A separately approved scaffold request; then replace proposals with actual commands from opened manifests/scripts, with dated execution evidence.

### DEC-17

Adopt repository-only automation (Husky hooks and an AI-agent pull-request template) without authorizing an application scaffold or runtime work.

- **Status:** Contracted repository tooling, added at the user's explicit request on 2026-11-07; not a runtime or provider decision.
- **Rationale:** AI agents will push changes, so local hooks catch forbidden credential files, high-confidence secret patterns, unresolved conflict markers, oversized files, broken Markdown links/anchors, and non-conventional commit messages before they reach the remote. A pull-request template makes agent identity, verification evidence, safety checks, runtime impact, and human approval explicit.
- **Alternatives and trade-offs:** (a) No hooks — fewer moving parts, but quality and safety checks depend on each agent remembering them. (b) CI-only enforcement — central and hard to bypass, but slower feedback and requires remote configuration. (c) Husky — one small development dependency, standard Git hooks, local feedback; requires Node/npm and `npm ci` after clone.
- **Implications:** `package.json`, `package-lock.json`, `.husky/`, and `scripts/` now exist for tooling only. `npm run check` is runnable and validates the repository; it does not build, test, or run the assistant. Application commands in [build.md](build.md) remain proposed/non-runnable. Runtime gates RT-G00–RT-G05 remain open.
- **Source evidence:** Explicit user request in this session (2026-11-07); `.github/pull_request_template.md`, `.husky/pre-commit`, `.husky/commit-msg`, `.husky/pre-push`, `scripts/check-repo.mjs`, `scripts/check-commit-msg.mjs`; [build.md](build.md).
- **Reopen:** A decision to remove or replace Husky, add CI enforcement, or expand hooks to application tests after an approved scaffold.

### DEC-18

Replace the blanket ban on assistant capabilities with a capability ladder: authority grows one tier at a time, each tier only after its own approved design.

- **Status:** Proposed 2026-11-12 by `jeevesh2515`. Not in force until `abhishek3059` approves in the PR that carries it ([approval record](docs/approvals/capability-ladder-decision.md)). It authorizes no runtime work by itself.
- **Rationale:** The product goal is a personal assistant that talks like a person, advises on productivity, and does day-to-day work for its owner. A fixed-worker-only rule ([REQ-08](prd.md#req-08)) cannot reach that goal. A single switch that opens everything would remove the main defense against prompt injection, which is the main threat to a voice agent that reads email and web pages.
- **The ladder:**

  | Tier | Capability | Gate to enable |
  | --- | --- | --- |
  | T0 | Conversation, coaching, planning, advice. No tools, no personal data access. | Data-boundary and cost decision (R-A.2). |
  | T1 | Read-only access to calendar, email, notes, and allowlisted folders. | Approved design plus independent security review (R-A.4), after the PH-02 policy layer exists. |
  | T2 | Reversible writes: drafts, calendar events, reminders, notes, files in a sandbox folder. Logged, with an undo path. | Approved design plus review (R-A.6), after the PH-03 stop controls exist. |
  | T3 | Consequential actions: sending email or messages, allowlisted shell commands, browser actions, moving files to trash. Each action needs on-device approval. | Approved design plus review (R-A.8), after the PH-03 stop controls exist. |
  | T4 | Purchases, money movement, credential handling, permanent deletion. | Stays disabled. Each needs its own separately approved design. |

- **Invariants that do not change:** loopback-only API with a token ([REQ-11](prd.md#req-11)); voice is not identity, and voice alone never approves a T3 action ([REQ-09](prd.md#req-09), [DEC-07](#dec-07)); limits, scopes, recipients, and budgets are enforced in code, outside the model ([REQ-10](prd.md#req-10)); content from email, web pages, files, and tool output is data and never instructions; fail closed; every action is logged; an emergency stop always works.
- **Alternatives and trade-offs:** (a) Keep REQ-08 as written: safest, but caps the product at demos. (b) Open all capabilities at once: fastest, but one injected email could send messages or run commands as the owner. (c) The ladder: slower, but each step is reviewed on its own and can be rolled back alone.
- **Implications:** [REQ-08](prd.md#req-08) and [AGENTS.md](AGENTS.md) section 5 are amended to point here. Real voice and personal data going to a cloud provider needs the decision in R-A.2, because the PH-00 boundary kept personal microphone audio local and a free tier may train on inputs ([REQ-13](prd.md#req-13)). The $0 cap may need a decision for a paid tier, which needs both maintainers. The fixed workers in PH-02 and PH-03 are unchanged and stay the first implementation. Roadmap items are in parallel track A of [roadmap.md](roadmap.md); no phase moves.
- **Source evidence:** `jeevesh2515` in chat with Claude Code, 2026-11-12, asking for max-capability use as the project's CTO; [AGENTS.md](AGENTS.md) sections 5 and 10.
- **Reopen:** Any tier's design review fails or an incident occurs at that tier (drop back one tier); or the maintainers decide to add, merge, or remove a tier.

### DEC-19

Replace the required human review on `develop` with one shared AI reviewer that both maintainers run: [.claude/agents/reviewer.md](.claude/agents/reviewer.md).

- **Status:** Proposed 2026-11-12 by `abhishek3059`. Not in force until `jeevesh2515` approves in the PR that carries it ([approval record](docs/approvals/shared-ai-reviewer-decision.md)). After both approve, `abhishek3059` removes the required approving review from the `develop` ruleset.
- **Rationale:** The maintainers work in different time zones, so waiting for a human review stalls every PR. The quality gate in [AGENTS.md](AGENTS.md) section 9 already existed, but each agent scored itself or picked its own reviewer, so scores were not comparable across machines and tools. One committed reviewer, run in a fresh context with a fixed rubric (and a fixed model within Claude Code), makes the gate the same for every PR. Other tools use their own model and record it in the report.
- **Alternatives and trade-offs:** (a) Keep the required human code-owner review: strongest check, but blocks for a day per PR across time zones. (b) No review: fastest, but nothing independent checks evidence before a roadmap tick. (c) A shared AI reviewer, run locally: free under the $0 cap and uniform, but a model can miss what a person would catch. (d) A hosted reviewer in CI or GitHub Agent HQ: automatic, but costs money against the $0 cap.
- **Implications:** AGENTS.md sections 3, 9, and 11 rule 7, [CONTRIBUTING.md](CONTRIBUTING.md), the PR template, and roadmap item R-R.4 point to the shared reviewer. The **Repository checks** status check stays required. [.github/CODEOWNERS](.github/CODEOWNERS) still requests reviews, but they no longer block merging. The changes listed in AGENTS.md section 3 still need both maintainers (a paid service, moving a gate or phase, a roadmap exception, and, added by this decision, a change to an AGENTS.md rule or a DEC entry), and the reviewer returns REVISE without them. The reviewer's Bash access is read-only by instruction in its file, not by tool permissions. Maintainers can still review any PR by choice.
- **Source evidence:** `abhishek3059` in chat with Claude Code, 2026-11-12 ([approval record](docs/approvals/shared-ai-reviewer-decision.md)).
- **Reopen:** A defect reaches `develop` that the reviewer passed; a dishonest roadmap tick is found; or either maintainer asks to bring human review back.

## Register fields

Every DEC entry from [DEC-01](#dec-01) to [DEC-19](#dec-19) above carries the seven contracted fields inline: status, rationale, alternatives and trade-offs, implications, source evidence, and reopen conditions. This summary restates the register; it does not replace the individual records.

## Provisional and post-review status

[DEC-04](#dec-04) is conditional; [DEC-06](#dec-06) records a provisional post-review Researcher follow-up candidate, not a re-voted council consensus and not a tested or approved runtime selection; [DEC-13](#dec-13), [DEC-14](#dec-14), and [DEC-15](#dec-15) are deferred; [DEC-17](#dec-17) is repository tooling only; [DEC-18](#dec-18) is proposed and not yet approved by both maintainers. None of these statuses is a runtime approval, and no decision in this register claims tested access or an approved provider.

See [Native transport research](docs/design/super-agent.md) in the signed design and the council meeting records.
