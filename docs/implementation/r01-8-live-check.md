# R-01.8 and R-01.9: opt-in synthetic live check

| Field | Value |
| --- | --- |
| Roadmap items | R-01.8 (command built) and R-01.9 (synthetic live test run and recorded; unsupported transport fails closed) |
| Date | 2026-11-12 |
| Operator | `jeevesh2515` |
| Built and run by | Claude Code (`claude-sonnet-5-5`) on the operator's Mac |
| Output | [r01-9-live-check-output-20261112T000230Z.txt](evidence/r01-9-live-check-output-20261112T000230Z.txt) |
| Gate effect | None. RT-G01 stays open (R-01.10 remains). |

## The command

```bash
GEMINI_API_KEY=... python -m super_agent_voice.live_check --send-synthetic-audio
```

- `apps/api/src/super_agent_voice/live_check.py`. Not collected by pytest and
  never run by CI. The flag is required and acknowledges that audio goes to
  Google.
- The key comes from `GEMINI_API_KEY` in the process environment only. For
  this run the shell read it from `~/.super-agent/gemini-key` (mode 0600) into
  that variable for one process. It is never printed; the saved output
  contains no `AIza` string.
- Input is synthetic speech: macOS `say` renders "Hello. In one short
  sentence, what is two plus two?" as 3.6 seconds of 16 kHz PCM in a temporary
  folder that is deleted immediately. On other systems, `--wav` takes a file of
  synthetic speech. No microphone and no personal data are involved.
- Output is one JSON line per step with timings, event names, byte counts, and
  fixed error categories. It never contains audio, a transcript, a key, or a
  provider message.
- Offline tests (4) use the fake adapter and an injected failing connection;
  none touch the network.
- Dependency: `google-genai` 2.33.0, released 2026-10-23 (over 14 days old),
  Apache-2.0, with 15 pinned transitive packages, all released on or before
  2026-10-27 and each with a Python 3.14 wheel. Licenses of note: `certifi`
  MPL-2.0; `cryptography` Apache-2.0 or BSD-3-Clause. `pip-audit` on the updated
  lock: no known vulnerabilities.

## Results (free tier, home network, model `gemini-3.8-live`)

| Step | Observed |
| --- | --- |
| conversation | Connected in 734 ms. 3.6 s of speech sent at real-time pace. First audio 5086 ms after start, 613 ms after the last audio frame was queued. About 1.7 s of spoken reply (81,600 bytes of 24 kHz PCM16), then `TurnComplete`. |
| interrupt | `interrupt()` called at first audio. The provider answered with `TurnComplete` (not `Interrupted`) 1.6 s later, inside the 5 s window, so the session stayed healthy. |
| unsupported-model | Model `not-a-real-model`: `AdapterError` category `provider-unsupported` after 342 ms, no audio, `fails_closed: true`. |

An earlier run of the same command, before the close-code mapping below, gave
the same timings within noise and `session-failed` for the unsupported model.

What this shows:

- The model ID `gemini-3.8-live` is accepted for this key and the adapter
  works end to end against the real SDK: connect, audio in, audio out, turn
  completion, stream end, close.
- An unknown model fails closed with a fixed category and no audio.
- SDK facts checked on the installed package, not from memory: `go_away` is a
  field of the message, not of `server_content`; `send_realtime_input` takes
  `audio` and `audio_stream_end`; `receive()` ends after each complete
  interaction. The adapter already handled all three.

What this does **not** show:

- That `interrupt()` stops a long reply. The reply was short and ended on its
  own before any interruption could matter. The known limit (muting or pressing
  Interrupt mid-answer may end the session after 5 s) stays unmeasured.
- Anything about a rejected key. A deliberately malformed key (39 `x`
  characters) failed with close code 1007, which is not mapped and gives
  `session-failed`. The design has no row for a rejected key.
- Behaviour at the provider's session limit, GoAway, or long sessions; tool
  calling; real microphone audio; Windows.
- Anything beyond three sessions on one day. The timings are a single sample,
  not a distribution.

## Changes made because of the run

- Close code 1008, the SDK `APIError` code for an unknown model, now maps to
  `provider-unsupported` (observed, with a test).
- The unused `server_content.go_away` check was removed.
