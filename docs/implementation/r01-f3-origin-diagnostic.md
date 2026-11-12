# R-01.F3: actionable local Origin diagnostic

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Trigger | Windows microphone test stopped at `Local voice connection failed` before the browser permission prompt |
| Scope | Local connection diagnostics only; no Origin-policy or provider change |

The frontend can load through `http://localhost:4200` because that name resolves
to loopback, but the reviewed backend policy accepts only the exact
`http://127.0.0.1:4200` Origin. A rejected WebSocket handshake previously showed
only `Local voice connection failed`, which did not identify either likely
operator correction: use the exact URL or start the backend on port 8000.

The fixed frontend message names both checks. The run guide and microphone
handover now warn that `localhost` is not an accepted alias. The backend
allowlist remains unchanged; hostile, null, and alternate Origins still fail
closed before microphone access.

## Reproduction and verification

Live local probes against the running Windows services produced:

- health request to `127.0.0.1:8000`: HTTP 200, fake provider;
- WebSocket with Origin `http://127.0.0.1:4200` and the token file: accepted,
  `session.ready` returned;
- WebSocket with Origin `http://localhost:4200`: HTTP 403 before acceptance;
- no microphone or provider audio was used by these probes.

Automated verification on Windows passed: the frontend service and
playback-epoch suites remained at 39 and 8 cases, with the existing pre-ready
case also asserting the actionable failure message. The production build
completed at 116.07 kB, and the repository/roadmap check reported 0 errors.
