# Jarvis HQ: local run record

The [2026-11-17 approval](../approvals/jarvis-hq-dec-23-approval.md) closes R-H.1
and authorizes the [synthetic OpenAI voice check](jarvis-hq-voice-check.md).
The record grew over several sessions: the 2026-11-17 runs come first, the
2026-11-19 security round last. Each section names its own date.

| Field | Value |
| --- | --- |
| Date | 2026-11-17 to 2026-11-19 |
| Host | macOS, Node 22.22.3, Hermes Agent v0.22.2, Google Chrome |
| Model | The operator's Hermes default (`nvidia/nemotron-3-super-120b-a12b`, provider `nvidia`) |
| Run by | Claude Code (`claude-fable-5-2`, later `claude-opus-5-5`) for `jeevesh2515`, against a scratch data folder with synthetic requests |
| App | [apps/hq](../../apps/hq/README.md) |

Output below is copied from the terminal. Bot ids are omitted.

## Checks

```text
$ npm run typecheck        (no errors)
$ npm test                 (2026-11-19, at 578fb52)
# pass 30
# fail 0
$ npm run build            (no errors)
$ npm audit
found 0 vulnerabilities   (2026-11-19, at e71f06f)
$ npm run check            (repository root)
"errors": 0
roadmap self-test: all checks passed
```

The self-checks grew from 6 to 30 during review and containment work, with
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

### Round after the independent security review (R-H.4)

The [security review](../reviews/jarvis-hq-security-review.md) found that
bots could reach every loopback service through `::ffff:0.0.0.0`, and could
write the operator's preferences. After the fixes, on 2026-11-19, with real
bots and the real model:

```text
ports:  8787 app  8788 bots' tool endpoint  8789 bots' internet proxy
proxy -> https://example.com              200
proxy -> http://127.0.0.1:8787/api/health 403
tool port /api/health                     404 (no app API there)

Jarvis -> Scout: open https://www.iana.org/domains/reserved, report heading
  Scout: "IANA-managed Reserved Domains"; Jarvis reported it.

Forge's own shell, no proxy:
  http://[::ffff:0.0.0.0]:8787/api/health     000 exit=7
  http://[::ffff:0.0.0.0]:8650/health         000 exit=7
  http://[::ffff:0.0.0.0]:9301/json/version   000 exit=7
  http://127.0.0.1:8787/api/health            000 exit=7
  http://127.0.0.1:8651/health                000 exit=7
  http://127.0.0.1:9302/json/version          000 exit=7
Forge through the proxy:
  loopback 000 (refused)    https://example.com 200
  defaults write com.hqlive.canary            Could not write domain (exit 1)
  ls /private/var/tmp                         Operation not permitted
outside: defaults read com.hqlive.canary      Domain not found
```

Not tested: a deliberate attempt to break out of `sandbox-exec` itself, and
the memory-edit race itself (the change removes it by design: the edit runs
inside the bot's sandbox).

## Not run

- Any OpenAI call in these runs: no key was present. The synthetic live voice
  run passed on 2026-11-19 ([voice check record](jarvis-hq-voice-check.md#live-run-2026-11-19)).
  Voice preview and dictation are still not run.
- Composio connected apps and xAI `x_search`. Both are switched off in code.
- All five browsers at once. Five gateways and two browsers ran together.
- Windows and Linux. Bots do not start there without `HQ_UNCONTAINED=1`.
- Nothing further for CI: the Jarvis HQ workflow (typecheck, self-checks,
  build on macOS) runs on every push to PR #56 and passed on `e71f06f` and
  `f96184e`.

## Provider workspace recovery, 2026-11-20

A synthetic HQ workspace used a dedicated Hermes seed with the NVIDIA
Nemotron Ultra hosted model and an empty fallback list. The seed had no
Gemini, local model or OpenAI platform route. HQ opened on 127.0.0.1.

The first agent call failed before inference. The isolated seed could not
read the shell launcher's target, and the default Chrome debugging port was
already in use. The retry used the real launcher, explicit read-only runtime
paths and a separate browser port range.

Hermes v0.23.3 still could not start. Its state store checks the home
directory with `os.access`. The sandbox now allows the operation needed by
that check. The macOS tests verified that a process still cannot rename or
remove its root, or read the HQ session secret or another bot's folder.
The same Hermes release also requires an additional private listener. HQ
still grants one fixed TCP listener per bot, so that release remained
incompatible with this setup.

The workspace switched to an isolated copy of the previously tested Hermes
v0.22.2 source with locked dependencies and a Homebrew Python environment.
The live check started the loopback Hermes gateway on port 8650. A
synthetic Jarvis chat returned the expected `READY` through hosted NVIDIA
Nemotron Ultra. The first handoff had no HQ tools because the runtime lacked
Hermes' optional MCP dependency. After installing it from the same lockfile
and restarting Jarvis, the HQ tool recorded a Jarvis-to-Scout handoff. Scout
returned `TEAM_READY`, and Jarvis received and reported the result. Atlas and
Quill also completed synthetic replies. Forge's first attempt hit a Python
import lock while starting the OpenAI SDK used by the NVIDIA transport. The
local launcher in the operator's Hermes workspace (outside this repository)
now imports those SDK types before starting the gateway. After
restarting Forge, its synthetic reply matched too. All five workers returned
the expected text. HQ build passed and all 30 HQ tests passed. OpenAI subscription voice and Claude Pro
through HQ: not run.

## Hosted model picker verification, 2026-11-20

The local preview's NVIDIA catalog reported 37 entries, including embedding
and safety routes, while disconnected provider entries still appeared in the
old picker. The revised picker kept the connected hosted chat choices and
disabled unconnected providers. It excluded Gemini and Ollama and rejected
direct engine-setting requests for Gemini, an embedding model and a
disconnected OpenAI Codex route with HTTP 409.

In Chrome, the test selected hosted NVIDIA Nemotron 3.5 Lightning from
the Model dropdown, saved it and reloaded the page. HQ kept the selection.
Jarvis returned the exact synthetic reply `SWITCH_READY`. The Hermes session
record named the selected model. The original
Nemotron Ultra selection was restored. The preview reported OpenAI voice
enabled. The separate voice connection and operator report are in the
[voice record](jarvis-hq-voice-check.md#preview-openai-connection-2026-11-20).

HQ typecheck, build, 33 self-checks and repository checks passed. OpenAI
Codex and Anthropic worker inference and account sign-in in HQ: not run.

## Desktop, browser bar and sign-in controls, 2026-11-20

Run on the operator's Mac with the provider-test workspace and a dedicated
Hermes seed (`HERMES_HOME_PRIMARY`). Two browser passes in Playwright
Chromium, run by an agent session, not by a person.

- Jarvis and Scout opened on the new desktop: clock, date, owner greeting,
  bot name and label, search box and eight app tiles. The Files tile showed
  the bot's working folder as a `file://` listing.
- The browser bar navigated to an address, turned plain text into a Google
  search, and opened, switched and closed tabs. Back, forward, reload and
  home worked. Tab titles showed `&` and not `&amp;`. Google answered the
  search with its "unusual traffic" page, which is outside HQ.
- In one pass the tab strip reordered once and could not be reproduced. The
  likely cause was an empty poll result resetting the order. The strip now
  ignores empty results. Not re-tested after that change.
- Engine settings listed connected and unconnected providers. A malformed
  Claude key was refused with a format message and the field was cleared.
- "Sign in with ChatGPT" opened OpenAI's sign-in page and Cancel restored the
  button. A completed ChatGPT sign-in, a saved real Anthropic key, and worker
  inference through either: not run.

HQ typecheck, build and 40 self-checks passed.

## Read access, skills and accounts, 2026-11-20

Same workspace, with `HQ_READ_DIRS` set to `~/dev` and `~/Documents`. An
agent session chatted with Jarvis (NVIDIA Nemotron Ultra) in Playwright
Chromium and checked each answer from a shell.

- `system_info` reported macOS 27.2, Apple M5, 16 GB and the top processes,
  matching `sw_vers` and `sysctl`.
- Jarvis listed the 17 top-level folders in `~/dev`, matching `ls`.
- A write to `~/Documents` failed with "Operation not permitted" and no file
  was created. Listing `~/.ssh` failed the same way. Jarvis blamed macOS
  privacy settings and suggested Full Disk Access. The persona now says the
  refusal is HQ's sandbox and forbids that advice. Not re-tested after that
  change.
- Jarvis named five real skills. One came from `~/.hermes/skills`, not from
  `~/.claude/skills` as asked.
- Jarvis made a `qa-hello` skill and saved it to `shared-skills`. Scout then
  found it there. The test skill was removed afterwards.
- After the maintainer's real ChatGPT sign-in, the Accounts section showed
  ChatGPT as connected and the Provider list showed OpenAI Codex as
  connected. Worker inference through OpenAI Codex: not run.

HQ typecheck, build and 44 self-checks passed.

This run sent real operator data (the `~/dev` folder names, `system_info`
output and skill names) to hosted NVIDIA Nemotron. DEC-23 allows synthetic
data only until R-A.2 is decided. The shared reviewer flagged it. The read
folders, skill folders and `system_info` are now off by default, and
`HQ_READ_DIRS` was removed from the test workspace the same day.

## Semantic memory, 2026-11-21

Roadmap item R-H.8 (per-bot semantic memory in local PostgreSQL + pgvector,
embeddings from local Ollama). Built and checked by an agent session on the
maintainer's Mac with synthetic text only.

What ran:

- Services: `pgvector/pgvector:pg17` (PostgreSQL 17.10, pgvector 0.8.6) on
  `127.0.0.1:5433`, and Ollama with `nomic-embed-text` on `127.0.0.1:11434`.
- `npm test` from `apps/hq` without a database: 54 tests, 49 passed, 5 skipped
  (the SQL and real-embedding tests, skipped by design), 0 failed.
- The same with `HQ_MEMORY_TEST_DB_URL` set to the local database: 54 tests,
  54 passed, 0 skipped. This ran the real schema creation (extension, table,
  hnsw index, bot index), save and dedupe, cited search, the no-match message,
  bot and user scoping, Hermes entry sync in and out, the limit cap of 10, and
  deleting a bot's rows. The test rows used bot ids starting with `bot_test_`.
  `select count(*) from hq_memories` returned 0 afterwards.
- `npm run typecheck` and `npm run build` from `apps/hq` passed.
- `docker compose -f docker-compose.memory.yml config` rendered with
  `POSTGRES_PASSWORD` set and failed with "required variable POSTGRES_PASSWORD
  is missing a value" without it. The compose file was not started here: the
  database above was already running.
- `npm audit` from `apps/hq`: found 0 vulnerabilities. New packages: `pg`
  8.23.1 (MIT, published 2026-09-30) and `@types/pg` 8.23.1 (MIT, published
  2026-08-17), exact pins. Their runtime dependencies are MIT or ISC and all
  were published more than 14 days ago.

Threshold tuning with the real model. The score is cosine similarity between a
`search_query:` embedding and `search_document:` embeddings. Best match per
query over eight stored facts:

- Related questions (10): 0.549, 0.614, 0.624, 0.681, 0.684, 0.705, 0.750,
  0.777, 0.778, 0.797.
- Unrelated questions (12): 0.476, 0.517, 0.519, 0.536, 0.537, 0.546, 0.554,
  0.565, 0.584, 0.602, 0.622, 0.710.

The ranges overlap, so no threshold is clean. `MIN_SIMILARITY` is 0.6. It
keeps 9 of 10 related questions and passes 3 of 12 unrelated ones ("tallest
mountain on Earth" 0.602, "capital of Australia" 0.622, and "the user's home
address" 0.710, which is close in topic to the stored facts). A higher value
would drop correct paraphrases ("which hosting provider did we pick" 0.624).
The integration test asserts the cases that clear the margin, not those three.

Not run:

- A live chat turn through a real bot: whether a model calls `memory_search` (run later the same day, see "Semantic memory through a live bot" below)
  first, cites `[mem:...]`, and says "not in memory" when nothing comes back.
  The persona lines and tool descriptions exist, but model behavior is unchecked.
- The tools reached through a bot's MCP endpoint (`/mcp/<botId>`). Only the
  functions behind them and the tool list were tested.
- Deleting a bot through the API with memory on: `forgetBotMemory` was tested
  directly, not through the delete route.
- Windows and Docker Desktop with WSL2.
- An existing bot's `SOUL.md` is rewritten when its engine next starts, not
  at once.

## Semantic memory through a live bot, 2026-11-21

Jarvis (NVIDIA Nemotron Ultra), memory on, synthetic facts only, driven by
an agent session in Playwright Chromium.

- First pass: the model ignored the persona line, saved facts with Hermes'
  own memory tool and never called `memory_search`, so nothing went through
  pgvector and nothing was cited. The app now runs the search itself before
  each user turn, after syncing the bot's Hermes notes into pgvector.
- Second pass: "codename" was answered "Bluefin [mem:003fe3b2]" from a
  synced Hermes note. A never-stored fact was answered "not in memory"
  without a guess. A new fact saved through Hermes was recalled with a
  citation on the next turn. A general-knowledge question was refused as
  "not in memory", so the rule now applies only to questions about the
  user and past work. The third pass is below.
- Memory text is embedded locally by Ollama and stored in a local Postgres.
  Retrieved entries go to the bot's hosted model with the turn.
- Grounding is enforced by what the app attaches to each turn and by an
  instruction. The app cannot stop a model from ignoring it.
- Third pass, after that change: "capital of Australia" was answered
  "Canberra", marked as general knowledge, and "codename" was answered
  "Bluefin [mem:543286d4]".

HQ self-checks at 454088e: 56 passed with the memory database, and 49
passed with 7 skipped without it.
