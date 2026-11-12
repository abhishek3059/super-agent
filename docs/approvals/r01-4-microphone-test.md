# R-01.4 local microphone test

| Field | Value |
| --- | --- |
| Roadmap item | R-01.4 [human], local microphone test (start, mute, conversational barge-in, stop) on the revised scaffold; no audio leaves the machine |
| Date | 2026-11-12 |
| Tester | `jeevesh2515`, on the Mac, following the [R-01.4 handover](../implementation/r01-4-microphone-handover.md) |
| Tested commit | `a790530` on `feat/ph-01-gemini-live` |
| Adapter under test | The offline fake adapter (echo). Gemini was not involved. |
| macOS | 27.2 |
| Browser, version, microphone device | Google Chrome (version not stated), with headphones as the audio device (model not stated) |
| Provider key | The count of `GEMINI` variables in the backend shell was `0`, checked by the agent before the backend started. The backend log shows only local connections. |
| Result | **PASS for the R-01.4 scope** (start, mute, conversational barge-in, stop). One observation on the manual Stop playback button, below. |

## What the tester reported

`jeevesh2515` ran all nine handover steps twice and reported, in chat, that
every feature worked as expected except one: pressing **Stop playback**
(step 6) gave no visible or audible response.

In the tester's words, summarized: the test ran in Chrome with headphones
on. Their own voice came back live in the headphones, loud and clear. Other
voices in the room were also picked up and played back. While the tester was
quiet, the session only listened and the level meter looked fine. The tester
judged listening and detection to be perfect.

No per-step notes, error text, or timings were supplied, so none are
recorded here. The terminal 1 log for
the session shows three accepted local WebSocket connections and no
traceback.

## Observation on step 6 (Stop playback)

- Not reproduced and not root-caused. The agent read the code path
  (`interrupt()` in `voice-session.service.ts`, `playback.interrupt` handling
  in `app.py`, `FakeVoiceAdapter.interrupt`) and found no defect.
- A likely explanation, unverified: the fake adapter echoes each microphone
  frame at once, so the button cuts audio that is only ~130 ms deep, and new
  echo plays again as soon as the next frame arrives. If nothing is playing,
  the button changes no visible state.
- Per the [PH-01 sequencing record](ph-01-sequencing.md), the button is a
  secondary control and conversational barge-in is the acceptance path, so
  this does not block R-01.4. It is a missing-feedback gap, carried forward
  as an open item in the handoff and not hidden.

## Owner statement

On 2026-11-12 `jeevesh2515` told Claude Code, in chat, that the test was run
twice, that everything worked as needed apart from step 6, and asked for the
result to be recorded as working. This record is written from that statement.
It ticks R-01.4 only and closes no other item or gate.
