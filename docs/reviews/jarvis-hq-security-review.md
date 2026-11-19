# Jarvis HQ: independent security review (R-H.4)

| Field | Value |
| --- | --- |
| Date | 2026-11-19 |
| Revision reviewed | `9b6baf9` (PR #56) |
| Host | macOS 27.2 (26B123), Google Chrome 157.0.8103.79, Node 22.22.3 |
| Reviewer | A `claude-opus-5-5` security-auditor subagent that did not write the code. It ran an isolated instance (port 8797) with a stub Hermes gateway under the real sandbox profile, synthetic canaries and dummy credentials, and drove real Chrome. The same approach as the [R-01.6 review](r01-6-security-review.md). |
| Brief | [security review brief](jarvis-hq-security-brief.md) |
| First verdict | **REJECT.** Scores: correctness 6, security 3, honesty 6, scope 8, clarity 8, average 6.2. |
| Closure | See "Closure" below. Everything below the findings table is the coordinating agent's record of what changed. |

## Findings

| ID | Severity | Finding | Reproduced as | Status |
| --- | --- | --- | --- | --- |
| F1 | CRITICAL | `(deny network-outbound (remote ip "localhost:*"))` did not match `::ffff:0.0.0.0`, which the kernel routes to 127.0.0.1. Any bot or its Chrome reached every loopback service: other bots' unauthenticated DevTools and gateways, and the operator's own local services. | From Forge's profile, `connect(("::ffff:0.0.0.0", port))` reached a canary; Forge drove Scout's tab and read its cookies. Every other loopback form was refused. | Fixed (C1) |
| F2 | HIGH | `cfprefsd` read and wrote any of the operator's preference domains for a bot. | `defaults write` / `defaults read` inside the sandbox reached `~/Library/Preferences`. | Fixed (C2) |
| F3 | MEDIUM | Through `com.apple.lsd.modifydb` a bot could change the operator's default app for a URL scheme. | `LSSetDefaultHandlerForURLScheme` on a synthetic scheme succeeded. | Fixed (C2) |
| F4 | MEDIUM | Ports were reused after a bot was deleted, so a process the deleted bot detached could drive the next bot's browser. | A detached loop set the new bot's page title. | Fixed (C3) |
| F5 | MEDIUM | Every bot got the operator's whole `auth.json` and every `*_API_KEY` / `*_BASE_URL`. | Dummy keys for unused providers were copied. | Fixed (C4) |
| F6 | LOW | Bots could reach the whole app API, not only `/mcp`, and could flood the owner challenge. | 2 of 10 owner sign-ins refused during a flood from a bot. | Fixed (C1) |
| F7 | LOW | Owner proofs did not name the server's address, so a listener on another port could relay a sign-in. | A relay on 18798 obtained a link from 8797. | Fixed (C5) |
| F8 | LOW | `/private/var/tmp` was readable. | `ls` listed it. | Fixed (C2) |
| F9 | LOW | The README described a session cookie that no longer exists; the app page had no CSP. | Code reading and requests. | Fixed (C5) |
| F10 | INFO | A pid record named a process only by its command text, so a reused pid could be mistaken for a gateway. | Reasoned. | Fixed (C3) |
| F11 | INFO | The settings routes did not refuse a bot that was being deleted, so a request could recreate its folder. | Reasoned. | Fixed (C3) |

Attempts the reviewer found correctly refused, with output, included reads of the session secret, database, other bots, home, `/private/tmp` and the per-user temp folder; writes outside the bot's folders; hard links; removing its own folder; signals; binds; launchd, `open`, AppleScript, Keychain, clipboard, logs and screen capture; unix sockets; every server-side link and folder-swap attempt; forged pid files and a fake DevTools endpoint; forged Host and Origin; bearer, proof and link replay; a spoofed server; and every screen-socket bypass.

Not tested by the reviewer: real Hermes model runs and prompt injection, UDP, a live folder-swap race during delete, Chrome renderer escapes, Windows.

## Closure

| Change | What changed | Verified by |
| --- | --- | --- |
| C1 | The profile now denies all outbound network (`remote ip "*:*"`) and then allows only the process's listed loopback ports. Bots reach the internet only through a new proxy (`apps/hq/server/src/lib/egress.ts`) on its own loopback port: it resolves each name itself, refuses unless every address is public (loopback, private, link-local, unspecified, mapped and embedded forms included), then dials the checked address. Gateways get `HTTPS_PROXY` and related variables; Chrome gets `--proxy-server`. The bots' tool endpoint (MCP) moved to its own port; bots can no longer reach the app API at all. | Self-check: every loopback form refused from inside the sandbox, which fails with the old rule. Proxy self-checks (6). Live: Forge's shell got exit 7 for `[::ffff:0.0.0.0]` on 8787, 8650 and 9301, and for 127.0.0.1 on 8787, 8651 and 9302; the proxy refused loopback; the internet worked through it (200). A real Jarvis to Scout handoff with browsing worked, model calls included. |
| C2 | `(deny user-preference-read user-preference-write)`, `com.apple.lsd.modifydb` closed, `/private/var/tmp` closed. | Self-check for the profile text and a live `defaults write` refused; live from Forge: `Could not write domain`, and the domain did not exist when read from outside. |
| C3 | Engine ports come from a high-water mark and are never reused. Pid records hold the start time, and a process counts as ours only if command and start time match. Settings routes refuse a bot being deleted. | Self-checks; lifecycle checks updated to the new record format. |
| C4 | A bot gets sign-ins and keys only for the providers named in the operator's Hermes settings (default, fallbacks, custom), not every key. | Live: of the operator's keys, the bot received only `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`, `ANYAPI_API_KEY`, `CLOUDFLARE_API_KEY`; its `auth.json` kept only the `openrouter` and `nvidia` pools. Messaging tokens and unused providers' credentials were not copied. |
| C5 | Owner proofs include the server's own origin. The app page sends a content security policy. README corrected. | Sign-in self-checks updated; live sign-in through the launcher. |

## Closure check

The same reviewer re-ran every reproduction on `553b8a6` (plus the then-uncommitted CSP placement change).

| Field | Value |
| --- | --- |
| Verdict | **ACCEPT WITH CONDITIONS.** Scores: correctness 8, security 8, honesty 8, scope 9, clarity 8, average 8.2. |
| F1 to F11 | All closed. F1: 22 address forms against IPv4 and IPv6 canaries, 66 refusals; UDP refused; Chrome got the proxy's refusal page for every loopback URL. The proxy refused 30 plain-HTTP and every CONNECT loopback, private and malformed target, request smuggling (`Content-Length` with `Transfer-Encoding`, obfuscated encodings) and pipelined loopback requests. F5 mostly closed (N3). F9 closed with the CSP change. |
| Conditions | 1. Fix N1. 2. Commit the CSP change and recheck it. 3. Fix N2 and N3, or list them as open. |

| ID | Severity | New finding | Status |
| --- | --- | --- | --- |
| N1 | MEDIUM | After an upgrade, gateways recorded by the older format (a bare pid) were never stopped, so they kept the older, open profile. | Fixed (C6) |
| N2 | LOW | The proxy resolved names with `dns.lookup` on Node's small shared worker pool; slow names stalled every bot's lookups. | Fixed (C7) |
| N3 | LOW | Unknown top-level keys in `auth.json` were copied to bots. | Fixed (C8) |
| N4 | INFO | The proxy would allow the host's own public addresses, leading to services listening on all interfaces. | Fixed (C7) |
| N5 | INFO | Any public port is reachable through the proxy, and names still resolve through the system resolver. Both follow from the accepted internet access. | Accepted, documented in the README |

## Second closure

| Change | What changed | Verified by |
| --- | --- | --- |
| C6 | A bare-pid record from an earlier version is recognised by its command and stopped. While verifying this live, a related gap appeared: Hermes relaunches itself in a new session after starting, so the process the server spawned is gone and the real gateway was left untracked (still inside its sandbox, but never stopped or adopted). A bot's gateway is now identified as the process listening on that bot's engine port whose command runs from that bot's home; only that bot's sandbox may listen there. It is stopped on restart, upgrade and delete. | Self-checks: a bare-pid record is found and stopped (fails with the old parsing); a relaunched gateway is found by port and home and stopped while an unrelated listener is left alone (fails with the old behaviour). Live: two orphaned gateways from an earlier run were stopped at startup; across two further restarts all five gateways were replaced cleanly; a Jarvis to Quill handoff then ran without any gateway restart. |
| C7 | The proxy resolves names with c-ares (`dns.Resolver`, 3 s timeout) instead of the shared worker pool, caps pending lookups at 32, and also refuses the host's own interface addresses. Names resolve through DNS only, so `localhost`, `127.1` and decimal forms do not resolve at all. | Proxy self-checks updated (names are refused with 502 or 403, never reaching the canary). Live: example.com, iana.org and the model provider reached through the proxy; real bots browsed and called the model. |
| C8 | `auth.json` for a bot holds only `version`, `providers`, `credential_pool` and `active_provider`, each filtered to configured providers. | Code; live bot home inspected by name only. |
| C9 | The CSP is set in the middleware that wraps every page response, so the static handler cannot skip it. | Live: the header on `/`, `/index.html` and `/assets/`; the app loaded and every request returned 200 with no policy violations. |

With the conditions met, R-H.4 is ticked. The macOS sandbox itself was not attacked directly, and `sandbox-exec` is deprecated by Apple; both stay in the README's list of what containment does not cover.
