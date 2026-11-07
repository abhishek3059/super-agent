# Council meeting 3 — chair synthesis and post-review Researcher follow-up

| Field | Value |
| --- | --- |
| Date | 2026-11-07 (source council session) |
| Source | [docs/delivery/council.md](../docs/delivery/council.md) |
| Status | Archived deliberation record; post-review follow-up is later research |

## Navigation

- [Council meetings index](README.md)
- [Council deliberation source](../docs/delivery/council.md)
- [Signed design](../docs/design/super-agent.md)
- [Delivery status](../docs/delivery/super-agent.md)
- [Discovery brief](../docs/delivery/super-agent-brief.md)
- [Requirements](../prd.md)
- [Decisions](../descisions.md)
- [Architecture](../architecture.md)
- [Phases](../phases.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Tasks](../taks/README.md)
- [Implementation report](../docs/implementation/super-agent.md)

## Part A — chair synthesis and resolutions

Chair synthesis: native voice interface over controlled task service, not a single omnipotent model.

Resolutions recorded:

- Native voice over controlled task truth.
- Small ledger where overlap/restart justify it.
- Fixed workers first.
- External capabilities/budgets/idempotency/verification.
- Distinct stops.
- Low-risk existing grants only.
- No presumed Gemini/runtime account.
- No unsupported local-hardware promise.
- Optional contained OpenCode later.

## Part B — post-review Researcher follow-up, not re-voted consensus

This section records a separately headed post-review Researcher follow-up, not re-voted consensus.

It records the provisional GPT-Live candidate and official-documentation checks.

- It is later research supplied with the delivery instructions.
- It was followed by the architect's provisional adoption.
- It is not an additional council vote and was not re-voted by all four original council members.
- The source council itself only recommended investigating an eligible direct OpenAI native alternative.

Official documentation checks (read for this contract on 2026-11-07; public-documentation verification only; no credentials, model API requests, provisioning, microphone capture, or authenticated account capability tests were performed):

- [GPT-Live delegation](https://developers.openai.com/api/docs/guides/live-delegation)
- [GPT-Live conversations](https://developers.openai.com/api/docs/guides/live-conversations)
- [GPT-Live WebRTC](https://developers.openai.com/api/docs/guides/voice-webrtc?api=live)
- [GPT-Live server controls](https://developers.openai.com/api/docs/guides/voice-server-controls?api=live)
- [Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations)
- [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
- [Gemini Live overview](https://ai.google.dev/gemini-api/docs/live)
- [Gemini API terms, effective 2026-03-23](https://ai.google.dev/gemini-api/terms)
- [OpenCode V2 permissions](https://opencode.ai/v2/docs/permissions)
- [OpenCode V2 client guide](https://opencode.ai/v2/docs/build/client)

Public capability confirmation is not a runtime feasibility result.

### Faithful findings recorded from the follow-up (not re-voted)

The follow-up's substantive findings, as recorded by this research rather than endorsed by any original vote:

- A native conversational frontend can delegate to a separately operated backend using client delegation. `session.delegation.created` provides delegation metadata, not the user's task text.
- Building a task proposal consumes transient `session.input_transcript.delta` / `session.output_transcript.delta` context plus authoritative application state. A transcript fragment is not a complete turn, may be mistaken or later corrected, and must not dispatch arbitrary work or assume a fabricated turn-complete event. No external STT → text-chat → TTS voice chain is introduced by consuming native transcript events for task interpretation; native audio remains the conversational path.
- Published sideband events (`session.thinking.append`, `session.commentary.append`) can carry quiet progress and speech-intended facts. Their acknowledgments are not evidence of completed work, correct wording, silence, or actual playback. Never send secrets or private reasoning through "thinking" context: it can influence later speech.
- Barge-in or conversation steering does not cancel backend work; the application requests and verifies job cancellation separately. A provider-side mute is not a privacy mic-stop: the client must stop transmitting local microphone media and discard unsent buffers.
- The backend sideband observes delegation/transcript events directly and is the sole execution and result-update owner. Browser event echoes are captions/control requests, not a second worker executor or trusted task-state writer. Attach/control access and client permissions need deployed verification; execution fails closed if the required backend control channel fails.
- A reconnect uses a new application epoch and, when required, a new native session with minimized current context and only allowed transient history. Never reuse an old session's delegation ID as an ID known to the new session. Stored-session forking is not the recovery mechanism: it requires persistence and completed recordings, has provider retention implications, and still creates a new session.
- Provider recording/storage defaults are off in the initial slice, but default abuse-monitoring logs may retain content for up to 30 days with stated legal/safety exceptions. No-training is not no-retention; ZDR/MAM require eligibility and prior approval; local deletion cannot erase provider logs/recordings. The official data-controls page currently documents no public stored-session deletion endpoint.
- Named runtime access, consent, and budget are not approved by this research. Actual account access, model identifier, SDK/server compatibility, client-control restrictions, pricing, initialization/session charges, duration limits, region, retention, and microphone/context consent remain RT-G00 gates. The architect profile is not a runtime voice-model selection.

