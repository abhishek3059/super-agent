# Gemini Live console: operator test, 2026-11-14

| Field | Value |
| --- | --- |
| Tester | `jeevesh2515`, on the Mac, Chrome, real microphone |
| Code | PR #41 branch `feat/gemini-live-console` at `7bc0272` |
| Data boundary | The [Gemini testing exception](../approvals/gemini-live-testing-exception.md) |
| Result | Conversation quality good. Three defects found, listed below. |

## What the tester reported

In the tester's words, summarized: the conversation was really nice and
Gemini answered perfectly, much better than the local 4B model. It could only
do calculations and tell the time. It said it cannot give real-time weather
and that it has no access to past conversations. The tester could not see the
mute, stop playback, and end session buttons during the session, and the
session dropped in the middle of the talk with "Voice session failed:
invalid-audio".

The backend status lines (state only) show three sessions, connect times of
436 to 519 ms, turns with 37 to 593 KB of reply audio, first audio between
1.7 and 23 seconds after the previous turn boundary, one `calculate` call,
several interruptions, and closes.

## Defects and causes

1. **Disconnect (`invalid-audio`).** The backend refuses any provider audio
   frame over 32 KiB or of odd length and ends the session. Gemini sometimes
   sends a larger frame during a long reply.
2. **Controls off screen.** The transcript panel grows and pushes the control
   dock below the window.
3. **Wrong label.** The status said "Microphone streaming locally" while audio
   went to Gemini.

A Gemini Live connection also has a limited lifetime and announces its end
with `go_away`; the adapter treated that as the end of the session.

Fixes are tracked in the PR that carries this record. Tools beyond the
calculator and clock, and continuity across sessions, were not available in
this test; see the widening in the exception record.

## Not done

- Stop playback was not reported on.
- No timing targets are claimed; the first-audio range above includes the
  user's own speaking time.
