# A2 portions of the Windows spike compatibility implementation

| Field | Value |
| --- | --- |
| Feature | `docs/design/windows-spike-compatibility.md` (signed 2026-11-08/1) tasks 1-3, A2 scope |
| Produced by | **Fallback developer model** (primary dev model exhausted step budget with no source edits); model: `opencode/glm-5.3-flash-free`, session date 2026-11-08 |
| Worktree | `C:\Users\user\AppData\Local\Temp\opencode\super-agent-review-46b65829\windows-fix` |
| Status | Implemented and locally verified on Windows Node 26.1.0; no commits, pushes, or PRs. An independent A3/workflow agent owns the other untracked/modified files. |

## 1. Files changed (A2 owned files only)

| File | Change |
| --- | --- |
| `spikes/entrypoint.mjs` | New shared guard `isDirectRun(moduleUrl, argvPath = process.argv[1])`: compares `import.meta.url` to `pathToFileURL(resolve(argvPath)).href`; canonicalizes absolute, relative-to-cwd, and URL-encoded (spaces, `#`, `%`, non-ASCII) entry paths. |
| `spikes/a2-permission-hook/token-file.mjs` | New internal helper `writeTokenFile({ target, token, run, timeoutMs })` + exports `parseDaclDump`, `windowsCurrentSid`. Stages a unique sibling staging dir (0700 POSIX, native-ACL'd on Windows) and exclusively created 0600 token file, verifies, writes token only after verified protection, atomically publishes by same-volume rename, re-verifies the published object, and cleans up only files the startup created (previous token restored from a private 0600 snapshot if a failed publish replaced it). Windows: fixed `SystemRoot\System32\whoami.exe` / `icacls.exe`, argument arrays, `shell:false`, 5 s / 64 KiB bounds, no tokens in argv or logs. Parent DACL verified as not shared-writable (only current SID / SYSTEM / BUILTIN\Administrators may hold write rights; other principals must be read-only; aliases `SY`/`BA` trusted, `WD`/`ED`/`BU` allowed read-only, everything else rejected). Parent ACL dumps are read from `icacls /save` (UTF-16LE, observed) inside the staging dir and deleted; POSIX trust = current uid + no group/other write on parent; 0700/0600 verified before write and re-verified (0600 preserved across replacement) after publish. |
| `spikes/a2-permission-hook/server.mjs` | Imports side-effect-free behind `isDirectRun`; `startServer` gains an optional internal `gate` (ready-by-default preserved; existing exports/result shape kept); listen errors reject the `startServer` promise (no unhandled event) and close the listener; CLI startup binds first (latch closed), stages/verifies/publishes the token via `writeTokenFile`, only then opens admission and logs readiness; on any failure: admission stays closed (503), listener closed, files cleaned; fixed safe categories only. Raw server JSON errors replaced with `malformed request`. |
| `spikes/a2-permission-hook/hook.mjs` | Guarded `main`; fetch bounded by `AbortSignal.timeout(115_000)` (below the 120 s hook window, above the 110 s server decision timeout); `describeHookError` maps failures to fixed safe categories (incl. undici `cause` unwrapping); `toHookOutput` unchanged. |
| `spikes/a2-permission-hook/selftest.mjs` | Extended assert-based harness under `main()` guarded by `isDirectRun`; no side effects at import. Test root requires `SUPER_AGENT_TEST_TMP` on Windows (fails closed before storage when absent); POSIX keeps the system-temp default. Suite dir has spaces and non-ASCII (`Süper Agent spike` + scheme); token filenames include `#`, `%`, spaces, non-ASCII. Children tracked with bounded stdout/stderr capture, 10 s deadlines, immediate premature-exit diagnosis in `waitPending`, unconditional kill/close awaits, server/all-listener/temp cleanup in `finally`. Coverage: guard unit tests, import side-effect probes, allow/deny/timeout/auth 401/Origin 403/explicit-127.0.0.1 bad Host 403/invalid decision/malformed request, missing token (server up), occupied port, server-down with existing token (real connect failure), ready-gate fail-closed, direct helper success + Windows owner-only DACL verification via `parseDaclDump` + POSIX 0600 preservation across replacement, injected native-exit/native-timeout/malformed-SID/unverifiable-parent-dump failures (fail closed, no leftovers, existing token untouched), publication failures (target inside a file; existing directory as target), and the real Windows direct CLI (bind → staged verified token → ready, hook allow decided with the published token, no staging leftovers). |
| `spikes/a2-permission-hook/config.mjs`, `approve.mjs`, `README.md`, `spikes/a3-gemini-live/*`, docs, workflow | Deliberately untouched (not A2-owned). |

Probe evidence for icacls/whoami behavior was gathered with throwaway scripts in
`C:\Users\user\AppData\Local\Temp\opencode\sa-probe-x1` (outside the repo).

## 2. Commands actually run

| Command (from worktree) | Result (real output) |
| --- | --- |
| `$env:SUPER_AGENT_TEST_TMP="C:\Users\user\AppData\Local\Temp\opencode"; node spikes\a2-permission-hook\selftest.mjs` | `selftest: all checks passed`, `exit=0` (ran twice; both passes) |
| `node spikes\a2-permission-hook\selftest.mjs` without the env | `selftest: requires SUPER_AGENT_TEST_TMP ...` exit 1 (fail-closed, exercised via the imported selftest probe) |
| `npm run check` | `{"errors": 0, "files_scanned": 84, "markdown_files": 45, "local_links_checked": 871, "fragment_links_checked": 260}` exit 0 |
| `git status --short` / `git diff --stat` | Only A2-owned edits plus the other agent's A3/workflow files; working tree left dirty |

## 3. Explicitly not done

- POSIX 0700/0600 paths execute on this Windows host only when run on POSIX; POSIX-side assertions run on POSIX (selftest is platform-consistent) — POSIX execution itself: **not run on this machine**.
- Node versions other than 26.1.0, the hosted CI workflow run, independent review/security assessment, and maintainer approval: **not run / not obtained**.
- macOS hook behavior, provider/network tests: not applicable, not run.
- No commits, pushes, PRs, repository settings, or file modifications outside the A2-owned paths.
