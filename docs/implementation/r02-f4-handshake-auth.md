# R-02.F4 record: authenticate in the WebSocket upgrade (closes F2)

| Field | Value |
| --- | --- |
| Date | 2026-11-20 |
| Branch | `feat/ph02-ledger-policy`, stacked on PR 64 |
| Host | macOS, Python 3.12, Node 22, synthetic data, no network |
| Finding | F2 in the [R-01.6 security review](../reviews/r01-6-security-review.md), B2 in the R-01.10 boundary review |
| Why now | The [R-01.10 decisions](../approvals/r01-10-decisions.md) section 3 requires the fix before job control is reachable from a voice session. `delegate_task` and cancel already are (behind `SUPER_AGENT_DELEGATE`). |

## The problem

The backend accepted every socket with the right Host and Origin, then ran
the token proof. A local process without the token, sending forged headers,
could hold all 4 pre-auth places by reopening sockets. The real user was
refused with close 1013 for as long as it ran (0 logins in 30 seconds in the
R-01.6 measurement).

## The fix

The review named the fix: authenticate during the handshake, with a token in
`Sec-WebSocket-Protocol` checked before accept. Sending the raw token would
undo R-01.F9, because a process squatting the port would receive it. So the
browser sends a proof of the token instead:

- Subprotocols offered: `super-agent.v1` and
  `sa-auth.<nonce>.<unix seconds>.<HMAC-SHA256(token, "upgrade|" + nonce + "|" + seconds)>`,
  with a fresh 128-bit nonce from `crypto.getRandomValues`.
- `_AuthControl.upgrade_ok` in `apps/api/src/super_agent_voice/app.py` runs
  after the Host and Origin checks and before the pre-auth cap. It requires
  both entries, exactly one proof, a time within 30 seconds of the server
  clock, an HMAC that matches (`hmac.compare_digest`), and a nonce not used
  before. Any other input is a refusal, and so is any exception.
- A refusal closes before accept, which the client sees as HTTP 403. It holds
  no socket and no pre-auth place. It is not counted by the failed-login
  throttle, so it cannot be used to delay the real user either.
- The accepted socket selects only `super-agent.v1`; the proof is not echoed.
- The R-01.F9 mutual proof then runs unchanged.

Why this keeps R-01.F9: a squatter that holds the port receives one upgrade
proof. It is valid for at most 30 seconds and only once, and it does not let
the squatter answer the server's challenge in the mutual proof, which uses a
fresh server nonce. The raw token still never crosses the wire.

The console (`apps/web/src/app/voice-session.service.ts`) computes the proof
with WebCrypto before it opens the socket. A stop or a newer start during that
await opens nothing.

## Tests

| Claim | Test |
| --- | --- |
| No proof, the proof without the protocol, a wrong token, a tampered nonce, time or MAC, a time 31 s off either way, two proofs, and malformed entries are refused before accept, and no adapter is created | `apps/api/tests/test_handshake.py::test_a_socket_without_the_upgrade_proof_is_refused_before_accept` |
| A valid proof is accepted once, selects only `super-agent.v1`, and a replay is refused | `test_an_upgrade_proof_works_once_and_selects_only_the_protocol` |
| The F2 attack: 20 refused upgrades with a pre-auth cap of 1 leave the cap free, the user's session starts, and the user's first real failed login is not delayed | `test_refused_upgrades_hold_no_slot_and_do_not_throttle_the_user` |
| A real uvicorn server accepts the proof on a raw socket and never logs the token | `apps/api/tests/test_server_logging.py` (both tests now send the upgrade proof) |
| The console offers the two protocols with a correct proof and never the token | `apps/web/scripts/selftest-voice-session.mjs` (`startLive`) |
| A stop while the proof is computed opens no socket | `selftest-voice-session.mjs`, case "a stop while the upgrade proof is computed opens no socket" |

Real browser run on 2026-11-20 ([saved output](evidence/r02-f4-browser-run-20261120.txt)):
in Chromium, sockets with no proof, the protocol only, or a forged proof were
refused with HTTP 403 and never opened. The console with the synthetic token
was accepted, passed the mutual proof, and reached `session.ready` with the
fake adapter.

Results: `apps/api`: 1387 passed, 5 skipped (macOS, Python 3.12; the 3 opt-in PostgreSQL tests skip without a database). `npm run check`: 0 errors. Web console: voice-session self-test 73 cases, ui 48, epoch 8, all PASS; `npm run build` passes.

## Limits

- Microphone capture after the handshake was not run in a real browser. The
  built-in browser pane blocks the microphone. The operator's own console run
  with synthetic speech is still the check for that part.
- The 30-second window assumes the browser and backend share one clock, which
  holds for the loopback design. A remote host would need a server nonce
  fetched first.
- `spikes/a6-openai-call/test_realtime_probe.py` still sends the raw token
  from before R-01.F9. It is a spike, not in CI, and was already stale.
