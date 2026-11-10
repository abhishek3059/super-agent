# R-01.4 microphone observations and proposed next step

| Field | Value |
| --- | --- |
| Date | 2026-11-10 |
| Source | `abhishek3059`, operator report in chat |
| Scope | Existing local fake-adapter console |
| Result | Partial observations, not an acceptance PASS |
| Tested commit / browser / hardware | Not supplied |

## Operator observations

- The console shows `speaking` even when the operator is silent.
- The operator cannot confirm that microphone input and listening work as
  expected.
- Mute and the other buttons appear to work, according to the operator.
- Automatic conversational interruption has not been confirmed. The operator
  wants speech-driven interruption, not reliance on an Interrupt button.
- The operator requested stopping this test and focusing on the real scaffold.

No recording, transcript, token, or browser network log was collected. The
agent did not independently observe the session. Audio egress, cleanup, and
barge-in are not independently verified by this report.

## Code-based explanation

The browser sends every unmuted PCM frame, without a silence gate, in
[voice-session.service.ts](../../apps/web/src/app/voice-session.service.ts),
lines 112 to 125. [FakeVoiceAdapter](../../apps/api/src/super_agent_voice/adapter.py),
lines 28 to 31, returns every frame unchanged. The browser sets `speaking`
whenever it starts playing a frame, in the service, lines 131 to 152. Silent
frames therefore also drive the speaking state.

That is a supported explanation for the misleading display. It does not prove
whether this operator's microphone captured usable audio. The existing RMS
threshold interruption mechanism is not evidence of working conversational
barge-in on this machine.

## Current disposition

Do not mark R-01.4 complete. Do not repeatedly ask the operator to test the same
uncertain echo behavior. The misleading state is a known issue that must be
fixed and evidenced, not silently waived. R-01.3 remains pending as well.

## Proposed execution change, not approved

The operator requested prioritizing the real scaffold. A possible roadmap
revision would:

1. Allow credential design and reviewed local-only implementation to proceed
   while Mac and microphone acceptance evidence remain pending.
2. Replace the request/response echo seam with the designed streaming seam and
   scripted offline events, with tests for silence, playback, interruption,
   stale output, mute, and stop.
3. Keep the input level indication distinct from model speech playback. Do not
   label every received PCM frame as detected speech.
4. Make conversational interruption the required acceptance path. Keep any
   explicit interrupt control secondary; a button test cannot satisfy barge-in.
5. Run Mac and local microphone acceptance against the revised scaffold before
   closing PH-01. Keep independent credential and boundary reviews mandatory
   and complete them before live provider execution.
6. Keep provider execution synthetic-only. Personal microphone audio to Gemini
   still requires a separate approval and reviewed data boundary.

This changes the current ordered prerequisites. Under
[AGENTS.md](../../AGENTS.md) section 11 and
[roadmap.md](../../roadmap.md), the roadmap revision needs both maintainers'
approval in a roadmap PR, with corresponding phase definitions if a gate
moves. This proposal changes no roadmap item, status, approval, or runtime
authority. No real-scaffold implementation has started under this proposal.
