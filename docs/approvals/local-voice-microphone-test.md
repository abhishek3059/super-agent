# Local voice adapter: operator microphone test

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Tester | `jeevesh2515`, on the Mac (MacBook Air M5, 16 GB, macOS 27.2) |
| Tested commit | `55dcf2e` on `feat/local-voice-adapter` (PR [#36](https://github.com/abhishek3059/super-agent/pull/36)) |
| Setup | Google Chrome (version not stated), earphones, backend started with `SUPER_AGENT_ADAPTER=local` |
| Pipeline | whisper.cpp `base.en`, `qwen3.5:9b` through Ollama on `127.0.0.1`, macOS `say`. No cloud provider. |
| Result | **Works**, by the tester's statement. Not accepted as good enough: the tester rates it 66 out of 100 and sets 90 as the bar. |
| Roadmap effect | None. Nothing is ticked and no gate moves. |

## What the tester reported

In chat with Claude Code on 2026-11-12, `jeevesh2515` said the local assistant
connected in Chrome, captured his voice well through earphones, responded
well, and held a good conversation. He also said he is not satisfied with it
yet: he scores it 66% and wants at least 90% before calling it a
JARVIS-like system.

No step-by-step observations, timings, error text, or reasons for the score
were supplied, so none are recorded. Barge-in, mute, and stop were not
reported on separately. This is not the denied-egress test that the PH-07
gate asks for.

## Known gaps at the time of the test

These come from the measurements in [spike A4](../../spikes/a4-local-voice/README.md)
and the code, not from the tester:

- About two to three seconds from the end of speech to the first reply audio.
- The built-in macOS voice, not a natural one.
- Conversation only: no tools, no actions, no memory across sessions.
- Energy-based end-of-speech detection, with no wake word.
