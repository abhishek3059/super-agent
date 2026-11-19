# R-01.F9: mutual handshake proof before any credential is sent

| Field | Value |
| --- | --- |
| Roadmap item | R-01.F9, a fix item under PH-01 (roadmap rule 4) |
| Finding | B1 (was F5) in the [R-01.10 boundary review](../reviews/r01-10-boundary-review.md), and F5 in the [R-01.6 review](../reviews/r01-6-security-review.md) |
| Status | Implemented on branch `fix/r01-f9-handshake-proof`. **Not merged. Not ticked.** The roadmap item stays `Evidence: none yet` until this is merged. |
| Author | Claude Code (`claude-opus-5-5`), reviewed by the shared reviewer: not run in this record |

## The problem

The console sent the session token as its first WebSocket message to whatever
process held `127.0.0.1:8000`. The server never proved it knew the token, so a
local process that bound the port while the backend was down received the
token (valid up to 24 hours) and the live microphone audio.

## What changed

Only the WebSocket `/ws/voice` path ever carried the token (`grep` over
`apps/api/src` and `apps/web/src`; the HTTP `/health` endpoint takes no
credential). Changed files:

- `apps/api/src/super_agent_voice/app.py`: `_authenticate` now runs the proof.
- `apps/web/src/app/voice-session.service.ts`: the console runs its side.
- Tests and helpers, the design text, and the roadmap files listed in the PR.

### Protocol

1. Client picks a random 128-bit nonce (`crypto.getRandomValues`) and sends
   `{"type":"session.hello","nonce":"<32 lowercase hex>"}`. No token.
2. Server replies `{"type":"session.challenge","nonce":<its own 128-bit nonce>,"proof":<proof_s>}` with
   `proof_s = HMAC-SHA256(token, "server-proof|" + client_nonce + "|" + server_nonce)` as hex.
3. Client checks `proof_s` with `crypto.subtle.verify` (full 32-byte digest,
   constant time). On any mismatch, malformed field, repeated challenge, or a
   server nonce equal to its own, the client closes the socket, shows
   "The local voice backend did not prove it holds the session token", sends
   nothing else, and never asks for the microphone. A silent server is cut off
   after 5 s by a client timer.
4. Client sends `{"type":"session.auth","proof":HMAC-SHA256(token, "client-proof|" + server_nonce + "|" + client_nonce)}`.
   Server compares with `hmac.compare_digest`. Only then is the session
   authenticated and an adapter created.

The token is used only as an HMAC key inside the browser service and the
server. Stop, mute, and interrupt send nothing until step 3 has passed.

### Server rules

- The hello must be a JSON object with `type == "session.hello"` and a nonce
  matching `[0-9a-f]{32}`; anything else is `invalid-control`, already counted
  as a failed attempt. Frames are still capped by `max_control_bytes`.
- Each step (receive hello, send challenge, receive auth) has its own
  `auth_timeout_seconds` deadline, still bounded by the total session budget.
- A wrong, missing, non-string, oversized, or replayed `proof` closes 1008 and
  is counted by the existing failure throttle (`auth.failed()`), exactly like
  a wrong token was before. A client proof is bound to a fresh server nonce,
  so replaying a recorded one fails.
- Expiry, revocation, Host, Origin, CSP, the pre-auth connection cap, and the
  single-session gate are unchanged.

## What it closes

- **B1 / F5, the capture of the token by a port squatter: closed in the
  console.** A squatter without the token cannot produce `proof_s`, so the
  console sends only a random nonce, then closes. No token, no audio, no
  provider claim is accepted. The raw token no longer appears in any frame in
  either direction, so DEBUG-level frame logging or a passive tap no longer
  yields it.

## What stays open

- **B2 / F2 (pre-auth lockout) is not closed.** Counting a failed proof is
  not new: a wrong token was already counted. What changes is that a squatter
  or attacker cannot learn anything useful per attempt. A local process that
  forges Origin can still hold the 4 pre-auth sockets, and idle holders are
  not counted as failures. The per-step deadlines allow a holder up to about
  twice `auth_timeout_seconds` (10 s, was 5 s) per socket before it is cut
  off, a small widening. The existing
  [F2 risk acceptance](../approvals/r01-6-f2-risk-acceptance.md) is unchanged.
- The server answers `proof_s` for any client nonce it is sent. That gives an
  offline guessing oracle only if the token is guessable; it is a 256-bit
  random value (`generate_token`), so this is accepted.
- A process that already has the token (same user, or reads the 0600 token
  file or process environment) can still authenticate. This fix does not
  change that.
- The proof does not encrypt or sign later traffic. A process in the middle
  after authentication on loopback can still read or alter frames. Local
  loopback `ws://` is the existing accepted scope.
- B3 to B8 of the boundary review are untouched.

## Tests (offline)

API (`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/api/src`, `-p no:cacheprovider --tb=no`):

```
1 failed, 1103 passed, 109 skipped, 1 warning in 79.65s
FAILED apps\api\tests\test_memory.py::test_files_are_private_even_when_they_already_existed
```

The one failure is the known Windows file-mode failure (boundary review B5),
unrelated to this change. New tests are in `apps/api/tests/test_handshake.py`:
the server proof is correct and never contains the token; server nonces are
fresh; a replayed client proof is rejected and the next failure is delayed; a
missing, null, wrong, oversized, raw-token, and second-hello answer are each
rejected, throttled, and create no adapter; each handshake step times out and
fails closed. `test_voice_api.py` gained malformed-hello cases and the
never-leaks test now also checks the challenge. `test_server_logging.py` runs
the real uvicorn handshake and checks the token is absent from the wire and
the logs.

Frontend (`apps/web`, `npm run test:voice`, `test:ui`, `test:epoch`):

```
voice-session self-test: PASS (66 cases)
voice-ui state self-test: PASS (50 cases)
playback-epoch self-test: PASS (8 cases)
```

New voice-session cases: a server with the wrong token, a proof over the
wrong nonce, a reflected nonce, a malformed proof, a ready frame instead of a
challenge, and binary data each make the console fail with the fixed error, send
only the hello, request no microphone, and close; a second challenge fails
closed with no proof sent; a silent server hits the 5 s timeout; stop, mute,
and interrupt send nothing before the server is proven. `npx tsc --noEmit -p
tsconfig.app.json` is clean. A real browser run against the running backend
was not run.
