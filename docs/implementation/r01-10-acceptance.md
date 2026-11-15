# R-01.10: PH-01 acceptance record

| Field | Value |
| --- | --- |
| Date | 2026-11-12; criteria table, offline re-run, and revised live run added 2026-11-15 |
| Integration baseline | `3025155` on `develop` (merge of [PR #34](https://github.com/abhishek3059/super-agent/pull/34)); offline suites re-run at `0638660` on 2026-11-15 |
| Status | In progress. R-01.10 cannot be ticked: RT-002 and RT-003 are not accepted and [RT-G01](../../prd.md#rt-g01) remains open. Blockers are listed under [Blockers](#blockers). |
| Approved boundary | [PH-00 setup decisions](../approvals/ph-00-setup-decisions.md): synthetic speech only to Gemini, personal microphone audio stays local |

## Criteria and evidence

Each row was checked against the linked record, not its title. "Met" means
the criterion's text is supported by that evidence for the code it covers;
the last column says what the evidence does not cover.

| Criterion | Evidence | Verdict and limit |
| --- | --- | --- |
| RT-002: minimal scaffold, exact dependency and command contract | [PR #13](https://github.com/abhishek3059/super-agent/pull/13), locked `apps/api/requirements.lock` and `apps/web/package-lock.json`, [run instructions](../../apps/voice-foundation.md), [Windows launcher](r01-f4-windows-launcher.md), [offline re-run](evidence/r01-10-offline-suites-20261115.txt) | Met for the scaffold. |
| RT-002: unauthenticated clients, hostile or null origins, wrong Host cannot create a session; fail closed | Backend cases `test_rejects_bad_origin_and_token`, `test_wrong_origin_is_refused_before_auth`, `test_wrong_host_is_refused_before_auth`, `test_adapter_never_created_without_valid_auth` in `apps/api/tests/test_voice_api.py`; [security review](../reviews/r01-6-security-review.md) | Met offline. The independent review read commit `5de7293` and its closure check read `d5808c6`, with the fake adapter. |
| RT-002: credential design reviewed; entropy, token file, expiry, throttling implemented | [credential design review](../reviews/r01-5-credential-design.md), token and throttle cases in `test_voice_api.py` | Met, except the Windows owner-only ACL (N2) and the token directory mode, which stay open as recorded in the [F2 acceptance](../approvals/r01-6-f2-risk-acceptance.md). |
| RT-002: independent review covers the boundary as it now exists on `develop` | None. The `docs/reviews` folder has no review of the local adapter, the T1 and memory tools, the rebuilt console, or Gemini mode in the console. | **Missing.** |
| RT-003: single manual native adapter and thin UI with indicators, backend control, mic and playback stops | Gemini adapter ([R-01.7](r01-7-gemini-adapter.md)); console with fake adapter tested by a person ([R-01.4](../approvals/r01-4-microphone-test.md), predates #34); generated-audio browser run (summary below, raw output not saved) | Partly met. The operator reported in the [PR #41](https://github.com/abhishek3059/super-agent/pull/41) description that a live Gemini session through the console worked. The output was not saved, so it is not evidence. |
| RT-003: native behavior measured: stops, interruption, consent and failure | [Saved synthetic run](evidence/r01-9-live-check-output-20261112T000230Z.txt): reply, unsupported model refused. [Revised synthetic run, 2026-11-15](evidence/r01-10-live-check-output-20261115T172901Z.txt): reply, provider `Interrupted` on barge-in, `calculate` and `current_time` tool calls, unsupported model refused. Offline bridge tests for PCM framing and interruption order. | Partly met in the standalone tests. Each run had one sample. The explicit interrupt ended with `TurnComplete`. Measured playback stop, visible state and consent through the application remain **missing**. |
| RT-003: no silent provider fallback; native model access not assumed | `test_gemini_selection_needs_the_key_and_never_echoes_it` in `test_gemini_console.py`, `SUPER_AGENT_ADAPTER` selection in `app.py` (unknown value or missing key refuses to start), `unsupported-model` step of the saved run, F7 and F8 below | Met offline and by one standalone live step. |
| RT-G01: reviewed scaffold and commands | R-01.6 review, [Windows launcher record](r01-f4-windows-launcher.md) | Partly met. Same limit as the independent-review row. |
| RT-G01: deployed authentication, Host, Origin, CORS, WebSocket, CSRF controls | R-01.6 review and [F2 acceptance](../approvals/r01-6-f2-risk-acceptance.md) | Met for the reviewed boundary. Review finding F5 (token goes to whatever process holds the port) is open, and the review said to raise it before Gemini is wired into a session. Gemini mode now is. The F2 acceptance has the same trigger. |
| RT-G01: backend-only secrets | Key read from the process environment only; no key in logs or messages (`test_tokens_never_appear_in_logs_output_or_client_messages`, the selection test above); R-01.6 review | Met offline. |
| RT-G01: measured native media and backend event and control connection, manual activation, stop controls, visible states | None through the application. | **Missing.** |
| RT-G01: fail-closed unsupported transport | `unsupported-model` result in the saved run (`fails_closed: true`); R-01.F7 and R-01.F8 checks below | Met. |

## Blockers

R-01.10 stays unticked until these are cleared. Native media evidence needs a
live run. Boundary implementation and offline verification can proceed first.

The [subscription-backed runtime proposal](../design/subscription-backed-runtime.md)
describes an OpenAI candidate and a later Claude worker. It needs a provider
decision and its own runtime evidence. The existing Gemini-specific evidence
and blockers below record the current approved path.

1. **Revised synthetic live run. Cleared 2026-11-15.** `abhishek3059` ran the
   [live command](../../apps/voice-foundation.md#synthetic-live-check-opt-in)
   on Windows at `0638660` and the
   [saved output](evidence/r01-10-live-check-output-20261115T172901Z.txt) is
   complete and holds no key. Summary line: `reached_gemini`, `tools_ok`, and
   `fails_closed` all true. The barge-in step got a provider `Interrupted`
   event after enqueueing began for the second clip. It is one sample on
   one host. An earlier
   attempt the same evening failed every step with `session-failed`; the key
   prompt had probably received pasted text instead of the key. That output
   was not kept.
2. **Native run through the console, recorded.** Activation, playback, visible
   state, stop and interruption, fail-closed failure with no fallback, and a
   check that client audio cannot bypass the adapter. A maintainer must first
   say which path counts for RT-G01: a real-microphone run under the
   [Gemini testing exception](../approvals/gemini-live-testing-exception.md)
   (that record says no gate moves), or the synthetic-only console in the
   [proposal](../design/synthetic-voice-console.md), which was never reviewed
   or built. Owner: one maintainer, per [DEC-21](../../descisions.md#dec-21).
3. **Independent review of the code now on `develop`**, including Gemini mode,
   plus a decision on finding F5 and the F2 condition. Both were tied to
   wiring Gemini into a session. Owner: one maintainer decides; an
   independent reviewer agent can do the review.
4. **Records.** After 2 and 3, update the RT-002 and RT-003 records and tick
   R-01.10 with links to the saved output and review.

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
  verify that SDK exit errors are reported without a traceback. The later
  [standalone run](evidence/r01-10-live-check-output-20261115T172901Z.txt)
  reported a provider interruption after enqueueing the second clip.

The follow-up reliability slice frames larger Gemini PCM messages within the
configured WebSocket limit, lets the writer run between chunks, and invalidates
queued audio when Gemini reports an interruption. A partial sample is discarded
at an interrupt or turn boundary. It keeps Stop, Mute and End visible while the transcript scrolls and
labels Gemini microphone upload in the listening state. The Windows launcher
scopes the provider key to the backend, and the synthetic command removes voice
credentials from both speech generator environments. Gemini session resumption
and the native gate run remain open.

Offline re-run on 2026-11-15 at `0638660` (macOS, Python 3.14.4, Node 22.22.3,
no key set): 492 backend tests passed and 2 skipped (no `onnxruntime`; a
non-macOS-only check); frontend self-tests passed (57 voice, 47 UI, 8 epoch);
the build passed; `npm audit` reported 0 vulnerabilities. Saved output:
[r01-10-offline-suites-20261115.txt](evidence/r01-10-offline-suites-20261115.txt).
No provider call was made.

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

See [Blockers](#blockers). Two statements in the first version of this
record are out of date. The browser console can now construct the Gemini
adapter (`SUPER_AGENT_ADAPTER=gemini`, merged in
[PR #41](https://github.com/abhishek3059/super-agent/pull/41) under the
[testing exception](../approvals/gemini-live-testing-exception.md)), and the
synthetic-only console proposal was not the route taken. Leave PH-02
untouched until the PH-01 exit is accepted.
