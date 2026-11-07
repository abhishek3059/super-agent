# Super-agent: discovery brief

Date: 2026-11-07
Status: requirements and architecture exploration; not an implemented assistant.

## User intent

Build a personal assistant with the conversational feel of Jarvis: talk naturally,
delegate multiple tasks to the background, steer work while it runs, and let the
assistant iterate and make decisions within explicit limits.

The user clarified that the interface must be **native voice-to-voice**, similar
to Gemini Live, with hands-free interaction. A mandatory external speech-to-text
to text-chat-model to text-to-speech pipeline is not the requested experience.
Voice-only describes the interaction: structured internal tool arguments, job
records, and task summaries are still necessary.

Privacy is an important eventual goal. The user explicitly permits cloud models
from OpenCode, AgentRouter, OpenRouter, or Gemini for development. This does not
by itself authorize streaming personal microphone audio or personal documents to
a particular runtime provider. Runtime cloud use requires a separate explicit
setup decision.

## Current scope and unresolved decisions

This discovery pass produces council deliberation and a proposed buildable
architecture, not an unrequested production deployment or an installed model.

- First real task categories and examples have not been selected.
- Target deployment hardware has not been confirmed.
- A Gemini Live-style experience is requested; a paid Live API account, exact
  provider/model, region, quota, and pricing have not been verified.
- Initial microphone permission, secret setup, and device security may require
  manual setup. Hands-free operation afterwards is the goal, not a promise to
  bypass operating-system permissions or identity checks.
- Arbitrary host shell access, purchases, sending messages, deleting user files,
  and general computer control are not authorized first-version capabilities.

## Observed development environment

- The project directory was empty at the beginning of discovery; no existing
  application, repository history, tests, or stack conventions were present.
- Windows; approximately 7.8 GiB usable RAM; Intel i5-10300H, four CPU cores;
  NVIDIA GTX 1650 Ti with approximately 4 GiB reported adapter memory.
- These specifications constrain a future local native-audio model. No local
  model was downloaded or benchmarked. Performance claims need measurement.
- Installed CLI reports OpenCode v2.1.2. Its local service is running.
- Global custom profiles include architect, developer, reviewer, security-auditor,
  and designated free fallbacks. No global configuration was modified, and no
  credentials were copied into project documents.
- The local AgentRouter proxy port is reachable. This is a TCP availability
  observation, not a successful test of every configured model.
- A read-only request through `opencode api get
  /api/experimental/voice/models` returned HTTP 404. The current public V2 API
  reference lists experimental voice routes, but they cannot be assumed to work
  with this installed service. A voice provider adapter must not depend on them
  without explicit version/capability verification.

## Requirements to preserve in the design

1. Stream microphone audio to a verified native-audio model and play its audio
   response; do not silently substitute a chained text voice system.
2. Support barge-in and natural turn-taking. Stopping playback, interrupting a
   conversational response, cancelling a particular job, and stopping all work
   are distinct operations.
3. Keep foreground conversation responsive while bounded jobs execute. A slow
   worker or failed provider must not freeze microphone processing or playback.
4. Persist authoritative task state outside the live model session. Reconnects,
   duplicate tool calls, service restarts, and delayed completion events must not
   duplicate side effects or produce invented progress.
5. Enforce scope, paths, tool availability, credentials, network destinations,
   cost, time, concurrency, and iteration limits outside model instructions.
6. Treat audio, websites, documents, and worker output as potentially untrusted.
   A wake word or spoken yes is not strong identity verification.
7. Allow only low-risk, pre-scoped actions through spoken interaction initially.
   Consequential actions remain disabled unless stronger authorization is
   designed and approved. Strictly hands-free operation must not imply insecure
   approval of irreversible actions.
8. Keep local raw-audio recording and transcript persistence off by default.
   Minimize stored task content; explain that cloud audio processing and provider
   retention are separate from local storage choices.
9. Expose a clear listening/cloud-connected state, a way to pause microphone
   upload, task cancellation, and an emergency stop. Do not claim that a prompt
   alone enforces any of those boundaries.
10. Keep native audio, worker reasoning, tools, task storage, and policy replaceable
    independently. A later private runtime needs genuinely compatible local
    native-audio inference and an egress boundary, not merely a local database.

## Public documentation consulted by the parent session

These are discovery observations, not tested runtime integrations. Documentation
and deployed service versions may differ.

- Gemini Live overview: https://ai.google.dev/gemini-api/docs/live
- Gemini Live tools: https://ai.google.dev/gemini-api/docs/live-tools
- Gemini Live ephemeral tokens: https://ai.google.dev/gemini-api/docs/ephemeral-tokens
- OpenCode V2 configuration: https://opencode.ai/v2/docs/config
- OpenCode V2 agents: https://opencode.ai/v2/docs/agents
- OpenCode V2 permissions: https://opencode.ai/v2/docs/permissions
- OpenCode V2 client: https://opencode.ai/v2/docs/build/client
- OpenCode V2 API: https://opencode.ai/v2/docs/api

The Gemini documentation describes streamed audio input and output, barge-in,
manual function-call handling, and model-dependent asynchronous tool calling.
Short-lived client tokens reduce credential exposure but do not make cloud audio
private or authenticate the speaker. The OpenCode client guide describes live-only
event subscriptions without automatic replay/reconnect; durable reconciliation
belongs to the application. OpenCode permissions are not an OS sandbox: shell
commands run with the host user's authority, and child-agent permissions are
independent rather than automatically intersected with the parent's permissions.
