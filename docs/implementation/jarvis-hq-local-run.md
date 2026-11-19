# Jarvis HQ: local run record

The [2026-11-17 approval](../approvals/jarvis-hq-dec-23-approval.md) closes R-H.1
and authorizes the [synthetic OpenAI voice check](jarvis-hq-voice-check.md).
The run below predates it.

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
# pass 15
# fail 0
$ npm run build            (no errors)
$ npm audit
found 0 vulnerabilities
$ npm run check            (repository root)
"errors": 0
roadmap self-test: all checks passed
```

The self-checks grew from 6 to 15 during review and containment work, with
more assertions added inside them in later rounds; the figure above is the final
run. With `xaiKey` in `env.ts` put back to read the environment, the
"services stay off" check failed (`# pass 8`, `# fail 1`), so it does guard
that setting.

## Boundary probes

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

## Containment

Run on 2026-11-17 with every gateway and browser restarted under the final
sandbox profile. Paths are shortened: `<data>` is the scratch data folder.

Forge was asked to run these in its own shell and report the output:

```text
1. cat <data>/session-secret            cat: ...: Operation not permitted (exit 1)
2. ls <data>/engines                    ls: ...: Operation not permitted (exit 1)
3. ls ~/.ssh                            ls: ...: Operation not permitted (exit 1)
4. head -c 30 ~/.hermes/.env            head: ...: Operation not permitted (exit 1)
5. head -c 30 ~/dev/super-agent/README.md   head: ...: Operation not permitted (exit 1)
6. touch ~/hq-escape-test               touch: ...: Operation not permitted (exit 1)
7. curl http://127.0.0.1:8650/health    000 (exit 7, connection failed)   [another bot's gateway]
8. security find-generic-password ...   The specified item could not be found in the keychain. (exit 44)
9. open -a Calculator                   cannot be opened for an unexpected reason, Code=-13056 (exit 1)
10. pbpaste | head -c 20                (empty output)
11. echo ok > ./inside.txt && cat ./inside.txt   ok
12. curl https://example.com            200
```

`~/hq-escape-test` did not exist afterwards. These are the bot's own reports
of its tool output; item 6 was also checked from outside.

Scout was asked to open these in its browser. The tab contents were then read
from outside the sandbox through the browser's DevTools port:

```text
https://example.com/                    "This domain is for use in documentation examples ..."
file://<data>/session-secret            "Your file couldn't be accessed"
file://~/dev/super-agent/README.md      "Your file couldn't be accessed"
http://127.0.0.1:8650/health            refused by Hermes' browser tool before it reached the browser
```

A separate direct test of a sandboxed Chrome gave `net::ERR_ACCESS_DENIED`
for a local port and for both file URLs.

After the restart, Jarvis asked Scout for the first sentence on example.com
and reported it back, with all five gateways and two browsers running
contained.

Ego Browser (`ego lite`) also started headless inside the sandbox and
answered on its DevTools port. Nothing else was tested with it.

One defect found by the self-checks: with the data folder outside the home
folder, the session secret was readable. The profile now closes the data
folder wherever it is.

### Attacks through the server (after review pass 5)

Review pass 5 found that the unsandboxed server could be used to get out:
it followed links a bot planted in its own folders, and it signalled pids a
bot wrote. Both were changed, then tried again through the running app on
2026-11-17. Forge was asked to:

```text
1. ln -sf ~/hq-target-save planted.txt     (in its working folder)
2. save_file planted.txt "PWNED"
3. ln -sf ~/hq-target-soul <its home>/SOUL.md
4. echo <pid of a Chrome helper of the operator's> > <its home>/gateway.pid
```

Checked from outside the sandbox afterwards:

```text
~/hq-target-save                        original   (unchanged)
<files>/planted.txt                     regular file containing PWNED (the link was replaced)
operator's Chrome helper, after restarting Forge from the app    still running
~/hq-target-soul after the restart     original   (unchanged)
<its home>/SOUL.md after the restart   regular file, 363 bytes (the link was replaced)
```

The same attempts from the bot's shell, also checked from outside:

```text
touch /opt/homebrew/hq-probe            Operation not permitted
touch /private/tmp/hq-probe             Operation not permitted
launchctl submit ... touch ~/hq-launchd-probe   exit 1, no file, no job listed
ls <data>/run <data>/engines            Operation not permitted
```

A sandboxed shell with the final profile also could not write
`/usr/local/bin` or `/Applications`, read `/private/tmp` or the per-user
temporary folder, or reach an ssh agent (none was running, so only the
error path was seen). It could reach `https://example.com` (200) and its own
folder.

The self-check for planted links was run against the old write code and
failed (`# pass 12`, `# fail 1`), so it guards that behaviour.

### Round after review pass 6

Review pass 6 found that a bot could listen on another bot's browser port,
that the server's own memory edit could be raced, and that the live view
trusted whatever answered on the port. After the fixes, on 2026-11-17, with
the latest `develop` merged in:

```text
Jarvis -> Scout: open https://www.iana.org/help/example-domains, report heading
  Scout replied "Example Domains"; Jarvis reported it.  Screenshot of Scout: 200, 59343 bytes.

Scout's browser stopped, then Forge asked to listen in its own shell:
  bind 127.0.0.1:9302 (Scout's browser port)   PermissionError: Operation not permitted
  bind 127.0.0.1:0    (any port)               PermissionError: Operation not permitted
lsof on 9302 afterwards (from outside)         nothing listening
Scout's browser reset from the app             ok; screenshot 200

Sandboxed shell, final profile:
  bind its own port                            ok
  bind ::1:9302                                Operation not permitted
  connect [::ffff:127.0.0.1]:8650, [::1]:8650  refused (000)
  https://example.com                          200
Sandboxed Chrome with its own port allowed     up in 1 s, loaded example.com
```

The self-check that guards the bundle-id validation was run with the
validation removed and failed (`# pass 12`, `# fail 1`).

### Round after review pass 7

Review pass 7 found that a bot could remove its own folder and put a link in
its place, so the server would build the next sandbox around wherever the
link pointed. After the fix, Forge was asked to try it:

```text
rm -rf <files>/<forge>            the folder itself: Operation not permitted
mv <files>/<forge> <...>.x         Operation not permitted
ln -s $HOME <files>/<forge>.y      Operation not permitted (outside its folders)
rm -rf <engines>/<forge>           the folder itself: Operation not permitted
save_file hq-swap-probe.txt        saved inside <files>/<forge>
```

Checked from outside: both folders are still plain folders, nothing was
written to the home folder, and `~/.zshrc` matched its earlier checksum.
Afterwards Scout's browser restarted, browsed example.com, the Library
listed Forge's files and a download returned the 5-byte file.

The new self-check that swaps a folder for a link failed with the
folder-pinning rule removed (`# pass 13`, `# fail 1`).

### Round after review pass 8

Review pass 8 found that deleting a bot used the unsandboxed server's
recursive delete, which a process the bot left running might redirect.
After the fix, a temporary bot was created, its gateway and browser were
started, and links to a folder of the operator's (`~/hq-keep-dir`, holding
`precious.txt`) were planted in its working folder, Hermes home and browser
profile, at the top and one level down. Then the bot was deleted from the app:

```text
DELETE /api/bots/<id>                       {"ok":true}
its files, engines and profiles folders     No such file or directory (all three)
~/hq-keep-dir/precious.txt                  keep   (unchanged)
process records for the bot in <data>/run   none left
listeners on its gateway and browser ports  none
```

The race itself, a process swapping a folder during the delete, was not
reproduced. The delete now runs inside the sandbox, where it cannot reach
past the folder.

Not tested: a deliberate attempt to break out of `sandbox-exec` itself, and
the memory-edit race itself (the change removes it by design: the edit runs
inside the bot's sandbox).

## Not run

- Any OpenAI call: voice, voice preview, dictation. No key was present.
- Composio connected apps and xAI `x_search`. Both are switched off in code.
- All five browsers at once. Five gateways and two browsers ran together.
- Windows and Linux. Bots do not start there without `HQ_UNCONTAINED=1`.
- The CI workflow. It runs when the pull request opens.
