# Windows spike compatibility: signed implementation design

| Field | Value |
| --- | --- |
| Date / revision | 2026-11-08 / 1 |
| Author | Solution Architect, `agentrouter/gpt-6.1-sol` |
| Status | Signed proposal for bounded spike implementation and independent review. Not implementation approval or a test result. |
| Repository / branch | `abhishek3059/super-agent`, `fix/windows-spike-compatibility` |
| Stacked base | Restoration PR #10, `fix/restore-reverted-pr-8`, inspected HEAD `b9c12be3651fd0e18e1a645726df33c5e79d7f9c` |
| Authoring scope | Only this document. No source edits, commits, pushes, PRs, merges, or repository-settings changes. |

## 1. Problem

The restored A2 and A3 throwaway spikes need to execute correctly on Windows without disturbing the macOS colleague's workflow. A2 spawns a file URL's `.pathname` as an OS path (`spikes/a2-permission-hook/selftest.mjs:19-25`), and both spikes compare entrypoints against a manually assembled `file://` URL (`spikes/a2-permission-hook/server.mjs:99`, `spikes/a2-permission-hook/hook.mjs:26`, `spikes/a3-gemini-live/live.mjs:112`). The operator reports A2 failing on Windows Node 26 with `request never became pending`, exit 1; this design does not claim to have rerun it. Token startup also needs a Windows equivalent of the existing POSIX 0600 protection, and offline tests must exercise A3's presently unchecked tool responses and cleanup (`spikes/a2-permission-hook/server.mjs:100-103`, `spikes/a3-gemini-live/live.mjs:49-95`). Deliver these bounded fixes and a separate Windows CI status, not product voice policy, provider measurements, or new assistant capabilities.

## 2. Approach

All additions below are proposed, not existing APIs. Use Node 22 standard-library facilities and the existing SDK only. Keep one implementation of each spike, with an OS branch only at the file-permissions boundary.

### Portable entrypoints

- Add a tiny shared `spikes/entrypoint.mjs` predicate used by A2 server, hook, selftest, and A3 live. Compare `import.meta.url` with `pathToFileURL(resolve(argvPath)).href`; missing `process.argv[1]` means imported, not directly executed. This helper has four callers and allows the actual guard to be tested without launching the cloud CLI.
- Use `fileURLToPath(new URL(..., import.meta.url))` for child-script arguments. Never use URL `.pathname`, manually prefix `file://`, or interpolate a shell command.
- Put A2 selftest execution behind its entry guard. Imports must not start servers, read credentials, create files, or run tests. Preserve the existing `startServer` parameters/result, `toHookOutput`, and exported A3 `JOBS` (`spikes/a2-permission-hook/server.mjs:12-19,90-96`, `spikes/a2-permission-hook/hook.mjs:8-12`, `spikes/a3-gemini-live/live.mjs:15-18`).

### Token file lifecycle

Add one internal `spikes/a2-permission-hook/token-file.mjs` helper, shared by CLI startup and its tests. Preserve `TOKEN_FILE`, port, and timeout defaults (`spikes/a2-permission-hook/config.mjs:4-7`). Do not change Gemini key storage or the approver API.

1. Generate the existing random token in memory. Create a unique sibling staging directory and exclusively created staging file. Reject symlinks/junctions and unexpected existing target types; do not traverse or recursively change ACLs on user directories. The target parent must be a trusted user-owned local directory, not a shared writable directory.
2. POSIX: private staging directory mode 0700 and file mode 0600, verified before writing. Atomic replacement must preserve 0600 even when replacing a less-restricted file; the existing direct `writeFileSync` mode does not repair an existing file's mode (`spikes/a2-permission-hook/server.mjs:101-102`).
3. Windows: resolve native `whoami.exe` and `icacls.exe` from the Windows system directory, not PATH or a test/model-selected executable. Discover the current numeric SID with `whoami /user /fo csv /nh`; validate a single well-formed SID. Apply ACLs to newly created staging objects only: remove inherited grants, set the owner to that SID, and grant only that SID full control. The private directory's grant must be inheritable to its staging file. Start from a fresh/reset DACL, since replacing this SID's grant alone does not remove other explicit grants.
4. Verify the protected directory and file DACLs from bounded `icacls /save` output, not localized display text or POSIX mode bits. Accept only the expected current-SID allow entries and required rights; reject NULL/empty DACLs, other principals, unrecognized descriptors, or enabled inheritance on the final file. `/verify` checks structure, not owner-only access, and is not sufficient. Keep ACL dump files inside the private staging directory and delete them.
5. Only after protection is established and verified, write the token. Bind with a CLI-internal readiness latch that rejects approval requests until startup completes. Atomically publish the staging file at `TOKEN_FILE` on the same volume, reverify the published DACL/mode, then enable handling and report readiness. Existing library callers retain ready-by-default behavior; the latch adds no HTTP route or authority. Do not overwrite an existing token if bind fails. On bind/publication/verification failure, keep admission closed, close any listener, and remove only files created by this startup. Never serve approvals while token protection is uncertain.

Native calls use `execFile`/`spawn` with argument arrays and `shell: false`; tokens never enter arguments, executable paths, or logs. Bound each native call to 5 seconds and output to 64 KiB. Missing tools, bad SID/output, nonzero exit, timeout, and unverifiable filesystem permissions all fail closed, with no chmod-only Windows fallback. No dependencies, PowerShell ACL scripts, `/T`, or `/C`.

Microsoft's command reference documents numeric SID prefixes, inheritance removal, grant replacement, ownership, `/save`, and the limited purpose of `/verify`: `https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls`, checked 2026-11-08. Native option spelling must be confirmed against the installed Windows command during implementation. This is ordinary-user file isolation, not a boundary against administrators or another process running as the owner.

### A2 failure behavior and test harness

- Preserve loopback binding, authentication, Host/Origin checks, body cap, and allow/deny/ask semantics (`spikes/a2-permission-hook/server.mjs:9,16-19,46-80,90-94`). Reject the `startServer` promise on listen errors instead of leaving an unhandled event. Token setup errors must terminate CLI startup unsuccessfully.
- Hook errors still produce no stdout decision and exit 0, retaining the normal permission flow (`spikes/a2-permission-hook/hook.mjs:1-4,21-28`). Use fixed safe diagnostic categories rather than raw error messages. Bound fetch completion below the documented 120-second hook window; retain the 110-second default server decision timeout (`spikes/a2-permission-hook/config.mjs:6-7`, `spikes/a2-permission-hook/README.md:25`).
- Extend the existing assert-based selftest, not a new test framework. Its raw HTTP Host test must explicitly connect to `127.0.0.1`, rather than relying on localhost address ordering (`spikes/a2-permission-hook/selftest.mjs:65-66`).
- Capture bounded child stdout/stderr, handle spawn errors, exit codes/signals, stdin errors, and a 10-second child deadline. Diagnose premature child failure immediately rather than waiting for `waitPending`. Every fetch/poll also has a deadline. In `finally`, stop and await all tracked children, settle pending requests without approval, await server shutdown, restore test environment overrides, and remove only the suite's temporary directory. Do this on assertion failure as well as success; current cleanup is success-path only (`spikes/a2-permission-hook/selftest.mjs:8-17,74-80`).

### A3 offline seam and tool validation

Keep `GoogleGenAI`, model/run defaults, prompt, synthetic jobs, audio format, and existing successful result fields unchanged (`spikes/a3-gemini-live/live.mjs:4,9-18,82,97-109`). Retain the pinned SDK and lockfile (`spikes/a3-gemini-live/package.json:9-11`, `spikes/a3-gemini-live/package-lock.json:8-17`). Do not edit the recorded macOS measurements (`spikes/a3-gemini-live/README.md:31-50`).

- Export a small pure response builder/validator and the existing `runOnce`. Add optional test-only inputs for a short timeout and reply-file destination; defaults remain 30 seconds and the existing system-temp PCM path. Tests may disable writing or provide a private synthetic output path. Do not add a CLI bypass or a second Windows implementation.
- Validate the complete tool-call batch before sending any response. Permit only `get_agent_jobs`, already declared at `spikes/a3-gemini-live/live.mjs:20-29`. Require 1 to 16 calls, object entries, and absent arguments or an empty plain object. If a correlation ID is present, require a nonempty string of at most 256 characters and reject duplicate IDs. Preserve optional IDs as the current response does; do not invent a mandatory SDK field. Unknown tools, extra arguments, malformed envelopes, or calls before session readiness reject the run and send no jobs or partial response.
- Implement a single settled flag for the connection/event lifecycle. Clear the timer and close the session on success, validation failure, send failure, connection rejection, websocket error, early close, and timeout. Ignore events after settlement. A connection resolving after timeout must be closed without sending the prompt or tools. Catch synchronous callback/send/close failures and handle promise rejections; none may escape as an unhandled exception. The current connection rejection path does not clear its timer and late connection resolution can still send (`spikes/a3-gemini-live/live.mjs:50,78-94`).
- Emit fixed failure categories, not raw provider errors, close reasons, request URLs, or credential values (`spikes/a3-gemini-live/live.mjs:78-79,120-122`). Validate that run count is a finite positive integer before credential access. A CLI run with no successful results exits nonzero and does not print a successful summary.
- Add `spikes/a3-gemini-live/selftest.mjs` using assertions and a fake `ai.live.connect` implementing only the existing session methods/callbacks (`spikes/a3-gemini-live/live.mjs:58-60,81-94`). Importing the SDK is allowed; constructing a real client, calling `readKey`, or connecting it is not. Never directly run `live.mjs` in offline CI.

### Temporary data and Windows CI

Use a test-only `SUPER_AGENT_TEST_TMP` root. Local Windows execution must set it to the approved `C:\Users\user\AppData\Local\Temp\opencode`; fail before imports/credential operations if absent or unusable. Create a unique suite directory with spaces and non-ASCII characters underneath it. Never use `.super-agent`, the actual token/key files, or repository-local outputs. Preserve POSIX selftest's system-temp default when no override is supplied (`spikes/a2-permission-hook/selftest.mjs:4-9`).

Assumption for hosted CI: the operator's approved local path is machine-specific. The Windows runner instead creates a private test root at `RUNNER_TEMP/opencode` and passes it explicitly through the same variable. This is test storage, not a credential location. Child environments omit `GEMINI_API_KEY` and other provider credential variables; tests use generated synthetic bearer tokens only. Test runtime network is loopback only, with no external services, microphone, provider connection, or real key read. Registry downloads needed for CI setup are distinct from offline test execution.

Create only `.github/workflows/windows-spikes.yml`:

- Workflow name `Windows spikes`; one job named exactly `Windows spike checks`, `windows-latest`, Node 22, 10-minute job timeout, `contents: read` permissions.
- `pull_request` targets: `develop`, `main`, and `fix/restore-reverted-pr-8`. `push` branches: those three plus `fix/windows-spike-compatibility`. Include `workflow_dispatch`. The stacked PR target must run before restoration merges.
- Reuse the existing checkout/setup-node v4 convention (`.github/workflows/ci.yml:17-24`). Install existing root and A3 lockfiles with `npm ci --ignore-scripts`, `HUSKY=0`, in separate failing steps. Then run `npm run check`, A2 selftest, and A3 offline selftest as separate failing steps. Never mask failures with `continue-on-error` or a later successful PowerShell command. No secret inputs, cloud credentials, artifact uploads, or live measurement step.
- Leave `.github/workflows/ci.yml` byte-for-byte unchanged. It currently exposes `Repository checks` on Ubuntu/Node 22 (`.github/workflows/ci.yml:3-15,20-32`). No dependency connects its job to Windows.

Creating a distinct status does not configure it as required. A non-required Windows status does not itself add a merge gate to macOS work. Existing branch protection and rulesets remain authoritative; their actual settings were not inspected. Do not change them, rename an existing status, or claim all merges are guaranteed unblocked. GitHub distinguishes required checks and warns about duplicate job names: `https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches`, checked 2026-11-08. Human review/merge rules remain unchanged (`AGENTS.md:40-45`).

## 3. Alternatives considered

1. **Windows-specific copies or PowerShell launchers.** Rejected: duplicate protocol and cleanup logic would drift from the existing Node-only A2 design (`spikes/a2-permission-hook/README.md:4-13`). Native URL conversions solve the path issue once.
2. **Treat Windows chmod 0600 as sufficient, or continue after ACL failure.** Rejected: this does not establish owner-only NTFS access and violates fail-closed secret handling (`AGENTS.md:64-75`). Use verified native ACLs or refuse startup.
3. **Add Windows to the existing CI job/matrix and make it required.** Rejected: changes the colleague's existing status/gating surface. The request explicitly calls for an independent workflow and no settings changes.
4. **Validate Windows by running Gemini or Claude Code.** Rejected: unnecessary credentials, network, and measurement changes. Existing A2 already has a local harness; A3 accepts a client parameter suitable for a fake (`spikes/a2-permission-hook/selftest.mjs:1-3`, `spikes/a3-gemini-live/live.mjs:42,81-88`).

## 4. Trade-offs and risks

- Native ACL handling is the only platform-specific boundary. SID/SDDL parsing must be bounded and narrowly tested; unsupported descriptors or unavailable tooling mean unavailable startup, not weaker protection. Localization, NTFS replacement behavior, existing broad ACLs, and spaces in paths need real Windows tests.
- Atomic staging adds a little startup complexity but avoids writing a readable bearer token or damaging an existing token when bind fails. User-controlled writable parents, reparse races, same-user processes, administrators, and orphaned processes after forced host termination are not made into a new security sandbox.
- Offline fake events prove validation/lifecycle behavior, not SDK/provider access, Gemini latency, microphone support, or a product runtime gate. Windows Node 22 CI does not establish support for every Node version. Node 26 can be reported separately if actually run.
- A separate optional status provides visibility, not enforced Windows quality. Maintainers may later decide on a required check, outside this change. Hosted-runner availability and actual budget/account settings are not verified here; do not approve paid runner usage.
- No changes to product voice policy, contributor policy, unrelated documents, measurement records, runtime gates, or capabilities. These remain throwaway experiments (`AGENTS.md:18-19,67-81`, `prd.md:73-97`).

## 5. Task breakdown

Each task is `not started`. Complete in order; each is a separate reviewable unit. No subagent commits, pushes, opens a PR, changes settings, or merges.

1. **Portable entrypoints.** Add the small shared guard; update A2 server/hook/selftest and A3 live; replace spawn `.pathname` with `fileURLToPath`. Add focused guard assertions for missing argv, imports, relative/absolute paths, spaces, percent/hash characters, and non-ASCII paths. Preserve existing exports/defaults.
2. **Private token startup.** Add the single token-file helper with POSIX mode checks and native Windows SID/DACL setup, verification, bounded subprocesses, staging/publication, and cleanup. Wire only A2 CLI startup, gate admission until final verification, reject listen errors, and add real temporary NTFS tests plus injected native-call/publication failures. Check 0600 replacement on POSIX.
3. **A2 offline regression harness.** Extend selftest for direct server/hook execution from encoded paths, imported modules, existing allow/deny/timeout/auth/Host/Origin cases, malformed stdin, missing token, server down, occupied port, spawn failure, and child/network deadlines. Add the safe hook diagnostic/deadline, explicit IPv4 Host test, and unconditional tracked-resource cleanup.
4. **A3 validation and lifecycle tests.** Export the minimal response/run seams, validate tool batches, and make settlement/timer/session cleanup reliable with safe failures. Add offline selftest for valid jobs/audio, invalid tools/arguments/IDs/envelopes, connect/send failures, error/early close, timeout/late connect, import/guard behavior, zero-success handling, and private-output cleanup. No key reads or real client connections.
5. **Independent Windows workflow and evidence.** Add `windows-spikes.yml` with the named job/triggers and explicit temporary root. Run repository checks and both offline suites on Windows Node 22, report actual install/audit results, and obtain independent implementation review/security assessment. Verify the diff leaves `ci.yml`, branch settings, macOS defaults, policy, and measurement records unchanged. Record macOS/Node 26 results only if actually run; human approval and merging remain separate.

## 6. Definition of done

- Portable guard assertions and direct A2 subprocess tests pass on Windows Node 22, including paths requiring URL encoding. A3 imports and fake runs perform no credential access, real connection, or default-file writes.
- Native NTFS tests prove current-SID-only protected file DACLs and successful secure replacement; injected missing-tool, timeout, invalid-SID/descriptor, extra-principal, and publication failures never publish an unprotected usable token or leave a listener running. A request arriving before final verification cannot receive approval. POSIX tests prove 0600 remains intact.
- A2 retains its documented decisions and security rejection cases. Every new failure yields no implicit approval. A3 validates the entire batch before returning jobs and closes/settles correctly on every tested failure, including a connection arriving after timeout.
- Passing and deliberately failing suites both terminate within deadlines and remove their synthetic token/ACL/PCM files, tracked child processes, timers, listeners, and environment overrides. Logs contain no credential sentinels or raw sensitive errors. No test touches actual key/token locations or external services.
- `npm run check` and both selftests pass with real output attached to the implementation review. The separate workflow exposes `Windows spike checks` for the stacked target and fails on a failing test; no existing status, workflow, settings, or product record is changed. Unrun macOS/provider/Node 26 tests remain explicitly `not run`.
- Independent implementation review and security assessment accept the actual developer diff. The design signature alone is not approval, a merge authorization, or closure of any product gate (`AGENTS.md:45,49-55`).

**Signed:** Solution Architect, `agentrouter/gpt-6.1-sol`, 2026-11-08. Scope: this implementation proposal only. Runtime tests, dependency installation/audit, CI execution, independent review, and maintainer approval: **not run / not obtained by this architect**.
