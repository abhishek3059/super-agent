# Council deliberation: a native-voice personal super-agent

Date: 2026-11-07
Status: discovery synthesis; no assistant has been implemented or deployed.
Requirements source: [super-agent-brief.md](super-agent-brief.md).

## Question

How can we build a Jarvis-like assistant that accepts and produces native live
audio, remains conversational while several tasks run, iterates within bounded
authority, works hands-free after setup, and has an honest path toward privacy?

The user permits cloud models for development and wants stronger privacy later.
Permission to use a specific runtime microphone/cloud connection is a separate,
unresolved decision. Actual first tasks and deployment hardware are unconfirmed.

## Mode and panel

Quick mode: four independent `general` subagent sessions, followed by anonymized
cross-review and chairman synthesis. This is perspective diversity, not a claim
that the four sessions used different model families. Existing specialized
architect/reviewer/security profiles are available for subsequent design gates.

- A: The Architect — systems design and state ownership.
- B: The Skeptic — exploit paths, failure modes, and authority.
- C: The Pragmatist — smallest credible voice-first experiment.
- D: The Researcher — official API capabilities, terms, and prior art.

## Individual perspectives

### A — The Architect

Separate an ephemeral native-audio conversation plane from a durable, locally
controlled execution plane. The voice coordinator owns turns, playback epochs,
and conversational interruptions; the task service owns job state, cancellation,
budgets, and verified results. Tool requests are typed proposals through a policy
broker, never direct authority for the voice model.

Verify native audio and obtain microphone-egress consent rather than assuming
configured text APIs support it. Barge-in stops the response and queued playback,
not background jobs. Use scoped capabilities and credentials outside the LLM;
any future OpenCode coding worker needs OS-level containment. Spoken confirmation
can refine low-risk work within existing authenticated grants, not authorize
consequential actions or new authority. Journal intent/result/idempotency; reconcile
after reconnect instead of replaying actions. Local native inference is a later
benchmark, not an established capability of this laptop.

### B — The Skeptic

Build a bounded voice appliance before an autonomous host operator. Ambient,
replayed, or synthetic audio, web pages, and tool output can induce unsafe actions.
Wake words and voiceprints do not authenticate intent. Use schema-validated tools,
scoped access, denied egress by default, and exact-action approval boundaries.

Interrupted approvals expire. Reconnects must not repeat irreversible actions;
uncertain outcomes need reconciliation. Stopping speech cannot undo completed
effects. Require evidence before claiming progress or completion, and externally
limit concurrency, time, steps, retries, and spend. Disable local raw recordings
and transcript persistence, but disclose independent provider retention. Start
with two read-only sample jobs; consequential actions remain unavailable.

### C — The Pragmatist

Prove the experience with a localhost browser and one backend, one native voice
adapter, two trusted fixed-function workers, and a small job store. Return job IDs
quickly and allow continued conversation. Illustrative sample-data analysis jobs
are enough to test overlap; they are not assumed to be the user's desired tasks.

Manual account/microphone setup precedes hands-free operation in the active app.
Use a headset and echo cancellation first. Separate stopping speech from cancelling
jobs. Keep long-lived keys in the backend/OS vault, not the browser. Use bounded
input sizes and job limits; do not present trusted in-process functions as an
arbitrary-code sandbox. Measure latency, cancellation, restart, and denied-scope
behavior. Defer desktop packaging, always-on wake detection, general host control,
and local native-model inference until the basic experience is demonstrated.

### D — The Researcher

Official Gemini Live documentation supports direct streamed audio input/output,
barge-in, optional transcription, and structured tool calls. Nonblocking function
behavior is model-dependent; resumption is not permanent memory. Expiring tokens,
session rotation, exact account access, and retained provider content need explicit
validation. Existing OpenCode/router text-model configuration proves none of this.

Current Gemini developer terms describe professional/business use rather than
consumer use and warn against personal/sensitive content on unpaid services.
Paid services still process/log data. Eligibility must be checked rather than
presumed for this personal assistant. Native local audio prior art exists, but
Moshi's published PyTorch setup requires much more GPU memory and lacks official
Windows support. Do not promise a turnkey private native-voice assistant on 4 GiB
VRAM. Verify transport before selecting an agent framework.

## Peer review summary

Each member scored the other three responses on relevance, feasibility, and
insight, each from 1 to 5. The following are arithmetic means of the three
received ratings, rounded to two decimals; they are discussion aids, not proof.

| Response | Relevance | Feasibility | Insight | Main contribution |
| --- | ---: | ---: | ---: | --- |
| A — Architect | 5.00 | 3.33 | 4.67 | State ownership, recovery, and authority separation |
| B — Skeptic | 5.00 | 4.00 | 5.00 | Concrete security and evidence boundaries |
| C — Pragmatist | 4.67 | 4.00 | 4.00 | A small, testable vertical slice |
| D — Researcher | 4.67 | 3.67 | 4.67 | Provider eligibility and capability gates |

Rankings of other responses:

- A: B > C > D.
- B: A > D > C.
- C: D > B > A.
- D: B > C > A.

All four converged on native audio, external authority enforcement, explicit cloud
consent, no early unrestricted shell, and no unsupported local-hardware promise.
The cross-review changed the initial provider recommendation: Gemini must not be
the presumed personal runtime. An eligible direct OpenAI native-audio API is an
alternative to investigate, not an established account connection.

## Genuine disagreements and their resolution

1. **Durable workers now or later?** The Architect favors recovery guarantees;
   the Pragmatist and Researcher would omit a queue for trivial disposable tasks.
   Resolution: use only a small authoritative job ledger when the chosen demo
   tests overlap/cancellation/restart. Do not add distributed scheduling, recurring
   jobs, or a general agent fleet before actual tasks justify them.
2. **Wake words immediately?** Local gating supports privacy and an eventual
   assistant experience, but adds complexity to a first experiment. Resolution:
   manually activate one explicitly consented voice session initially; defer
   system-wide wake detection and locked-screen/background listening. This is
   hands-free during the active session, not yet an always-on appliance.
3. **In-process workers or isolation?** Trusted fixed sample functions can share
   the backend; arbitrary/generated code and plugins cannot. Resolution: only
   bounded trusted functions initially. CPU-heavy work must still run off the
   audio/control event loop. General agent execution requires a separately tested
   OS containment and egress boundary before it is enabled.
4. **Cloud-first versus private-first?** Cloud may validate native conversation
   on current hardware, but only after runtime consent, eligibility, and acceptable
   data terms. If those fail, investigate a private native-audio host or change
   scope/hardware; never quietly substitute a chained STT/chat/TTS system.

## Counterfactual pass

Because round one converged quickly, every cross-review also assumed the shared
plan was wrong. The council identified the following evidence that would flip it:

- No eligible provider, withheld microphone consent, unacceptable retention, or
  failed native duplex/barge-in tests: reject that cloud runtime.
- A genuinely native local model meets measured quality/latency within confirmed
  hardware limits: prefer local inference.
- First tasks are instantaneous/disposable and need no recovery: remove durable
  scheduling rather than manufacture background work.
- Tasks must continue while this laptop is asleep/off: use an approved always-on
  host. A persistent queue alone cannot execute work on a sleeping computer.
- Failed containment/egress tests: remove the affected tools; a diagram or prompt
  is not a substitute for an enforced boundary.

## Chairman's synthesis

Build a **native voice interface over a controlled task service**, not a single
omnipotent model. The voice model maintains the conversational relationship; a
local broker grants only allowed work; the task service tracks execution truth.
Specialized reasoning workers are introduced only after a bounded voice-first
slice succeeds. OpenCode's existing agents can assist development now and become
an optional, isolated coding-job adapter later—not the assistant's microphone
transport or a security sandbox by default.

The intended interaction is: ask for two jobs, continue talking, interrupt a
spoken answer, steer or cancel a named job, and hear a concise completion report
backed by actual results. Long tasks return IDs rather than occupying the live
conversation. Completion notifications wait for an idle conversational boundary
unless the user requests otherwise. Task grants, budgets, and state survive voice
reconnects without granting new authority or promising acoustic continuity.

Native audio is a non-negotiable UX constraint. Internal JSON arguments, task
summaries, and evidence records do not turn this into a chained voice chatbot.
Likewise, local memory does not make cloud microphone inference private.

## Key decisions

- Architecture first in this session; no model downloads, microphone capture,
  provider provisioning, credentials in project files, or runtime deployment.
- Keep native audio, worker reasoning, policy, and task storage independently
  replaceable. Do not silently fail over to another cloud provider.
- Provider gate before live testing: eligibility, exact model/transport, account,
  region, quota, data terms, usage costs, and explicit microphone/context consent.
- One local authenticated service and thin audio UI for the first experiment;
  no microservices, vector database, or general-purpose computer-control agent.
- Routine low-risk operations only within preapproved scopes. Voice is not
  identity; consequential actions remain disabled without stronger authorization.
- No default persisted recordings/transcripts or model-content telemetry. Minimal
  task records also need retention/deletion rules; provider logs are independent.
- Minimal job states distinguish `cancel_requested`, `cancelled`, and `unknown`.
  Evidence and reconciliation determine outcomes, not model narration.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Ambient audio or prompt injection | Untrusted-input treatment; fixed allowlisted tools; no authority escalation |
| A malicious website targets localhost | Authenticated local API; strict Origin/Host/CORS checks; CSRF protection; no URL-carried permanent secrets |
| Duplicate execution after reconnect | Durable request/effect IDs; deduplication; receipts; no blind uncertain retries |
| Unresponsive audio during work | Separate audio/control paths from job processing; size/concurrency/time limits |
| Runaway bills or recursive agents | External session/worker budgets, reservation/usage accounting, deadlines and step ceilings |
| Misleading completion or cancellation | Stored verified outcomes; explicit cancellation acknowledgements and partial-effect reporting |
| Hidden cloud data exposure | Named provider and recipient scope; explicit runtime opt-in; no automatic fallback; retention disclosure |
| Overclaiming local feasibility | Benchmark compatible native models on confirmed hardware; upgrade/approved private host if necessary |
| Laptop sleep stops jobs | Disclose execution-host lifecycle; always-on host only with explicit approval |

## Next steps

1. Have the configured architect produce an implementation-ready design with
   explicit assumptions, acceptance tests, and unresolved release gates.
2. Review that design and perform an independent design-stage security assessment.
   Those checks do not certify an application that does not yet exist.
3. Select one real task pair, target host, and eligible native-audio runtime with
   the user. Obtain microphone-egress consent and a usage budget before testing.
4. Implement and measure the smallest native-audio connection, then bounded jobs,
   steering/cancellation, truthful progress, and reconnect behavior.
5. Add richer workers, opted-in memory, desktop wake behavior, and private native
   inference as separate reviewed increments.

## Sources and compatibility notes

- Gemini Live: https://ai.google.dev/gemini-api/docs/live
- Gemini Live tools: https://ai.google.dev/gemini-api/docs/live-tools
- Gemini ephemeral tokens: https://ai.google.dev/gemini-api/docs/ephemeral-tokens
- Gemini terms (effective 2026-03-23): https://ai.google.dev/gemini-api/terms
- Native OpenAI Realtime overview: https://developers.openai.com/api/docs/guides/realtime
- OpenCode V2 client: https://opencode.ai/v2/docs/build/client
- OpenCode V2 API: https://opencode.ai/v2/docs/api
- OpenCode V2 permissions: https://opencode.ai/v2/docs/permissions
- Local native-audio prior art: https://github.com/kyutai-labs/moshi

The installed OpenCode service reports v2.1.2; its documented experimental
voice-model route returned HTTP 404 in this environment. Do not depend on the
published route without deployed capability/version validation. Public API facts
above are documentation observations, not authenticated integration tests.
