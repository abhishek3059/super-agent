# R-01.10 independent review: local boundary on `develop` with Gemini mode

| Field | Value |
| --- | --- |
| Roadmap item | R-01.10, blocker 3 in the [PH-01 acceptance record](../implementation/r01-10-acceptance.md#blockers) |
| Date | 2026-11-19 |
| Reviewer | A `claude-opus-5-5` reviewer subagent that did not write the code under review |
| Reviewed | `develop` at `d52d894` |
| Previous review | [R-01.6 security review](r01-6-security-review.md) at `5de7293` and its closure check at `d5808c6` |
| Verdict | **ACCEPT WITH CONDITIONS** for maintainer-only testing. F5 is raised to MEDIUM. The decision on F5 and the F2 condition belongs to a maintainer and is not made here. |

## Scope

- `apps/api/src/super_agent_voice/app.py`: routes, Host and Origin checks,
  token authentication, throttling, debug-log guard, adapter selection.
- `config.py` and `generate_token.py`: token source and file checks.
- `gemini_adapter.py` and `tools.py`: Gemini mode and the tools it can reach.
- `local_adapter.py`, `tier1.py`, `memory.py`: the local adapter and the
  T1 and memory tools it can reach.
- `delegation.py`, `runner.py`, `ledger.py`, `graph.py`: the job entry points,
  checked for reachability from a voice session.
- `apps/web/src`: the rebuilt console (token handling, CSP, provider check).
- `scripts/start-voice-windows.ps1` and `scripts/start-voice-mac.sh`: launch flags.

Not in scope: `hermes_runs.py`, `planner_check.py`, `live_check.py`, and
`lfm3_voice.py` beyond confirming that no session path imports them.

## Method

Code reading with `grep` for every import and caller, and the offline API
test suite. No server probes, mutation tests, browser run, or live provider
call were made for this review.

API tests on Windows 11, Python venv as used by the maintainers, run as
`python -m pytest apps/api/tests -q --tb=no` with `PYTHONPATH=apps/api/src`.
pytest printed no summary line in this environment, so the counts come from
`--junitxml`: **1199 tests, 1089 passed, 109 skipped, 1 failed, 0 errors**.
The failure is the known Windows case
`test_memory.py::test_files_are_private_even_when_they_already_existed`
(see B5).

## What changed since the R-01.6 review

1. `SUPER_AGENT_ADAPTER=gemini` wires `GeminiLiveAdapter` into the console
   session (`app.py:226-239`), under the
   [Gemini testing exception](../approvals/gemini-live-testing-exception.md).
2. `SUPER_AGENT_ADAPTER=local` wires `LocalVoiceAdapter` (`app.py:223-225`).
   It can offer T1 read tools for files, Calendar, Notes and Mail
   (`local_adapter.py:106-109`, opt-in through `SUPER_AGENT_T1`, macOS only
   per `tier1.py:86`), memory and reminders (`memory.flag()`), and
   `delegate_task` (`SUPER_AGENT_DELEGATE=on`).
3. The console was rebuilt; it accepts the providers `fake`, `local` and
   `gemini-live` only (`apps/web/src/app/voice-session.service.ts:182`).

The authentication path itself did not change: the socket is accepted, then
the first message must carry the token (`app.py:525-559`, `448-475`).

## Findings

| ID | Severity | Finding | Status |
| --- | --- | --- | --- |
| B1 (was F5) | MEDIUM (was LOW) | The console sends the token as its first message to whatever process answers on `ws://127.0.0.1:8000` (`voice-session.service.ts:94-99`); the server never proves it knows the token. A local process that binds port 8000 while the backend is down gets the token and the live microphone audio, and can claim provider `local` so the console says audio stays local. The token stays valid for up to 24 hours from backend start (`config.py:48`). With it, that process can open a real session later. That session now reaches a Gemini session under the owner's key (Gemini mode) or, in local mode, T1 reads of mail, notes, calendar and allowlisted files plus memory reads and writes, spoken back as audio. Reasoned, not run. | Fixed by R-01.F9 in the PH-01 pull request. See the [R-01.F9 record](../implementation/r01-f9-handshake-proof.md) and "F5 and F2 condition". |
| B2 (was F2) | MEDIUM (LOW for one user on one machine) | Pre-auth lockout is unchanged: sockets are accepted before authentication and 4 pre-auth places are shared (`app.py:540-557`, `config.py:36`). A local process that forges Origin can keep the real user out. Not re-measured. | **Accepted for maintainer-only testing** in the [decisions record](../approvals/r01-10-decisions.md), which confirms the [F2 risk acceptance](../approvals/r01-6-f2-risk-acceptance.md). See "F5 and F2 condition". R-01.F9 narrows it only slightly (a failed browser proof is now throttled) and does not close it; see the [R-01.F9 record](../implementation/r01-f9-handshake-proof.md). |
| B3 | LOW | The local adapter's remote-model check fails open when Ollama is unreachable at session start (`local_adapter.py:527-528`, called once at `248`). If Ollama comes up later in the session, turns go to whatever the model name resolves to without the `/api/show` check. Only a name containing `cloud` is still refused (`local_adapter.py:507-508`). A cloud-forwarded alias would send transcripts and T1 results off the machine, against the PH-00 data boundary. Reasoned, not run. | Open. Fix: refuse the session when the check cannot run, or re-check before the first chat request. |
| B4 | LOW (latent) | `Runner.claim_and_run` (`runner.py:92-107`) builds an `Admission` without `policy.admit`, ignores the job's own admitted tools, hardcodes `planner_is_local=True`, and offers tools from `HERMES_WORKERS` (`runner.py:29-60`), including `memory_recall` and `memory_save`, which do not exist. `run_read_tool` refuses unknown names (`delegation.py:34-35`), so those two do nothing. The worker descriptions claim capabilities beyond T1 ("editing", "git commits", "desktop application launches"). No code outside the tests calls `claim_and_run` or `claim_next_job` (grep over `apps/api/src`), so a voice session cannot reach it today. | Open. Must go through `policy.admit` or be removed before any caller is added. |
| B5 (was N2) | LOW | On Windows, POSIX modes are not enforced: the token file check is skipped (`config.py:83`), and the memory and ledger databases rely on `os.chmod(0o600)` (`memory.py:100-102`, `ledger.py:199-201`), which Windows ignores beyond the read-only bit. The failing test above shows this for memory. Windows is a confirmed host and the revised live run was on Windows. Privacy then depends on the default profile ACL, which was not checked. | Open. Still needs the tracked item the R-01.6 reviewer recommended. |
| B6 (was F6) | LOW | The loopback bind is still enforced only by the launch command. Both launchers pass `--host 127.0.0.1` (`start-voice-windows.ps1:75`, `start-voice-mac.sh:47`). | Open, unchanged. |
| B7 | INFO | Gemini adapter queues are bounded by provider behaviour, not by code: `_events` and `_tool_out` are unbounded (`gemini_adapter.py:122`, `128-130`), and the tool-call counter resets on every provider `turn_complete` (`gemini_adapter.py:349`), so the cap of 4 is per provider turn, not per user reply. Only `calculate` and `current_time` can run. | Open, low impact. |
| B8 | INFO | `/health` needs only the Host header and returns the adapter name (`app.py:202-206`). A local process learns whether Gemini mode is on. No CORS headers are sent, so a web page cannot read it. | No change needed for development. |

## Checked and found as intended

- Gemini mode reaches only `calculate` and `current_time`
  (`tools.py:20-24`, `67-73`; `gemini_adapter.py:282-296`), as condition 4 of
  the testing exception requires. Tool names are allowlisted before logging
  (`app.py:899`, `gemini_adapter.py:288`).
- The Gemini key comes from the process environment only and is never put in
  a message (`app.py:230-239`). The SDK destination is pinned to the
  Developer API (`gemini_adapter.py:63-67`). Provider errors are reduced to
  fixed categories (`gemini_adapter.py:40-55`).
- Adapter selection fails closed on an unknown name (`app.py:240-241`).
- Host and Origin checks, the constant-time token comparison, the failure
  throttle, and expiry are unchanged (`app.py:448-475`, `525-530`). The
  debug-log guard still runs at startup and per connection (`app.py:193-194`,
  `531-533`).
- No CORS middleware; only `/health` and `/ws/voice` are routed; the docs and
  OpenAPI routes are off (`app.py:200`).
- The console carries a CSP with `script-src 'self'` and a fixed
  `connect-src` (`apps/web/src/index.html:7`), clears the token field after
  Start (`app.component.ts:83`), and uses no `innerHTML` (grep over
  `apps/web/src`). Transcripts are capped at 500 characters by the bridge
  (`app.py:894-897`) and rendered with Angular interpolation.
- Delegation from a voice session refuses every call: it is off by default
  (`local_adapter.py:76-80`), and when on, `delegation.Service()` is built
  with no model (`local_adapter.py:118`), so `delegate` raises
  `delegation_unavailable` (`delegation.py:64-65`).
- A turn that read T1 data cannot write memory or start a job
  (`local_adapter.py:141-156`). T1 fails closed off macOS (`tier1.py:86`).
- The Windows launcher reads the Gemini key as a secure string, keeps it in
  the process environment, and restores the previous environment on exit
  (`start-voice-windows.ps1:59-71`, `116-118`).

## F5 and F2 condition

### Facts at `d52d894`

1. Gemini is wired into a console session, opt-in only, under a testing
   exception approved by both maintainers on 2026-11-13. Its tools are the
   calculator and the clock.
2. The local adapter can also be wired into a console session with T1 reads
   of personal mail, notes, calendar and files, and with memory writes. These
   are opt-in and macOS-only.
3. Job control is not reachable from a session: delegation refuses every
   call, and `claim_and_run` has no caller.
4. The authentication design is unchanged since R-01.6. F2 and F5 are both
   still present in the code.
5. The R-01.6 reviewer recommended a roadmap gate for F5 "before Gemini or
   job control is wired into a session". The F2 acceptance says the risk must
   be removed before "a Gemini or job-control capability that matters enough
   to deny". Neither gate item exists in `roadmap.md`.

### What the token is worth now

Before, a stolen token opened a session with the fake echo adapter. Now it
opens a session that can use the owner's Gemini key, or, on a Mac with T1
and memory on, read personal data aloud and write reminders that later speak
in the assistant's voice. The same port-squatting position also receives the
live microphone audio. That is why B1 is raised to MEDIUM.

F2 is a denial of service. For maintainer-only testing, losing access to a
Gemini test session is an inconvenience, not a harm.

### Recommendation, pending maintainer decision

Decided 2026-11-19 in the [decisions record](../approvals/r01-10-decisions.md): F5 fixed in R-01.F9, F2 accepted for maintainer-only testing. The text below is the review as written.

1. **F2:** treat the condition as not yet triggered for maintainer-only
   Gemini testing, and say so in the F2 acceptance record. It becomes
   triggered when R-A.2 allows real use, or for any multi-user or always-on
   host, as the record already says.
2. **F5:** do not keep it open as LOW. Either:
   - (preferred) add a PH-01 fix item and implement mutual proof during the
     handshake: the server sends a nonce and proves it holds the token, the
     client answers with an HMAC, and no token ever crosses the wire. This
     also removes the accept-before-auth window behind F2 if done as
     handshake-time authentication; or
   - record a maintainer acceptance limited to testing, with the condition
     that T1 and memory stay off whenever the console is used, and that the
     fix lands before R-A.2 is decided or T1 is enabled with the console.
3. Add the two gate items the R-01.6 reviewer asked for (F5, and N2 as B5)
   in a roadmap pull request, so the condition is tracked by the checklist
   and not only by this record.

## What was not checked

- Not run: real uvicorn probes, mutation tests, the F3 memory measurement,
  a browser session of the rebuilt console, and any live Gemini call.
- Not run: `npm audit` and `pip-audit` for this revision.
- The Windows profile ACL on `~/.super-agent` (B5).
- macOS: T1 and memory paths were read, not executed, for this review.
- `hermes_runs.py`, `planner_check.py`, `live_check.py`, `lfm3_voice.py`:
  only confirmed not to be imported by a session path.
