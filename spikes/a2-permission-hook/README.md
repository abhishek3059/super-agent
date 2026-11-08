# Spike A2: answer Claude Code permission prompts from outside the terminal

Throwaway spike for assumption A2 in [product direction](../../docs/product/direction.md#assumptions-to-test-riskiest-first).
Not product code. Node 22 standard library only, no dependencies.

## Pieces

| File | Role |
| --- | --- |
| `hook.mjs` | Claude Code `PermissionRequest` hook. Forwards the request, prints the decision. Prints nothing on any error, so Claude Code keeps its normal flow; it never allows on failure. |
| `server.mjs` | Loopback-only server on `127.0.0.1:7717`. Bearer token (written to `~/.super-agent/spike-token`, mode 0600), Host allowlist, rejects any browser `Origin`, 64 KB body cap. Holds each request open until allow/deny or 110 s timeout. |
| `approve.mjs` | Approver CLI: `list`, `allow <id>`, `deny <id> [reason]`. |
| `selftest.mjs` | End-to-end check without Claude Code. |

## Run it

```bash
node spikes/a2-permission-hook/selftest.mjs
node spikes/a2-permission-hook/server.mjs
```

Hook settings (pass with `claude --settings <file>` or add to `.claude/settings.json`):

```json
{"hooks":{"PermissionRequest":[{"matcher":"Bash","hooks":[{"type":"command","command":"node /abs/path/spikes/a2-permission-hook/hook.mjs","timeout":120}]}]}}
```

Then, from another terminal: `node spikes/a2-permission-hook/approve.mjs list`.

## Results (2026-11-07, Claude Code 2.1.318, macOS, headless `claude -p`)

| Test | Result |
| --- | --- |
| Self-test: allow, deny, timeout, server down, no token, bad Host, browser Origin, bad decision | pass |
| Read-only command (`echo`) | No `PermissionRequest` fired; Claude Code auto-allowed it. The hook only sees calls that need a decision. |
| `touch` + allow from the CLI | Request appeared about 5 s after launch (includes model time); command ran, file created |
| `touch` + deny with reason | Command blocked; Claude received the reason text and did not retry |

**Verdict: A2 holds.** Permission prompts can be captured and answered from
outside the terminal, using only documented hooks.

## Not tested yet

- Interactive (TTY) sessions: does the terminal prompt also show, and which answer wins?
- Real timeout path: per the docs, headless runs deny when no hook decides; interactive runs should fall back to the prompt.
- Tools other than Bash (Edit, Write, MCP tools).
- OpenCode and Codex equivalents.
- Low-risk classification for voice approval (assumption A4). Today every decision here is a deliberate human action in the CLI.
