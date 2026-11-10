# R-01.7 streaming seam and Gemini Live adapter

| Field | Value |
| --- | --- |
| Roadmap item | R-01.7, Gemini Live adapter behind the replaceable seam, covered by offline tests with the fake |
| Date | 2026-11-10 |
| Implemented by | Claude Code (`claude-opus-5-5`) for `jeevesh2515` |
| Reviewed by | Claude Code code-reviewer subagent (Sonnet), see "Review" below |
| Design | [Voice foundation design](../design/voice-foundation.md), sections 4, 5, 6, and section 7 conditions CR-06 and CR-08 |
| Status | Implemented and offline-tested. Not wired into the running app; no provider call, key, microphone, or spend. R-01.7 is not ticked here; the PH-01 owner ticks it after merge. |

## What changed

| Area | Change |
| --- | --- |
| `apps/api/src/super_agent_voice/adapter.py` | Streaming seam: `AudioChunk`, `TurnComplete`, `Interrupted`, `AdapterError` with fixed categories, `VoiceAdapter` protocol, bounded drop-oldest `AudioInputQueue`. The fake adapter echoes by default and can be scripted with events, errors, a start error, or a start delay. |
| `apps/api/src/super_agent_voice/gemini_adapter.py` (new) | Gemini Live adapter. The `google-genai` SDK is imported only when a real session starts; tests inject `connect` and `blob`. One send loop (audio and stream end), one receive loop (re-enters `receive()` per turn), `go_away` and provider end fail closed, every provider error reduced to a fixed category by `classify()`. |
| `apps/api/src/super_agent_voice/app.py` | Authenticates before taking the session slot (CR-06); compares tokens as bytes (CR-08); bounded provider start; receiver, forwarder, and watchdog tasks with one sender owning every socket write; epoch announced before awaiting the adapter; provider closed before the slot is freed; bounded teardown; child tasks always cancelled. |
| `apps/api/src/super_agent_voice/config.py` | `provider_start_timeout_seconds` (10) and `teardown_timeout_seconds` (2). |
| `apps/web/src/app/voice-session.service.ts` | Plays audio at the `rateHz` announced by `audio.chunk` (Gemini sends 24 kHz); drops audio with a missing or implausible rate. |
| Tests | `test_voice_api.py` updated to protocol revision 2 and extended; `test_gemini_adapter.py` new. 29 tests. |

Protocol revision 2 fields now sent: `session.ready` carries `outputRateHz` and
`provider`; `audio.chunk` carries `rateHz`, `channels`, and `format`;
`playback.interrupted` carries `source` (`local` or `provider`); odd-length
audio fails with `invalid-audio`.

## Deviations from the design, stated

- The protocol adds `name`, `output_rate_hz`, and `end_audio_stream()`. Section 6 requires a stream end on mute, and the section 4 contract had no call for it.
- `interrupt()` does not send `audio_stream_end`, because that does not cancel model output. With a model turn in flight the adapter waits for `interrupted` or a turn completion and otherwise fails closed; with no turn in flight a local interrupt is local only. Real provider barge-in is verified in R-01.9.
- Outbound audio drops the newest chunk when the outbound queue is full (marked `shortcut:` in the code); true drop-oldest needs paired metadata and binary removal.
- `session.metrics` and state-transition logging are not implemented yet. Nothing is logged, so nothing can leak.
- The SDK is not added to `requirements.lock`; it is added, pinned and audited, with the opt-in live command (R-01.8), its first real caller.

## Verification (2026-11-10, Jeevesh's Mac)

| Check | Result |
| --- | --- |
| Backend tests, Python 3.14.5 | 29 passed |
| Backend tests, Python 3.12.13 with `apps/api/requirements.lock` | 29 passed |
| Unretrieved task exceptions in test logs | 0 |
| Frontend build (`ng build`) | succeeded |
| Playback epoch self-test | PASS (8 cases) |
| `npm run check` | 0 errors |

Not run: any real Gemini session, any microphone test, load or stalled-client
tests against a real browser.

## Review

| Pass | Verdict | Correctness | Security | Honesty | Scope | Clarity | Average |
| --- | --- | --- | --- | --- | --- | --- | --- |
| First | REQUEST CHANGES | 6 | 8 | 7 | 8 | 8 | 7.4 |
| Second | APPROVE | 8.5 | 8.5 | 8.5 | 9 | 8.5 | 8.6 |

The first pass found six required issues, all fixed: an interrupt with no
model turn in flight killed the session after 5 seconds; a missing key was
reported as `session-failed`; provider start had no timeout; the final send
drain had no timeout; the playback epoch could be announced out of order; the
session slot was freed before the provider closed. Optional items done: stream
end routed through the single send loop, binary first frame closed with 1008,
design `go_away` row corrected, dead counters removed, empty audio frames
ignored, and the droppable stream-end marker documented as a `shortcut:`.
Deferred and recorded here: `session.metrics`, state-transition logging, and a
test for a start cancelled mid-connect.

## What R-01.7 does not cover

- R-01.F1, the console's speaking-on-silence and self-echo defect (next item).
- R-01.6 conditions not touched here: throttling, pre-auth cap, weak-token rejection, token file helper, mandatory expiry, cookie flow.
- Wiring the Gemini adapter into the app and installing the SDK (R-01.8).
