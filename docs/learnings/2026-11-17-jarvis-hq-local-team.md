# Jarvis HQ: adapting Bot HQ to run locally

| Field | Value |
| --- | --- |
| Date | 2026-11-17 |
| Scope | `apps/hq` local multi-bot workspace |
| Evidence | [App README](../../apps/hq/README.md), [approval record](../approvals/jarvis-hq-local-team.md) |

## What happened

The multi-bot work was spread over several unmerged branches with two
separate OpenAI implementations and no running product. Bot HQ already had
the product shape the maintainer asked for, under MIT. We adapted it to run
on one Mac: local Chrome per bot in place of a cloud computer, a DevTools
screen relay in place of VNC, OpenAI Realtime in place of xAI voice.

## What we learned

- A handoff that depends on the worker model calling `send_to_bot` to reply
  fails with smaller models. The worker answered in its own chat and the
  asking bot heard nothing. The app now returns the result or the failure
  itself. A reply never triggers another reply, which stops ping-pong.
- A headless Chrome tab reports itself hidden. It paints nothing for a
  screencast, and input sent to it never returns. `Page.bringToFront` alone
  did not fix it. Focus emulation plus an active lifecycle state did.
- Hermes' browser helper listens on a Unix socket under `BH_HOME`. A long
  data path broke it. Keep that path short.
- Headless Chrome reserves 87 pixels of window height. A 1280x800 window
  gives a 1280x713 page.
- A cached `index.html` kept serving an old script after a rebuild. The page
  is now sent with `Cache-Control: no-cache`.
- Bot HQ's avatars and icons are not covered by its MIT license. They were
  left out and replaced.
- The first review found a script-injection hole in an inherited callback
  page that needs no sign-in. On a loopback app with shell-capable workers
  that is code execution from one link. Adopted code needs the same review
  as new code.
- A chat message cannot suspend a security invariant. It needs a decision
  entry and a rule edit, which became DEC-23.

- Containment on macOS did not need a second user account. `sandbox-exec`
  with a deny rule on the home folder and narrow allows was enough to keep a
  bot's shell and browser out of the operator's files.
- Chrome will not start if Launch Services is closed to it, and it cannot
  start its own inner sandbox inside an outer one. It needs `--no-sandbox`
  there, and the outer profile then covers its child processes.
- A self-check that used a data folder outside the home folder showed the
  session secret was readable there. Closing "the home folder" was the wrong
  rule; the data folder has to be closed by name.
- Anything that runs Hermes on a bot's home must run inside that bot's
  sandbox, because the bot can write the home. The in-app sign-in was
  removed for that reason.

- Sandboxing the agent was not enough. The server that works for it is
  outside the sandbox, so every file it reads or writes in the agent's folder
  and every pid it takes from there is a way out. The fix is to treat those
  folders as hostile: write fresh, never follow links, keep state elsewhere.
- Chromium ignores `TMPDIR` for its profile lock on macOS and puts it in the
  per-user temporary folder, with a socket path limit of 104 bytes.

## What to do differently

- Check for an existing licensed implementation before building in parallel
  on several branches.
- Test handoffs with the weakest model the operator actually uses.

## Still unknown

- Whether the OpenAI Realtime call works end to end. It has not been run.
- Memory use with all five gateways and five Chromes running.
- How Hermes workers behave under prompt injection from pages they read.
  They are sandboxed, but they keep their own keys and internet access.

## Maintainer decision

Record approval for the local exception and the US$5 monthly OpenAI cap
in the [R-H.1 record](../approvals/jarvis-hq-dec-23-approval.md). Keep live
voice evidence separate from approval.

## Checking voice and startup

A synthetic audio clip still needs a fresh HQ instance. The live session
prompt can carry the owner identity, chat and memory from an existing
workspace. The [voice probe](../implementation/jarvis-hq-voice-check.md)
checks both boundaries. Verify stale process cleanup before binding the
server and keep PID records if identity checks fail.
