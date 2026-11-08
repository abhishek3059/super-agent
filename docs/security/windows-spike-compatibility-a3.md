PASS (partial scope: A3 spike and Windows CI only; A2 and token storage excluded)

# Windows spike compatibility: independent security audit

| Field | Value |
| --- | --- |
| Date | 2026-11-08 |
| Verdict | **PASS for the audited scope.** No CRITICAL, HIGH or MEDIUM finding. Four INFO items, none blocking |
| Scope | `spikes/a3-gemini-live/live.mjs`, `spikes/a3-gemini-live/selftest.mjs`, `.github/workflows/windows-spikes.yml`, `docs/windows-spikes.md` |
| Explicitly excluded | `spikes/a2-permission-hook/*` including `token-file.mjs` and the A2 edits to `hook.mjs`, `server.mjs`, `selftest.mjs`. The A2/token correction was still in progress during this audit, so **this verdict is partial** and does not cover A2 |
| Also excluded by instruction | `spikes/entrypoint.mjs` (the `isDirectRun` helper implementation). Only its call sites in the A3 files were considered |
| Assessed revision | `b9c12be` plus the uncommitted worktree changes for this branch |
| Assessor | Security & Compliance, independent of developer and reviewer, profile `opencode/deepseek-v4.1-flash-free` |
| Evidence base | All four in-scope files read in full, plus the A3 diff against `HEAD`, `.github/workflows/ci.yml` for convention comparison, and local execution of the offline self-test |
| Not verified | GitHub-hosted `windows-latest` with Node 22, macOS execution, any real Gemini session, A2 behaviour |

## 1. Attack surface of this change

The change is a spike script, an offline self-test, one new workflow and one doc page. It adds no listener, no endpoint, no privileged operation and no new product capability.

Attacker-reachable surfaces, and how each is reached:

| # | Surface | Who controls it | Reachable by |
| --- | --- | --- | --- |
| S1 | Gemini Live messages: `toolCall.functionCalls`, `serverContent`, error and close objects | The provider connection, or anything that can influence it | A real run of `live.mjs` only |
| S2 | Environment: `GEMINI_API_KEY`, `SUPER_AGENT_RUNS`, `SUPER_AGENT_LIVE_MODEL`, `SUPER_AGENT_TEST_TMP` | The local operator | Local process start |
| S3 | The key file `~/.super-agent/gemini-key` | The local operator | A real run of `live.mjs` only |
| S4 | CI execution of PR code on `windows-latest` | Any PR author against the listed branches | The workflow triggers |
| S5 | The test root named by `SUPER_AGENT_TEST_TMP` (mkdir and recursive delete under it) | The local operator or the CI workflow | Local run, or CI |

No in-scope file opens a socket, reads a repository file other than the key, or writes outside the OS temp directory. The offline path constructs no client, so S1 and S3 are unreachable from the self-test.

## 2. Findings

No CRITICAL, HIGH or MEDIUM finding. Four INFO items follow. None is exploitable, none changes the verdict.

### INFO-01 — The A3 key read does not verify the `0600` claim in its own header comment

- **Location:** `spikes/a3-gemini-live/live.mjs:3`, `spikes/a3-gemini-live/live.mjs:52-55`.
- **What is missing:** the header says the fallback key file is "mode 0600", but `readKey()` reads it without checking mode or ownership, and on Windows a POSIX mode is not a meaningful control anyway.
- **Why not a higher severity:** there is no exploit path that the read creates. An attacker who can read that file already had read access before the spike ran, and the key value is never logged, echoed or transmitted anywhere except to the provider endpoint the spike is measuring. `docs/windows-spikes.md:31-34` correctly states that Windows needs verified NTFS owner-only permissions and that A2 is the component responsible for token storage. This is a comment that overstates an enforcement that does not exist in this file.
- **Action:** change the comment to "user-owned file outside the repo, permission not checked here", or add a mode check for POSIX. Does not block this PASS.

### INFO-02 — A developer-specific absolute temp path is hardcoded in the self-test failure message

- **Location:** `spikes/a3-gemini-live/selftest.mjs:16`.
- **What it is:** `C:\Users\user\AppData\Local\Temp\opencode` is embedded in the Windows guard message and committed to the repository. The same page in `docs/windows-spikes.md:16` avoids this by using `$env:LOCALAPPDATA`.
- **Security impact:** none. The string contains the generic local account name `user`, no credential and no personal data, and the guard is a fail-closed path that only prints when the operator omitted the variable. It is still a local path disclosure in source, and it is wrong for every other machine, which makes the message misleading.
- **Action:** print only the variable name and its purpose, not a path. Does not block this PASS.

### INFO-03 — CI hygiene follows the existing repository convention rather than the stricter option

- **Location:** `.github/workflows/windows-spikes.yml:10-11`, `:20`, `:23`.
- **What it is:** `permissions` is correctly narrowed to `contents: read` and the workflow references no `secrets.` context. The actions are pinned to major tags (`actions/checkout@v4`, `actions/setup-node@v4`) and `checkout` keeps its default `persist-credentials: true`, so the read-only `GITHUB_TOKEN` is present in the runner's git config while PR code runs.
- **Why not a higher severity:** this matches `.github/workflows/ci.yml`, the repository is public, the token is read-only, and no secret is available to the job. A PR author executing code in a runner with a read-only token and no secrets gains nothing beyond what public read access already gives.
- **Action:** pin actions to commit SHAs and set `persist-credentials: false` in a later hardening pass. Does not block this PASS.

### INFO-04 — The provider session allows repeated tool-call batches within one 30 s window

- **Location:** `spikes/a3-gemini-live/live.mjs:123-144`, `:147-171`.
- **What it is:** `MAX_TOOL_CALLS` bounds one batch, but nothing bounds the number of `toolCall` messages before the turn completes. A misbehaving endpoint can elicit many responses in the window.
- **Security impact:** none in this spike. Every response is the fixed synthetic `JOBS` constant (`live.mjs:21-24`, `:78`), so there is no amplification of real data, no disk write per batch, and the 30 s timeout bounds the session. The model can request exactly one tool, with empty arguments, and that is enforced in code, not by the prompt.
- **Action:** if this pattern is carried into product code, add a per-session tool-call budget. Not needed for the spike.

### Controls that were checked and held

- **Full batch validation before any send:** `buildToolResponses` (`live.mjs:59-81`) validates array shape, non-empty, size limit, plain-object element, allowlisted tool name, empty arguments only, id type and length, and duplicate ids, and it returns the whole payload or throws. `handleToolCall` (`live.mjs:123-144`) sends only after the whole batch validates, so a rejected batch produces no partial `sendToolResponse`. Verified by `testUnknownToolRunNoPartialSend`, which asserts `toolSends === 0` after a batch containing `make_purchase`.
- **Fixed error categories:** every reject uses a constant string (`live.mjs:40-48`, `:114-119`, `:133`, `:140`, `:169`, `:173-174`, `:195-196`, `:213`). Provider error text, close codes, close reasons and connect failures never reach a log line. Verified by the `SENTINEL` assertions in `testWebsocketErrorCategory`, `testEarlyCloseCategory`, `testConnectRejection`, `testSendFailure` and `testOfflineCliFailures`.
- **Credential redaction at the CLI boundary:** `runCli` catches client construction failure and logs a fixed message (`live.mjs:236-241`), and catches run failure and logs fixed text (`live.mjs:250-252`). `testOfflineCliFailures` asserts that invalid run counts create no client at all, so no credential read happens on a bad `SUPER_AGENT_RUNS`.
- **Session lifecycle and fail-closed behaviour:** one settle flag, one close, a timer that is always cleared, and a late connection that is closed without sending anything (`live.mjs:96-120`, `:177-199`, `:202-206`). Covered by `testToolCallBeforeReady`, `testTimeoutAndLateConnection`, `testReplyWriteFailure`, `testCloseThrowSwallowed`.
- **Import guard:** importing `live.mjs` starts no CLI. `isDirectRun` itself is out of scope, but the property was checked empirically: the self-test imports the module and runs to completion with a sentinel `GEMINI_API_KEY` set and prints no key material (see section 5).

## 3. Privacy compliance

Checked item by item against `AGENTS.md` section 5 and the requirement IDs it cites.

| Contract item | Result | Evidence |
| --- | --- | --- |
| No cloud telemetry added | Honours | No analytics, reporting or telemetry code in any in-scope file. The only network use is the Gemini Live session that is the spike's declared purpose, and the offline self-test never constructs a client |
| LAN-only / loopback transmission, no new listener | Honours | No `listen`, no server, no port in the change. `windows-spikes.yml` exposes nothing |
| No screen capture | Honours | No screen, window or display API is imported or called |
| No microphone or ambient capture | Honours | The prompt is a fixed string (`live.mjs:12`) sent as text. Audio is received from the provider, never captured locally |
| Synthetic data only, no real personal data to a provider | Honours | `JOBS` is a hardcoded synthetic ledger (`live.mjs:21-24`). No file, ledger, environment or user record is read into the request |
| No secrets in the repo, logs, URLs or prompts (REQ-12) | Honours | No credential literal in any in-scope file; the workflow uses no `secrets.` context; key values are read from env or a file outside the repo and never formatted into a log or error. Empirically confirmed with a sentinel key (section 5) |
| Never commit audio, transcripts, `.env` or model weights (REQ-14) | Honours | `git ls-files` shows no `.pcm`, `.env` or key file tracked. The reply PCM is written to the OS temp directory at runtime only |
| Limits live outside the model (REQ-10) | Honours, for this spike | Tool allowlist, batch size, id length and the 30 s timeout are code constants. The model cannot name a tool the code does not accept |
| Fail closed on error | Honours | Every error path rejects with a fixed category and closes the session. The Windows test-root guard exits non-zero rather than falling back to a path it cannot verify |
| Voice is not identity (REQ-09) | Not applicable | No approval path, no grant, no authority in this change |
| No new capability authority (REQ-08) | Honours | The only tool returns a constant. No shell, purchase, message, file deletion or plugin surface |

Two accepted-by-design items, recorded so they are not mistaken for findings:

- The default reply file `join(tmpdir(), "super-agent-a3-reply.pcm")` (`live.mjs:18`, `:209-215`) is written with the process default mode, so on POSIX it can be world-readable in `/tmp`. The content is a synthetic model reply to a synthetic prompt, and the instruction for this audit records the default PCM output as intentionally preserved by the signed design. No personal data and no key material is in it.
- The transcript logged at `live.mjs:249` is the model's spoken reply to the fixed synthetic prompt. It contains no personal data, and it is printed, not stored.

## 4. Residual risk

- **A2 is not audited here.** Per instruction, `spikes/a2-permission-hook/*` and the token work were not inspected while that correction is in progress. The workflow runs the A2 self-test, but this report makes no claim about what that test does or whether its token handling is sound. This verdict is partial for that reason.
- **`spikes/entrypoint.mjs` was excluded.** I did not audit `isDirectRun` itself. A defect there could make an import start the CLI, which would read a key and contact a provider. That did not happen in the two runs below, but the helper's implementation is unverified.
- **No GitHub-hosted or macOS execution.** The workflow was read, not run. `windows-latest` with Node 22, the CI-only environment (no `GEMINI_API_KEY`, fresh `npm ci`), and macOS were not exercised.
- **Local runs used Node v26.1.0, not Node 22.** `docs/windows-spikes.md:9-10` correctly requires other Node versions to be reported separately.
- **No real provider session was opened.** The behaviour of the real `@google/genai` client, the real endpoint, and the real tool-call payload shape is unverified. The validation assumes the shape the self-test fakes.
- **Dependency audit result:** `npm audit` in `spikes/a3-gemini-live` reported 0 vulnerabilities across 42 production dependencies. `@google/genai` is pinned to `2.31.0` with a lockfile, and both `npm ci` steps in the workflow use `--ignore-scripts`.
- **Supply chain of the workflow itself:** actions are tag-pinned (INFO-03). I did not verify the published action sources.

## 5. Tests run (truthful record)

All commands were run locally on Windows in the review worktree, with the approved test root.

| Command | Result |
| --- | --- |
| `node selftest.mjs` in `spikes/a3-gemini-live`, `SUPER_AGENT_TEST_TMP=C:\Users\user\AppData\Local\Temp\opencode`, Node v26.1.0 | 19 of 19 passed, exit 0 |
| Same command with `SUPER_AGENT_TEST_TMP` unset | Exit 1, prints the fail-closed Windows guard message, no test executed |
| Same command with `GEMINI_API_KEY=SENTINEL-KEY-DO-NOT-PRINT` and the test root set | Exit 0, 19 of 19 passed, zero occurrences of the sentinel in output, so no key read and no key leak on the offline path |
| `npm run check` at repository root | Exit 0, 0 errors (44 Markdown files, 870 local links, 260 fragment links) |
| `npm audit --json` in `spikes/a3-gemini-live` | Exit 0, 0 vulnerabilities |

Not run: `windows-latest` Node 22 on GitHub, macOS, any real Gemini Live session, the A2 self-test, the A2 workflow steps as an independent security check.
