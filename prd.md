# Super-agent — requirements and acceptance criteria (documentation pack)

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Revision | 4 |
| Status | Documentation-only pack; documentation authored, and actual independent design-stage reports are available ([design review](docs/reviews/super-agent.md), opens PASS; [design-stage security](docs/security/super-agent.md), opens PASS) for the previously assessed revisions: the review covers the revision-3/minor-polish correction set, the security assessment covers signed design revision 1 plus that set. Latest assessed-revision status and final acceptance are recorded in the [delivery status](docs/delivery/super-agent.md); these documents do not self-approve and no runtime/code gate, provider access, budget approval, or application build is claimed here. |
| Revision 2 note | Corrections applied 2026-11-07 for independent review finding R-03 (see [docs/reviews/super-agent.md](docs/reviews/super-agent.md)): the requirement traceability table was restored. |
| Revision 4 note | Status-and-acceptance clarification set applied 2026-11-07, acting on the design review PASS and the design-stage security PASS for the previously assessed revision: fresh current-status metadata (security report INFO-01), [RT-A05](#rt-a05) added to the [WF-01](flow.md#wf-01-setup-and-manual-activation) acceptance references (INFO-02), explicit emergency-stop ephemeral-context clearing in [WF-07](flow.md#wf-07-emergency-stop) (INFO-03), and the security report's LOW-01 finding tracked as an unimplemented future authentication-design acceptance obligation under [RT-A05](#rt-a05) and [RT-002](taks/002-local-scaffold-and-boundary.md). No runtime test has run on this snapshot; its own independent re-review is pending. |
| Signed design | [docs/design/super-agent.md](docs/design/super-agent.md), revision 1 |
| Delivery record | [docs/delivery/super-agent.md](docs/delivery/super-agent.md) |

This document is part of the requested documentation-only pack. It is a contract artifact, not an implemented product. No requirement below is claimed to be implemented, tested, approved, or authorized for runtime use.

## Navigation

- [Signed design — definition of done](docs/design/super-agent.md)
- [Delivery status](docs/delivery/super-agent.md)
- [Discovery brief](docs/delivery/super-agent-brief.md)
- [Council deliberation](docs/delivery/council.md)
- [Architecture](architecture.md)
- [Decisions](descisions.md)
- [Phases](phases.md)
- [Progress](progress.md)
- [Build](build.md)
- [Flow](flow.md)
- [Tasks](taks/README.md)
- [Council meetings](council%20meetings/README.md)
- [Implementation report](docs/implementation/super-agent.md)

## Documentation requirements

### REQ-D01

Deliver the literal, cross-linked documentation taxonomy; no scaffold or runtime actions in this request.

### REQ-D02

Distinguish recorded evidence, published capability, proposals, approvals, and tests; preserve council provenance and accurate statuses.

## Product requirements

### REQ-01

Native streaming audio input/output; no mandatory external STT/chat/TTS chain and no silent transport/provider fallback.

### REQ-02

Manual activation/setup first, then hands-free interaction within an active authenticated browser session; truthful listening/cloud state and accessible mic-stop.

### REQ-03

Barge-in stops stale speech/playback without implicitly cancelling jobs; natural turn-taking and non-disruptive notifications are measured.

### REQ-04

Bounded jobs return durable IDs quickly and overlap without blocking audio/control processing. CPU-heavy work runs off the voice event loop.

### REQ-05

Application-owned ledger and verified receipts determine job progress and terminal outcomes, including cancellation and uncertainty.

### REQ-06

Request/action idempotency, task revisions, stale-session rejection, and reconciliation prevent blind replay after duplicates, disconnects, or restarts.

### REQ-07

Steering a named job, cancelling that job, stopping speech, stopping microphone upload, and emergency-stopping work are distinct operations.

### REQ-08

Initial workers are small trusted fixed functions over synthetic data, not arbitrary/generated code, plugins, unrestricted shell, or external actions.

### REQ-09

Low-risk voice requests operate only within existing authenticated grants; high-risk actions and new authority are disabled without a separately approved strong out-of-band/device-authentication design.

### REQ-10

Schemas, tool/path/dataset scope, egress recipients, input sizes, concurrency, deadlines, steps, retries, and spend are enforced outside models.

### REQ-11

Loopback API authentication plus strict Host/Origin/CORS/WebSocket checks and CSRF defense; a malicious website cannot create sessions or jobs.

### REQ-12

Long-lived provider/tool credentials stay in a backend OS vault or externally supplied environment, never in browser code, project files, URLs, logs, or model context.

### REQ-13

Named runtime microphone/context recipients, eligibility/account/region/quota/cost/data terms, first real task pair, host, and budget require explicit setup approval. Development permission is not that approval.

### REQ-14

Local raw audio, persistent transcripts, model-content telemetry, and provider stored-session recording are off by default; even minimal task content has a bounded retention/deletion policy. Provider retention is disclosed separately.

### REQ-15

Native transport, optional worker reasoning, tools, policy, and storage are independently replaceable; future private inference must be genuinely native and enforce egress boundaries.

### REQ-16

Demonstrate a useful bounded planner for an approved real task pair separately from the deterministic sample-worker proof. Neither unbounded autonomy nor tested runtime reasoning models are claimed now.

### REQ-17

All limits and latency targets are provisional until approved/measured; no native local or locked-screen/always-on guarantee on the observed laptop.

### REQ-18

Host sleep/offline lifecycle is explicit; durable records do not promise execution during sleep/off. An always-on host requires separate approval.

## Requirement traceability

Canonical mapping from the signed design's requirements table (`docs/design/super-agent.md:89-114`). Requirement text is not duplicated here: cite source evidence, governing decisions, and the designated acceptance anchors. [DEC links](descisions.md) resolve to the expanded decision register; [RT-A anchors](#rt-a01) and [RT-G anchors](#rt-g00) resolve within this PRD.

| REQ | Source evidence (opened delivery sources) | Governing decisions | Acceptance anchors |
| --- | --- | --- | --- |
| [REQ-D01](#req-d01) | Delivery instruction recorded in the design and [delivery record](docs/delivery/super-agent.md) | [DEC-01](descisions.md#dec-01), [DEC-16](descisions.md#dec-16) | [DOC-A01](#doc-a01), [DOC-A02](#doc-a02), [DOC-A03](#doc-a03), [DOC-A04](#doc-a04), [DOC-A05](#doc-a05), [DOC-A06](#doc-a06) |
| [REQ-D02](#req-d02) | [Council](docs/delivery/council.md):95-117, :211-214, :234-237 | [DEC-06](descisions.md#dec-06) | [DOC-A02](#doc-a02), [DOC-A03](#doc-a03), [DOC-A04](#doc-a04), [DOC-A05](#doc-a05), [DOC-A06](#doc-a06) |
| [REQ-01](#req-01) | [Brief](docs/delivery/super-agent-brief.md):12-16, :61-62 | [DEC-02](descisions.md#dec-02), [DEC-06](descisions.md#dec-06) | [RT-A01](#rt-a01) |
| [REQ-02](#req-02) | [Brief](docs/delivery/super-agent-brief.md):33-35, :82-84; [Council](docs/delivery/council.md):126-130 | [DEC-03](descisions.md#dec-03), [DEC-08](descisions.md#dec-08), [DEC-15](descisions.md#dec-15) | [RT-A01](#rt-a01), [RT-A02](#rt-a02) |
| [REQ-03](#req-03) | [Brief](docs/delivery/super-agent-brief.md):63-67; [Council](docs/delivery/council.md):167-172 | [DEC-08](descisions.md#dec-08), [DEC-09](descisions.md#dec-09) | [RT-A02](#rt-a02) |
| [REQ-04](#req-04) | [Council](docs/delivery/council.md):64-75, :131-135 | [DEC-04](descisions.md#dec-04), [DEC-05](descisions.md#dec-05), [DEC-12](descisions.md#dec-12) | [RT-A02](#rt-a02), [RT-A03](#rt-a03) |
| [REQ-05](#req-05) | [Brief](docs/delivery/super-agent-brief.md):68-70; [Council](docs/delivery/council.md):192-193 | [DEC-04](descisions.md#dec-04), [DEC-09](descisions.md#dec-09) | [RT-A03](#rt-a03), [RT-A04](#rt-a04) |
| [REQ-06](#req-06) | [Council](docs/delivery/council.md):44-45, :55-58, :201 | [DEC-09](descisions.md#dec-09) | [RT-A04](#rt-a04) |
| [REQ-07](#req-07) | [Brief](docs/delivery/super-agent-brief.md):63-65, :82-84 | [DEC-08](descisions.md#dec-08) | [RT-A02](#rt-a02), [RT-A04](#rt-a04) |
| [REQ-08](#req-08) | [Brief](docs/delivery/super-agent-brief.md):36-37; [Council](docs/delivery/council.md):60-75, :131-135 | [DEC-05](descisions.md#dec-05) | [RT-A03](#rt-a03), [RT-A05](#rt-a05) |
| [REQ-09](#req-09) | [Brief](docs/delivery/super-agent-brief.md):73-78; [Council](docs/delivery/council.md):188-189 | [DEC-07](descisions.md#dec-07) | [RT-A05](#rt-a05) |
| [REQ-10](#req-10) | [Brief](docs/delivery/super-agent-brief.md):71-74; [Council](docs/delivery/council.md):199-205 | [DEC-07](descisions.md#dec-07), [DEC-11](descisions.md#dec-11), [DEC-12](descisions.md#dec-12) | [RT-A05](#rt-a05), [RT-A06](#rt-a06) |
| [REQ-11](#req-11) | [Council](docs/delivery/council.md):200 | [DEC-11](descisions.md#dec-11) | [RT-A05](#rt-a05) |
| [REQ-12](#req-12) | [Council](docs/delivery/council.md):69-72; [Brief](docs/delivery/super-agent-brief.md):49-50 | [DEC-11](descisions.md#dec-11) | [RT-A05](#rt-a05), [RT-A06](#rt-a06) |
| [REQ-13](#req-13) | [Brief](docs/delivery/super-agent-brief.md):18-35; [Council](docs/delivery/council.md):184-185, :215-216 | [DEC-06](descisions.md#dec-06), [DEC-10](descisions.md#dec-10) | [RT-G00](#rt-g00) |
| [REQ-14](#req-14) | [Brief](docs/delivery/super-agent-brief.md):79-81; [Council](docs/delivery/council.md):190-191 | [DEC-10](descisions.md#dec-10) | [RT-A06](#rt-a06) |
| [REQ-15](#req-15) | [Brief](docs/delivery/super-agent-brief.md):85-87; [Council](docs/delivery/council.md):182-183 | [DEC-03](descisions.md#dec-03), [DEC-10](descisions.md#dec-10), [DEC-14](descisions.md#dec-14) | [RT-A01](#rt-a01); later [RT-012](taks/012-private-native-audio-feasibility.md) |
| [REQ-16](#req-16) | [Brief](docs/delivery/super-agent-brief.md):8-10, :29; [Council](docs/delivery/council.md):162-165, :215-220 | [DEC-13](descisions.md#dec-13) | later [RT-009](taks/009-bounded-real-task-planner.md) |
| [REQ-17](#req-17) | [Brief](docs/delivery/super-agent-brief.md):43-46; [Council](docs/delivery/council.md):73-75, :126-139 | [DEC-12](descisions.md#dec-12), [DEC-15](descisions.md#dec-15) | [RT-A02](#rt-a02), [RT-A06](#rt-a06) |
| [REQ-18](#req-18) | [Council](docs/delivery/council.md):152-153, :207 | [DEC-15](descisions.md#dec-15) | [RT-A04](#rt-a04); later [RT-011](taks/011-always-on-and-desktop-feasibility.md) |

The later RT-009/RT-011/RT-012 anchors are future task files, not run tests; none has an execution result today.

## Initial exclusions

The initial capability set excludes arbitrary host shell access, purchases, message sending, user-file deletion, and general computer control; unconditional cloud fallback; presumed Gemini personal runtime; presumed OpenCode voice route; and presumed local hardware capability.

## Unresolved approvals

Runtime consent, provider eligibility and access, first real task pair, host, monetary and resource budgets, retention windows, and implementation authorization remain unresolved and are tracked under [RT-G00](#rt-g00).

## Future runtime gates (definition of done 6.2)

All runtime gates below are future obligations for separately authorized implementation work. None has been started, and none is closed by this documentation pack.

### RT-G00

Authority and feasibility before runtime: explicit new implementation/scaffold authorization; confirmed host; user-selected first real task pair; eligible provider/model/native transport and actual account/region/quota access; disclosed terms/retention/recipients; named microphone/context/worker egress consent; external secret setup; approved monetary/resource limits and bounded retention/retry windows. Without these, no cloud audio test or unapproved task execution.

### RT-G01

Local boundary and native connection: actually reviewed scaffold/commands and deployed authentication/Host/Origin/CORS/WS/CSRF controls; backend-only secrets; measured native media and backend event/control connection with manual activation, stop controls, visible states, and fail-closed unsupported transport behavior.

### RT-G02

Fixed-worker proof: two trusted read-only synthetic workers with bounded inputs, receipts, off-loop execution, authoritative ledger states, and externally enforced resource limits; continued native conversation during overlap. No arbitrary-code/host-shell/plugin/external-action exposure.

### RT-G03

Steering, cancellation, and recovery: evidence for revisions, all stop semantics, cancellation races/unknown outcomes, stale commands/audio/notifications, duplicate requests/actions, lost events, native replacement sessions, and backend restart without blind effects replay. Sleep/off limitations are disclosed/tested.

### RT-G04

Measured slice acceptance: RT-A01–RT-A06 results, actual latency/barging distributions and failures, retention/budget behavior, negative security tests, and independent implementation review/security assessment of the actual revision. Targets failing measurement require a reported disposition, not marketing claims.

### RT-G05

Extensions require separate gates: real-task planner, new tools/authority, arbitrary/generated workers, OpenCode, persistent memory, wake/locked-screen/always-on hosting, stored-session recording, or private inference each needs its own approval, containment/egress/data tests, and measured utility/feasibility. Fixed demo acceptance does not enable these automatically.

## Future runtime acceptance tests (tests that would prove the future fixed slice)

None of the tests below has been run. Each would be evidence only for a separately authorized, implemented, and measured future slice.

### RT-A01

Native and consent: verified named account/endpoint actually accepts and emits native live audio; no external STT/chat/TTS voice chain or automatic cloud fallback. Withheld consent, unsupported endpoint, expired grant, lost control channel, or permission failure prevents upload/dispatch. Test backend key protection and actual media lifecycle.

### RT-A02

Responsiveness and playback: two bounded workers run while native conversation continues; measure first useful played speech and barge-in against provisional targets on declared hardware/network. Confirm stale output is not replayed, notifications respect measured conversation/playback boundaries, mic-stop stops transmission, and stopping speech does not cancel jobs.

### RT-A03

Task truth and bounded work: IDs return promptly; synthetic results match independently computed expectations; malformed/oversized proposals and forged/superseded receipts cannot commit success. Verify aggregate concurrency, steps/retries/deadline limits, and CPU work outside audio/control processing.

### RT-A04

Duplicates, races, and recovery: duplicate create/revise/cancel calls, crash before/after dispatch/result commit, delayed old-session events, revision races, lost worker receipts, and interrupted approvals never blindly repeat effects or invent progress. Cancellation resolves only with evidence; uncertainty remains `unknown`. New sessions get reconciled facts, not old delegation IDs or acoustic-continuity promises.

### RT-A05

Authority and local attack surface: unauthenticated clients, hostile/null origins, incorrect Hosts, cross-site requests, forged WS controls, prompt-injected audio/transcripts/results, expired grants, new capability requests, shell/plugins/purchases/messages/deletion, and unapproved egress are denied. Ambient "yes" cannot elevate authority or re-arm emergency stop. Demonstrate the deployed boundary, not merely prompt instructions.

Future authentication-design obligation (security report LOW-01, an unimplemented future requirement — not a currently implemented vulnerability): before any scaffold acceptance ([RT-002](taks/002-local-scaffold-and-boundary.md)), a future design must define — and be independently reviewed for — cryptographically strong/high-entropy device/session credentials, their secure storage, expiry/rotation/revocation, and failed-authentication throttling/rate-limiting; short PIN-only authentication is rejected and online guessing controls are tested. Source: [design-stage security assessment](docs/security/super-agent.md), finding LOW-01. The exact credential scheme and parameters are deliberately unspecified now and require their own separate design and security review; this wording adds acceptance per the auditor's recommended action and does not create an implemented control, code, or an approved cryptographic algorithm.

### RT-A06

Privacy, budgets, and lifecycle: no local raw recordings/transcript/model-content logs; bounded task/metadata retention and secondary-store purge; expired replay rejection; credentials absent from browser/project/context/records/logs; provider retention disclosed independently. Budget reservation/usage, unsafe retry prevention, caps, uncertain finalization, and host sleep/restart behavior are measured and reported honestly.

## Documentation acceptance

### DOC-A01

Complete literal taxonomy: all 24 target Markdown files exist with the exact requested root/folder names and numbered task paths; sources/design preserved; no source scaffold, manifests, scripts, Git initialization, downloads, recordings, credentials, or globals changed by this delivery.

### DOC-A02

Grounded and traceable: existing facts cite opened delivery source line references; published capabilities link official sources and dates; REQ/DEC/RT/PH/WF IDs resolve; proposed interfaces/stack/limits are not described as existing APIs or tests.

### DOC-A03

Faithful council: all four opinions, means/ranks, actual disagreement resolutions and counterfactuals are preserved; anonymity/provenance caveats retained; later GPT-Live research is visibly separate from chair synthesis and not presented as re-voted unanimity.

### DOC-A04

Consistent architecture and flows: eight job states, cancellation/unknown semantics, typed external authority, idempotency/revisions/stale sessions, distinct stop controls, native-only audio path, retention, fixed versus arbitrary workers, budgets and host lifecycle agree across documents.

### DOC-A05

Honest build/progress/status: no runtime/model/voice/performance/security/build success is claimed. Future commands are prominently proposed/non-runnable; prior 404 diagnostics are not success tests. Future phases/tasks initially say `not started`; documentation authoring and independent assessments have separate dated status/evidence.

### DOC-A06

Independent dispositions and navigation: links work for actual pack/source artifacts. Actual independent design-review and design-security reports for the assessed revision are authoritative and their dispositions are faithfully reflected, with unresolved blockers recorded. Absence is explicitly unreviewed, not a fabricated pass or an unexplained broken evidence link.


