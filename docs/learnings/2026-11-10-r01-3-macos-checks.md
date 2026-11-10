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
- In a side check that was not saved, the lock file also installed on Python 3.14. That is a lead to confirm, not evidence.
- A handover that fixes the commit, refuses a dirty tree, saves the output, and stops on the first failure made the run quick to execute and easy to check.
- Raw output contains the home directory and temporary paths. Redact those before committing evidence, and say so in the record.

## What to do differently

Name the Python interpreter (or minimum version) in future handovers, and keep a redacted copy of the output in the repository so the evidence survives outside one person's Desktop.

## Still unknown

Whether the backend tests pass on Python 3.14, and how the real browser microphone path behaves on macOS (R-01.4).
