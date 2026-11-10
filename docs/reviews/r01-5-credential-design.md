# R-01.5 credential design review

| Field | Value |
| --- | --- |
| Roadmap item | R-01.5, credential design written and independently reviewed (RT-A05 obligation, security finding LOW-01) |
| Design reviewed | [Voice foundation design](../design/voice-foundation.md), revision 2, section 7 (with section 9 for context) |
| Design author | OpenCode, architect-free (GLM-5.3-Flash Free), for `abhishek3059` |
| Reviewer | Claude Code security-auditor subagent (Anthropic Sonnet), read-only, run on 2026-11-10 for `jeevesh2515`. Independent of the design author's tool and model. |
| First verdict | **ACCEPT WITH CONDITIONS** (design stage only) |
| Final verdict | **ACCEPT** (design stage), third pass, 2026-11-10 |
| Revision reviewed after fixes | Revision 2.1, 2026-11-10 (see "Closure" below) |
| Status | Design review only. Nothing is implemented by this record, and R-01.5 is not ticked here; the PH-01 owner ticks it after merge. |

## Verdict summary (first pass)

The core scheme is sound: a 256-bit random token held by the backend, a
constant-time compare, and restart-based rotation and revocation. Two gaps had
to be closed in the design before R-01.5 could be ticked (CR-01 throttling,
CR-02 generation and storage), plus the medium findings below.

## Findings (first pass)

| ID | Severity | Issue | Required change |
| --- | --- | --- | --- |
| CR-01 | HIGH | A global failed-auth counter with a hard cooldown lets any local process lock the user out (5 bad tokens a minute, forever). It gives an attacker no guessing benefit but full control of availability. | Use an increasing delay instead of a hard lockout and keep a valid token always accepted; state the trade-off. |
| CR-02 | MEDIUM | The design said the token lives in the backend environment but not how it is generated or delivered. Environment variables are visible to same-user processes, shell history, and crash dumps. | Specify a generation command, a 0600 file or OS vault outside the repo, the backend reading it at start, and no inline `export` in docs. |
| CR-03 | MEDIUM | Threat model missed other local OS users, same-user processes, browser extensions, shoulder surfing, logs and crash dumps, and DNS rebinding. | Add the actors and mark each in or out of scope. |
| CR-04 | MEDIUM | The recommended cookie flow left the cookie value, server-side store, lifetime, rotation, logout, enrollment CSRF, and enrollment throttling unspecified. SameSite=Strict does not separate localhost ports. | Define the session id, store, lifetime, rotation, and logout; require exact Origin and Host on enrollment and upgrade; throttle enrollment. |
| CR-05 | LOW | Expiry was optional with no default, and its start point was unclear. | Make expiry mandatory with a default, measured from process start, failing closed on bad values. |
| CR-06 | LOW | The current code takes the single session slot before authentication, so unauthenticated clients can hold it for 5 seconds repeatedly. | Authenticate before taking the slot, or cap pre-auth holders separately. |
| CR-07 | LOW | In the minimal flow the token stays in page memory, exposed to XSS and extensions. | Require a strict CSP and zero the token after the first message. |
| CR-08 | INFO | The current code passes `str` to `hmac.compare_digest`, which raises on non-ASCII input. | Compare bytes; test non-ASCII input. |
| CR-09 | INFO | The current code checks only length, so a repeated 32-character string passes. | Add a generation helper and reject low-entropy values. |

Code facts in CR-06 and CR-08 were confirmed by the maintainer's agent in
`apps/api/src/super_agent_voice/app.py` (slot taken at line 80, auth awaited at
line 96; `compare_digest` on `str` at line 106) and CR-09 in `config.py` line 23.

## RT-A05 / LOW-01 obligations (first pass)

| Obligation | First pass |
| --- | --- |
| High-entropy credential | Met in design; generation and weak-value rejection not specified |
| Secure storage | Partly met; delivery path and OS-user exposure missing |
| Expiry | Partly met; optional |
| Rotation | Met (restart) |
| Revocation | Partly met; no runtime revoke for the cookie flow |
| Failed-auth throttling | Not met as written |
| PIN-only rejected | Met implicitly; should be stated |
| Online guessing controls tested | Not yet (implementation, R-01.6) |

## Required negative tests for R-01.6

1. Wrong, empty, short, non-ASCII, non-string, and oversized token: close 1008, no audio accepted, no hint of closeness.
2. Missing or wrong Host or Origin (including `null`, a `localhost` alias, another port): refused before auth.
3. Throttle: five bad tokens add delay; a valid token still succeeds; the counter resets; no timing or message side channel.
4. Pre-auth slot hold: unauthenticated connections cannot starve the real user.
5. Expiry: a token past max age is refused; an unparsable setting fails startup.
6. Cookie flow, if approved: missing, forged, expired, and post-restart cookies; cross-origin WebSocket upgrade; cross-site enrollment POST; HttpOnly and SameSite present.
7. Secret scan: the token never appears in logs, error bodies, URLs, close reasons, or crash output.
8. DNS rebinding: a Host mismatch is refused.
9. A weak token at startup is rejected.

## Not checked by the reviewer

No code was run. Only sections 7 and 9, `app.py`, `config.py`, and the web token
field were read. The rest of the Angular service, sections 6 and 8, the Gemini
key path, and the test suite were not reviewed. Cryptographic parameters were
not checked against a primary source. Whether Starlette logs the Cookie header
or token in any log format is unverified.

## Closure

The design was revised to revision 2.1 and re-reviewed twice by the same
reviewer on 2026-11-10.

| Finding | Final status |
| --- | --- |
| CR-01 throttling lockout | Resolved in design: increasing delay, no hard lockout, a correct token always accepted |
| CR-02 generation and storage | Resolved: `generate-token` helper, 0600 file or Keychain on macOS, owner-only ACL or Credential Manager on Windows, no inline export in docs |
| CR-03 threat model | Resolved: actor table with in and out of scope stated |
| CR-04 cookie flow | Resolved in design; remaining details carried as N3 |
| CR-05 expiry | Resolved: mandatory, default 24 hours from process start, bad values stop startup |
| CR-06 pre-auth slot hold | Carried as an implementation condition with a test |
| CR-07 token in page memory | Resolved: strict CSP required, token zeroed after first message |
| CR-08 `str` compare | Carried as an implementation condition with a test |
| CR-09 weak token accepted | Carried as an implementation condition with a test |

New issues raised on the second pass:

| Finding | Severity | Final status |
| --- | --- | --- |
| N1 pre-auth cap could be filled by failed attempts held during their delay | MEDIUM | Resolved: failed attempts close immediately; the delay applies to the next attempt; test added |
| N2 0600 file does not cover Windows | MEDIUM | Resolved: Windows owner-only ACL or Credential Manager; ACL check added |
| N3 cookie session id expiry, enrollment Origin, enrollment after token expiry | LOW | Carried as an implementation condition |
| N4 Host allowlist differed from section 9 and the code | LOW | Resolved: one exact Host, `127.0.0.1:<port>` |
| N5 accept-fast and reject-slow reveals validity | INFO | Stated and accepted (harmless at 256 bits) |

RT-A05 / LOW-01 at design stage: entropy, storage, expiry, rotation,
revocation, throttling, and PIN-only rejection are met. Online-guessing
controls are **planned, not yet tested**: R-01.6 must run the nine tests above
plus the N1 and N2 tests, and implement CR-06, CR-08, CR-09, N3, and N4.

This closes the design review only. No code changed, nothing was run, and
R-01.5 is left for the PH-01 owner to tick after this record merges.
