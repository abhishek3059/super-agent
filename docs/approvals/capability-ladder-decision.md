# Capability ladder decision (DEC-18)

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Scope | Replace the blanket ban on assistant capabilities in REQ-08 and AGENTS.md section 5 with a tiered capability ladder. Decision text: [DEC-18](../../descisions.md#dec-18). |
| `jeevesh2515` | **Proposed and approved, 2026-11-12**, in chat with Claude Code (`claude-sonnet-5-5`), which recorded it at his instruction. He asked for a way to use the assistant at higher capability as the project's CTO. |
| `abhishek3059` | **Pending.** Approval is the PR review or merge of the PR that carries this record. Until then DEC-18 is a proposal. |
| Effect | Authorizes no runtime work. No tier is enabled. No roadmap item is ticked and no gate moves. [phases.md](../../phases.md) is unchanged because the new items sit in parallel track A, not in a phase. |

## What changes if both approve

- REQ-08 and AGENTS.md section 5 point to the ladder instead of a flat ban.
- Roadmap track A adds items R-A.1 to R-A.9. R-A.1 is ticked only after `abhishek3059` approves, with this record updated to show it.
- Tiers T1 to T3 each need an approved design and an independent security review before any build. T4 (purchases, money, credentials, permanent deletion) stays disabled.

## What does not change

Loopback-only API with a token, voice is not identity, limits enforced outside the model, content treated as data, fail closed, full logging, and an always-available emergency stop. The PH-02 and PH-03 fixed-worker work continues first.

## Open questions for the maintainers

1. May real voice and personal data go to a cloud provider (R-A.2)? The PH-00 boundary kept personal microphone audio local.
2. Is a paid tier acceptable, given that free tiers may train on inputs? This changes the $0 cap and needs both maintainers.
3. Are the tier boundaries right, or should any capability sit in a different tier?
