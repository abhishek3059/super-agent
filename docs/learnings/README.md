# Learnings

Short, dated notes on what we learned while building. Each note is written
when a spike, phase, or incident ends, so the next person (or agent) does not
repeat the mistake or redo the experiment.

These notes are evidence-backed observations, not decisions. A decision still
goes in [descisions.md](../../descisions.md).

## Index

| Date | Note | Topic |
| --- | --- | --- |
| 2026-11-07 | [Spike A2: permission hook](2026-11-07-spike-a2-permission-hook.md) | Answering agent permission prompts from outside the terminal |
| 2026-11-07 | [Spike A3: Gemini Live](2026-11-07-spike-a3-gemini-live.md) | Latency, tool calling, and client pitfalls |
| 2026-11-08 | [Stacked PRs and the PR #8 accident](2026-11-08-stacked-prs-and-pr8-accident.md) | Process lesson |
| 2026-11-09 | [Gemini account verification](2026-11-09-gemini-verification.md) | Terms, region, quota, and what they mean for open source |
| 2026-11-10 | [R-01.5 credential review](2026-11-10-r01-5-credential-review.md) | Loopback credentials: lockout as an attack, per-OS storage, localhost CSRF |

## How to add a note

1. Copy the template below to `YYYY-MM-DD-short-topic.md`.
2. Keep it under one page. Link the evidence (spike README, PR, record) instead of repeating it.
3. State what is verified and what is a guess. Never record a secret, a personal location, or real audio.
4. Add a row to the index above in the same PR.

```markdown
# Title

| Field | Value |
| --- | --- |
| Date | YYYY-MM-DD |
| Evidence | link to spike, PR, or record |

## What happened
## What we learned
## What to do differently
## Still unknown
```
