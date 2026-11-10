# Voice streaming slice: signed implementation contract

| Field | Value |
| --- | --- |
| Date / revision | 2026-11-10 / 4 |
| Document | Technical sign-off for the local implementation slice defined below. |
| Revision 4 amendments | Only the two teardown-aligned amendment blocks were tightened (CT-03 release now requires *confirmed* adapter closure; raising-close gate-release expectation superseded per [voice-streaming-teardown.md](voice-streaming-teardown.md) revision 2). No other term re-signed. |
| Author | Solution Architect subagent (GLM-5.3-Flash Free, zero-cost fallback). |
| Design basis | [voice-foundation.md](voice-foundation.md) revision 2, sections 4 to 6, 9, 10. |
| Revision 2 note | Corrects revision 1's CT-01 and CT-02 findings, which overstated the draft: CT-01 now requires the post-await epoch/mute recheck as defense in depth (a single sender cannot interleave a new acknowledgement inside one JSON/binary pair), and CT-02 no longer requires a sequence number (the existing selective removal already drops the oldest item). CT-04 now preserves the total session budget during auth via an explicit `auth_timeout_seconds` setting. Revision 1 is not preserved elsewhere; wording below is authoritative. |
| Phase context | PH-01 in progress; PR #24 work bundle; branch `docs/ph-00-close`. |
| Roadmap effect | None. This document ticks nothing, moves no gate, and reorders nothing. R-01.3, R-01.4, R-01.5, R-01.6 stay open blockers for acceptance. |
| What this is not | NOT maintainer approval. NOT an independent security PASS (R-01.6 is pending). NOT a Gemini Live / native provider grant. NOT evidence for R-01.7 or R-01.10. No both-maintainer approval is claimed anywhere here. |
| Scope | The uncommitted streaming draft only: FastAPI streaming bridge + streaming fake adapter + Angular console changes. Fake adapter only. No Google SDK, no provider call, no credential-throttling build, no same-origin serving, no provider mode UI, no persistence, no new dependency. |

## 1. Problem

The scaffold's request/response seam (`send_audio -> AudioReply`) cannot carry
asynchronous provider events, and revision 2 of the design
([voice-foundation.md](voice-foundation.md) section 4, lines 133 to 231) replaces it
with a streaming adapter seam plus a concurrent backend bridge. A draft
implementation already exists as uncommitted working-tree changes. This
contract reviews that draft, lists the corrections it must make, and defines
exactly what tests and evidence make the slice done.

Baseline before the draft (recorded by the parent session, not re-run by this
subagent): Python backend 11 passed; playback-epoch self-test 8 cases passed.
The existing tests still target the old API and need migration; see section 5.3.

## 2. Current draft, as inspected (facts, not guesses)

The working tree has uncommitted changes on top of commit `4f51e00`:
`apps/api/src/super_agent_voice/adapter.py`, `apps/api/src/super_agent_voice/app.py`,
`apps/web/src/app/app.component.ts`, `apps/web/src/app/voice-session.service.ts`,
`apps/web/src/styles.css`, and a new untracked
`apps/web/src/app/audio-signal.ts`.

Backend (`adapter.py`, `app.py`):

- Streaming `VoiceAdapter` protocol: `start`, `enqueue_audio`, `interrupt`,
  `events`, `close` ([adapter.py:28-37](../../apps/api/src/super_agent_voice/adapter.py)).
- `FakeVoiceAdapter`: bounded input queue with drop-oldest
  ([adapter.py:62-71](../../apps/api/src/super_agent_voice/adapter.py)),
  generation-stamped frames so queued pre-interrupt audio is discarded
  ([adapter.py:73-87](../../apps/api/src/super_agent_voice/adapter.py)),
  one-consumer guard, idempotent `close` via a `None` sentinel
  ([adapter.py:95-100](../../apps/api/src/super_agent_voice/adapter.py)).
- Backend: strict Host and Origin before accept
  ([app.py:161-166](../../apps/api/src/super_agent_voice/app.py)); single-session gate; first-message
  auth with `hmac.compare_digest` ([app.py:180-198](../../apps/api/src/super_agent_voice/app.py));
  adapter created and started only after successful auth
  ([app.py:200-210](../../apps/api/src/super_agent_voice/app.py)); `session.ready` with
  playback epoch, output rate, and provider name is queued after `start()`
  succeeds ([app.py:214-217](../../apps/api/src/super_agent_voice/app.py)); four tasks
  (receive, forward, single serialized sender, watchdog) launched together and
  ended on first completion ([app.py:218-226](../../apps/api/src/super_agent_voice/app.py));
  tasks cancelled and gathered, adapter closed with a 2 s timeout, gate
  released in `finally`, final redacted error or `stopping` state sent after
  the sender has ended, then close
  ([app.py:236-258](../../apps/api/src/super_agent_voice/app.py)).
- `_OutboundQueue` keeps an `audio.chunk` JSON and its binary bytes as one
  item, uses drop-oldest for audio, and fail-closes with `session-failed` when
  more than 32 controls are queued ([app.py:67-92](../../apps/api/src/super_agent_voice/app.py)).
  `clear_playback` drops epoch-tagged queue items and keeps untagged controls
  ([app.py:106-112](../../apps/api/src/super_agent_voice/app.py)).
- Watchdog enforces the total deadline and the idle deadline, mapped from
  input timestamps only ([app.py:349-359](../../apps/api/src/super_agent_voice/app.py)).
- `_forward` validates adapter audio (bytes, even, non-empty, within
  `max_audio_frame_bytes`, integer rate in {8000, 16000, 24000, 48000}) and
  re-raises an unmapped iterator end as `provider-session-ended`
  ([app.py:304-336](../../apps/api/src/super_agent_voice/app.py)). Adapter events that fail
  validation raise `invalid-audio` and fail the session closed.

Frontend (`voice-session.service.ts`):

- `session.ready` triggers capture; capture is requested only after ready
  ([voice-session.service.ts:89-97](../../apps/web/src/app/voice-session.service.ts)).
- Late-permission guard: if the socket changed, closed, or Stop ran while
  `getUserMedia` was pending, tracks are stopped and no capture attaches
  ([voice-session.service.ts:126-129](../../apps/web/src/app/voice-session.service.ts)).
  Pre-permission mute is re-applied to tracks
  ([voice-session.service.ts:131-134](../../apps/web/src/app/voice-session.service.ts)).
- Binary frames are untagged: a frame plays only when a current-epoch
  `audio.chunk` tag arrived first, the rate is from the metadata (so 24 kHz
  metadata works), and no interrupt is pending
  ([voice-session.service.ts:159-171](../../apps/web/src/app/voice-session.service.ts),
  [playback-epoch.ts:50-59](../../apps/web/src/app/playback-epoch.ts)).
- Silent PCM does not set `speaking`; the audible floor is RMS > 0.002 and is
  explicitly labeled as not speech recognition
  ([audio-signal.ts:1-15](../../apps/web/src/app/audio-signal.ts));
  the level meter is labeled "Microphone input level (not speech detection)"
  ([app.component.ts:20-21](../../apps/web/src/app/app.component.ts)).
- Automatic barge-in on RMS > 0.02 while playing is retained; the interrupt
  button is secondary and relabeled "Stop playback"
  ([voice-session.service.ts:145-147](../../apps/web/src/app/voice-session.service.ts),
  [app.component.ts:29](../../apps/web/src/app/app.component.ts)).
- Errors are not downgraded to `stopped` by the close event
  ([voice-session.service.ts:218-219](../../apps/web/src/app/voice-session.service.ts)).

`apps/web/angular.json` has a local user-added `cli.analytics` setting. This
contract does not touch that file. The developer must not stage, revert, or
reproduce its identifier. If a commit would include it, re-stage the file
without that change.

## 3. Contract terms for the backend

3.1 The five-method streaming protocol and the four backend tasks stay as the
draft has them. The contract adds these corrections, each requiring a test.

3.2 **CT-01 (post-await epoch/mute recheck as defense in depth).** The
serialized sender checks the epoch, then awaits `send_json`, then sends the
binary frame ([app.py:340-346](../../apps/api/src/super_agent_voice/app.py)).
Correction of an earlier overstated finding: the sender is single, so a new
epoch's acknowledgement can never be interleaved inside one JSON/binary pair,
and it is wrong to claim the new-epoch JSON "already went out" while the pair
is in flight. What can happen: during the `send_json` await, a control
(`playback.interrupt` or `capture.mute`) can change `state.epoch` or
`state.muted`, so the browser applies the old metadata and then receives a
payload that no longer belongs to it. Order is preserved; ownership is not.
Required defense-in-depth correction: re-check
`item.epoch == state.epoch and not state.muted` after the `send_json` await
and before `send_bytes`; if it no longer holds, drop the stale payload and do
not send bytes under metadata whose epoch or mute state has expired. The
browser must still drop such frames because `onServerInterrupt` clears the
pending tag ([playback-epoch.ts:40](../../apps/web/src/app/playback-epoch.ts));
the backend must not rely on that alone. Test required: a fake WebSocket send
barrier (or an equivalent deterministic injection point) that pauses the
sender between the JSON send and the binary send, applies an interrupt or mute
at that boundary, and asserts the stale payload is not sent and the session
continues under the new epoch or muted state.

3.3 **CT-02 (drop-oldest correctness, proven by regression, not by redesign).**
An earlier overstated finding is corrected: `put` locates the oldest audio
item with `next(...)` and then removes it with `deque.remove`
([app.py:79-92](../../apps/api/src/super_agent_voice/app.py)). Because
`_Outbound` dataclasses compare structurally equal, `deque.remove` deletes the
first equal element, which is exactly the item `next(...)` yielded.
Equal-content queue items therefore do not demonstrate a mis-ordering: the
removed element is the oldest one the code found, whether or not contents
match later items. Required behavior: keep the existing selective removal as
the default implementation. A deterministic regression test is required, not a
speculative sequence number: fill the queue past `max_audio` with equal-content
pairs and assert that the oldest queued pair is the one dropped and that
`dropped_audio` counts exactly one. If the developer changes the queue
implementation anyway, the change must demonstrably preserve the drop-oldest
guarantee, and the reason for the change must be recorded in the queue class
docstring. No sequence-number requirement in this contract.

3.4 **CT-03 (cleanup failure must not overwrite the real category).** In the
`finally` block, `except Exception: failure = _SessionFailure("session-failed")`
unconditionally replaces an already-set failure ([app.py:243-244](../../apps/api/src/super_agent_voice/app.py)),
so a real `provider-session-ended` or `invalid-audio` could be re-labeled when
`adapter.close()` misbehaves. Required correction: only set `session-failed`
when `failure` is `None`; a cleanup failure with a prior category must keep the
original category and record a note. Test required: adapter whose `close()`
raises, asserting the earlier redacted category survives and the session slot
is released (a follow-up connection with a valid token authenticates).

   *Amendment 2026-11-10 (teardown addendum revision 2,
   [voice-streaming-teardown.md](voice-streaming-teardown.md)):* the
   unconditional "always releases the slot" rule is superseded. Cleanup is
   still always attempted and presence-bounded, but the gate is released
   exactly once only when worker quiescence is observed AND the adapter
   close attempt is *confirmed* — the close task finished without an
   exception (`close_confirmed`). A close that settles with a raise or a
   cancellation retains the slot (quarantine) pending at most one
   idempotent retry by the single residual supervisor, and a permanently
   failing close holds the gate. The old expectation "raising close still
   releases the gate" is superseded by two replacement test shapes
   (raise-once-then-retry-success; permanent-failure-gate-held), without
   weakening the category-preservation rule or the bounded cleanup
   attempt (this CT-03's core). Scope is the teardown path only; other
   CT terms and the frontend terms are unaffected.

3.5 **CT-04 (explicit auth timeout, total budget preserved during auth).**
The auth wait maps its timeout to `max-duration` when `max_session_seconds
<= 5` and to `session-timeout` otherwise
([app.py:184-187](../../apps/api/src/super_agent_voice/app.py)); this is a
test-oriented heuristic on a config field rather than a deadline decision.
Required correction: introduce an explicit setting, for example
`auth_timeout_seconds` with a fixed default of 5 seconds, in
[config.py](../../apps/api/src/super_agent_voice/config.py). The total session
budget must not be dropped during auth: the effective auth deadline is the
smaller of the auth deadline and the remaining total deadline
(`loop.time() + settings.max_session_seconds`), and the category is chosen by
whichever actual deadline expires: expiry of the remaining total budget yields
`max-duration`; expiry of the auth deadline yields one fixed category
(`session-timeout`). No comparison between `max_session_seconds` and the
auth/value heuristic remains. Tests required: (a) a client that connects and
sends nothing, with `auth_timeout_seconds` set explicitly in the test config,
receives the fixed auth category, and the gate is released; (b) a total budget
that expires during the auth window yields `max-duration` and releases the
gate. The idle timeout mechanism and its tests are unchanged and are not
reused for the auth deadline.

3.6 **CT-05 (gate placement).** The session gate is acquired before accept and
before auth ([app.py:167-170](../../apps/api/src/super_agent_voice/app.py)), so an
unauthenticated connection can hold the single voice slot for its whole life.
The window is bounded by the 5-second auth timeout but not by a global
connection limit. Required correction: either acquire the gate after successful
auth and before adapter creation, or keep pre-auth acquisition only with an
explicit recorded reason and a test that unauthenticated connections time out
and release the slot. The accepted behavior must be written in this document's
acceptance table (section 7). Fake-only constraint makes the pre-auth slot low
risk in this slice, but the decision must be explicit, not accidental.

3.7 **CT-06 (fake adapter lifecycle).** Keep and test: `enqueue_audio` on a
closed or unstarted adapter raises; `events()` admits exactly one consumer and
raises for a second; `interrupt()` bumps the generation and clears queued
input; stale frames from a previous generation are silently consumed and never
yielded ([adapter.py:73-87](../../apps/api/src/super_agent_voice/adapter.py)); `close()` is
idempotent and wakes a blocked consumer ([adapter.py:95-100](../../apps/api/src/super_agent_voice/adapter.py)).
Test required: close-then-close again, close with a consumer blocked on an
empty queue, drop-oldest with a scripted full queue, and a scripted consumer
that never receives old-generation audio after an interrupt.

3.8 **CT-07 (watchdog while the adapter is silent).** The idle deadline uses
input timestamps only ([app.py:349-359](../../apps/api/src/super_agent_voice/app.py)), so a
silent or broken event source still expires the session. Test required: a
scripted adapter that emits nothing; the session must end with
`session-timeout` within the idle window and the adapter must be closed.

3.9 **CT-08 (frame validation at both boundaries).** Keep the existing
reject-and-close for odd-length, empty, and oversized frames from the browser
([app.py:277-278](../../apps/api/src/super_agent_voice/app.py)) and the equivalent
validation for adapter output including the rate allowlist
([app.py:318-323](../../apps/api/src/super_agent_voice/app.py)). Tests required: odd,
empty, and oversized input; a scripted adapter that yields an odd or oversized
chunk and a `rate_hz` of 24000 validly, plus one invalid rate, each ending the
session with a fixed category.

3.10 **CT-09 (redaction).** A scripted adapter that raises a `SENTINEL`
exception mid-stream must end the session with the fixed category only; no
provider detail in any JSON response. Requires a scripted adapter (the old
`send_audio` override is gone; see section 5.3), e.g., a subclass whose
`enqueue_audio` or a scripted `events()` raises after `start()`.

3.11 **CT-10 (independent output without input).** A scripted adapter that
emits audio without any `enqueue_audio` call must deliver exactly that ordered
output to the client, proving the forward path does not depend on the receive
path.

## 4. Contract terms for the frontend

4.1 **CT-11 (restart after error).** After any redacted error, `cleanup` sets
the status to `error` ([voice-session.service.ts:202-220](../../apps/web/src/app/voice-session.service.ts))
and the Start button is disabled whenever the status is not `stopped`
([app.component.ts:24](../../apps/web/src/app/app.component.ts)). The user cannot
restart without a page reload. Required correction: allow Start when the
status is `stopped` or `error`; `start()` already guards against a live socket
([voice-session.service.ts:21-25](../../apps/web/src/app/voice-session.service.ts)).
Test required: service-level test that `start()` succeeds from the `error`
state (the service sets a fresh socket) without a reload.

4.2 **CT-12 (service-level scripted tests).** The service uses browser APIs
that the existing Node-transpile self-test pattern
([selftest-playback-epoch.mjs](../../apps/web/scripts/selftest-playback-epoch.mjs))
cannot run directly, because those are async and DOM-dependent. The contract
requires scripted service tests using injected fake `WebSocket`,
`AudioContext`, and `getUserMedia` objects (fakes written by the developer in
the test file; the pinned `typescript` and existing npm scripts only; no test
framework added). The test suite must cover: initial state silence until
`session.ready`; `speaking` is set only by audible PCM of the current epoch;
current rate metadata (including a 24000 chunk) reaches `createBuffer`; stale
epoch frames after an interrupt do not play; mute stops frames and resets the
level; a late microphone permission after Stop attaches nothing; automatic
interruption fires on a loud frame while playing; `session.error` produces the
redacted message and cleanup. See section 6 for the honest uncertainty about
how much of this can be tested without a browser.

4.3 **CT-13 (stop with a silent event source).** Stopping while the adapter
sends no events must close the socket and clean all playback and capture
state, with the status `stopped`. Cover in the service tests and in the
backend stop-with-silent-adapter test (CT-07).

4.4 **CT-14 (retained behavior, unchanged).** Local interrupt bumps the
frontend epoch immediately and the backend epoch is authoritative
([voice-session.service.ts:59-66](../../apps/web/src/app/voice-session.service.ts),
[playback-epoch.ts:29-41](../../apps/web/src/app/playback-epoch.ts)). The
interrupt control is the secondary "Stop playback" action; automatic
interruption is primary. PCM conversion, mute track disablement, chat-free
recycling of `pendingRateHz`, and the "errors not downgraded" behavior are
retained as drafted.

4.5 **CT-15 (honest labeling).** The input meter is a level meter; it is not
voice activity detection and must not be presented as speech recognition. The
comment at [audio-signal.ts:12-14](../../apps/web/src/app/audio-signal.ts) stays in
place, and product text may not call it VAD or speech detection. The RMS
thresholds (0.002 audible floor, 0.02 barge-in) are provisional and
unmeasured. They may be tuned in this slice; every human gate, R-01.3 and
R-01.4 among them, remains open and unaffected by that tuning, and no
measurement claim may be made for threshold behavior until those checks are
recorded by the operator.

## 5. Concurrency and race findings in the draft

These findings record the draft's flaws explicitly. The developer must correct
or, for each item, record why the correction is unnecessary. Findings 5.1 and
5.2 correct overstated claims from the contract's first revision; the current
wording below is authoritative.

5.1 The sender's epoch check is not atomic with the binary send (CT-01). The
pair is ordered, but the ownership check can go stale during the `send_json`
await; a re-check after the await is required as defense in depth. Fix
required before the slice is accepted.

5.2 `clear_playback` drops every epoch-tagged queue item, including the
current epoch's `turn.complete` when the user mutes mid-playback
([app.py:106-112](../../apps/api/src/super_agent_voice/app.py)). This is
intended stale-state cleanup, not an accidental control drop, because a
muted session's turn boundary is not actionable. The comment at
[app.py:107](../../apps/api/src/super_agent_voice/app.py) is accurate as written; keep it,
and add a queue test that mute drops audio and tagged turn events but keeps
untagged acknowledgements, and that a control-overflow `put` raising
`_SessionFailure` keeps the whole session closed (fail-closed control bound).

5.3 Tests still target the old API. Three concrete breakages in
[test_voice_api.py](../../apps/api/tests/test_voice_api.py):
`authenticate` expects the ready message without the new `outputRateHz` and
`provider` fields ([test_voice_api.py:35-40](../../apps/api/tests/test_voice_api.py));
`test_muted_audio_is_not_sent_to_adapter` monkeypatches `adapter.send_audio`,
which no longer exists ([test_voice_api.py:175-182](../../apps/api/tests/test_voice_api.py));
`test_adapter_error_is_redacted` overrides `send_audio` and therefore cannot
inject the error anymore ([test_voice_api.py:213-225](../../apps/api/tests/test_voice_api.py));
the interrupt and audio tests also compare whole JSON objects that now carry
extra fields. All must be migrated to the streaming API (scripted enrichments,
epoch-tagged payloads) as part of this slice, keeping standard library,
`pytest`, and the existing `TestClient` pattern.

5.4 The gate-before-auth slot squatting decision (CT-05) and the
cleanup-failure category overwrite (CT-03) are smaller but recorded, because
both change user-visible or category-visible behavior.

5.5 Note that `test_only_one_active_session_is_allowed` relies on the second
connection being accepted only to be closed with 1013
([test_voice_api.py:63-75](../../apps/api/tests/test_voice_api.py)); the
correction in CT-05 must not silently change that test's semantics to "close
before accept". Decide which and keep the test in step.

## 6. Honest uncertainty statement

I am the zero-cost fallback model, not the primary architect. Each of the
following is a point where I believe a stronger model, or the developer's
own environment, would resolve what I could not:

1. **Frontend test harness (CT-12) is the largest unresolved item.** The
service uses `WebSocket`, `AudioContext`, `MediaStream`, `getUserMedia`, and
async cleanup. The existing self-test pattern transpiles and runs
synchronously in Node. Whether the service's async paths (`AudioContext`
closure, `getUserMedia` promises) can be exercised well enough by hand-written
fakes without adding a test framework is genuinely unverified. The task list
below splits it into a standalone incremental step precisely so that if the
fakes are brittle, a smaller scoped harness change or an operator-approved
script-only verification plan can be decided without reworking the slice.
2. **CT-01 test determinism.** The contract requires a fake-WebSocket send
barrier (or equivalent deterministic injection point) that pauses the sender
between the JSON send and the binary send. Whether such a barrier can be
injected through Starlette's `TestClient` WebSocket transport, or whether the
test should drive `_send` directly with a stub WebSocket object, is a code
design choice the developer makes from the test harness reality. The
correction itself (the post-await recheck) is mechanical and not uncertain.
3. **Close codes before accept on a real browser.** Existing tests pass with
Starlette's TestClient, but whether a browser observes close code 1008, a
handshake failure, or something else for a pre-accept `close()` cannot be
verified from here. This matters for UX only and must be checked in the
operator's local run (it belongs to R-01.4, not this contract).
4. **CT-05 gate placement.** Either placement is defensible; the contract only
requires that the choice be explicit, wired, and tested, not that a particular
ordering be picked. The maintainer's review should confirm the chosen
ordering matches the section 5 review intent.

These do not block the backend fixes; CT-01, CT-02, CT-03, CT-04, CT-07, and
CT-09 are mechanical enough to proceed as written.

## 7. Acceptance criteria (definition of done)

Every item below is scoped, not maintainer-approved, and not yet done. Nothing
here ticks any roadmap item.

| # | Test / criterion | Layer |
| --- | --- | --- |
| A-01 | Strict Host and Origin confirmed before accept; mismatched values close 1008 with no adapter and no session.error. | backend |
| A-02 | Wrong or missing token closes 1008; adapter never created or started; failed auth rate does not throttle sessions (throttling is R-01.5, out of scope). | backend |
| A-03 | Session starts only after `session.auth` and after `adapter.start()` succeeds; `session.ready` carries epoch, output rate, provider; a failing start yields one fixed category and no ready. | backend |
| A-04 | Independent output without input delivers ordered audio + turn (CT-10). | backend |
| A-05 | `rateHz` metadata validated server-side; a scripted adapter emitting rate 24000 works; an invalid rate fails the session. | backend |
| A-06 | Stale-epoch and mute filtering at the sender (CT-01, CT-02). | backend |
| A-07 | Interrupt epochs (local and provider sources), mute, stop with silent event source (CT-07, CT-13). | backend |
| A-08 | Queue controls: drop-oldest audio, never drop controls, fail closed on control overflow (CT-02, 5.2). | backend |
| A-09 | Idle and total deadlines fire while the adapter is silent (CT-07). | backend |
| A-10 | Odd, empty, oversized frames (browser and adapter paths), invalid rate (CT-08). | backend |
| A-11 | Adapter cleanup failure keeps the earlier category and releases the session slot (CT-03). | backend |
| A-12 | Fake adapter: single consumer, idempotent close, drop-oldest, stale generation filtering (CT-06). | backend |
| A-13 | Redacted error category with no provider detail in any response (CT-09). | backend |
| A-14 | Explicit authentication deadline bounded by the remaining total budget; the category reflects whichever actual deadline expires; the gate releases on auth expiry, and the total budget is enforced during auth (CT-04). | backend |
| A-15 | Service state machine through scripted fakes: silence until ready, audible-gated speaking, 24k rate, stale frame drop, mute, late permission, stop with silent source, restart from error (CT-11, CT-12, CT-13). | frontend |
| A-16 | Input level is labeled and implemented as a level meter, never as speech recognition or VAD (CT-15). | frontend |
| A-17 | `npm run check` passes on the final commit, including Markdown link validity for this document, and `angular.json` is untouched by the work. | repo |
| A-18 | `angular.json` analytics setting preserved; no secrets, recordings, or transcripts in the diff; no new dependency in either package or requirements files. | repo |

*Amendment 2026-11-10 (teardown addendum revision 2,
[voice-streaming-teardown.md](voice-streaming-teardown.md)):* (1) A-11's
"always releases the session slot" is amended to the confirmed-closure
release defined there: release exactly once, only at observed worker
quiescence AND `close_confirmed`; a close that settles with a raise or a
cancellation retains the slot pending at most one idempotent retry by the
single residual supervisor; permanent failure holds the gate (no
auto-success claim); category preservation is unchanged. (2) CT-05
placement note: the pre-auth single-slot acquisition is accepted intent,
as documented inline in the source
([app.py:171-180](../../apps/api/src/super_agent_voice/app.py)); the hold is bounded
by the auth deadline inside the total budget, and a refused second
connection still receives 1013.

Test materials: standard library and `pytest` only for Python; the existing
pinned `typescript` package and npm scripts only for the frontend self-test
pattern; no test framework, no `anyio` addition, no WebGL/Web Audio
dependency.

## 8. Rejected alternatives

1. **Patching the request/response seam instead of the streaming rewrite.**
Rejected. `send_audio -> AudioReply` cannot represent out-of-band
`Interrupted` or mid-turn model audio, and the design already made this
decision (voice-foundation section 4). The uncommitted draft is inside the
approved path; this slice keeps it.
2. **Blocking send-side backpressure (the sender awaits a full outbound queue)
rather than drop-oldest audio queues.** Rejected. Backpressure on the
outbound queue would stall real-time playback and, in that stall, controls
such as interrupts and stop as well. Drop-oldest audio with never-dropped
controls, per the foundation design (voice-foundation section 5), is
retained; CT-02 proves the existing queue's drop-oldest behavior with a
deterministic regression test instead of redesigning it.
3. **Dropping controls on overflow instead of fail-closing the session.**
Rejected. A dropped interrupt or stop is indistinguishable from a lost one
and can strand a session; fail-closed on control overflow matches the
fail-closed table in the foundation design (voice-foundation section 9,
line 571) and the draft's `_OutboundQueue.put`
([app.py:88-89](../../apps/api/src/super_agent_voice/app.py)).
4. **Introducing AudioWorklet, MediaRecorder, or a fake-adapter scripting
library in this slice.** Rejected. AudioWorklet is an operator-preference
change with macOS/Windows device testing (R-01.4 still open), and a scripting
library would add an audited dependency for no new capability. The fake is
deterministic enough through subclass overrides and direct queue
manipulation.

## 9. Trade-offs and risks

- The streaming rewrite touches the core socket loop. The migration of
`test_voice_api.py` (section 5.3) is the main regression surface; the whole
existing suite must stay green in its new form.
- The post-await recheck (CT-01) is defense in depth, not a fix for an
observed wrong-ordering. Its test needs a deterministic injection point; the
injection must not change production behavior, and approaches that take a
stub WebSocket directly are acceptable if Starlette's transport resists.
- RMS "audible" and "barge-in" thresholds are provisional and unmeasured
([audio-signal.ts:8-15](../../apps/web/src/app/audio-signal.ts),
[voice-session.service.ts:145-147](../../apps/web/src/app/voice-session.service.ts)).
False barges on loud ambient noise are possible until a real microphone test
is recorded; tuning these values in this slice is allowed, and the human
gates stay open.
- Mic capture uses `ScriptProcessorNode`, deprecated in the platform, with an
16 kHz context. Accepted here because the operator's microphone acceptance is
a separate open checklist item, not because it is the right long-term path.
- Cleanup failure, adapter failure, and connection failure all end in
fixed categories; surfacing "why" with counts and timings is left to the
metrics/records work, not to this slice.
- The locked-down `angular.json` constraint exists because a local user-made
CLI analytics setting must not leak into the repo diff or into tooling output.

## 10. Explicit limitations (do not mark covered by this slice)

- Security review pending. The controls in this slice are self-assessed, not
independently reviewed. R-01.6 stays open.
- Provider stale-event quarantine (e.g., post-interrupt Gemini audio) is not
provable with the fake adapter. The design's interrupt-acknowledgement and
stale-epoch rules are implemented as spec'd; their adequacy against the real
provider's interleaving is untested until R-01.9.
- Simple RMS is not real VAD and never claims to be.
- Microphone audio quality, echo, latency, and OS-level mute behavior are not
accepted here. R-01.3 and R-01.4 remain open human items.
- Credential throttling, token max-age, same-origin cookie flow, and the
provider consent UI are separate R-01.5 / R-01.6 work, untouched here.
- Native provider grant, keyed adapter, and synthetic live command are
R-01.7 to R-01.9, out of scope.

## 11. Ordered task breakdown

1. **Backend CT-01 post-await recheck.** Add the defense-in-depth re-check of
`item.epoch == state.epoch and not state.muted` after the `send_json` await
and before `send_bytes` ([app.py:339-346](../../apps/api/src/super_agent_voice/app.py));
drop the stale payload on mismatch; add the barrier test pausing the sender
at that boundary via a fake WebSocket or stub WebSocket (A-06).
2. **Backend CT-02 drop-oldest regression only.** Keep the existing
`_OutboundQueue` implementation unchanged by default; add the
equal-content regression test asserting the oldest pair is dropped and
`dropped_audio` counts one (A-08). Any queue redesign requires a recorded
reason and the same guarantee.
3. **Backend CT-03 cleanup-failure category preservation.** Change the
`finally` block to keep an existing failure category; add the close-raising
adapter test and assert the slot releasability (A-11).
4. **Backend CT-04 explicit auth deadline.** Add `auth_timeout_seconds`
(default 5) to `VoiceConfig`; bound the auth wait by the remaining total
deadline; choose the category by the deadline that actually expires;
add both tests: auth expiry releasing the gate, and total budget expiring
during auth (A-14). Idle timeout unchanged.
5. **Backend CT-05 gate decision.** Choose and wire gate placement (post-auth
or documented pre-auth), commit the reasoning as an inline "why" comment at
the acquisition site, and keep the concurrent-session test in step (A-02,
5.5).
6. **Backend CT-06 to CT-10 fill-in tests.** Fake adapter lifecycle tests,
silent-adapter idle deadline test, frame validation matrix, redaction test
with a scripted raising adapter, and the independent-output test (A-04,
A-07, A-08, A-10, A-11, A-12, A-13).
7. **Test migration (section 5.3).** Rewrite
`apps/api/tests/test_voice_api.py` for the streaming API and ready-message
shape; confirm the full backend suite green; retain the 11-baseline intent
(not necessarily count).
8. **Frontend CT-11 restart from error.** Allow Start after `error`; add the
service-level restart test (A-15).
9. **Frontend CT-12 scripted service tests.** Build the fake
`WebSocket`/`AudioContext`/`getUserMedia` injection and cover the A-15
criteria. Stop and ask the operator, per section 6 item 1, if the fakes are
too brittle rather than weakening the criteria silently.
10. **Frontend CT-13 and CT-15.** Stop-with-silent-source service test and
the level-meter labeling review of UI copy; no unlabeled "VAD" or speech
detection wording anywhere, and threshold tuning stays provisional until
the operator records real microphone behavior (A-15, A-16).
11. **Repo hygiene.** `npm run check`, confirm `apps/web/angular.json`
inherits the local analytics setting unstaged, confirm no diff secrets, and
finalize this document's status line from "contract" to "signed for this
slice" only after items 1 to 10 pass.
12. **Hand-off, not acceptance.** Record in the phase PR body that this is a
technical sign-off only; leave R-01.3, R-01.4, R-01.5, R-01.6 open; request
the operator's real review before any claim beyond this document.

## 12. Definition of done

- All items 1 to 11 finished. Item 12 is a delivery step, not a quality gate.
- Every acceptance row A-01 to A-18 has a written, runnable test or record; a
row with `not run` in the final PR body is treated as not met.
- No new roadmap tick, phase move, gate edit, `roadmap-ids.txt` edit, or
`phases.md` edit. No `angular.json` change. No commit, push, or PR action
from this subagent; the parent session handles those.
- The limitation list in section 10 stays in the PR body, not just this doc.

## Appendix A. Signatures

- Design review and contract: Solution Architect subagent (GLM-5.3-Flash Free,
  zero-cost fallback), 2026-11-10. Honest note recorded per AGENTS.md rule 4.
- Independent security review: pending (R-01.6). Not obtained; not waived.
- Maintainer approval: not obtained; not claimed.
- Native provider grant: not obtained; not needed for this slice (fake only).
- Human checks R-01.3 and R-01.4: open; unaffected by this contract.
