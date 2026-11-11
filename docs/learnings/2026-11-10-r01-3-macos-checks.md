# R-01.3: offline voice checks on macOS

| Field | Value |
| --- | --- |
| Date | 2026-11-10 |
| Evidence | [R-01.3 evidence record](../approvals/r01-3-macos-evidence.md) |

## What happened

Jeevesh's agent ran the R-01.3 handover procedure on an Apple Silicon Mac
against the exact PR #24 head. Every step passed: locked Python install, 11
backend tests, frontend audit, playback self-test, production build, and the
repository and roadmap checks. A redacted copy of the output is committed with
the record.

## What we learned

- `python3` on a maintainer's Mac can be a newer Python than CI (here 3.14.5, CI uses 3.12). The handover's plain `python3` would have tested a different interpreter than CI. Naming the interpreter in the procedure keeps the Mac result comparable with CI.
- A supplementary backend run on Python 3.14.5 also passed (11 tests, `overall_exit=0`), which supports PR #26's move of CI to 3.14.
- Capture the exit code in the same shell that runs the pipeline. A zsh wrapper around a bash-style `PIPESTATUS` left `overall_exit` blank once; the run was repeated under `bash`.
- A handover that fixes the commit, refuses a dirty tree, saves the output, and stops on the first failure made the run quick to execute and easy to check.
- Raw output contains the home directory and temporary paths. Redact those before committing evidence, and say so in the record.

## What to do differently

Name the Python interpreter (or minimum version) in future handovers, and keep a redacted copy of the output in the repository so the evidence survives outside one person's Desktop.

## Still unknown

How the real browser microphone path behaves on macOS (R-01.4).
