# Running the spikes on Windows

This change is prepared for inclusion in restoration PR #10. It adds Windows compatibility
and a separate Windows workflow, not an application runtime or new authority.
The implementation is governed by the [signed design](design/windows-spike-compatibility.md).
The operator chose to update that existing PR instead of opening a separate
stacked PR. The Windows workflow remains independent of the Ubuntu job.

## Local offline checks

Use PowerShell from the repository root. The workflow uses Node 22. Test
results for other Node versions must be reported separately.

```powershell
npm ci
npm ci --ignore-scripts --prefix spikes/a3-gemini-live

$env:SUPER_AGENT_TEST_TMP = Join-Path $env:LOCALAPPDATA "Temp\opencode"
New-Item -ItemType Directory -Force $env:SUPER_AGENT_TEST_TMP | Out-Null

npm run check
node spikes/a2-permission-hook/selftest.mjs
node spikes/a3-gemini-live/selftest.mjs
```

Run the commands separately and check each exit code. The self-tests use
temporary synthetic data and local fake clients. They do not need Gemini or
Claude Code credentials and must not read a real key or contact a provider.
Do not substitute the Gemini `live.mjs` script for its offline self-test.

## Windows token protection

Windows token storage must use verified owner-only NTFS permissions. POSIX
mode `0600` alone is not sufficient on Windows. Startup fails closed when
native permission setup or verification fails. Do not bypass that error by
manually making the token readable to other users.

These permissions isolate ordinary users. They do not protect against an
administrator or another process running as the same Windows account.
Keep Gemini keys outside the repository; these tests do not configure them.

## Separate CI status

The dedicated workflow is [Windows spikes](../.github/workflows/windows-spikes.yml),
with status name `Windows spike checks`. It runs the repository check and the
two offline self-tests on Windows with Node 22.

The existing [CI workflow](../.github/workflows/ci.yml) and its Ubuntu
`Repository checks` job are unchanged. No Windows dependency is added to
that job, and this change does not modify branch protection or make the
Windows status required. A Windows failure remains visible and is not
masked as a pass.

macOS keeps the same Node entrypoints, API defaults, and POSIX permission
behavior. No separate copy of the spike code is introduced. Actual macOS
execution and GitHub-hosted execution are distinct verification steps; a
local Windows pass does not claim either one passed.

Product voice-approval policy, historical Gemini measurements, and other
review findings from PR #10 are outside this Windows compatibility change.
