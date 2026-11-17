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

## What to do differently

- Check for an existing licensed implementation before building in parallel
  on several branches.
- Test handoffs with the weakest model the operator actually uses.

## Still unknown

- Whether the OpenAI Realtime call works end to end. It has not been run.
- Memory use with all five gateways and five Chromes running.
- How Hermes workers behave under prompt injection from pages they read.
  They are not contained.
