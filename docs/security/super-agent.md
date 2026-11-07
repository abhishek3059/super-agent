PASS

# Super-agent — independent design-stage security assessment

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Verdict | **PASS** — no CRITICAL or HIGH finding; the assessed documentation proposes a boundary that is honest about what it does not control |
| Scope | **Documentation/design-stage only.** The proposed architecture, policy, data-handling and release gates. No runtime implementation, provider, account, deployment or build is certified |
| Assessed revision | Signed design **revision 1** (`docs/design/super-agent.md`, 488 lines) plus the review revision-3 correction set; pack files self-declare revision 2 (see INFO-01) |
| Contract integrity | Design SHA-256 independently recomputed: `A895DB99B560A835F664872501F9304C39CC503930352C1355A7F8D842BF91A5` — matches the hash recorded by both review reports |
| Assessor | Security & Compliance, independent of developer and reviewer; configured profile **`opencode/deepseek-v4.1-flash-free`** (declared by assignment, not a runtime voice-model choice), distinct from the reviewer's `agentrouter/gpt-6-astra` and the developer's `opencode/flint-40b-free` / `opencode/glm-5.3-flash-free` |
| Evidence base | All 31 workspace Markdown files read in full; 24 requested pack targets + signed design + two delivery sources + implementation report + manager record + both review reports |
| Independence | The reviewer's PASS was not treated as evidence. The sources, the design and the pack were re-read, and this disposition was reached from those documents. Findings below are not restatements of the review |

**This report supplies a design-stage security disposition only.** It does not certify any control as implemented, does not test authentication, authorisation, billing, media handling, retention or performance, and does not approve runtime microphone/context egress, spending, a provider, a host or an always-on deployment. Runtime security behaviour is intentionally absent and is recorded below as residual risk and an open release gate, not as a manufactured implementation defect.

## 1. Present attack surface of this change

The workspace contains **only Markdown**: 31 `.md` files, no `.git`, no application scaffold, no manifest, lockfile, script, binary, configuration, model, recording or credential. There is no executable surface to attack in this change, and no dependency or supply-chain delta. A secret-pattern scan over every `.md` found no credential material (one regex false positive on a latency-target table row); no absolute user/AppData paths appear.

The reviewable security object is therefore the **proposed future boundary** and the policy the future implementation will be held to. An attacker's routes into that proposed system, and where the documents address them:

| # | Attacker route | Specified control (document location) | Status |
| --- | --- | --- | --- |
| A1 | Malicious website drives the loopback API/WS: creates sessions or jobs, forges controls | Loopback-only listener + exact Host allowlist; exact Origin for mutations and WS handshake; CSRF defence on cookie-auth mutations; WS messages authorised as well as the upgrade; no wildcard credentialed CORS; no native session from an anonymous request (`docs/design/super-agent.md:269`, `:209`, `prd.md:84`, `architecture.md:136`, `taks/002-local-scaffold-and-boundary.md:36`) | Specified; untested (RT-G01/RT-A05) |
| A2 | Ambient, replayed or synthetic voice induces work or approval | Voice is not identity; grants only within existing authenticated scope; no new authority by voice; expiry; visible controls; ambient "yes" cannot re-arm the latch (`docs/design/super-agent.md:234`, `:413`, `prd.md:76`, `:201`, `flow.md:120`) | Specified; accepted residual for *low-risk* work inside a grant |
| A3 | Injected content in transcripts, documents, pages or worker output escalates capability | Treated as data, not grant instructions; broker validation against fixed capability/dataset IDs; typed proposals; no prompt-based enforcement (`docs/design/super-agent.md:259`, `:271-272`, `flow.md:138-146`, `architecture.md:40`) | Specified; untested |
| A4 | Browser-direct provider session / stolen browser credential exfiltrates audio | Backend owns session creation and termination; thin frontend, no long-lived keys; a future short-lived scoped credential is permitted only with expiry/auth/exposure design **and a separate security review**; provider-side client permissions must be verified, not assumed (`docs/design/super-agent.md:190`, `:270`, `:273`, `descisions.md:148`) | Partly client-enforced; correctly gated |
| A5 | Forged browser event echoes become task truth; backend control channel fails | Backend sideband is sole execution/result owner; browser echoes are captions/control requests; execution fails closed if the required control channel is unhealthy (`docs/design/super-agent.md:163`, `architecture.md:73`) | Specified; untested |
| A6 | Worker code with host authority, arbitrary code, shell, plugins | Only fixed reviewed read-only synthetic functions; no network egress; threads/processes are scheduling isolation, not containment; OpenCode needs demonstrated OS containment, least privilege, child-scope and egress tests (`docs/design/super-agent.md:181`, `:274`, `:415`, `taks/005-fixed-sample-workers.md:15`, `taks/010-contained-opencode-adapter.md:15`) | Specified; untested |
| A7 | Credential theft from browser, project, logs, prompts or URLs | Backend OS vault / injected environment only; no permanent secrets in browser storage, URLs, prompts, records, telemetry or repository (`docs/design/super-agent.md:270`, `prd.md:88`, `descisions.md:147`) | Specified; verified absent from this pack |
| A8 | Provider-side retention / abuse logging beyond local deletion | Named recipients and terms; no-training ≠ no-retention; abuse logs up to 30 days; ZDR/MAM eligibility-gated; no stored-session deletion endpoint claimed; provider recording off (`docs/design/super-agent.md:150`, `:165`, `:304`, `council meetings/council-meeting-3.md:78`) | Disclosed; RT-G00 consent gate |
| A9 | Local unprivileged process reaches loopback | Authentication required and bound to subject/session/grant; revocation on logout/expiry (`docs/design/super-agent.md:268`) — but credential strength and failed-auth handling are unspecified (LOW-01) | Partial; see LOW-01 |
| A10 | Runaway spend or recursive work | Reservations before chargeable work; caps, deadlines, steps, retries, concurrency enforced outside models; children/revisions do not reset budgets (`docs/design/super-agent.md:292`, `:245`, `taks/004-task-ledger-and-policy.md:40`) | Specified; untested |
| A11 | Supply chain | No dependencies today; future stack and dependency choices belong to a separately authorised scaffold review; thin frontend without unnecessary third-party scripts (`docs/design/super-agent.md:172`, `:273`) | Correctly deferred |

## 2. Findings

No CRITICAL, HIGH or MEDIUM finding was identified. Three non-blocking items follow. None is a claim that a stated control is bypassed; none changes the verdict.

### LOW-01 — Loopback credential strength and failed-authentication handling are unspecified

- **Location:** `docs/design/super-agent.md:268`; `architecture.md:135`; acceptance wording at `taks/002-local-scaffold-and-boundary.md:36` and `prd.md:201`.
- **What is missing:** the contract requires "a locally established device/session credential" and tests that unauthenticated clients, hostile origins and incorrect Hosts are denied. It sets no minimum entropy, no rotation, no failed-attempt throttling or lockout, and no distinction between a high-entropy device secret and a user-chosen PIN. `docs/design/super-agent.md:271` requires message size/rate validation, which may slow guessing but is not authentication-failure handling.
- **Concrete path:** a future scaffold implements the credential as a short numeric PIN (permitted by the written gate), applies Origin/Host checks, and passes RT-A05 as written. Any local process on the same host can then reach loopback and guess the PIN online, create a session and admit jobs within the existing grants.
- **Impact and why LOW:** the effect is bounded — fixed read-only synthetic workers, no shell/purchases/messages/deletion, voice cannot add authority, budgets are capped, and results are synthetic. The realistic attacker needs local code execution on the host, which the pack already declares a different threat boundary (`descisions.md:149`, `docs/design/super-agent.md:414`). The defect is a specification/acceptance gap, not an exploitable bypass of a claimed control.
- **Recommended action:** add credential-strength, storage, rotation and failed-auth throttling to RT-002/RT-A05 acceptance before scaffold approval. Does not block this documentation-stage PASS.

### INFO-01 — Disposition and status fields are stale relative to the actual review and this assessment

- **Location:** `prd.md:7` ("independent re-review pending"); `progress.md:9`, `:18`, `:29-31` ("re-review and security assessment pending", "not yet supplied"); `docs/delivery/super-agent.md:10-11` and `:24` ("No verdict recorded").
- **Effect:** a reader could conclude no independent review or security disposition exists, while the review report now records PASS and this report supplies the security disposition. DOC-A06 requires actual dispositions to be reflected faithfully (`docs/design/super-agent.md:451`).
- **Security impact:** none — no control is claimed that does not exist; the records understate rather than overstate assurance.
- **Action:** the delivery manager should record both dispositions and correct these pointers before PH-DOC final acceptance. The manager record is already designated authoritative and awaiting post-verdict update.

### INFO-02 — WF-01 acceptance references omit the local-attack-surface test

- **Location:** `flow.md:47` (WF-01 lists RT-A01 and RT-A02 only).
- **Effect:** setup/activation is precisely where session creation and the loopback boundary are exercised, yet the workflow does not cite RT-A05 (`prd.md:201`).
- **Security impact:** none — REQ-11 (`prd.md:84`) and RT-A05 bind the deployed boundary globally, and RT-002 already requires hostile-origin/Host rejection (`taks/002-local-scaffold-and-boundary.md:36`). This is a traceability omission, not a lost control.

### INFO-03 — Emergency stop does not explicitly restate clearing of ephemeral transcript context

- **Location:** `flow.md:110-120` and `docs/design/super-agent.md:216`; contrast `flow.md:151`.
- **Effect:** emergency stop closes the native transport, which implies session end and context clearing under WF-10, but the strongest stop does not state it. No attacker path exists; this is privacy hygiene and consistency.

## 3. Privacy compliance — item by item

Assessed against the project contract as stated for this workspace. "Honoured" means the proposed contract and its gates state the obligation correctly; **no item is implemented or tested**.

| Contract item | Assessment | Evidence |
| --- | --- | --- |
| No cloud telemetry; no model-content telemetry | Honoured — no telemetry component is proposed; model-content telemetry is off by default and forbidden in records | `docs/design/super-agent.md:302`, `prd.md:96`, `architecture.md:137`, `descisions.md:136` |
| Loopback only; no LAN or remote hosting | Honoured — listener addresses and accepted Hosts restricted to configured loopback; any always-on/remote host is a separate deferred decision | `docs/design/super-agent.md:269`, `architecture.md:136`, `prd.md:112`, `taks/011-always-on-and-desktop-feasibility.md:15` |
| No screen-content capture | Absent by design — no screen-capture capability is proposed or authorised anywhere; initial exclusions bar general computer control | `prd.md:145` |
| No local raw-audio recording | Honoured — transient buffers only; mic-stop discards unsent buffers; no capture in this request | `docs/design/super-agent.md:298`, `:162`, `flow.md:99-107` |
| No persistent transcripts | Honoured — native transcript context in memory, bounded, cleared at session end; deltas/whole prompts not logged | `docs/design/super-agent.md:299`, `:306` |
| Provider stored-session recording off | Honoured — off in the initial slice; stored-session forks explicitly rejected as recovery | `docs/design/super-agent.md:165`, `:306` |
| Task/WAL/backup metadata retention bounded | Honoured as a **gate** — WAL, diagnostics, crash reports and backups covered by the same rules; windows and deletion procedure must be approved before a durable runtime; correctly unresolved today | `docs/design/super-agent.md:301-302`, `:306`, `prd.md:157`, `taks/007-recovery-and-retention.md:39` |
| Expired retries rejected, not re-admitted as new intent | Honoured | `docs/design/super-agent.md:306`, `flow.md:157` |
| Runtime microphone/context egress needs named consent; development-model permission is not consent | Honoured — stated in the brief, the PRD, the decision register and RT-G00 | `docs/delivery/super-agent-brief.md:18-22`, `prd.md:92`, `descisions.md:94`, `docs/design/super-agent.md:461` |
| Browser media egress and backend/worker context egress are separate consent boundaries | Honoured — two data paths with distinct recipients | `docs/design/super-agent.md:187-188`, `architecture.md:48-51` |
| Provider retention disclosed independently; no-training is not no-retention; abuse logs; ZDR/MAM eligibility | Honoured — 30-day abuse-log default, legal/safety exceptions, ZDR/MAM eligibility and prior approval, no public stored-session deletion endpoint claimed | `docs/design/super-agent.md:150`, `:304`, `council meetings/council-meeting-3.md:78` |
| No permanent secrets in browser/project/URLs/logs/prompts | Honoured — backend vault or injected environment; verified no credential material in the pack | `docs/design/super-agent.md:270`, `prd.md:88`, `descisions.md:147` |
| Transient native transcript context for client delegation permitted, disclosed, not persisted | Honoured — and explicitly distinguished from an external STT/chat/TTS chain | `docs/design/super-agent.md:159-160`, `descisions.md:45-50` |
| No silent provider or text-voice fallback | Honoured | `prd.md:44`, `docs/design/super-agent.md:251`, `flow.md:40` |
| No false "private" claim; local database ≠ private | Honoured — the "local database = private" position is explicitly rejected | `descisions.md:137`, `docs/design/super-agent.md:407` |
| No performance or always-on claim on the observed 4 GiB laptop | Honoured — targets provisional; sleep cannot run jobs; locked-screen/always-on deferred | `prd.md:108`, `docs/design/super-agent.md:290`, `:344`, `taks/011-always-on-and-desktop-feasibility.md:15` |
| GPT-Live provisional, post-review, not whole-council approval; Gemini eligibility-qualified (unpaid and paid data warnings) | Honoured — labelled as later research, not a re-vote; Gemini remains eligibility-gated, not prohibited, with the unpaid-service warning and paid-use processing/logging preserved | `docs/design/super-agent.md:152`, `:155`, `council meetings/council-meeting-3.md:42-51`, `council meetings/council-meeting-2.md:54-62` |

No privacy overclaim was found. A scan for "fully private", "end-to-end", "guarantee", "production-ready", "no data leaves" and "provider approved" returned only negations and explicit non-claims.

## 4. Residual risk and release gates

What this assessment could not establish, and which therefore remains open:

1. **Every runtime control is untested.** Authentication, Host/Origin/CORS/WS/CSRF enforcement, media lifecycle, fail-closed control channel, stop semantics, idempotency/races, budget accounting, retention purge (including WAL/backups), containment, latency and hardware behaviour have no evidence. Gates RT-G00–RT-G05 and tests RT-A01–RT-A06 remain open (`docs/design/super-agent.md:459-477`).
2. **The browser is the media egress owner.** No server-side policy can fully constrain a compromised page or a provider session that the browser is authorised to open; the design says so and requires deployed verification of provider client permissions rather than assuming them (`docs/design/super-agent.md:190`, `:273`). RT-G01/RT-A01 must supply that evidence before any microphone transmission is approved.
3. **Provider terms, eligibility, retention and account access were not re-verified.** No external page was fetched and no account or model API was contacted in this pass; the documents' citations and dates were checked against the local sources only.
4. **Local native feasibility, locked-screen operation and always-on hosting remain unproven** on the observed ~7.8 GiB / ~4 GiB GPU machine; sleep/off cannot execute jobs (`prd.md:108`, `docs/design/super-agent.md:290`).
5. **No provider, budget, retention window, first real task pair or host is approved.** RT-G00 is unresolved and must not be treated as passed.
6. **LOW-01 should be closed inside RT-002/RT-A05 acceptance** (credential strength, storage, rotation, failed-auth throttling) before scaffold acceptance.
7. **No Git baseline exists.** Authorship, history and byte-preservation claims cannot be diff-verified; only current file contents were assessed.
8. **DOC-A06 / PH-DOC acceptance is not closed by this report alone.** The manager must record the review PASS and this security PASS for the assessed revision and reconcile the stale status pointers (INFO-01).

## 5. Checks actually performed

- Read in full: the signed design (488 lines), both delivery sources, the PRD, architecture, phases, progress, build, decision register, workflows, task index and all twelve task files, all three council meetings and their index, the implementation report, the manager record, and both review reports.
- Recomputed the design SHA-256 and matched it to the hash recorded in both review reports.
- Confirmed the 24 requested targets exist at the literal paths (including `taks/` and `descisions.md` and `council meetings/`), with no `tasks/` or `decisions.md` duplicates; confirmed no non-Markdown file, scaffold, manifest or `.git` directory, hidden files included.
- Secret-pattern scan across all Markdown (`sk-`, `ghp_`, `AKIA`, `Bearer`, `api_key`/`password` assignments, private-key blocks, `xox*`): no credential material; one false positive on a latency-target row.
- Scanned for absolute user-profile/AppData paths: none. Scanned for privacy/security overclaims: only explicit negations.
- Traced the security-relevant obligations named in the assignment (voice not identity, absent high-risk tools, OpenCode OS containment, loopback auth/Origin/CORS/CSRF, browser secrets, separate egress boundaries, sideband ownership, provider mute vs local mic-stop, startup gating, emergency re-arm, cancellation races, idempotency/revisions/epochs/budget non-reset, evidence-before-completion, thinking-context prohibition, retention/retry expiry, abuse-log/ZDR caveats, hardware/always-on limits, provisional provider status) to specific design, PRD, flow, decision and task lines.

**Not performed:** no code, build, test, install, dependency, Git, credential/private/global-file, model API, cloud runtime or audio activity; no external URL fetch; no nested agents; no source, review, design or global configuration modified. Only `docs/security/super-agent.md` was written.

## 6. Verdict

**PASS.** The assessed documentation proposes a boundary that keeps execution truth, authority and budgets outside the model; treats voice, transcripts, documents and worker output as untrusted data; specifies the localhost browser-origin defences, secret handling, distinct stop semantics, sideband ownership and fail-closed startup; and states plainly that no control is implemented and that provider retention, hardware feasibility, budgets and consent are unresolved. The three findings above are non-blocking; none is exploitable at this stage because no runtime exists, and LOW-01 is an acceptance-wording gap to close before the scaffold is approved.

This PASS is a design-stage documentation disposition. It does not certify future code, and it does not close RT-G00 through RT-G05.
