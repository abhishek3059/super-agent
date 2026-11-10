# Super-agent — signed architecture and documentation contract

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Revision | 1 |
| Author | Solution Architect |
| Configured architect profile | `agentrouter/gpt-6.1-sol#max`, as declared in this assignment; not a runtime voice-model selection |
| Status | Signed design, ready for independent design review and design-stage security assessment |
| Current delivery | Documentation only; no application implementation, provisioning, or deployment |
| Source documents | [Discovery brief](../delivery/super-agent-brief.md), fully read, lines 1–110; [council deliberation](../delivery/council.md), fully read, lines 1–237 |
| Authority of signature | Defines the documentation contract and proposed future architecture. Does not approve runtime egress, spending, capabilities, or a scaffold. |

## 1. Problem

The user wants a personal, hands-free assistant that converses through native live audio, delegates overlapping background tasks, accepts steering and interruption, and reports real outcomes within explicit authority and resource limits—not a mandatory external STT → text-chat → TTS conversational chain (`docs/delivery/super-agent-brief.md:8-22`, `docs/delivery/super-agent-brief.md:61-87`). The immediate request, however, is to document requirements, architecture, phases, progress, tasks, council proceedings, build instructions, decisions, and flows. The source describes discovery, not an implemented assistant (`docs/delivery/super-agent-brief.md:4`, `docs/delivery/council.md:4`). This contract therefore specifies a maintainable documentation pack and a clearly proposed future runtime, preventing architectural recommendations, public API descriptions, development-model permission, and synthetic demonstrations from being mistaken for implemented software, approved microphone transmission, proven autonomy, or verified performance.

## 2. Approach

### 2.1 Scope, evidence, and decision authority

Use the existing Markdown documentation approach. There are no application conventions to extend: the brief records an initially empty project without an application, repository history, tests, or stack conventions (`docs/delivery/super-agent-brief.md:41-42`). The delivery instructions confirm that the current workspace is documentation-only and not a Git repository. No Git initialization is required or authorized.

This assignment changes **only this design document**. A separately commissioned documentation developer produces the pack below. Neither operation creates source files, package configuration, scripts, tests, models, recordings, dependencies, or credentials. Runtime work requires a subsequent explicit implementation request and the runtime gates in section 6.

The literal paths come from the latest user request supplied with this assignment, not from an invented existing file layout. Preserve `tasks/`, `council meetings/`, and `descisions.md`. Do not introduce silently corrected duplicates such as `tasks/` or `decisions.md`.

Every document must distinguish:

| Evidence class | Meaning and permitted language |
| --- | --- |
| Recorded observation | Something documented by discovery, cited to the source and dated; not necessarily rerun here. |
| Public documentation observation | Published capability or terms, with official URL and check date; not authenticated account access or an integration test. |
| Contracted decision | The architect's documentation/design choice, subject to independent review; not user authorization of runtime operations. |
| Provisional proposal | Candidate transport, future stack, illustrative task, limit, or performance target requiring approval and/or measurement. |
| Unresolved gate | Missing consent, eligibility, access, budget, task choice, retention rule, or implementation evidence. Never describe it as passed. |

Grounding to preserve throughout the pack:

| Fact | Existing evidence |
| --- | --- |
| Native voice-to-voice is required; structured task text remains allowed. | `docs/delivery/super-agent-brief.md:12-16`; `docs/delivery/council.md:174-176` |
| Cloud models are permitted for development, not automatically for runtime microphone or personal-context transmission. | `docs/delivery/super-agent-brief.md:18-22`; `docs/delivery/council.md:13-15` |
| First real task categories, deployment host, actual native model/account, region, quota, and pricing are unresolved. | `docs/delivery/super-agent-brief.md:29-35`; `docs/delivery/council.md:184-185` |
| Current observed Windows machine has about 7.8 GiB usable RAM, an i5-10300H, and a GTX 1650 Ti reporting about 4 GiB memory. Native local feasibility was not benchmarked. | `docs/delivery/super-agent-brief.md:43-46` |
| First experiment is a manually activated localhost browser and one backend, with two trusted fixed sample functions and a small store. It is hands-free in an active session, not always-on. | `docs/delivery/council.md:64-75`; `docs/delivery/council.md:123-135` |
| Host shell, purchases, messages, deletion of user files, and general computer control are not authorized initial capabilities. | `docs/delivery/super-agent-brief.md:36-37` |
| Voice is not identity; policy, execution truth, budgets, and verification must live outside model instructions. | `docs/delivery/super-agent-brief.md:68-78`; `docs/delivery/council.md:50-60` |
| Local recordings/transcripts are off by default. Minimal task records still require retention/deletion rules; provider logs are separate. | `docs/delivery/super-agent-brief.md:79-81`; `docs/delivery/council.md:190-193` |
| OpenCode v2.1.2 discovery returned HTTP 404 for its experimental voice-model route. A reachable router port does not prove model access. | `docs/delivery/super-agent-brief.md:47-57`; `docs/delivery/council.md:234-237` |
| OpenCode workers are optional later; permissions are not OS containment, and event streams require reconciliation. | `docs/delivery/council.md:159-165`; `docs/delivery/super-agent-brief.md:106-110` |
| A sleeping/off execution host cannot continue processing jobs merely because a ledger exists. | `docs/delivery/council.md:152-155`; `docs/delivery/council.md:207` |

### 2.2 Documentation taxonomy and navigation

The requested pack contains **24 Markdown files**: seven root documents, two folder indexes, three council records, and twelve numbered future task files. These are target paths, not claims that the files already exist. Existing delivery sources remain unchanged. This design is an additional handoff artifact outside that count.

#### Root documents and folder indexes

| Literal target path / root navigation link | Canonical responsibility and required content |
| --- | --- |
| [prd.md](../../prd.md) | Requirements and acceptance criteria; user intent; current documentation scope versus future product; requirement IDs; initial exclusions; synthetic examples; unresolved runtime approvals. |
| [architecture.md](../../architecture.md) | Proposed logical components, trust boundaries, native media/control data paths, conceptual interfaces, authoritative job state, grants, budgets, reconciliation, retention, and future adapter seams. No assertion that these APIs exist. |
| [phases.md](../../phases.md) | Ordered milestone/phase plan; prerequisites and exit gates; task links; explicit initial `not started` status for every future phase. Link to progress for dated evidence rather than duplicating a permanently pending status. |
| [progress.md](../../progress.md) | Dated documentation-only milestone, artifact/revision evidence, independent review/security dispositions, unresolved gates, next owner/action. No runtime completion or passing test claims without evidence. |
| [build.md](../../build.md) | No current build; separately labeled recorded diagnostics; visibly proposed, currently non-runnable future command contract; prerequisites, consent gates, secret-handling rules, and future verification expectations. |
| [descisions.md](../../descisions.md) | Canonical decision register using the IDs below: status, rationale, alternatives, trade-offs, evidence, implications, and evidence that would reopen a decision. Keep the requested spelling. |
| [flow.md](../../flow.md) | Numbered Markdown workflows and state/transition tables; activation, native conversation, delegation, steering, all stop operations, denied requests, recovery, retention, and host lifecycle. No generated PDF/image or application diagram artifact is needed. |
| [tasks/README.md](../../tasks/README.md) | Future task index, ordering, dependencies, phase/requirement/decision IDs, task template, initial statuses, and distinction between documentation creation and future runtime implementation. |
| [council meetings/README.md](../../council%20meetings/README.md) | Provenance, panel/mode caveat, meeting index, dates, evidence links, and distinction between archived deliberation and later research. Spaces are literal filesystem characters; percent-encode them in links where appropriate. |

#### Council records

| Literal target path | Content contract |
| --- | --- |
| [council meetings/council-meeting-1.md](../../council%20meetings/council-meeting-1.md) | Faithful summaries of four independent opinions: Architect, Skeptic, Pragmatist, Researcher. Do not fabricate verbatim transcripts, timestamps, tested integrations, participant models, or additional votes. |
| [council meetings/council-meeting-2.md](../../council%20meetings/council-meeting-2.md) | Anonymized Response A–D / Reviewer A–D cross-review, exact source means and rankings, genuine disagreements, and the counterfactual pass. Do not invent individual raw scorecards from aggregate means. |
| [council meetings/council-meeting-3.md](../../council%20meetings/council-meeting-3.md) | Chair synthesis and resolutions first. A separately headed **post-review Researcher follow-up, not re-voted consensus** then records the provisional GPT-Live candidate and official-documentation checks. Do not attribute this later recommendation to all four original votes. |

#### Linking and maintenance rules

- Every root document provides a compact navigation block linking all seven root documents, both folder indexes, this design, and the two delivery sources. Nested files link their index, relevant root documents, and specific IDs. Use working relative links, not environment-specific absolute paths.
- `prd.md` owns requirements; `descisions.md` owns decisions; `architecture.md` owns the detailed job-state contract; `flow.md` applies it; task files own their scoped work description. Other documents summarize and link rather than maintaining competing full copies.
- Use stable explicit ID headings, for example `REQ-01`, `DEC-01`, `RT-001`, `PH-01`, and `WF-01`. Reference IDs as links to those headings. Retire an ID with a supersession note; do not renumber to hide a changed decision.
- Give each future task a status, scope, prerequisites, inputs, small deliverable, acceptance checks, failure/rollback considerations, requirement/decision links, and evidence field. Initially: **Status: not started; execution evidence: none**.
- Review/security reports are independent evidence, not authored conclusions to be manufactured by the documentation developer. Proposed handoff locations are `docs/delivery/super-agent-design-review.md` and `docs/delivery/super-agent-design-security.md`; these files are **not present in the source set read for this contract**. The delivery manager may supply different actual report paths. Use the real existing paths as authoritative links, explicitly identify design-stage versus implementation-stage assessments, and do not create fake reports to satisfy navigation.
- While reports are absent, `progress.md` states that evidence is absent and lists expected locations as planned references, not successful assessment links. Later update the status from dated report dispositions for the assessed revision. Council cross-review is not a substitute for the independent architecture review or security assessment (`docs/delivery/council.md:209-214`).

### 2.3 Requirement IDs and traceability

The following IDs are the minimum PRD contract. Documentation acceptance is separate from future runtime acceptance.

| ID | Requirement | Grounding / decision / future acceptance |
| --- | --- | --- |
| REQ-D01 | Deliver the literal, cross-linked documentation taxonomy; no scaffold or runtime actions in this request. | Latest delivery instruction; DEC-01, DEC-16; DOC-A01–DOC-A06 |
| REQ-D02 | Distinguish recorded evidence, published capability, proposals, approvals, and tests; preserve council provenance and accurate statuses. | `docs/delivery/council.md:95-117`, `docs/delivery/council.md:211-214`, `docs/delivery/council.md:234-237`; DEC-06; DOC-A02–DOC-A06 |
| REQ-01 | Native streaming audio input/output; no mandatory external STT/chat/TTS chain and no silent transport/provider fallback. | `docs/delivery/super-agent-brief.md:12-16`, `docs/delivery/super-agent-brief.md:61-62`; DEC-02, DEC-06; RT-A01 |
| REQ-02 | Manual activation/setup first, then hands-free interaction within an active authenticated browser session; truthful listening/cloud state and accessible mic-stop. | `docs/delivery/super-agent-brief.md:33-35`, `docs/delivery/super-agent-brief.md:82-84`; `docs/delivery/council.md:126-130`; DEC-03, DEC-08, DEC-15; RT-A01, RT-A02 |
| REQ-03 | Barge-in stops stale speech/playback without implicitly cancelling jobs; natural turn-taking and non-disruptive notifications are measured. | `docs/delivery/super-agent-brief.md:63-67`; `docs/delivery/council.md:167-172`; DEC-08, DEC-09; RT-A02 |
| REQ-04 | Bounded jobs return durable IDs quickly and overlap without blocking audio/control processing. CPU-heavy work runs off the voice event loop. | `docs/delivery/council.md:64-75`, `docs/delivery/council.md:131-135`; DEC-04, DEC-05, DEC-12; RT-A02, RT-A03 |
| REQ-05 | Application-owned ledger and verified receipts determine job progress and terminal outcomes, including cancellation and uncertainty. | `docs/delivery/super-agent-brief.md:68-70`; `docs/delivery/council.md:192-193`; DEC-04, DEC-09; RT-A03, RT-A04 |
| REQ-06 | Request/action idempotency, task revisions, stale-session rejection, and reconciliation prevent blind replay after duplicates, disconnects, or restarts. | `docs/delivery/council.md:44-45`, `docs/delivery/council.md:55-58`, `docs/delivery/council.md:201`; DEC-09; RT-A04 |
| REQ-07 | Steering a named job, cancelling that job, stopping speech, stopping microphone upload, and emergency-stopping work are distinct operations. | `docs/delivery/super-agent-brief.md:63-65`, `docs/delivery/super-agent-brief.md:82-84`; DEC-08; RT-A02, RT-A04 |
| REQ-08 | Initial workers are small trusted fixed functions over synthetic data, not arbitrary/generated code, plugins, unrestricted shell, or external actions. | `docs/delivery/super-agent-brief.md:36-37`; `docs/delivery/council.md:60-75`, `docs/delivery/council.md:131-135`; DEC-05; RT-A03, RT-A05 |
| REQ-09 | Low-risk voice requests operate only within existing authenticated grants; high-risk actions and new authority are disabled without a separately approved strong out-of-band/device-authentication design. | `docs/delivery/super-agent-brief.md:73-78`; `docs/delivery/council.md:188-189`; DEC-07; RT-A05 |
| REQ-10 | Schemas, tool/path/dataset scope, egress recipients, input sizes, concurrency, deadlines, steps, retries, and spend are enforced outside models. | `docs/delivery/super-agent-brief.md:71-74`; `docs/delivery/council.md:199-205`; DEC-07, DEC-11, DEC-12; RT-A05, RT-A06 |
| REQ-11 | Loopback API authentication plus strict Host/Origin/CORS/WebSocket checks and CSRF defense; a malicious website cannot create sessions or jobs. | `docs/delivery/council.md:200`; DEC-11; RT-A05 |
| REQ-12 | Long-lived provider/tool credentials stay in a backend OS vault or externally supplied environment, never in browser code, project files, URLs, logs, or model context. | `docs/delivery/council.md:69-72`; `docs/delivery/super-agent-brief.md:49-50`; DEC-11; RT-A05, RT-A06 |
| REQ-13 | Named runtime microphone/context recipients, eligibility/account/region/quota/cost/data terms, first real task pair, host, and budget require explicit setup approval. Development permission is not that approval. | `docs/delivery/super-agent-brief.md:18-35`; `docs/delivery/council.md:184-185`, `docs/delivery/council.md:215-216`; DEC-06, DEC-10; RT-G00 |
| REQ-14 | Local raw audio, persistent transcripts, model-content telemetry, and provider stored-session recording are off by default; even minimal task content has a bounded retention/deletion policy. Provider retention is disclosed separately. | `docs/delivery/super-agent-brief.md:79-81`; `docs/delivery/council.md:190-191`; DEC-10; RT-A06 |
| REQ-15 | Native transport, optional worker reasoning, tools, policy, and storage are independently replaceable; future private inference must be genuinely native and enforce egress boundaries. | `docs/delivery/super-agent-brief.md:85-87`; `docs/delivery/council.md:182-183`; DEC-03, DEC-10, DEC-14; RT-A01 and later RT-012 |
| REQ-16 | Demonstrate a useful bounded planner for an approved real task pair separately from the deterministic sample-worker proof. Neither unbounded autonomy nor tested runtime reasoning models are claimed now. | `docs/delivery/super-agent-brief.md:8-10`, `docs/delivery/super-agent-brief.md:29`; `docs/delivery/council.md:162-165`, `docs/delivery/council.md:215-220`; DEC-13; later RT-009 |
| REQ-17 | All limits and latency targets are provisional until approved/measured; no native local or locked-screen/always-on guarantee on the observed laptop. | `docs/delivery/super-agent-brief.md:43-46`; `docs/delivery/council.md:73-75`, `docs/delivery/council.md:126-139`; DEC-12, DEC-15; RT-A02, RT-A06 |
| REQ-18 | Host sleep/offline lifecycle is explicit; durable records do not promise execution during sleep/off. An always-on host requires separate approval. | `docs/delivery/council.md:152-153`, `docs/delivery/council.md:207`; DEC-15; RT-A04 and later RT-011 |

### 2.4 Decision register contract

“Contracted” below means the design/documentation choice, **not runtime authorization or completed independent review**. `descisions.md` expands each entry with alternatives, consequences, citations, and reopen conditions.

| ID | Decision | Status and rationale |
| --- | --- | --- |
| DEC-01 | Documentation-only delivery at the user's literal paths. | Contracted scope; avoids silently implementing a prototype or renaming requested artifacts. |
| DEC-02 | Native audio conversation; internal structured text and transient native transcripts are permitted. | Contracted UX constraint, grounded in `docs/delivery/super-agent-brief.md:12-16`. |
| DEC-03 | Thin manually activated browser plus one local authenticated service; separate logical conversation and task/policy planes. | Contracted proposed shape, not a stack already present (`docs/delivery/council.md:33-37`, `docs/delivery/council.md:64-75`). |
| DEC-04 | Tiny authoritative local job ledger for the overlap/cancel/restart demonstration; no distributed queue/framework. | Conditional architecture choice. Reopen if selected tasks are truly disposable and require no recovery (`docs/delivery/council.md:121-125`, `docs/delivery/council.md:150-151`). |
| DEC-05 | Two bounded trusted fixed sample functions initially; compute isolation from the event loop is not arbitrary-code containment. | Contracted boundary; arbitrary workers remain disabled (`docs/delivery/council.md:131-135`). |
| DEC-06 | Provider gate first. Investigate direct GPT-Live / WebRTC / client delegation as a provisional candidate; Realtime is another native candidate; Gemini remains eligibility-gated. | Provisional post-review research adoption, not re-voted council consensus, tested access, or selection of an existing text-router model. See 2.5. |
| DEC-07 | Models propose; local policy grants. Voice never creates new authority. High-risk tools are absent initially. | Contracted safety boundary (`docs/delivery/council.md:50-60`, `docs/delivery/council.md:188-189`). |
| DEC-08 | Independent speech interruption, per-job cancellation, mic-stop, and emergency-stop controls. | Contracted semantics; completed effects cannot be undone by stopping speech (`docs/delivery/super-agent-brief.md:63-65`; `docs/delivery/council.md:55-58`). |
| DEC-09 | Durable intent/result/action IDs, task revisions, session/playback epochs, verified outcomes, and reconciliation. | Contracted correctness boundary; do not promise universal exactly-once external execution (`docs/delivery/council.md:192-204`). |
| DEC-10 | Minimal local records with retention; no recordings/transcripts by default; no silent cloud fallback; private native migration is a later measured increment. | Contracted privacy boundary; no-training and local deletion do not mean no provider retention (`docs/delivery/council.md:136-139`, `docs/delivery/council.md:182-191`). |
| DEC-11 | Backend-only external secrets; authenticated loopback with strict browser-origin and request boundaries. | Contracted security requirement, not a property already implemented (`docs/delivery/council.md:69-72`, `docs/delivery/council.md:200`). |
| DEC-12 | Externally enforced budgets and admission limits; provisional targets only; keep CPU work off audio/control processing. | Contracted enforcement principle, provisional numeric values (`docs/delivery/council.md:57-60`, `docs/delivery/council.md:133-134`, `docs/delivery/council.md:202-203`). |
| DEC-13 | Add an explicitly bounded planner only after the deterministic voice/job slice and approval of real task capabilities. | Deferred capability; avoids pretending fixed demo functions prove useful autonomous reasoning (`docs/delivery/council.md:162-165`, `docs/delivery/council.md:219-220`). |
| DEC-14 | OpenCode V2 may later be an OS-contained worker adapter, not the assumed voice transport or sandbox. | Deferred; version/access/child scope/event reconciliation must be tested (`docs/delivery/super-agent-brief.md:53-57`, `docs/delivery/super-agent-brief.md:106-110`). |
| DEC-15 | Defer desktop packaging, wake detection, locked-screen operation, always-on hosting, and private native deployment guarantees. | Deferred feasibility/authorization work (`docs/delivery/council.md:73-75`, `docs/delivery/council.md:126-139`, `docs/delivery/council.md:152-153`). |
| DEC-16 | No current build commands; future commands remain proposed/non-runnable until a separately approved scaffold exists. Record diagnostics without claiming they tested voice. | Contracted documentation honesty; discovery is not deployed software (`docs/delivery/super-agent-brief.md:4`, `docs/delivery/super-agent-brief.md:51-57`). |

### 2.5 Native transport research: published, provisional, untested

The following official pages were read for this contract on 2026-11-07. This was public-documentation verification only: no credentials, model API requests, provisioning, microphone capture, or authenticated account capability tests were performed.

| Official source | Published capability or constraint relevant to the design |
| --- | --- |
| [GPT-Live delegation](https://developers.openai.com/api/docs/guides/live-delegation) | A native conversational frontend can delegate to a separately operated backend using client delegation. Application permissions, task state, routing, budgets, context preparation, and result verification remain application responsibilities. |
| [GPT-Live conversations](https://developers.openai.com/api/docs/guides/live-conversations) | Native full duplex; transcript fragments, audio playback, and backend progress are different observations. Replacement sessions can use relevant text history. Stored-session forking requires a completed stored recording and a new connection/session, not seamless persistent acoustic continuity. |
| [GPT-Live WebRTC](https://developers.openai.com/api/docs/guides/voice-webrtc?api=live) | Browser microphone and generated audio use negotiated media tracks; transcript/delegation events use the data channel. A trusted server handles session configuration and project-key authentication. Published examples are not an adequate authenticated localhost security design by themselves. |
| [GPT-Live server controls](https://developers.openai.com/api/docs/guides/voice-server-controls?api=live) | A backend sideband can receive events and send controls while WebRTC carries audio. Assign one execution owner. Sideband instructions do not directly stop client playback, and provider input muting does not itself stop local capture, upload, output, or backend work. |
| [Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations) | Realtime supports native speech-to-speech and structured function calling. Its event/session contract is distinct from GPT-Live; do not mix their event names or assume configured text endpoints provide either transport. |
| [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data) | API content is not used for training unless opted in. Default abuse-monitoring logs may retain content for up to 30 days, with stated legal/safety exceptions. ZDR/MAM require eligibility and prior approval; endpoint/model exceptions remain relevant. GPT-Live recording/storage defaults off, but that does not remove abuse-monitoring retention. Backend models/tools have separate controls. |
| [Gemini Live overview](https://ai.google.dev/gemini-api/docs/live) | Direct streamed audio input/output, interruption, and tool use are published native capabilities. Verify exact selected model/transport rather than assuming universal asynchronous function behavior. |
| [Gemini API terms, effective 2026-03-23](https://ai.google.dev/gemini-api/terms) | Terms describe professional/business developer use, not consumer use. Unpaid-service terms warn not to submit sensitive, confidential, or personal information and include regional qualifications. Paid use still processes/logs content. Eligibility for this personal assistant must be resolved rather than presumed. |
| [OpenCode V2 permissions](https://opencode.ai/v2/docs/permissions) and [client guide](https://opencode.ai/v2/docs/build/client) | Shell retains host-user authority; custom children have independent permissions. Client subscriptions are live-only without replay or automatic reconnect. These constraints support the source's caution about optional future workers. |

**Provisional recommendation.** Investigate GPT-Live with browser WebRTC and backend-owned client delegation because the published separation fits the independent task/policy service. This recommendation is the **post-review Researcher follow-up supplied with the delivery instructions**, checked against the official pages above, followed by this architect's provisional adoption. It is not an additional council vote. The source council itself only recommends investigating an eligible direct OpenAI native alternative (`docs/delivery/council.md:113-117`).

Important integration obligations if that candidate is later approved:

1. `session.delegation.created` provides delegation metadata, not the user's task text. Client delegation needs transient `session.input_transcript.delta` / `session.output_transcript.delta` context and authoritative application state to build a task proposal. A transcript fragment is not a complete turn and may be mistaken or later corrected. Do not dispatch arbitrary work from a fragment or assume a fabricated turn-complete event exists.
2. Native audio remains the conversational path. Consuming the native provider's transcript events for task interpretation does **not** introduce an external STT/chat/TTS conversational chain. The demonstration may conservatively recognize explicit synthetic worker requests and ask for clarification rather than inventing an unrestricted interpreter or planner.
3. Published `session.thinking.append` can carry factual quiet progress; `session.commentary.append` can carry facts intended for speech. Their acknowledgments are not evidence of completed work, correct wording, silence, or actual playback. Never send secrets/private reasoning through “thinking” context: it can influence later speech.
4. Barge-in or conversation steering does not cancel backend work. The application requests and verifies job cancellation separately. A provider-side mute is not a privacy mic-stop: the client must stop transmitting local microphone media and discard unsent buffers. Hold outgoing media disabled during startup until the authenticated session binding and required backend control channel are healthy; do not assume negotiating a peer connection proves those prerequisites.
5. Backend sideband observes delegation/transcript events directly and is the sole execution/result-update owner. Browser event echoes are captions/control requests, not a second worker executor or trusted task-state writer. Attach/control access and client permissions need deployed verification; fail closed if the required backend control channel fails.
6. A reconnect uses a new application epoch and, when required, a new native session with allowed task summaries and available transient history. Never reuse an old session's delegation ID as an ID known to a new session. Use the selected provider's verified current-session context mechanism for reconciled summaries.
7. Keep provider recording/storage off in the initial slice. Stored-session forks are not the recovery mechanism: they require persistence and completed recordings, have provider retention implications, and still create new sessions. The data-controls page currently documents no public stored-session deletion endpoint. Local deletion cannot erase provider logs/recordings or promise their deletion.
8. Actual account access, model identifier, SDK/server compatibility, client-control restrictions, pricing, initialization/session charges, duration limits, region, retention, and microphone/context consent remain RT-G00 gates. Do not substitute the architect profile, an AgentRouter/OpenRouter text model, or OpenCode's documented-but-404 voice route as a guessed native transport.

Do not paste provider example programs into the pack or prescribe untested exact application endpoints. Provider event names above identify verified public documentation; all application interfaces below are proposed conceptual contracts.

### 2.6 Proposed future components and ownership

No component in this section exists in the current project. Use **one service with logical modules**, not microservices. A thin browser UI, a supported Node.js/TypeScript service, and a single SQLite ledger are a **provisional future stack proposal**, not installed dependencies, a package manifest, or a validated Windows build. Exact runtime versions, SDK/SQLite compatibility, native-binding requirements, and dependency choices belong to a separately authorized scaffold review. Plain Markdown needs none of them.

| Logical component | Owns | Does not own / boundary |
| --- | --- | --- |
| Browser audio/control UI | Manual activation, browser permission, native media tracks, listening/cloud indicator, player gating, speech epochs, accessible stop/mic/emergency controls. | No long-lived keys, grant creation by voice, host tools, authoritative job state, or recording persistence. |
| Native transport adapter | Verified native media/session configuration, provider lifecycle/events, backend control-channel health, usage observations, translation to conceptual conversation events. | No action authorization, worker execution, or assumed cross-provider failover. Exact vendor event mapping is untested. |
| Conversation coordinator | Ephemeral native transcript context where required, task/delegation correlation, turn/playback bookkeeping, bounded factual status requests, notification scheduling. | No durable conversational transcript or authority based on spoken “yes”; model narration is not execution evidence. |
| Policy/admission broker | Authenticated subject/grants; typed proposal validation; fixed dataset/tool scope; egress, size, deadline, step/retry/concurrency/spend checks; revocation and emergency admission latch. | No trust in prompts as enforcement, and no approvals of initially disabled consequential capabilities. |
| Task service and tiny ledger | Job IDs, current revisions/states, request/action deduplication, intent/receipt records, leases, budget reservations/usage, cancellation truth, reconciliation, retention and purge metadata. | Not a general scheduler/agent fleet or guaranteed execution when the host sleeps. |
| Bounded trusted worker executor | Only approved fixed functions, finite inputs, cooperative cancellation, isolated CPU execution from the audio/control event loop, structured receipts. | A worker thread/process used for responsiveness is not an arbitrary-code security sandbox. No generated code, plugins, unrestricted shell, or external actions. |
| Result verifier / notification coordinator | Check worker evidence against the task specification/revision; persist outcomes; send concise allowed facts when conversation policy permits; track publication versus playback separately. | No successful-job assertion from model confidence, an append acknowledgment, or a late superseded result. |
| Future bounded planner / contained adapters | Later typed multi-step proposals, checkpointed reasoning, and individually approved worker capabilities, through the same broker/ledger. | Not part of the deterministic proof; no capability expansion through delegation. OpenCode remains optional and disabled until OS containment is independently tested. |

Two data paths are deliberately separate:

- **Native audio:** after authenticated setup and named consent, browser microphone media goes to the approved native provider and native output returns to the browser player. No obligatory text reasoning service or TTS lies in this audio path.
- **Control/tasks:** backend-owned native events and authenticated local control requests become untrusted proposals; broker validation precedes ledger admission; executor receipts are verified and journaled; only minimized factual summaries return to the native conversation. Browser-direct media egress and backend/worker context egress are distinct recipient/consent boundaries.

The local broker is not falsely presented as an OS firewall over browser WebRTC. The trusted UI enforces its media lifecycle; backend policy controls session creation, native session termination, task admission, and worker recipients. A compromised browser/host or stronger private egress guarantee needs additional OS/network controls and later testing.

### 2.7 Conceptual records and interfaces

These are proposed field responsibilities, **not existing APIs or code signatures**. No HTTP routes, SDK packages, or database schemas are implemented by this contract.

| Conceptual record | Minimum contents / invariants |
| --- | --- |
| Authenticated grant | Subject/device session, allowed fixed capability/dataset IDs, named recipients, grant/policy version, expiry, budget scope, and revocation status. Credentials are external references, never secret values. Voice cannot expand it. |
| Task proposal | Client intent/request ID, authenticated subject, originating session epoch, desired fixed operation, bounded structured arguments, target job/current revision for steering, required scope, and deadline/budget request. Provider delegation ID is correlation metadata, not authorization. |
| Task record | Stable job ID, request ID, current revision, state, minimal approved input/specification, grant/policy references, timestamps/deadline/lease, reservations/usage and limits, cancellation request/acknowledgment, outcome/evidence reference, retention metadata. No raw transcript, audio, secret, or full model reasoning. |
| Action/attempt record | Stable action ID and bounded attempt number tied to job/revision; validated operation and argument digest; pre-dispatch intent; worker receipt; observed outcome and partial-effect information; retry/reconciliation disposition. |
| Worker receipt | Job/revision/action IDs, executed fixed function, actual start/finish/stop observations, bounded structured output, verification evidence, failure/partial-effect/cancellation facts. Treat it as untrusted until checked against the admitted action. |
| Notification record | Job and revision, verified state/evidence reference, recipient/session epoch, publication ID, whether announced or held/interrupted, and observed playback disposition where available. “Published” and “heard” are different facts. |

Conceptual operations:

| Operation | Input / result contract |
| --- | --- |
| Start native session | Authenticated setup grant plus approved configuration/consent and budget reservation; return a current session binding or an explicit failure/uncertain-start outcome. No native session from an anonymous website request. |
| Propose/create task | Validated proposal with stable request ID; return admitted job ID/state or a bounded rejection/clarification. Repetition of the same request/specification returns the same job, not another execution. |
| Read task snapshot | Authenticated scoped job IDs; return ledger states/current revisions and verified evidence, not the voice model's remembered status. |
| Revise/steer task | Target job, expected current revision, request ID, and allowed bounded changes; atomically create a new revision or reject stale/conflicting/out-of-scope changes. Never overwrite completed facts. |
| Request job cancellation | Target job/revision and request ID; durably record request, signal worker, and return `cancel_requested` until stop/non-execution evidence establishes an outcome. Duplicate requests are harmless. |
| Stop speech | Advance playback epoch and stop/drop stale output; request appropriate provider conversational interruption through its verified adapter. No job-state transition. |
| Stop microphone upload | Immediately stop local transmission/capture as selected, discard unsent buffers, and reflect truthful disconnected/paused status. Jobs continue only within independently valid background grants. No silent buffering for later upload. |
| Emergency stop | Latch admission/dispatch off, revoke applicable execution grants, stop microphone transmission and playback, close native transport, request all-job cancellation, and verify/report outcomes. Manual authenticated re-arm is required. |
| Reconcile/purge | Scoped application operation, not a model-created tool: obtain authoritative snapshots/receipts, resolve uncertainties where evidence permits, and purge under retention rules without permitting expired request replay. |

#### Job-state definitions

`architecture.md` owns this canonical state table. `flow.md` and the task files link to it. Project delivery statuses are different from runtime job states.

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

The initial fixed workers are read-only and high-risk tools are absent. `waiting_for_approval` documents a fail-closed checkpoint contract, **not a latent approval path for disabled purchases, shell, messages, or deletion**. Missing task details normally trigger clarification before admission. An authenticated low-risk voice correction inside an existing grant is revalidated, not treated as new authority. Strong approval mechanisms for consequential/new capabilities require a separate future design.

#### Idempotency, revisions, and uncertainty

1. Bind client intent IDs to subject, validated specification, and a bounded retry window. Reject the same ID with changed parameters. Record admission/action intent before dispatch and outcome before announcing completion.
2. Enforce unique request/action IDs in the ledger. Repeated create, revise, and cancellation requests return current recorded disposition; read/speech/mic-stop/emergency-stop operations are safe to repeat. Do not rely only on provider tool-call IDs or model instructions.
3. Increment job revision on accepted steering. Before each step/result commit, compare current revision, grant/policy version, deadline, emergency latch, and lease. Discard superseded results as current answers while preserving actual old execution evidence. An already-running action may need cancellation/reconciliation before a replacement starts.
4. A voice-session epoch is not a job ID or task revision. Reject delayed commands from stale/closed sessions. A reconnect may restore scoped task summaries, not expired approvals or expanded grants. Old audio/notification epochs never resume playback after a barge-in, stop, or replacement session.
5. Chargeable session creation also needs local intent deduplication and conservative uncertain-start handling. Do not assume a provider honors an idempotency header or that SDK automatic retries are safe. Verify the deployed provider contract before enabling retries; otherwise report uncertain startup/charges instead of repeatedly creating sessions.
6. On backend restart, re-read records and reconcile previously `running` / `cancel_requested` work before scheduling it. The ledger preserves evidence, not the executing process. Terminal receipt and cancellation races are resolved by facts, not by whichever narration arrives last.

A retryable **action-attempt** failure is not automatically the terminal job state `failed`: retain the attempt evidence and retry only within the job's existing grant, step/retry/deadline limits and reservation. Once the job revision is terminal, an intentional subsequent retry requires a fresh explicitly admitted request/revision or job. Steering, new revisions, adapter boundaries and child work do not reset the original job/shared-grant budget counters or manufacture a new retry allowance.

### 2.8 Workflow contract for `flow.md`

Expand these into numbered Markdown workflows with actor, input, policy preconditions, ledger transition, output, failure path, and acceptance links. Use state tables rather than generated assets.

1. **WF-01 — setup and manual activation.** User/device authentication, named native/provider/context consent, eligibility/access/cost/retention review and grants precede session creation. User manually permits microphone and activates the browser session. Controls/health checks are ready before upload. Any failed prerequisite keeps microphone transmission off; no alternate cloud or text-voice fallback.
2. **WF-02 — native conversation and two sample jobs.** Native input/output continues directly. Backend assembles conservative transient task context, validates a fixed proposal, reserves limits, journals it, returns job IDs, and dispatches bounded workers off the audio/control loop. Results are verified and committed before concise completion facts are sent at an appropriate idle boundary.
3. **WF-03 — barge-in/stop speech.** Detect/accept the interruption, advance speech epoch, gate/drop stale player output, and invoke verified conversational interruption semantics. Job state is unchanged. A provider acknowledgment is not proof that the user heard silence or that jobs stopped.
4. **WF-04 — steer a named job.** Resolve an unambiguous job/revision; clarify ambiguous references. Admit only bounded changes within the existing grant. Record a new revision and retire/cancel superseded execution safely. Late old results cannot become new-revision answers. Do not claim completed effects were undone.
5. **WF-05 — cancel a named job.** Record `cancel_requested`, signal/check the worker, then establish `cancelled`, a raced terminal outcome, or `unknown` from evidence. Speak “cancellation requested” before stop confirmation, not “cancelled” prematurely.
6. **WF-06 — mic-stop/pause.** Local UI immediately stops microphone transmission and discards unsent audio. Provider muting alone is insufficient. Job grants, audio output, and worker/model-context egress have separate controls; disclose which remain active. Resume requires current authenticated consent and deliberate activation; paused speech is not recorded for later upload.
7. **WF-07 — emergency stop.** Local controls stop microphone/playback even if the backend/provider is unhealthy. Backend latches off new sessions/jobs/steps, revokes execution grants, cancels running work, and reconciles. Keep uncertain outcomes explicit. No spoken “yes” clears the latch or grants new power.
8. **WF-08 — disconnect, replacement session, and restart.** Freeze stale-session commands/output; persist job truth; invalidate interrupted approvals. Reconcile a scoped snapshot and current grants before any resumed task work. New native session gets minimized current facts and only allowed transient history, not raw persisted transcripts or repeated actions. Re-subscription is not replay or guaranteed acoustic continuity.
9. **WF-09 — denied scope, injection, or exhausted budget.** Malformed/oversized/out-of-scope/expired/over-budget proposals fail closed without dispatch. Treat audio, native transcripts, documents, pages, and worker output as data, not grant instructions. Explain the denial without inventing a completed task.
10. **WF-10 — retention, session end, and host lifecycle.** End native audio and clear ephemeral transcript context; keep only bounded approved task evidence. Purge content and eventually dedup metadata under explicit windows; reject expired retries. Record unfinished shutdown/usage reconciliation honestly. Sleep/off stops local execution; an approved always-on host is a different deployment decision.

For GPT-Live, the coordinator must establish a measured application idle/playback policy rather than borrowing Realtime's response-completion events or treating transcript-delivery gaps as silence. Notifications may be held and summarized later. Speech publication, audio playback, and task completion remain distinct observations.

### 2.9 Security, budgets, data minimization, and limits

#### Local security boundary

- Serve the first UI and API from one deliberately chosen loopback origin. Authenticate setup using a locally established device/session credential outside project documents; bind requests to subject/session/grant and revoke on logout/expiry. Loopback location and an Origin header are not identity by themselves.
- Restrict listener addresses and accepted Host values to configured loopback hosts/ports. Check exact allowed Origin for browser mutations and WebSocket handshakes; deny unexpected/null origins as appropriate. Use narrow/no cross-origin access, never wildcard credentialed CORS. Apply CSRF defense to cookie-authenticated mutations and authenticate/authorize WebSocket messages as well as their upgrade.
- No permanent secrets in URLs, browser storage, provider/model prompts, task records, telemetry, or repository files. Future backend credentials come from an OS vault or externally injected environment. Do not read/copy current global credentials into the pack.
- Validate message/schema/content type, sizes, rates, fixed capability and dataset IDs, deadlines, request revisions, and recipient scope. Initial workers accept synthetic dataset identifiers, not model-selected arbitrary paths or URLs. Future path/URL capabilities need canonicalization and egress/redirect/SSRF tests before approval.
- Deny worker/tool network egress by default. Initial fixed sample workers have no network capability; only the explicitly consented native provider's required media/control recipients are enabled for the voice connection. New recipients, redirects, routers, hosted tools, or worker models require separate named grants and verification, never a prompt-selected fallback. Stronger OS-level network containment is a separate requirement before arbitrary workers are enabled.
- Keep the browser frontend thin, without unnecessary third-party scripts/content. Backend session configuration and fixed policy are not editable by voice or untrusted webpage/tool content. Restrict frontend native-session control privileges through the deployed provider contract where available; verify rather than assume those permissions.
- Trusted worker bugs remain a risk; “fixed function” is a narrowed reviewed capability, not protection against arbitrary code with host authority. Moving CPU work to another thread/process solves scheduling, not credential/filesystem/network containment.

These requirements address the localhost attack and authority risks recorded at `docs/delivery/council.md:199-205`; they are acceptance obligations, not currently implemented controls.

#### Provisional targets — not measurements or spending approval

| Target | Proposed test interpretation |
| --- | --- |
| Maximum 2 simultaneously running jobs | Aggregate local scheduler ceiling, including child/future delegated work; not two jobs per agent. Queue admission also has a finite separately configured bound. |
| Maximum 3 execution/planner steps per job | Bound all dispatched steps; retries count within the same ceiling. Deterministic fixed jobs can use fewer steps. |
| Maximum 1 retry per job | Only after a verified retryable failure or safe reconciliation decision; subject to remaining deadline, steps, grants, and cost. |
| 60 seconds job wall-clock budget | Provisional admission-to-completion deadline, including queue/waits. Cancellation/reconciliation still records uncertain outcomes rather than asserting forced rollback. |
| Useful spoken-response latency < 1.5 seconds | Provisional p95 test target for end of a defined synthetic user request to first useful played native reply in an active session, including a two-worker overlap scenario. Define timing independently of transcript packet arrival. Not a task-completion target. |
| Barge-in stale-playback stop < 300 ms | Provisional p95 target from test-observed interruption onset to no stale audible output; measure the actual player/media path, not only receipt of an event. |
| Monetary budget | **Unset and unapproved.** No amount, free-tier assumption, or model-price inference in the documents authorizes runtime use. RT-G00 must establish explicit session/job/provider budgets first. |

All numeric targets in the preceding table are proposals for later review/measurement on a confirmed host/network/account. Do not advertise them as achieved performance, user-approved resource choices, or evidence that the 8 GiB / 4 GiB machine can run native local models.

Budget enforcement lives outside models: reserve before chargeable work, account for voice/session creation and duration separately from worker/model tokens, reconcile provider usage without double-counting cumulative counters, enforce aggregate concurrency/step/retry/deadline limits, and close/refuse work at caps. Provider reporting/finalization can lag or fail; record uncertainty and conservatively block further spending rather than claim perfect billing control. Recursive workers cannot reset budgets or spawn unbounded children.

#### Data lifecycle

| Data category | Initial policy / necessary future decision |
| --- | --- |
| Raw microphone/output audio | No local recording/persistence. Transient media buffers only; mic-stop discards unsent buffers. No capture in this documentation request. |
| Native transcript context | In-memory, bounded to task interpretation/corrections when needed; clear at session end/expiry. Do not log deltas or whole prompts. On service restart, ask for lost details rather than pretending full conversational memory survives. |
| Structured task input/result | Synthetic/minimized, scoped and bounded; still potentially sensitive later. Explicit retention period and deletion procedure must be approved before a durable runtime starts. No indefinite default. |
| Intent/action IDs, receipts, budget/denial metadata | Minimized non-content evidence with a defined retention/dedup/retry horizon; not exempt from retention just because called metadata. |
| Ledger journal/WAL, diagnostics, crash reports, backups | Covered by the same content/retention rules. No model-content telemetry or unreviewed backup duplication. Future purge tests include secondary stores, not just one visible row. |
| Credentials | External backend vault/environment references; never stored in ledger or frontend. |
| Provider retained content | Independent of local logging and deletion; named provider, endpoint, backend-tool recipients, retention terms, and account controls require disclosure/consent. No-training is not no-retention; ZDR/MAM cannot be assumed. |

Before RT-G00 closes, choose bounded task-content and metadata windows, maximum retry age, grant/session expiry, and operational deletion behavior. Retain only the minimum dedup evidence necessary for the approved retry window; reject expired requests after purge instead of treating them as new intent. Do not preserve an unbounded transcript to improve recovery. Default provider stored recording/fork recovery remains off.

### 2.10 Faithful council record contract

The council used quick mode with four independent general sessions and anonymized cross-review. Perspective diversity does not prove different model families (`docs/delivery/council.md:19-27`). Meeting records are a readable reorganization of the source, not new meetings or fresh independent reviews.

**Meeting 1:** summarize A's separation of ephemeral audio/durable execution and evidence, B's appliance-first authority and injection boundaries, C's minimal manually activated browser/fixed-worker experiment, and D's provider/native/local feasibility checks (`docs/delivery/council.md:31-91`). Preserve that samples are illustrative and hardware/account access unverified.

**Meeting 2:** reproduce the following aggregate received ratings exactly, using anonymized response labels. Each dimension is 1–5; these are rounded arithmetic means and discussion aids, not proof (`docs/delivery/council.md:95-104`).

| Response | Relevance | Feasibility | Insight |
| --- | ---: | ---: | ---: |
| A | 5.00 | 3.33 | 4.67 |
| B | 5.00 | 4.00 | 5.00 |
| C | 4.67 | 4.00 | 4.00 |
| D | 4.67 | 3.67 | 4.67 |

Preserve reviewer rankings: A: B > C > D; B: A > D > C; C: D > B > A; D: B > C > A (`docs/delivery/council.md:106-111`). Do not fabricate individual dimension scores, infer a unanimous winning model, or turn the means into a security certification.

Include all counterfactual flips: reject an ineligible/unconsented/unacceptable or failed cloud runtime; prefer genuinely compatible native local inference if measurements support it; remove unnecessary durable scheduling for disposable tasks; use an approved always-on host if sleep/off continuity is required; remove tools whose containment/egress tests fail (`docs/delivery/council.md:141-155`). Preserve the actual provider recommendation change and disagreements over ledger necessity, wake words, isolation, and cloud/private sequencing (`docs/delivery/council.md:113-139`).

**Meeting 3, part A — chair synthesis:** native voice over controlled task truth; small ledger where overlap/restart justify it; fixed workers first; external capabilities/budgets/idempotency/verification; distinct stops; low-risk existing grants only; no presumed Gemini/runtime account; no unsupported local-hardware promise; optional contained OpenCode later (`docs/delivery/council.md:157-193`).

**Meeting 3, part B — post-review Researcher follow-up:** official GPT-Live client-delegation research and architect's provisional candidate in 2.5, with check date, URLs, transient transcript requirement, independent backend work/cancellation, non-seamless recovery, recording/retention implications, and still-open consent/access/cost gates. Clearly label it later research, not re-voted unanimity. Public capability confirmation is not a runtime feasibility result.

### 2.11 Future phases and numbered task files

Future phases and task files initially say **not started**. That is a dated initial status, not a permanent “pending forever” banner. Update status only when a separately authorized task actually begins and link evidence when it changes.

| Phase ID | Scope and task links | Initial status / gate |
| --- | --- | --- |
| PH-DOC | Current documentation pack; DOC-001–DOC-012 below. | Pack not yet authored at this signature. `progress.md` later records the actual documentation-only milestone and independent report dispositions. |
| PH-00 | Runtime eligibility, consent, real-task selection, host, budgets, retention, and implementation authorization; RT-001. | not started; RT-G00 |
| PH-01 | Separately approved scaffold/local boundary and manually activated native voice connection; RT-002–RT-003. | not started; RT-G01 |
| PH-02 | Ledger/policy and two deterministic trusted synthetic workers; RT-004–RT-005. | not started; RT-G02 |
| PH-03 | Steering/stops, recovery/retention, measured negative and performance validation; RT-006–RT-008. | not started; RT-G03–RT-G04 |
| PH-04 | Useful bounded planner for the approved real task pair; RT-009. | not started; new capability/worker approval and RT-G05 |
| PH-05 | Optional OS-contained OpenCode worker adapter; RT-010. | not started; independent containment/egress/child-scope gate |
| PH-06 | Optional desktop/wake/locked-screen/always-on host feasibility; RT-011. | not started; explicit device/host/security/power decision |
| PH-07 | Optional genuinely native private audio feasibility/migration; RT-012. | not started; compatible hardware/quality/latency/egress benchmark |

Current status (2026-11-09): PH-00 is `in progress`. The table above keeps the
initial status from the signed design. See [roadmap.md](../../roadmap.md) for
the checklist of record.

The future task index and twelve files must contain the following scopes. These are planning records only; creating a task Markdown file does not start or authorize its implementation.

| Task ID and exact file | Independently reviewable future deliverable | Prerequisites / requirement and decision links |
| --- | --- | --- |
| RT-001 — [tasks/001-runtime-consent-and-feasibility.md](../../tasks/001-runtime-consent-and-feasibility.md) | Dated setup decision covering candidate eligibility/native access, account/region/quota/data/cost, named egress, budget, host, retention, and first real task pair; separate implementation authorization. No consent/access fabrication. | REQ-13, REQ-14, REQ-17; DEC-06, DEC-10, DEC-16; RT-G00 |
| RT-002 — [tasks/002-local-scaffold-and-boundary.md](../../tasks/002-local-scaffold-and-boundary.md) | After a new implementation request only: minimal reviewed local scaffold, exact dependency/command contract, device/session authentication and loopback HTTP/WS/CSRF boundary, without voice capture yet. | RT-001 and explicit scaffold authority; REQ-11, REQ-12; DEC-03, DEC-11, DEC-16 |
| RT-003 — [tasks/003-native-voice-session.md](../../tasks/003-native-voice-session.md) | Single manually activated native voice adapter and thin UI with indicators, backend control ownership, mic/playback stops, consent and failure behavior measured. No task workers or silent fallback. | RT-002 plus approved runtime grant; REQ-01–REQ-03, REQ-15; DEC-02, DEC-03, DEC-06, DEC-08 |
| RT-004 — [tasks/004-task-ledger-and-policy.md](../../tasks/004-task-ledger-and-policy.md) | Small durable state/admission/idempotency/revision/budget contract with synthetic tests; no arbitrary tools or provider dependencies required for ledger tests. | RT-002; REQ-05, REQ-06, REQ-09, REQ-10; DEC-04, DEC-07, DEC-09, DEC-12 |
| RT-005 — [tasks/005-fixed-sample-workers.md](../../tasks/005-fixed-sample-workers.md) | Two trusted bounded read-only synthetic workers, finite input/output, off-loop CPU execution, structured receipts/verification and overlap demonstration. | RT-003–RT-004; REQ-04, REQ-08; DEC-05, DEC-12 |
| RT-006 — [tasks/006-steering-and-stop-controls.md](../../tasks/006-steering-and-stop-controls.md) | Named-job revisions/cancellation plus distinct speech/mic/emergency semantics, cancellation races and partial-result reporting, held notifications and stale output checks. | RT-005; REQ-03, REQ-07, REQ-09; DEC-07–DEC-09 |
| RT-007 — [tasks/007-recovery-and-retention.md](../../tasks/007-recovery-and-retention.md) | Reconciliation after event loss/disconnect/restart; stale commands/approvals rejected; no blind effects replay; bounded content/metadata purge and lost-context disclosure. | RT-006; REQ-05, REQ-06, REQ-14, REQ-18; DEC-09, DEC-10, DEC-15 |
| RT-008 — [tasks/008-runtime-validation.md](../../tasks/008-runtime-validation.md) | Measured native/overlap/control/negative/security/privacy/budget evidence for the fixed slice, actual distributions/failures, and independent implementation review/security assessment. | RT-007; RT-A01–RT-A06; REQ-17; DEC-11, DEC-12 |
| RT-009 — [tasks/009-bounded-real-task-planner.md](../../tasks/009-bounded-real-task-planner.md) | Separately approved planner/worker increment for one real task pair; typed bounded steps, checkpointed steering, verifier evidence and comparative usefulness versus fixed baselines. No high-risk authority by voice. | Accepted fixed-slice evidence, real-task/capability/recipient grants; REQ-09, REQ-10, REQ-16; DEC-07, DEC-13 |
| RT-010 — [tasks/010-contained-opencode-adapter.md](../../tasks/010-contained-opencode-adapter.md) | Optional V2 adapter only inside demonstrated OS containment with least privilege, restricted credentials/egress, independent child-scope enforcement, event-gap reconciliation and version/capability tests. | Separate capability request and security design; REQ-06, REQ-08–REQ-12, REQ-15; DEC-14 |
| RT-011 — [tasks/011-always-on-and-desktop-feasibility.md](../../tasks/011-always-on-and-desktop-feasibility.md) | Optional feasibility/decision record for desktop activation, wake gating, locked-screen identity/privacy, sleep/power behavior or an approved always-on host; no always-on promise. | Separate UX/deployment consent; REQ-02, REQ-17, REQ-18; DEC-15 |
| RT-012 — [tasks/012-private-native-audio-feasibility.md](../../tasks/012-private-native-audio-feasibility.md) | Optional measurement and migration decision for genuinely native local/private audio with confirmed OS/hardware, quality/latency and denied-egress tests; no downloads from this request. | Separate private-runtime/hardware approval; REQ-01, REQ-14, REQ-15, REQ-17; DEC-10, DEC-15 |

Illustrative first-slice worker examples are **synthetic only**: compute bounded metrics for a bundled sample dataset and compare two bundled sample snapshots. They are not the user's selected first real task pair or an approved personal-data workflow. Any deliberate timing delay is a test fixture for overlap, not evidence of useful reasoning. A future bounded planner may propose useful multi-step work, but it cannot directly execute or enlarge grants; the same admission, budget, verification, and cancellation contracts apply.

### 2.12 `build.md` and `progress.md` contracts

#### Build and diagnostics

`build.md` begins: **“Documentation-only project. There is no runnable assistant, application scaffold, package manifest, install script, or verified application build command.”** No dependency installation, package/config/script creation, model download, Git setup, service restart, global change, credential reading, model API contact, or audio capture is part of this request.

Keep distinct sections:

1. **Recorded discovery diagnostics — not application tests, not rerun for this contract.** The source records OpenCode v2.1.2; exact version-command invocation is not supplied. The recorded read-only command `opencode api get /api/experimental/voice/models` returned **HTTP 404**, not native voice success (`docs/delivery/super-agent-brief.md:47-57`). Router TCP reachability is only port availability (`docs/delivery/super-agent-brief.md:51-52`). Do not invent successful model tests or additional executed commands.
2. **Proposed future command contract — NOT RUNNABLE IN THIS PROJECT; DO NOT RUN UNTIL AN APPROVED SCAFFOLD EXISTS.** If the later scaffold uses the proposed Node stack, candidate command names are `npm ci`, `npm run dev`, `npm run typecheck`, `npm test`, and `npm run build`. Each row carries that warning and specifies prerequisites, purpose, future owner, and “execution evidence: none.” No package scripts or lockfile are currently defined. Do not present these names as APIs/scripts discovered in the source or copy install commands from provider examples as current setup instructions.
3. **Future verification protocol.** After separately authorized scaffolding, replace proposals with actual commands supported by opened manifests/scripts; record versions, date, working directory, exit status, and redacted result/evidence. Diagnose locally without reading credentials; native tests require RT-G00. A successful build is not proof of native access, safety, or latency.

The recorded 404 observation may be documented without rerunning it. Publicly documented diagnostic commands that were not run must be labeled documented/unexecuted, not “verified executed.” Markdown artifact review needs no added linter/script/dependencies.

#### Progress and evidence

`progress.md` is a dated status record, not a success narrative. Include milestone ID, artifact revision/date, scope, state, evidence links, independent reviewer/security report dispositions, blocking gates, and next owner/action. It may record **documentation authored** when the requested files exist, while separately recording that reviews are absent or changes requested. Only actual independent evidence can close the documentation review gate.

Initial factual entries may link the discovery brief, council source, and signed design. After the pack is written, link its indexes/documents and the actual independent review/security reports when available. Those reports are authoritative for their scope and assessed revision; neither this signature nor council consensus is an application certification. Missing or superseded reports cannot be shown as passed. Never claim runtime tasks, microphone integration, tests, build execution, performance, containment, or provider access merely because the documentation is complete.

All future phase/task entries initially read `not started`, with the unresolved prerequisite. Later statuses are evidence-driven; do not hardcode a forever-pending review banner or prematurely claim every gate passes. Keep documentation creation, independent design review/security, implementation, and measured runtime acceptance as separate milestones.

## 3. Alternatives considered

| Alternative | Why not selected now / evidence that could reopen it |
| --- | --- |
| Mandatory STT → text-chat → TTS conversational pipeline | Rejects the clarified native voice UX (`docs/delivery/super-agent-brief.md:12-16`). Internal text is allowed, but cannot be used to silently substitute that audio path. Only an explicit user scope change could reopen this. |
| One omnipotent voice model with direct host tools and remembered job state | Confuses conversational output with execution truth, makes ambient/injected audio authority, and fails duplicate/restart/cancel correctness. Rejected by the control-plane split and explicit initial exclusions (`docs/delivery/council.md:33-60`; `docs/delivery/super-agent-brief.md:36-37`). |
| Heavy agent framework, distributed queue, microservices, vector database, or general agent fleet before first tasks | No existing application requires them. Adds operational/state surfaces before evidence of need. One service and a tiny ledger match the minimal council resolution (`docs/delivery/council.md:121-125`, `docs/delivery/council.md:186-187`). Reopen only for measured workloads and reviewed lifecycle requirements. |
| Entirely stateless fixed demo, no ledger | Simpler for instantaneous disposable tasks, and a legitimate counterfactual. Not chosen for this proposed overlap/cancellation/restart proof because it cannot establish durable truth or safe reconciliation. Remove the ledger if approved tasks genuinely need no recovery (`docs/delivery/council.md:121-125`, `docs/delivery/council.md:150-151`). |
| Presume Gemini because the UX example is Gemini-like, or use an existing router text model as audio transport | Branding is not a user requirement for that provider. Eligibility/terms/account/native access are unresolved; a text model or reachable proxy proves nothing about native transport (`docs/delivery/council.md:79-91`, `docs/delivery/council.md:113-117`; official terms in 2.5). Gemini remains a gated alternative, not a globally prohibited technology. |
| GPT-Live managed Responses delegation as the initial backend | Published and potentially useful later, but unnecessary for two fixed workers and less aligned with application-owned context/routing/result review. Client delegation provisionally fits independent policy/task truth. This does not claim managed delegation cannot be secured; compare actual capability, cost, latency, and data handling after RT-G00. See official delegation guide in 2.5. |
| Trusted browser event forwarding as the only task/control authority | Smaller plumbing, but browser echoes should not define execution truth or duplicate sideband actions. Backend-owned control/interpretation provides one owner and protects backend credentials. Authenticated local controls remain supported; backend/native event failure must fail closed rather than trusting forged task facts. See official server-controls guide in 2.5. |
| Download a local native model and promise private/always-on operation immediately | No model was benchmarked on the observed Windows/4 GiB device; target hardware is unconfirmed. Privacy compatibility, native quality/latency, and wake/locked-screen behavior need separate evidence and approval (`docs/delivery/super-agent-brief.md:43-46`; `docs/delivery/council.md:85-91`, `docs/delivery/council.md:126-139`). Prefer local later if genuine native measurements pass. |

## 4. Trade-offs and risks

| Trade-off / risk | What this design gives up; mitigation and acceptance obligation |
| --- | --- |
| Documentation now, no runnable demonstration | Immediate product experience is deferred. The pack provides reviewable commitments and gates rather than pretending code exists. DOC-A01–DOC-A06 establish documentation delivery only. |
| Small fixed slice is not the full “superagent” | A passing future slice would demonstrate native conversation/control/task truth, not autonomous usefulness. RT-009 must separately demonstrate a bounded real-task planner against an approved pair and baseline. |
| Cloud-native candidate versus eventual privacy | Native UX may be easier to validate on current hardware, but microphone/context egress and provider retention remain real. No default consent, silent fallback, or “local database = private” claim; RT-G00 and RT-A06 apply. |
| Client delegation needs transient text context | Transcript mistakes and later corrections can misroute work; losing RAM context reduces conversational continuity. Keep audio native, validate fixed proposals conservatively, version corrections, ask when ambiguous, and never persist raw transcripts by default. |
| One backend/SQLite ledger | Boring and small but a single host/process/storage failure domain. Leases, transactions, receipt reconciliation, finite retention, and restart tests help; they do not make jobs run during sleep/off. |
| No universal exactly-once external effects | Durable dedup prevents local re-dispatch within its scope, but an uncertain external outcome still requires reconciliation/provider idempotency evidence. Initial workers have no external effects; future tools must supply receipts and safe retry contracts. |
| Barge-in and quiet notifications versus correctness/latency | Full-duplex output and vendor event behavior can make idle detection or stale audio hard. Client playback control and measured timing matter; append acknowledgments do not prove the intended audio behavior. |
| Cancellation is cooperative and can race completion | `cancel_requested` may resolve to success/failure/unknown rather than cancelled. Report evidence and partial effects; do not claim rollback or host-wide control not implemented. |
| Ambient/replayed/injected speech | May induce unwanted low-risk work inside a grant. Voice does not establish identity or approve new powers. Grants, small sample scopes, expiration, visible controls, and strong separate authentication requirements limit damage. |
| Malicious site targets localhost | Loopback is not sufficient. Authentication, exact Host/Origin/CORS/WS/CSRF boundaries and negative tests are mandatory; compromise of the already-authenticated host/browser is a different threat boundary. |
| Trusted fixed worker versus arbitrary-code sandbox | Reviewed fixed code can still be buggy; threads/processes alone do not restrict host authority. Arbitrary/generated code, plugins, shell and OpenCode jobs remain disabled until an OS/egress containment gate is demonstrated. |
| External budgets cannot erase provider billing uncertainty | Usage/close acknowledgments may fail or lag. Reserve conservatively, cap/close externally, reconcile without duplicate counting, disable unsafe automatic retries, and disclose incomplete finalization. |
| Minimal records and recovery versus retention | Dedup/evidence itself stores data. Define finite content/metadata/retry horizons and purge secondary stores; reject expired requests. Provider data lifecycle is independent and may not expose the same deletion controls. |
| Provisional stack/dependency compatibility | No current code justifies a library choice or proves Windows build support. Verify a supported SDK/runtime/SQLite combination only after a new scaffold request, with no downloads or manifests in this delivery. |
| Documentation drift/provenance inflation | Multiple root documents could disagree or invent consensus/status. Canonical ownership, stable IDs, faithful score/rank tables, separate later research, and independent artifact review prevent a misleading “all gates passed” pack. |

## 5. Task breakdown — documentation implementation only

These tasks are the exact ordered handoff to the documentation developer. Each is documentation-only and independently reviewable. DOC tasks describe authoring this requested pack; `tasks/` files describe future RT tasks and initially remain **not started**. The delivery manager commissions work against this contract and handles independent review/security evidence. No task here authorizes application implementation.

1. **DOC-001 — Create `prd.md`.** Document current scope, native-voice product intent, exclusions, unresolved approvals, synthetic examples, REQ-D01/REQ-D02 and REQ-01–REQ-18 with acceptance links and source citations; add the root navigation block.
2. **DOC-002 — Create `descisions.md`.** Expand DEC-01–DEC-16 with status, rationale, alternatives/trade-offs, source links, reopen conditions, and explicit provisional/post-review status of the native candidate; preserve the spelling and add root navigation.
3. **DOC-003 — Create `council meetings/README.md` and `council meetings/council-meeting-1.md`.** Index the three records, document quick-mode/perspective provenance, and faithfully summarize all four independent opinions with source citations; do not fabricate transcripts or participant models.
4. **DOC-004 — Create `council meetings/council-meeting-2.md`.** Preserve anonymized review labels, exact aggregate ratings/rankings, genuine disagreements, provider recommendation change, and all counterfactual flips; distinguish discussion aids from proof.
5. **DOC-005 — Create `council meetings/council-meeting-3.md`.** Record chair synthesis/resolutions separately from the clearly labeled later Researcher follow-up; link official sources and document untested access/consent/cost/recovery/retention constraints without inventing a re-vote.
6. **DOC-006 — Create `architecture.md`.** Describe proposed modules/media/control boundaries, conceptual records/interfaces, all eight canonical job states, grants, budgets, idempotency/revisions/epochs, result verification, security/retention, and deferred adapters; label stack, transport, limits and performance targets provisional.
7. **DOC-007 — Create `flow.md`.** Expand WF-01–WF-10 into numbered Markdown workflows and state tables, cross-linking the canonical architecture; preserve distinct stop semantics, cancellation/terminal races, stale session handling, failure paths and host lifecycle.
8. **DOC-008 — Create `phases.md`.** Define PH-DOC and PH-00–PH-07 with ordered prerequisites, task links, exit/approval gates and initial `not started` future statuses; keep documentation milestones distinct from measured runtime acceptance.
9. **DOC-009 — Create `tasks/README.md` and task files `tasks/001-runtime-consent-and-feasibility.md` through `tasks/006-steering-and-stop-controls.md`.** Apply the common template and exact RT-001–RT-006 scopes/IDs/dependencies; all future task statuses are `not started`, with no execution evidence.
10. **DOC-010 — Create task files `tasks/007-recovery-and-retention.md` through `tasks/012-private-native-audio-feasibility.md`.** Apply the same template to RT-007–RT-012; distinguish fixed-slice validation, useful planner, optional OS-contained OpenCode, always-on/device work and native-private feasibility; keep all future statuses `not started`.
11. **DOC-011 — Create `build.md`.** State that no application/build exists; separately label source-recorded diagnostics and unexecuted documentation observations; list any future command names only as proposed/non-runnable until an approved scaffold, with prerequisites and no fabricated execution evidence.
12. **DOC-012 — Create `progress.md` and complete the pack consistency review.** Record the dated documentation-only authoring milestone and actual evidence; use real independent review/security reports as authoritative when supplied, otherwise state their absence. Manually check all 24 target files, literal names, navigation/ID links, council fidelity, state/stop/consent consistency, future statuses, provisional targets and command labels; report unresolved gates without claiming runtime/tests exist.

## 6. Definition of done

### 6.1 Documentation-pack acceptance — this request

All checks below are artifact/manual review checks. No application test suite or added validation script is required or claimed.

| Acceptance ID | Evidence required |
| --- | --- |
| DOC-A01 — Complete literal taxonomy | All 24 target Markdown files exist with the exact requested root/folder names and numbered task paths; sources/design preserved; no source scaffold, manifests, scripts, Git initialization, downloads, recordings, credentials, or globals changed by this delivery. |
| DOC-A02 — Grounded and traceable | Existing facts cite opened `docs/delivery/...:line` references; published capabilities link official sources and dates; REQ/DEC/RT/PH/WF IDs resolve; proposed interfaces/stack/limits are not described as existing APIs or tests. |
| DOC-A03 — Faithful council | All four opinions, means/ranks, actual disagreement resolutions and counterfactuals are preserved; anonymity/provenance caveats retained; later GPT-Live research is visibly separate from chair synthesis and not presented as re-voted unanimity. |
| DOC-A04 — Consistent architecture and flows | Eight job states, cancellation/unknown semantics, typed external authority, idempotency/revisions/stale sessions, distinct stop controls, native-only audio path, retention, fixed versus arbitrary workers, budgets and host lifecycle agree across documents. |
| DOC-A05 — Honest build/progress/status | No runtime/model/voice/performance/security/build success is claimed. Future commands are prominently proposed/non-runnable; prior 404 diagnostics are not success tests. Future phases/tasks initially say `not started`; documentation authoring and independent assessments have separate dated status/evidence. |
| DOC-A06 — Independent dispositions and navigation | Links work for actual pack/source artifacts. Actual independent design-review and design-security reports for the assessed revision are authoritative and their dispositions are faithfully reflected, with unresolved blockers recorded. Absence is explicitly unreviewed, not a fabricated pass or an unexplained broken evidence link. |

The pack can be reported as **authored** before independent review concludes. The documentation milestone is **accepted** only when the manager has real independent review/security dispositions for the relevant revision and all blocking documentation/design findings are resolved or explicitly dispositioned by the appropriate owner. A design-stage security assessment certifies neither absent implementation nor native-account feasibility (`docs/delivery/council.md:211-214`). At this signature, these pack checks and assessments have not been completed.

### 6.2 Future runtime release gates — not this delivery

All runtime gates/tests below are **not started**. A signed documentation contract, a completed pack, or permission to use development models cannot close them.

| Gate | Required future evidence |
| --- | --- |
| RT-G00 — Authority and feasibility before runtime | Explicit new implementation/scaffold authorization; confirmed host; user-selected first real task pair; eligible provider/model/native transport and actual account/region/quota access; disclosed terms/retention/recipients; named microphone/context/worker egress consent; external secret setup; approved monetary/resource limits and bounded retention/retry windows. Without these, no cloud audio test or unapproved task execution. |
| RT-G01 — Local boundary and native connection | Actual reviewed scaffold/commands and deployed authentication/Host/Origin/CORS/WS/CSRF controls; backend-only secrets; measured native media and backend event/control connection with manual activation, stop controls, visible states and fail-closed unsupported transport behavior. |
| RT-G02 — Fixed-worker proof | Two trusted read-only synthetic workers with bounded inputs, receipts, off-loop execution, authoritative ledger states and externally enforced resource limits; continued native conversation during overlap. No arbitrary-code/host-shell/plugin/external-action exposure. |
| RT-G03 — Steering, cancellation, recovery | Evidence for revisions, all stop semantics, cancellation races/unknown outcomes, stale commands/audio/notifications, duplicate requests/actions, lost events, native replacement sessions and backend restart without blind effects replay. Sleep/off limitations are disclosed/tested. |
| RT-G04 — Measured slice acceptance | RT-A01–RT-A06 results, actual latency/barging distributions and failures, retention/budget behavior, negative security tests, and independent implementation review/security assessment of the actual revision. Targets failing measurement require a reported disposition, not marketing claims. |
| RT-G05 — Extensions require separate gates | Real-task planner, new tools/authority, arbitrary/generated workers, OpenCode, persistent memory, wake/locked-screen/always-on hosting, stored-session recording, or private inference each needs its own approval, containment/egress/data tests and measured utility/feasibility. Fixed demo acceptance does not enable these automatically. |

#### Tests that would prove the future fixed slice

| Test ID | Future proof obligation; none has been run |
| --- | --- |
| RT-A01 — Native and consent | Verified named account/endpoint actually accepts and emits native live audio; no external STT/chat/TTS voice chain or automatic cloud fallback. Withheld consent, unsupported endpoint, expired grant, lost control channel or permission failure prevents upload/dispatch. Test backend key protection and actual media lifecycle. |
| RT-A02 — Responsiveness and playback | Two bounded workers run while native conversation continues; measure first useful played speech and barge-in against provisional targets on declared hardware/network. Confirm stale output is not replayed, notifications respect measured conversation/playback boundaries, mic-stop stops transmission, and stopping speech does not cancel jobs. |
| RT-A03 — Task truth and bounded work | IDs return promptly; synthetic results match independently computed expectations; malformed/oversized proposals and forged/superseded receipts cannot commit success. Verify aggregate concurrency, steps/retries/deadline limits and CPU work outside audio/control processing. |
| RT-A04 — Duplicates, races and recovery | Duplicate create/revise/cancel calls, crash before/after dispatch/result commit, delayed old-session events, revision races, lost worker receipts and interrupted approvals never blindly repeat effects or invent progress. Cancellation resolves only with evidence; uncertainty remains `unknown`. New sessions get reconciled facts, not old delegation IDs or acoustic-continuity promises. |
| RT-A05 — Authority and local attack surface | Unauthenticated clients, hostile/null origins, incorrect Hosts, cross-site requests, forged WS controls, prompt-injected audio/transcripts/results, expired grants, new capability requests, shell/plugins/purchases/messages/deletion and unapproved egress are denied. Ambient “yes” cannot elevate authority or re-arm emergency stop. Demonstrate the deployed boundary, not merely prompt instructions. |
| RT-A06 — Privacy, budgets and lifecycle | No local raw recordings/transcript/model-content logs; bounded task/metadata retention and secondary-store purge; expired replay rejection; credentials absent from browser/project/context/records/logs; provider retention disclosed independently. Budget reservation/usage, unsafe retry prevention, caps, uncertain finalization and host sleep/restart behavior are measured and reported honestly. |

Future RT-009 additionally demonstrates usefulness and bounded decisions for the approved real task pair, including verification, checkpoints, cancellation/steering, denial of new authority, and limits under repeated failure. RT-010 demonstrates **OS** containment and child/egress restrictions rather than OpenCode prompt permissions alone. RT-011/RT-012 are feasibility gates, not promises that the observed laptop supports always-on or private native voice.

## Signature and handoff boundary

**Signed:** Solution Architect — `agentrouter/gpt-6.1-sol#max` (configured profile declared for this assignment)  
**Date:** 2026-11-07  
**Revision:** 1  
**Disposition:** Architecture/documentation contract delivered for independent review and design-stage security assessment. Only `docs/design/super-agent.md` is authored by this architect. No runtime voice/model integration, application code, dependency installation, credentials/private-file inspection, global change, model API test, microphone capture, or executed build/test command is claimed.

This signature commits to the literal documentation taxonomy, native-audio/control-plane separation, bounded externally enforced authority and truthful evidence/state, and the approval gates above. It does **not** substitute for independent review, user consent, spending approval, deployment authorization, or measured runtime acceptance. The numbered DOC-001–DOC-012 task breakdown in section 5 is the verbatim documentation handoff.
