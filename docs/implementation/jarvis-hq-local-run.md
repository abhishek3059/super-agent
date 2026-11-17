# Jarvis HQ: local run record

| Field | Value |
| --- | --- |
| Date | 2026-11-17 |
| Host | macOS, Node 22.22.3, Hermes Agent v0.22.2, Google Chrome |
| Model | The operator's Hermes default (`nvidia/nemotron-3-super-120b-a12b`, provider `nvidia`) |
| Run by | Claude Code (`claude-fable-5-2`) for `jeevesh2515`, against a scratch data folder with synthetic requests |
| App | [apps/hq](../../apps/hq/README.md) |

Output below is copied from the terminal. Bot ids are omitted.

## Checks

```text
$ npm run typecheck        (no errors)
$ npm test
# pass 9
# fail 0
$ npm run build            (no errors)
$ npm audit
found 0 vulnerabilities
$ npm run check            (repository root)
"errors": 0
roadmap self-test: all checks passed
```

The self-checks grew from 6 to 9 during review; the figure above is the final
run. With `xaiKey` in `env.ts` put back to read the environment, the
"services stay off" check failed (`# pass 8`, `# fail 1`), so it does guard
that setting.

## Boundary probes

The following output is from the original draft. The follow-up boundary checks
expect HTTP 403 for missing sessions and HTTP 400 for malformed bot creation
bodies. They also reject a remote Hermes URL and a symlinked data parent.
Those checks run with a temporary home and SQLite database. They do not start
Hermes or Chrome, exercise live voice, or connect HQ to the shared job ledger.

```text
GET /api/health                                   200
GET /api/health   with Host: evil.example         403
GET /api/health   with Origin: https://evil.example  403
GET /api/bots     without a session               401
one-time sign-in link, first use                  302
one-time sign-in link, second use                 410
GET /api/apps/callback?slug=</script><script>alert(1)</script>   page contains  slug:""
GET /api/apps/callback?slug=gmail                                page contains  slug:"gmail"
POST /api/approvals/<unknown>  body {}                            400
POST /api/approvals/<unknown>  body {"decision":"x"}              400
POST /api/approvals/<unknown>  body {"decision":"deny"}           404
POST /api/approvals/<unknown>  body not-json                      400
GET /api/apps  (connected apps switched off)                     {"apps":[],...,"total":0}
```

## Handoff, Jarvis to Quill and back

Request typed to Jarvis: "Ask Quill to write one short sentence welcoming me
to Jarvis HQ, then tell me the sentence."

```text
== Jarvis
  8 tool-call send_to_bot | Messaged Quill  | status done
  9 tool-call stay_silent | Stayed silent  | status done
  10 tool-call stay_silent | Stayed silent  | status done
  11 message user | Welcome to Jarvis HQ — glad you're here. | from Quill
  12 message assistant | Welcome to Jarvis HQ — glad you're here.
== Quill
  1 message user | Write one short sentence welcoming the user to Jarvis HQ. | from Jarvis
  2 message assistant | Welcome to Jarvis HQ — glad you're here.
```

Quill did not call `send_to_bot` to answer. The app returned its reply to
Jarvis (row 11), which is the behaviour the handoff rule exists for.

## Browser, screen and Library

- Jarvis asked Scout to open `https://example.com`. Scout's own Chrome (its
  DevTools port) listed `https://example.com/` tabs afterwards, and Scout's
  answer reached Jarvis and then the user. Scout's first two browser calls
  failed and the next three succeeded.
- The live view of Scout's browser drew frames in the app.
- In control mode, a click sent through the viewer on the page's link moved
  Scout's tab to `https://www.iana.org/help/example-domains`.
- Forge wrote `hello.txt` in its working folder. `GET /api/bots/<id>/files`
  returned `{"status":"ok","path":"","files":[{"name":"hello.txt","size":5,...}]}`.

## Not run

- Any OpenAI call: voice, voice preview, dictation. No key was present.
- Composio connected apps and xAI `x_search`. Both are switched off in code.
- All five gateways and browsers at once. Four ran together.
- Windows and Linux.
- The CI workflow. It runs when the pull request opens.

## Shared ledger revision

The earlier manual run above describes the original draft. This revision
adds the private jobs endpoint, role-filtered claim, receipt writeback and
macOS profile. An expired claim becomes unknown and is never replayed.
Test output covers the SQLite job lifecycle, cross-role refusals, retrying a
receipt, the Node client's contract, and a benign macOS child process allowed
to write its temporary workspace and refused access to a sibling fixture.
A separate macOS smoke used a temporary home, the real Python HTTP API
and SQLite, an installed Hermes virtual environment, contained Chrome, and
a local inference stub. Observed: DevTools HTTP 200 and a JPEG frame,
admission queued, Scout claimed the job, and HQ wrote a succeeded receipt.
The persisted event reasons were `created`, `claimed_hq_scout`, and
`hq_finished`. The test checked the synthetic output summary after opening
the SQLite ledger again.

The default Hermes launcher attempted dependency repair while sandboxed.
Using a preinstalled entry point in the Hermes virtual environment resolved
that setup issue. A real PostgreSQL server and live OpenAI voice were not run.
