# Shared AI reviewer decision (DEC-19)

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Scope | Replace the required human review on `develop` with one shared AI reviewer, [.claude/agents/reviewer.md](../../.claude/agents/reviewer.md). Decision text: [DEC-19](../../descisions.md#dec-19). |
| `abhishek3059` | **Proposed and approved, 2026-11-12**, in chat with Claude Code (`claude-opus-5-5`), which recorded it at his instruction. |
| `jeevesh2515` | **Pending.** Approval is the review of the PR that carries this record. Until then DEC-19 is a proposal. |
| Effect | None until both approve. On 2026-11-12 the `develop` ruleset still required one approving review and code-owner review. |

## What changes if both approve

- The shared reviewer becomes the review gate in AGENTS.md section 9 for every PR.
- `abhishek3059` removes the required approving review and code-owner review from the `develop` ruleset. **Repository checks** stays required, and force pushes and deletions stay blocked.
- Both-maintainer approval is still required, and checked by the reviewer, for the changes AGENTS.md reserves to both maintainers: moving a gate or phase, adding or removing roadmap items, changing AGENTS.md rules or a DEC entry, adding a paid service, and ticking a `[human]` item.

## Open questions for the maintainers

1. Should `main` keep a required human review for release PRs?
2. Should the reviewer's model be revisited when a newer Opus model ships?
