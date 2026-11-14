# Shared AI reviewer decision (DEC-19)

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Scope | Replace the required human review on `develop` with one shared AI reviewer, [.claude/agents/reviewer.md](../../.claude/agents/reviewer.md). Decision text: [DEC-19](../../descisions.md#dec-19). |
| `abhishek3059` | **Proposed and approved, 2026-11-12**, in chat with Claude Code (`claude-opus-5-5`), which recorded it at his instruction. |
| `jeevesh2515` | **Approved, 2026-11-13**, in a [PR #37 review](https://github.com/abhishek3059/super-agent/pull/37#pullrequestreview-5893054369). GitHub later marked that review dismissed only because `develop` was merged into the branch on 2026-11-14 to resolve `progress.md` conflicts; the decision text did not change. |
| Effect | None until both approve. On 2026-11-12 the `develop` ruleset still required one approving review and code-owner review. |

## What changes if both approve

- The shared reviewer becomes the review gate in AGENTS.md section 9 for every PR.
- `abhishek3059` removes the required approving review and code-owner review from the `develop` ruleset. **Repository checks** stays required, and force pushes and deletions stay blocked.
- Both-maintainer approval is still required, and checked by the reviewer, for the changes listed in [AGENTS.md](../../AGENTS.md) section 3: a paid service, moving a gate or phase, a roadmap exception, and (added by DEC-19) a change to an AGENTS.md rule or a DEC entry.
- The reviewer's Bash access is limited to read-only commands by instruction in its file, not by tool permissions.

## Open questions for the maintainers

1. This proposal keeps a required human review on `main` for release PRs. Should releases move to the shared reviewer later?
2. Should the reviewer's model be revisited when a newer Opus model ships?
