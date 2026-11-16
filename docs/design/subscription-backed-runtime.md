# Subscription-backed Jarvis runtime

Proposal for PH-01. Account access, spending, data egress, transport evidence
and any later worker capability are tracked separately.

## Account routes

| Use | Proposed route | Qualification |
| --- | --- | --- |
| Native Jarvis voice | OpenAI GPT-Live over a backend-owned WebSocket, with Realtime considered if the player cutoff or close checks fail | An eligible ChatGPT Pro or Business plan can claim API credits for a linked API organization. The app uses project API credentials and needs verified model access, permitted input and a bounded budget. |
| Claude Pro | The operator uses the official Claude Code binary with their own sign-in. Evaluate it later as a contained coding worker. | Claude Pro includes Claude Code. An integrated worker needs the PH-05 containment and scope review. A direct Claude API integration uses separate Console or cloud credentials and billing. |
| Hermes parity | Keep Hermes as a reference and optional future worker candidate. | The normal Hermes Anthropic subscription route excludes Claude Pro. The published experimental Claude provider runs the official CLI. Qualify its actual credential and egress handling before considering it. |

OpenAI's [subscriber credits](https://developers.openai.com/api/docs/guides/chatgpt-api-credits)
cover GPT-Live and Realtime if eligible. Active credits can be used without
adding an API payment method. The project still needs its own API credential
and a spending decision. The [ChatGPT voice interface](https://help.openai.com/en/articles/20001274-chatgpt-voice)
and [Claude voice interface](https://support.claude.com/en/articles/11101966-use-voice-mode)
can be used in their own apps. BotHQ's separate worker sign-in does not pay for
the call. Its backend requests a short-lived credential using the xAI API.
[API data controls](https://developers.openai.com/api/docs/guides/your-data)
apply at the chosen endpoint. Follow Anthropic's
[Claude Code terms and authentication guidance](https://code.claude.com/docs/en/legal-and-compliance).
The app must keep sign-in in Anthropic's own flow and must never collect
Claude.ai tokens. See the [Claude Pro plan](https://support.claude.com/en/articles/8325606-what-is-the-pro-plan),
[standard Hermes provider](https://hermes-agent.nousresearch.com/docs/integrations/providers/), and
[experimental Hermes provider](https://hermes-agent.nousresearch.com/marketplace/claude-subscription-directsdk).

## PH-01 candidate

1. Record the explicit provider change from the [approved PH-00 boundary](../approvals/ph-00-setup-decisions.md).
   Confirm project access, synthetic-only data, endpoint retention, quota,
   and the permitted spending limit. Keep the current $0 cap unless the
   decision changes. Retain Gemini evidence as dated history.
2. Resolve F5 and review F2 from the [loopback assessment](../reviews/r01-6-security-review.md).
   Verify backend identity before sending an authorization proof or asking
   for capture. Reject an unauthenticated upgrade before it takes an active
   voice slot. Test replay, a spoofed backend, lost control and valid access
   during unauthorized connection churn. Record the independent review.
3. Reuse the Angular controls and FastAPI voice seam. Script GPT-Live events
   offline before the approved generated-PCM test. Its
   [WebSocket guide](https://developers.openai.com/api/docs/guides/voice-websockets?api=live)
   supports 16 kHz PCM. Map readiness, microphone state, playback epochs,
   failure and confirmed closure to the local contract. Measure the output
   from the player. Keep the long-lived API key on the backend.
4. Test connection, useful audio, interruption, mute, end, unavailable model
   and exhausted usage. Disable tools and keep input synthetic for the first
   run. Set a session deadline. Stop when the selected provider is unavailable.
   Complete RT-002 and RT-003 against the actual results before ticking R-01.10.

The normal setup can drop the Gemini and local-model requirements after the
replacement is qualified. The fake adapter remains useful for offline tests.
The existing [synthetic console proposal](synthetic-voice-console.md) records
the previous Gemini design and can inform the generated-audio path.
The [offline call spike](../../spikes/a6-openai-call/README.md) compares BotHQ's
call flow with a scripted OpenAI Realtime session through the existing bridge.

## Workspace and later worker

The first workspace puts conversation beside two fixed local jobs with
visible progress, source references and verified receipts. Keep those jobs
local under the approved first task pair, including when OpenAI supplies
speech. The first connector and the Claude worker follow their own capability
gates. Voice, text and later workers use one application-owned job and policy
boundary. Super-agent verifies the result before displaying a success state.

For the later worker, qualify a pinned official Claude Code binary using
its native authentication inside a scoped environment. Verify the absence
of inherited project credentials, ambient tool or plugin access and out-of-scope
files. Disable persistence for the first synthetic run. Measure cancellation,
plan-limit failure and complete teardown. The official
[CLI reference](https://code.claude.com/docs/en/cli-reference) describes the
tool, settings and MCP controls. Treat those controls as defense in depth
and verify OS containment separately under [PH-05](../../phases.md).
