# R-01.F10: muted keep-alive and stalled-microphone reporting

| Field | Value |
| --- | --- |
| Date | 2026-11-19 |
| Trigger | The R-01.10 console run record `r01-10-console-run-20261119T101357Z.md` (not yet committed) ended a live Gemini session with `session-timeout` after about 3.5 minutes. |
| Scope | Console and backend control only. The 60-second idle limit and the 15-minute maximum are unchanged. |

## Cause

The backend watchdog ends a session when no message arrives for 60 s
(`_receive` sets `last_input` on any frame). The console returns early in
`onAudioProcess` while muted, so a mute longer than 60 s always ended the
session. This is proven from the code and covered by the new tests.

## Change

- Console: while connected, `session.ready` has been handled (capture ready)
  and muted, a 20 s interval sends `{"type":"session.keepalive"}`. The timer
  is cleared on unmute, stop, every cleanup path (error, close, timeout), and
  is only started once capture is ready. Unmuted sessions send nothing extra
  because audio frames already flow.
- Backend: `session.keepalive` is accepted after auth only. It refreshes
  `last_input` (as every frame does) and nothing else. Any extra field fails
  closed as `invalid-control`. Before auth it is refused like every other
  control.

Simpler options rejected: raising the idle limit (weakens REQ-10 for abandoned
sessions) and sending silent PCM while muted (would put audio frames on the
wire, which the mute contract forbids).

## Unmuted stall (part B)

Read from `voice-session.service.ts` before the change.

Already handled:
- Initially suspended context: `resume()` runs before `captureReady`.
- ScriptProcessor garbage collection: `this.processor` and `this.context` hold
  strong references for the session, so this is not a cause.
- Permission denied, factory failures, resume rejection at start.

Not handled (no code path reacted, so the console showed Listening and idled
into the timeout):
1. The audio context leaving `running` later (browser or OS suspends or
   interrupts it). No `onstatechange` handler existed.
2. The microphone track ending (device unplugged, permission revoked). No
   `track.onended` handler existed.
3. The source going silent (`track.onmute`, set by the browser or OS).

Fixes, each showing in the console: a context that is suspended or interrupted
shows the notice "Microphone paused by the browser or system. Trying to
resume." and `resume()` is called; if resume rejects the session ends with an
error. A muted source shows the same notice and clears it on unmute or when
the context runs again. An ended track ends the session with "Microphone
stopped by the browser or system. Start again to retry."

Hypothesis, not proven: the 3.5 minute session in Chrome Incognito stalled
because of cause 1, 2 or 3, or simply because the operator muted or was
silent (silence still sends frames, so this alone should not time out). The
run record does not say whether the mic was muted. The code gives no way to
tell which one happened. Check in the next manual run (below).

## Tests (real output, 2026-11-19, Windows)

- `npm run test:voice --prefix apps/web`: PASS (72 cases)
- `npm run test:ui --prefix apps/web`: PASS (48 cases)
- `npm run test:epoch --prefix apps/web`: PASS (8 cases)
- `npm run build --prefix apps/web`: complete
- API: 1108 passed, 109 skipped, 1 failed. The failure is the known Windows
  `test_memory.py::test_files_are_private_even_when_they_already_existed`.

New cases: keep-alive interval and payload, none when unmuted, none before
capture is ready, timer cleared on unmute, stop and socket close, suspended
context, muted source, ended track, resume failure; backend keep-alive refresh
past twice the idle limit then timeout, payload fails closed, refused before
auth.

## Next manual run

Mute for more than 90 s and confirm the session stays up and unmute works.
Then stay unmuted and silent for 2 minutes: expected to stay up. If the
session still ends, note whether a "Microphone paused" notice or a microphone
error appeared first, whether the tab was hidden, and the browser mode.
