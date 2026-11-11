# R-01.7: Gemini Live adapter behind the seam

| Field | Value |
| --- | --- |
| Roadmap item | R-01.7, Gemini Live adapter behind the replaceable seam, covered by offline tests with the fake |
| Date | 2026-11-11 |
| Operator | `jeevesh2515` |
| Built by | Claude Code. A `claude-sonnet-5-5` subagent ported the code; `claude-fable-5-2` reviewed the diff and re-ran the tests. |
| Source | Adapter and tests ported from the closed [PR 29](https://github.com/abhishek3059/super-agent/pull/29) by `jeevesh2515`, who keeps commit authorship |
| Design | [Voice foundation](../design/voice-foundation.md), section 6 |
| Gate effect | None. RT-G01 stays open. No provider call has been made with this code. |

## What exists now

- `apps/api/src/super_agent_voice/gemini_adapter.py`: `GeminiLiveAdapter`,
  implementing the `VoiceAdapter` protocol.
- `apps/api/src/super_agent_voice/adapter.py`: the seam gains `AdapterError`
  with five fixed categories, `end_audio_stream()`, and the adapter's `name`
  and `output_rate_hz`.
- `apps/api/src/super_agent_voice/app.py`: an `AdapterError` from start or
  from the event stream ends the session with its category; `session.ready`
  reports the adapter's rate and name; mute calls `end_audio_stream()`.
  Teardown, deadline, auth, and session-gate code is unchanged.
- `apps/api/src/super_agent_voice/config.py`: `gemini_model`, default
  `gemini-3.8-live`, overridden by `SUPER_AGENT_GEMINI_MODEL`.

## What does not exist

- The `google-genai` SDK is not a dependency. It is imported only inside the
  function that opens a real session, so that path has never run. It is first
  exercised by the opt-in live command (R-01.8).
- The application never builds a `GeminiLiveAdapter`. `create_app` still
  defaults to the fake adapter, and no setting switches the browser console
  to Gemini. Personal microphone audio stays local.
- No reconnect, session resumption, or context window compression. The design
  defers resumption to a separately reviewed design.

## Differences from the design text

| Design section 6 says | Implementation | Reason |
| --- | --- | --- |
| `server_content.go_away` | Checks `go_away` on the message and on `server_content`; either fails closed | The location in the SDK is unverified until the SDK is installed (R-01.8) |
| `session_resumption_update`: store the handle only | Ignored | Storing a handle nothing reads is dead code |
| Send `audio_stream_end` on mute or stop | Sent on mute; stop closes the provider session | Sending it on stop would change the reviewed teardown path |
| Missing key: `provider-unavailable` | Same | PR 29 used `provider-unsupported`; the design wins |

## Model ID check

On 2026-11-11 the subagent read <https://aistudio.google.com/docs/models>. It
reported `gemini-3.8-live` as the default Live API model and
`gemini-3.1-flash-live-preview` as legacy. The orchestrating agent did not
re-read the page. The ID is a config default, not a hard-coded value.

## Known limits

- With a model turn in flight, `interrupt()` waits 5 seconds for the provider's
  `interrupted` or turn completion and otherwise fails the session, as the
  design says. Muting or pressing Interrupt during a long model answer may
  therefore end the session. This is unmeasured; check it in the synthetic live
  run (R-01.9).
- `classify` maps HTTP 401, 403, and 5xx to `session-failed`. The design table
  has no row for a rejected key. Decide the category before the live run.
- The end-of-stream marker shares the bounded drop-oldest input queue, so under
  sustained overload it can be evicted.
- The adapter's outgoing event queue is unbounded.

## Independent review

A separate `claude-sonnet-5-5` reviewer, which did not write the code, read the
branch against `develop` on 2026-11-11 and scored it 7.2 out of 10, below the
8.5 bar in [AGENTS.md](../../AGENTS.md) section 9. Its findings and the fixes:

| Finding | Fix |
| --- | --- |
| `close()` returned at once on a second call, so the app's retry after a cancelled close would report a closure that never finished | One shielded release task shared by every `close()` call; a retry returns only when the provider session is really released. Tested. |
| An acknowledgement for an earlier turn could satisfy a later interrupt in the same event-loop tick | Each interrupt timer waits on its own event. The sequential case is tested; the same-tick case is fixed by construction and has no test. |
| Token generator followed a symlink and changed mode by path | The file is removed and created with `O_EXCL` and mode 0600 |
| Missing tests: silent provider end, `go_away` on `server_content`, model ID from the environment, weak token in the file; fixed sleeps as barriers | Added; send-path tests now wait on the recorded sends |
| Roadmap header still named PR 24 as the open work bundle | Now names PR 32 |
| Record did not name the Interrupt button | Named under Known limits |
| `AGENTS.md` edit (stale `taks/` rename note removed) is unrelated to R-01.7 | Kept, and called out in the PR 32 description for code-owner review |
| Token reader did not check ownership or file type | The reader now refuses a file that is not a regular file owned by the current user. Tested. |

The reviewer's second pass, on the commit with the first four fixes, scored
7.6: correctness 8, security 7.5, honesty 7, scope 7.5, clarity 8. It confirmed
the close and interrupt fixes and found two record errors, both corrected here:
a "Corrected" claim made before the roadmap edit was committed, and a
verification block that mixed re-run and carried-over results.

Not changed: the token reader does not check the parent directory mode, the
Windows ACL is not set (review item N2, R-01.6), removing and recreating the
token file is not atomic, and these cases have no test: eviction of the
stream-end marker itself, `close()` while `start()` is still connecting, and
the same-tick acknowledgement race.

The third pass, on `60a13cb`, scored 7.8: correctness 8, security 8, honesty 7,
scope 8, clarity 8. It found no code defect; its deductions were for stale
fields in the PR description, since corrected. After it, two tests were added
(drop-oldest input queue, start refused after close) with a guard in `start()`.

## Verification (macOS, Python 3.14.5, Node 22.22.3)

Every command below was re-run on 2026-11-11 after the first two rounds of
review fixes. After the last change, which touched only the adapter, its
tests, and this record, the backend tests and `npm run check` were run again.

```text
$ python3 -m pytest apps/api
84 passed in 3.60s

$ npm run check
  "errors": 0
roadmap self-test: all checks passed

$ npm run test:epoch --prefix apps/web
playback-epoch self-test: PASS (8 cases)

$ npm run test:voice --prefix apps/web
voice-session self-test: PASS (39 cases)

$ npm audit --prefix apps/web
found 0 vulnerabilities

$ npm run build --prefix apps/web
Application bundle generation complete.

$ python3 -c "import sys; sys.path.insert(0,'apps/api/src'); import super_agent_voice.gemini_adapter; assert 'google' not in sys.modules; print('lazy ok')"
lazy ok
```

The 84 backend tests are the 66 from the streaming slice, 1 for the token
generator, 9 ported adapter tests, 4 adapter tests added after review, and 4
new seam tests. Not run: a fresh
`npm ci` and a fresh locked `pip install`; the runs used existing local
installs. Hosted CI on macOS and Windows has not run on this commit yet.
