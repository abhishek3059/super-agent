PASS (reviewed A2 baseline; subsequent small corrections self-checked, not independently re-reviewed)

# A2 Windows compatibility: code review record

| Field | Value |
| --- | --- |
| Date | 2026-11-08 |
| Reviewer | Independent OpenCode `reviewer-free` session `ses_e44f9f60effe5d1DJiNJTmJ72T` |
| Scope | Shared entrypoint and A2 token-file, server, hook, self-test and implementation record, against Windows design revision 1 |
| Revision | Base `b9c12be` plus the Windows worktree implementation before the corrections below |
| Verdict | PASS, no blocker or major finding; minor findings and test gaps retained below |

## Evidence reported by the reviewer

- Windows Node 26.1.0: A2 self-test printed `selftest: all checks passed`, exit 0.
- Missing test-root override: exit 1 before storage, as intended.
- Repository check: 85 files, 872 local links, 0 errors, exit 0.
- Direct hook execution from a copied path containing spaces, hash, percent
  and non-ASCII characters: safe input-error category, exit 0.
- Deliberately failing temporary suite: exit 1 in 2.8 seconds, suite directory
  removed, no lingering child processes. The repository was not modified.
- Existing Ubuntu workflow diff was empty. Hosted Node 22 and macOS were not run.

Scores: correctness 9, security 8.5, honesty 9, scope 9, clarity 9.
Average 8.9. These are code-review scores, not an independent security audit.

## Subsequent small corrections

The coordinator expanded the parent-rights mask, normalized missing native
tool errors, added missing-argv and malformed/extra-principal/inherited-DACL
regressions, and changed token equality assertions to avoid printing values.
Both suites were rerun: A2 passed; A3 passed all 19 tests; repository check passed.

These changes were self-checked. The operator requested no repeat reviewer
run for this small increment, and skipped the remaining security-auditor run.
The initial PASS is not represented as an independent review of this delta.

## Residual limits

Encoded-path direct execution and deliberately failing cleanup were manually
tested by the reviewer, not embedded in the suite. Earlier empty temporary
directories from interrupted runs were observed but not removed. Host
termination can prevent `finally` cleanup. POSIX, hosted Node 22, real provider
and Claude Code behavior remain unverified by this review.
