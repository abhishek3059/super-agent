# R-01.6: acceptance of the pre-auth lockout risk (finding F2)

| Field | Value |
| --- | --- |
| Roadmap item | R-01.6, independent security review of the implemented boundary |
| Date | 2026-11-12 |
| Finding | F2 in the [R-01.6 security review](../reviews/r01-6-security-review.md): a local process that forges the Origin header can hold all 4 pre-auth sockets by reopening idle connections, and the real user is refused (close 1013) for as long as it runs. Measured: 0 successful logins in 30 seconds. |
| `jeevesh2515` | **Accepted, 2026-11-12**, in chat with Claude Code (`claude-sonnet-5-5`), which recorded it at their instruction, in answer to a question that stated the measurement and the condition below |
| `abhishek3059` | **Accepted, 2026-11-12**, by approving and merging [PR #32](https://github.com/abhishek3059/super-agent/pull/32), the acceptance route stated in this record. |

## What is accepted

For a **single-user development path on a loopback address** only. The
attacker must be a non-browser process on the same machine that sends the
expected Host and Origin headers, so any other OS user on the machine qualifies.
A web page cannot do it.

## Condition

The risk must be removed before any of the following: a multi-user machine, an
always-on or remote host (PH-06, PH-08 to PH-10), or a Gemini or job-control
capability that matters enough to deny. The fix named in the review is to
authenticate during the WebSocket handshake (a token in
`Sec-WebSocket-Protocol` checked before accept, or the cookie flow) so that no
unauthenticated socket is ever accepted.

## Not accepted by this record

This record accepts F2 only. It does not accept, and the review lists as still
open: F5 (token sent to whatever holds the port), F6 (no check that the socket
is the loopback one), N2 (Windows owner-only ACL), the token directory's mode,
and the missing `frame-ancestors` protection. The reviewer recommends a tracked
roadmap item for N2 before Windows use is called supported and a gate for F5
before Gemini or job control is wired into a session. Neither item exists in
the roadmap yet; adding them needs a roadmap pull request approved by both
maintainers.
