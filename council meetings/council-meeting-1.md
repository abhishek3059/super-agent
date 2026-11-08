# Council meeting 1 — four independent opinions

| Field | Value |
| --- | --- |
| Date | 2026-11-07 (source council session) |
| Source | [docs/delivery/council.md](../docs/delivery/council.md) |
| Status | Archived deliberation record; not a new meeting |
| Revision 2 note | Corrections applied 2026-11-07 for independent review finding R-04 (see ../docs/reviews/super-agent.md): the Researcher's terms/eligibility caveat was reintroduced with its regional/paid qualifications; no opinion text was recomposed. |

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
- [Tasks](../tasks/README.md)
- [Implementation report](../docs/implementation/super-agent.md)

## Provenance

Quick mode: four independent `general` subagent sessions, followed by anonymized cross-review and chairman synthesis. Perspective diversity does not prove different model families.

No verbatim transcript, timestamp, tested integration, participant model, or additional vote is asserted here.

## Opinion summaries

### A — The Architect

Separate an ephemeral native-audio conversation plane from a durable, locally controlled execution plane. The voice coordinator owns turns, playback epochs, and conversational interruptions; the task service owns job state, cancellation, budgets, and verified results. Tool requests are typed proposals through a policy broker, never direct authority for the voice model.

Verify native audio and obtain microphone-egress consent rather than assuming configured text APIs support it. Barge-in stops the response and queued playback, not background jobs.

### B — The Skeptic

Build a bounded voice appliance before an autonomous host operator. Ambient, replayed, or synthetic audio, web pages, and tool output can induce unsafe actions.

Wake words and voiceprints do not authenticate intent. Use schema-validated tools, scoped access, denied egress by default, and exact-action approval boundaries.

### C — The Pragmatist

Prove the experience with a localhost browser and one backend, one native voice adapter, two trusted fixed-function workers, and a small job store.

Manual account/microphone setup precedes hands-free operation in the active app.

### D — The Researcher

Official Gemini Live documentation supports direct streamed audio input/output, barge-in, optional transcription, and structured tool calls.

The existing OpenCode/router text-model configuration proves none of this. Native local audio prior art exists, but Moshi's published PyTorch setup requires much more GPU memory and lacks official Windows support.

Researcher terms caveat, preserved with the signed design's regional/unpaid qualifications ([signed design](../docs/design/super-agent.md):152; `docs/delivery/council.md`:85-87): current Gemini developer terms describe professional/business developer use rather than consumer use; unpaid-service terms warn against submitting sensitive, confidential, or personal information, with regional qualifications attached to that unpaid-service warning; paid use still processes/logs content. Eligibility for this personal assistant must therefore be checked rather than presumed — this caveat does not by itself prohibit Gemini, which remains eligibility-gated.

## Explicit caveats

- Samples discussed are illustrative; hardware/account access unverified.
- No microphone capture, provider provisioning, model download, or runtime deployment occurred.
- Preserve these opinions as source-derived summaries, not attributed verbatim statements or tested findings.
