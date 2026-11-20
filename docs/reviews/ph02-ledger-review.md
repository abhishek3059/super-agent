# PH-02 ledger work bundle: review record (PR 64)

| Field | Value |
| --- | --- |
| Date | 2026-11-20 |
| Branch | feat/ph02-ledger-evidence |
| Reviewers | Shared reviewer (`.claude/agents/reviewer.md`, Claude Code, Sonnet 5.5); independent security review (Claude Code, Opus 5.5, security-auditor) |

## Shared reviewer rounds

| Round | Head | Score | Verdict | Main findings |
| --- | --- | --- | --- | --- |
| 1 | 51a040f | 7.6 | REVISE | Subprocess timeout claimed but not shown; session check fails open after close; thread cap not atomic; admit race test probabilistic. |
| 2 | 72b76a4 | 9.0 | PASS | Unknown job returned `session_stale` (minor). |
| 3 | cdc8cc5 | 8.6 | PASS | Criteria source not stated; tick count wording; R-02.5 scope wording; R-02.4 needs a caveat on the five Hermes labels. |

## Security review

- Round 1 (51a040f): no critical or high. Medium: M1 session gate reopens for a missing id after close; M2 merging PR #56 needs `_spec` renamed to `validate_spec` in `_vetted`. Low: L1 thread cap not atomic; L2 a hung macOS network mount can fill the cap (fail closed); L3 late side effects limited to dropped results; L4 cancel had no ownership check.
- Round 2 (72b76a4): M1, L1, L4 closed. New: counting all in-flight threads capped healthy parallel reads; a never-started thread could stay registered.
- Round 3 (c571507): both closed. New low: a thread that finishes just after its timeout could stay counted. Fixed in d23cf2e by pruning before each check.
- M2 and L2 are recorded in the evidence record's Known limits, not code-fixed.
