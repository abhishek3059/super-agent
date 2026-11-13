# R-01.10: PH-01 acceptance record

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Integration baseline | `3025155` on `develop`, merge of [PR #34](https://github.com/abhishek3059/super-agent/pull/34) |
| Status | In progress. RT-002 and RT-003 are not accepted. [RT-G01](../../prd.md#rt-g01) remains open. |
| Approved boundary | [PH-00 setup decisions](../approvals/ph-00-setup-decisions.md): synthetic speech only to Gemini, personal microphone audio stays local |

## What the evidence covers

| Check | Evidence and limit |
| --- | --- |
| Local loopback boundary | [Independent review and disposition](../reviews/r01-6-security-review.md) and the [Windows launcher record](r01-f4-windows-launcher.md). Review of the deployed fake console does not approve native provider wiring. |
| Human microphone controls | [Jeevesh's test record](../approvals/r01-4-microphone-test.md) covers the revised fake scaffold at `a790530`. Manual Stop playback feedback was inconclusive. PR #34's rebuilt console was not the one used for this test. |
| Rebuilt console | Chromium smoke check at `3025155` covered the connection dialog. The later [browser verification](#browser-verification) exercised authenticated local echo, playback stop, mute, and session end with generated input. |
| Live provider | [Saved synthetic run](r01-8-live-check.md) measured a reply and an unsupported-model refusal through the standalone adapter. The reply ended naturally. It did not demonstrate barge-in or browser-to-provider controls. |
| Native bridge, offline | The authenticated in-process WebSocket tests use the real application and adapter with a scripted SDK. They verify PCM framing and interruption ordering without reaching a provider. |

## Offline fixes

- **R-01.F5.** The WebSocket regression at the baseline received
  `audio.chunk` at epoch 1 where it expected `turn.complete`: audio from
  the old turn arrived after the browser's local stop acknowledgement. The
  adapter now invalidates queued PCM on a local stop and drops audio until
  the provider reports an interruption or completes that turn. The regression
  passes with the fix and verifies that the next turn arrives at the new epoch.
- **R-01.F6.** A scripted SDK exit failure reproduced
  `Failed: DID NOT RAISE AdapterError`. The adapter now surfaces the fixed
  `session-failed` category on close and retry. The bridge can keep the slot
  unavailable when closure is unconfirmed. The offline regression passes.
  This check covers closure after startup. The console backend and live
  command await startup before closing.
- The revised live command adds a second generated clip during a longer
  reply. It reports `provider_interrupted_after_enqueue` only when
  `Interrupted` follows local enqueue with no error. This reports order,
  not proof that the queued frame reached Google or caused the interruption.
  Offline tests distinguish that observation from `TurnComplete` and
  verify that SDK exit errors are reported without a traceback. The revised
  live command has **not been run** against Gemini.

Local verification on 2026-11-12: 199 backend tests passed on Python 3.14.5.
The frontend self-tests passed (8 playback, 24 UI, 39 voice); the build
passed and its dependency audit reported zero vulnerabilities. The repository
check reported zero errors. The two new fixed phrases generated 4.57 s and
2.90 s of PCM locally, without a provider call.

## Browser verification

R-01.F7 adds a check for `provider: "fake"` before the local console
requests capture. The regression received `listening` instead of
`error` before the fix. After the fix, a missing provider and a reported
`gemini-live` provider both cause a fixed error, close the socket, and
send zero PCM. The provider field is a protocol check. The proposed
native probe needs its own endpoint authentication.

An isolated headless Chrome session used the Angular console and actual
Uvicorn WebSocket. The test supplied a generated Web Audio MediaStream
at the browser capture boundary. It checked that the console requested
the stream once, entered Local echo, called playback stop and sent an
interrupt control, sent no PCM while muted, and released the track at
session end. A local adapter reporting `gemini-live` exercised the
negative path. These checks covered generated local audio. Physical input
and a real provider were outside the run.

The two browser lines below are a hand summary of a local headless Chrome
run. Its raw output and harness were not saved to the repository; the
self-test line is reproducible with `npm run test:voice` in `apps/web`.

```text
Chrome/157.0.8103.52 local fake: generated audio echo, playback stop, mute, unmute, stop and track release PASS
Simulated provider mismatch: fixed error and no additional capture request PASS
voice-session self-test: PASS (41 cases)
```

## Provider destination

R-01.F8 makes the SDK's Gemini Developer API mode and base URL explicit.
The regression intercepted the installed SDK at the WebSocket dial and
checked the scheme, host, and Developer API path under alternate SDK
configuration. The baseline failed both cases. The revised adapter kept the
approved destination in both. The check used a test value and opened no
network connection. See the [Gemini Live WebSocket API reference](https://ai.google.dev/api/live).

The full offline backend suite passed 201 tests. The frontend passed 73
self-tests and its production build. The repository check reported zero
errors.

## Known limit

If Stop playback is pressed before any provider audio arrives, no
acknowledgement timer is armed, so a reply to audio already sent can still
play at the new epoch. This is local-only by design in
`gemini_adapter.py` and predates these fixes; PH-03 stop semantics (R-03.1,
R-03.2) must settle it.

## Remaining gate work

1. The operator runs the revised [synthetic live command](../../apps/voice-foundation.md#synthetic-live-check-opt-in)
   from the shell holding the approved key. Save only redacted timing, state,
   and outcomes. Treat a naturally completed turn as inconclusive for barge-in.
2. Review the [synthetic-only console proposal](../design/synthetic-voice-console.md)
   before enabling provider wiring. It covers session authentication,
   fixed server-generated input, and playback without microphone capture.
3. On the reviewed path, record authenticated activation, actual native
   playback and visible state, stop and interruption behavior, and
   fail-closed failure with no fallback. Include a negative check that
   client-supplied audio cannot reach the provider.
4. Complete [RT-002](../../tasks/002-local-scaffold-and-boundary.md) and
   [RT-003](../../tasks/003-native-voice-session.md) against that evidence.
   Leave PH-02 untouched until the PH-01 exit is accepted.
