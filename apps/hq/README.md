# Jarvis HQ

Jarvis is the voice entry point for five local specialists: Scout, Forge,
Quill, Atlas, and Ops. Each runs in a separate Hermes workspace and has a
headless browser and a DevTools view. This experimental scope is covered by
[DEC-23](../../descisions.md#dec-23) and the
[maintainer record](../../docs/approvals/jarvis-hq-local-team.md).

Adapted from [Bot HQ](https://github.com/nickvasilescu/bot-hq) (MIT). See
[third-party notices](THIRD_PARTY_NOTICES.md).

## Run it

HQ requires Node.js 22 or newer. Managed workers also require macOS, a
Hermes installation, Chrome, and a trusted local model endpoint compatible
with the configured Hermes adapter. Set `HQ_LOCAL_MODEL` and
`HQ_LOCAL_MODEL_PORT` for that endpoint. Use an inference-only service on
that port. Worker processes can connect to it directly.

```bash
cd apps/hq
npm ci
npm run build
npm run jarvis
```

The launcher serves `http://127.0.0.1:8787` and opens a signed-in window.
To run the shared ledger bridge, start the Python voice backend on
`127.0.0.1:8000` and set the same `SUPER_AGENT_HQ_LEDGER_TOKEN` in both
servers. Use a random base64url token of at least 43 characters. Keep it
out of browser configuration and worker environments. A role polls only
while its corresponding managed bot is available. Existing installations
need a managed bot with the corresponding specialist name for each role.

## Voice

The voice path requires `HQ_SYNTHETIC_VOICE=1` and `OPENAI_API_KEY` in
the HQ server environment or its private `.env`. Enable it only for a
synthetic session. The browser sends audio to OpenAI when voice is enabled.
The assistant asks the ledger to queue work through `delegate_task`, and
the selected specialist shows its execution in the dashboard. Voice confirms
admission. The worker writes a receipt and its status appears in the
specialist's dashboard.

## Where things live

HQ state lives under `~/.super-agent/hq` in a directory with mode 0700.
Each worker has `engines/<botId>/workspace` for deliverables and
`engines/<botId>/runtime` for its Hermes state. Profiles are under
`profiles/<botId>`. Legacy paths stay in place. The shared job ledger is
owned by the Python backend.

## Security boundary

The server checks Host and Origin and has a separate owner session. The
ledger API refuses browser Origins and requires a separate server bearer.
Managed processes have a macOS sandbox, no fallback launcher, and a filtered
environment. Only the worker's expected local ports and filesystem roots are
listed in its sandbox. Credentials and configuration from the operator's
Hermes installation are not copied. Chrome runs inside the HQ macOS
sandbox with its nested Chromium sandbox disabled. The outer profile blocks
Internet connections from the browser. The local gateway's bot-scoped bearer
is separate from the owner and ledger bearers.

The default experiment uses synthetic input. The synthetic local fixture verifies Chrome and Hermes with an inference stub.
Live OpenAI voice and production model use need separate evidence before the
roadmap runtime items can close. See the
[local run record](../../docs/implementation/jarvis-hq-local-run.md).

## Develop

```bash
npm run typecheck
npm test
npm run build
```
