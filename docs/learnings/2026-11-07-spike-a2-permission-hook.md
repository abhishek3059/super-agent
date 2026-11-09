# Spike A2: answering permission prompts from outside the terminal

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Evidence | [Spike A2 README](../../spikes/a2-permission-hook/README.md) |

## What happened

A Claude Code `PermissionRequest` hook forwarded real permission prompts to a
loopback server. Allow and deny from a separate command took effect in headless
runs (Claude Code 2.1.318).

## What we learned

- Read-only commands such as `echo` never reach the hook. Claude Code approves them itself, so the hook only sees requests that really need a decision.
- A hook that prints nothing and exits 0 leaves the normal permission flow in place. That is the safe failure mode: on any error the hook must print nothing, never "allow".
- The deny reason field is `message`, not `reason`. The deny text reached the model, which did not retry.
- Session experience, not in the spike README: the first version of the server rejected every request because the Host allowlist was built from the requested port (0 in tests) instead of the bound port, and the self-test exposed it. The fix, marked by a comment in `server.mjs`, builds the allowlist after the server is listening.

## What to do differently

Keep the fail-closed rule from [AGENTS.md](../../AGENTS.md) section 5 in every approval path, and keep a self-test that covers timeout and server-down cases.

## Still unknown

Interactive (terminal) sessions, the real timeout path, tools other than Bash, and OpenCode or Codex equivalents are not tested.
