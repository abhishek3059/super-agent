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
| Rebuilt console | Local Chromium smoke check at `3025155`: disconnected state, local-only disclosure, masked token field, locked loopback endpoint, empty-token rejection, and Escape restoring focus. No microphone or authenticated browser session was used. |
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

## Remaining gate work

1. The operator runs the revised [synthetic live command](../../apps/voice-foundation.md#synthetic-live-check-opt-in)
   from the shell holding the approved key. Save only redacted timing, state,
   and outcomes. Treat a naturally completed turn as inconclusive for barge-in.
2. Review a synthetic-only console design before enabling provider wiring.
   Address the open session-auth concern in the
   [boundary review](../reviews/r01-6-security-review.md). An opt-in test
   mode should require explicit activation, generate fixed speech on the
   server, reject browser PCM, and leave browser microphone capture off.
   Default local microphone use stays on the fake path. This is a proposal.
3. On the reviewed path, record authenticated activation, actual native
   playback and visible state, stop and interruption behavior, and
   fail-closed failure with no fallback. Include a negative check that
   client-supplied audio cannot reach the provider.
4. Complete [RT-002](../../tasks/002-local-scaffold-and-boundary.md) and
   [RT-003](../../tasks/003-native-voice-session.md) against that evidence.
   Leave PH-02 untouched until the PH-01 exit is accepted.
