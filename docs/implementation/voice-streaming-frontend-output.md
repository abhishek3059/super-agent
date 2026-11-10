# Voice streaming slice: frontend implementation output

| Field | Value |
| --- | --- |
| Date | 2026-11-10 |
| Scope | Frontend half of the signed PH01 local streaming slice ([contract](../design/voice-streaming-slice.md) revision 2). |
| Producer | GLM-5.3-Flash Free, free-profile developer agent, spawned as the frontend subagent under PR #24 work bundle on `docs/ph-00-close`. |
| Status | Frontend scope complete; nothing ticked, no acceptance claim. Backend files and backend tests are owned by a separate agent. |

This record is the frontend output only. The parent session owns governance,
progress, and task documents and the combined implementation record.

## What changed

Files in this subagent's ownership, all left uncommitted (no staging, push, or commit):

- `apps/web/src/app/voice-session.service.ts` (rewritten draft with the contract corrections below)
- `apps/web/src/app/app.component.ts` (CT-11: Start enabled from `stopped` or `error`)
- `apps/web/scripts/selftest-voice-session.mjs` (new; initially 24 service-level
  cases at the first build, then 37 after the review-correcting round, and 39
  after the two final state-nit regressions)
- `apps/web/package.json` (added the `test:voice` script; no dependency change)
- `.github/workflows/voice-foundation.yml` (new offline `test:epoch` + `test:voice` step; `NG_CLI_ANALYTICS: 'false'` added to the self-test, audit, and build steps)
- `apps/voice-foundation.md` (checks list and honest local UX notes)

A second, narrow review-correction pass then amended
`voice-session.service.ts`, `app.component.ts`,
`scripts/selftest-voice-session.mjs`, and this record only (findings F-01 to F-05
and the two nits below).

`apps/web/src/app/playback-epoch.ts` and `apps/web/src/app/audio-signal.ts` are
owned but needed no change; the old epoch tracker keeps its 8-case self-test
and passed them unchanged. `apps/web/src/styles.css` owned, unchanged
(the level meter labeling was already in the component template).

## Contract corrections implemented

- **CT-11 restart after error**: the template disables Start only for states
  other than `stopped`/`error`; the service guard is the pre-existing
  live-socket check, so `start()` succeeds from the `error` state, tested.
- **Per-session epoch reset**: `start()` allocates a new `PlaybackEpochTracker`
  for each socket, so an interrupt in a previous session followed by stop and
  a restart accepting fresh epoch 0 no longer drops all new audio. Tested.
- **Session identity/lifecycle guards**: a monotonic `generation` plus the
  session's own `socket` identity guard every async continuation. A late
  `getUserMedia` grant stops the returned old tracks and attaches nothing to
  a stopped or newer session; a late rejection fails only the session that
  requested it. Cleanup detaches the processor, stream, level, pending rate,
  interrupt and capture-declared state, socket callbacks, and socket
  synchronously; the awaited `context.close()` runs last. (The epoch
  tracker is not detached in cleanup; a fresh one is allocated in `start()`
  for each new session.) Cleanup applies the requested final state
  deterministically before the awaited close, and its post-await tail never
  mutates state, so a deferred old close can never close a newer session's
  socket or restage its signals.
- **Stale callback suppression**: old sockets have `onopen`, `onmessage`,
  `onerror`, and `onclose` nulled in cleanup before close; the handlers also
  re-check identity, so old socket events can never set state on a stopped or
  replaced session.
- **Duplicate ready fails closed**: a second `session.ready` in one session
  sets `Voice session failed` behavior off with the fixed message
  `Duplicate session.ready received.` and cleans up; only one microphone
  stream can be allocated per session. Tested.
- **Automatic barge-in**: retained (RMS > 0.02 while audible playback) and
  skipped while an interrupt is already pending; rapid manual interrupts keep
  the pending guard until both epochs are acknowledged. Tested.
- **Redaction allowlist**: `session.error` categories pass through a fixed
  allowlist (`max-duration`, `session-timeout`, `session-failed`,
  `provider-unavailable`, `provider-session-ended`, `invalid-audio`,
  `invalid-control`); anything else renders as `Voice session failed: unknown`.
  Tested with a sentinel category.
- **Malformed payload handling (retained hardening)**: invalid chunk metadata,
  odd/oversized tagged binary, and malformed JSON fail the session with the
  fixed message `Invalid local voice response.` and full cleanup; untagged
  oversized binary is dropped silently because it never owns a tag. Tested.
- **Honest labeling (CT-15, retained)**: the meter keeps its
  "Microphone input level (not speech detection)" label; thresholds 0.002 and
  0.02 stay provisional and unmeasured. No claim about threshold behavior
  against real audio is made anywhere.

## Real test output (this machine, Node v26.1.0, Windows)

```
npm run test:epoch       -> playback-epoch self-test: PASS (8 cases)
npm run test:voice       -> voice-session self-test: PASS (39 cases)
npm audit                -> found 0 vulnerabilities
git diff --check (owned) -> clean (whitespace/config advisories only)
npm run build            -> Application bundle generation complete.
                            [10.403 seconds]
                            Initial total 116.00 kB / transferred 35.03 kB
```

The 39 service cases: connecting/no mic before ready; silent PCM not
speaking; audible current-epoch speaking and returned to listening; 24 kHz
metadata rate; untagged and consumed tag; old epoch after interrupt; mute
(track enable, PCM drop, level and playback cleared) and unmute; automatic
barge-in once plus old epoch drop until ack; rapid manual interrupts; stop
with silent event source; late permission grant after stop and after a new
start; late permission rejection after stop and after a new start; duplicate
ready fails closed; deferred context close versus restart; restart from error
plus redaction; fresh epoch 0 on restart; invalid metadata; odd and
oversized tagged binary; untagged oversized drop; malformed JSON; guarded
starts; a createMediaStreamSource throw and a createScriptProcessor throw
failing closed; a synchronously throwing context close during stop; a
rejecting context close during fail; a hanging context close finalizing
immediately; suspended resume success and rejection; stop and new start
during a deferred resume (resolve and reject); the stale socket handler
regression; a session.error during pending permission; muted stop and
restart starting unmuted; mute during pending permission; a closing socket
without its close event never publishing listening; and audible playback
during a deferred resume keeping speaking after the resume completes.

Fakes are hand-written in the test file; the harness transpiles the real
sources with the pinned `typescript` package (`transpileModule`, CommonJS,
ES2020) and binds real `@angular/core` (genuine signals from the installed
package). There are no sleeps; only controlled promises and microtask flushes.
No test framework, no new dependency, no downloads, no microphone, no provider
call, and no key touched anything.

## Review findings and state-nit regressions fixed

The free frontend reviewer reported findings that the following rounds
resolved with tests; a later re-review confirmed all resolved and flagged two
remaining state nits and prose-honesty fixes, which are addressed below. No
design change, no new dependency:

- **F-01 cleanup final state**: the requested stopped/error state and the mute
  reset are applied synchronously after detach, before the awaited
  `context.close()`. A close that rejects or throws synchronously is caught
  internally (no raw detail, no unhandled void promise). A close that hangs
  is not caught or forced: it is tolerated, because the final state is
  already published before the await, so Stop and fail can no longer lock
  Start or lose the recorded category, and the promise may stay unsettled
  while the browser context remains open with no forced-close claim. Tested
  with sync throw (Stop), rejection (fail), and a hanging close (fail
  finalizes immediately and restart works while the close stays pending).
- **F-02 factory-failure leak**: `attachCapture` tracks the context immediately
  after construction and the processor immediately after its factory, so a
  `createMediaStreamSource` or `createScriptProcessor` throw closes the
  tracked context, stops the returned tracks, closes the socket, and reports
  the fixed recoverable message `Local audio capture failed.` (both throws
  tested; restart recoverable).
- **F-03 stale-handler regression**: the suite now captures the old session's
  `onopen`/`onmessage`/`onerror`/`onclose` references and invokes them after
  stop and a new live session, proving the identity guards (no extra auth, no
  duplicate mic request, no new-session side effects, status, level, and mute
  untouched) and the nulled bindings; plus a `session.error` during pending
  permission followed by the late grant (track stopped, new session intact).
- **F-04 mute inheritance**: a valid `start()` resets `muted` to false to match
  the backend default (invalid/busy starts leave the live session untouched);
  tested with muted stop plus slow old close and a new session: unmuted,
  track enabled, input frames reach the new socket, and the old close
  completion cannot stomp it.
- **F-05 suspended context**: an initially suspended `AudioContext` resumes (and
  only when state is `suspended`) before listening is published and before
  any microphone PCM or meter update ships (`captureReady` gates the
  processor callback). A resume failure reports the same fixed local capture
  error and cleans up; stop plus new start during a deferred resume works for
  both resolve and rejection without poisoning (tested all three).
- **Third pass, two remaining state nits with regressions**: the ready branch
  now also requires the session socket to still be OPEN, so a socket that is
  closing without having raised its close event can never publish a listening
  session even when a late permission grant resolves first (test: returned
  track stopped, status never listening, the eventual close finalizes
  stopped); and the published state after capture completion keeps an already
  speaking session speaking instead of downgrading it to listening
  (test: audible current-epoch playback during a deferred resume keeps
  speaking after the resume, meter works afterwards, playback ends to
  listening normally).
- **Nits**: this record no longer claims cleanup detaches epochs (the reset
  lives in `start()`); Mute and the manual "Stop playback" button are
  disabled for `stopped`, `connecting`, and `error` statuses in the UI while
  the service API still accepts a mute once authenticated (tested with the
  late track honoring a pending mute); the provisional RMS labeling is
  unchanged.

## Not done, not claimed

- Backend CT-01 to CT-10 files, backend tests, and the full backend suite: other agent and parent; not run here.
- `npm run check` (repo-wide): parent runs it last while backend is still editing.
- Mac and Windows operator microphone checks (R-01.3, R-01.4): open human gates, none passed.
- Credential design and independent security review (R-01.5, R-01.6): open; this slice is not a security PASS.
- No roadmap tick, no phase move, no tag or claim of full PH01 completion.
- I did not touch `apps/web/angular.json`; its 3-line working-tree diff predates this subagent (local user CLI analytics setting) and was left exactly as found.
