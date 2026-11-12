# R-01.F4: single-command Windows voice launcher

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Trigger | Repeated setup failures caused by running relative commands outside the repository and by one service exiting while the other remained visible |
| Scope | Local Windows development launcher only; no provider or deployment change |

[`scripts/start-voice-windows.ps1`](../../scripts/start-voice-windows.ps1)
derives the repository root from `$PSScriptRoot`, so the caller's current
directory does not matter. It:

1. refuses to reuse a stale service on required port 8000 or 4200;
2. creates the existing temporary Python environment when absent;
3. installs the locked backend and frontend dependencies;
4. temporarily removes provider and token environment overrides before starting services;
5. generates a fresh file-backed local token;
6. starts the backend with the reviewed loopback and WebSocket bounds;
7. waits for the loopback health check before starting the frontend; and
8. stops the backend when the frontend exits.

The caller's original provider, token, and `PYTHONPATH` environment values are
restored before the launcher returns.

The script does not print or copy the token, contact Gemini, widen the Host or
Origin allowlists, or send microphone audio anywhere except the local fake
adapter.

## Verification

Verified on Windows on 2026-11-12:

| Check | Observed result |
| --- | --- |
| PowerShell parser | PASS with no syntax errors |
| Occupied port 8000 | PASS; launcher failed before installation with `Port 8000 is already in use` |
| Occupied port 4200 | PASS; launcher failed before installation with `Port 4200 is already in use` |
| Launch from outside the checkout | PASS from `C:\Users\user`; backend bound to `127.0.0.1:8000`, `/health` returned `status: ok`, and the frontend served `http://127.0.0.1:4200` |
| Locked installs | PASS; pip used `apps/api/requirements.lock`; `npm ci --ignore-scripts` installed 243 packages and reported 0 vulnerabilities |
| Frontend exit cleanup | PASS; the test deliberately stopped the frontend listener, the launcher reported that nonzero frontend exit, and backend process 6384 terminated within 15 seconds |

The lifecycle check used no microphone input and made no provider request. It
printed the token file path, not the token. No listener remained on port 8000
or 4200 after the check.
