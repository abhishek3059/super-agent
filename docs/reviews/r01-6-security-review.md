# R-01.6 independent security review: implemented local boundary

| Field | Value |
| --- | --- |
| Roadmap item | R-01.6, independent security review of the implemented boundary: authentication, Host, Origin, CORS, WebSocket, CSRF, backend-only secrets |
| Date | 2026-11-12 |
| Reviewer | A `claude-opus-5-5` security-auditor subagent that did not write the code. It ran probes against a real uvicorn server and mutation tests on a copy of the source. |
| Reviewed | Branch `feat/ph-01-gemini-live`, code of commit `5de7293` (the next commit changed only documents) |
| First verdict | **ACCEPT WITH CONDITIONS**. C1, C2, and C3 blocked the tick; the other findings did not. |
| Closure | See "Closure" below. Everything on this page except the first verdict and the findings text is the coordinating agent's record of what it changed. |
| Reviewer scores | Correctness 8, security 7, honesty 7, scope 9, clarity 8, average 7.8 (before the fixes below) |

## Findings and what was done

| ID | Severity | Finding | Status |
| --- | --- | --- | --- |
| F1 | MEDIUM | At `--log-level debug` uvicorn logs the first WebSocket frame, which contains the token. Reproduced by the reviewer with a 32-character token (whole token logged) and re-checked by the coordinating agent on the pinned versions (uvicorn 0.54.0, websockets 17.3): the frame is truncated but 15 of 43 characters are logged. The TestClient secret test could not see this. | **Fixed (C1).** `create_app` refuses to start when `uvicorn.error` or `websockets` is enabled for DEBUG. Tests: two logger cases, plus a real uvicorn server at `info` (token absent from the log) and at `debug` (exits non-zero, token absent). |
| F2 | MEDIUM (LOW for one user on one machine) | A local process that forges the Origin header can hold all 4 pre-auth places by reopening idle sockets. Measured: 0 successful logins in 30 s, at about 0.8 connections per second. A shorter auth timeout does not help. | **Not fixed. Documented (C3).** Design section 7 now says so plainly. Needs the maintainers' acceptance for a loopback development path; must be fixed (handshake-time authentication or the cookie flow) before any multi-user or always-on host. |
| F3 | LOW | Before authentication uvicorn buffers up to 16 MiB per message and 32 queued messages. The reviewer drove the server to 519 to 637 MiB. | **Mitigated.** The documented launch command adds `--ws-max-size 65600 --ws-max-queue 4`. A real-server test sends a 70,000-byte frame and passes only with those flags (verified: it fails without them). The flags are a launch convention; the application cannot enforce them. |
| F4 | LOW | No Content-Security-Policy anywhere, although design CR-07 requires one. | **Fixed (C2).** `index.html` carries `script-src 'self'` and `connect-src` for the backend; production no longer inlines critical CSS, so the build has no inline script. Checked in a real browser on the production build and on the dev server: the page renders, the Vite reload socket connects, and an injected inline script is blocked. Inline styles stay allowed because Angular injects them. |
| F5 | LOW | The browser sends the token to whatever process holds port 8000 (port squatting by another local user). Reasoned only. | **Open.** Fix is challenge-response (server nonce, client sends an HMAC). Low impact while the adapter is the fake echo; raise before wiring Gemini or jobs into the session. |
| F6 | LOW | The loopback-only bind is enforced only by the documented launch command; with `--host 0.0.0.0` only the token protects the server. Reasoned only. | **Open.** A socket-address check was tried and reverted: the test client always reports the server as `testserver:80`, so it could not be tested without invasive changes. |
| F7 | LOW | Mutation: removing the message-type check left all tests passing. | **Fixed.** A correctly tokened `capture.mute` first message is now a test case. |
| F8 | INFO | Design text said failed attempts "close immediately", and called the starvation a "residual window". | **Fixed (C3).** Both statements corrected in design section 7; the R-01.5 review record carries dated implementation notes. |
| F9 | INFO | Expiry is measured from process start, so a restart makes a stolen token valid again until `generate_token` runs. | Documented, unchanged. |
| F10 | INFO | Duplicate `Host`: first value wins; duplicate `Origin`: rejected by the library. Browsers cannot send duplicate `Host`. | No change. |
| F11 | INFO | The throttle does not bound a parallel attacker once the 8 delay places are full. | No change; consistent with its stated purpose. |
| F12 | INFO | The token-file check followed symlinks and ignored the parent directory's mode. | **Symlinks fixed** (`lstat`, test added). Parent-directory mode and the Windows ACL (N2) stay open. |

## Closure of the three blocking conditions

- **C1 (token in logs):** F1 above.
- **C2 (CSP):** F4 above.
- **C3 (documentation):** F2 and F8 above.

The reviewer has been asked to confirm that these three are closed. Its answer
is recorded in the next section.

## Confirmation

Pending at the time of writing. Roadmap item R-01.6 is not ticked until this
section records the reviewer's confirmation.

## What was not checked

From the reviewer: library versions other than the locally installed
fastapi 0.138.1, uvicorn 0.49.0, websockets 15.0.1, and starlette 1.3.1 (the
coordinating agent re-checked F1 on the pinned versions only); Windows (N2); a
browser run of the full session; `npm audit` and `pip-audit` (run separately:
0 vulnerabilities each on 2026-11-12); live Gemini paths; the alternative
`wsproto` transport; raw-frame slowloris (bounded by the 5-second wait by
reasoning).

From the coordinating agent: the cookie flow and its N3 items do not exist and
were not reviewed; the F3 memory figures were not re-measured with the new
flags; the CSP was checked in one browser (the one `ego-browser` drives), not
Safari or Firefox.
