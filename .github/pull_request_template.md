# Pull request — AI-agent change

> This repository is maintained with AI-agent assistance. Complete the agent
> identity, verification, and safety sections honestly. Do not claim commands,
> tests, approvals, or runtime gates that were not actually executed or granted.

## Agent identity

| Field | Value |
| --- | --- |
| Agent / tool | <!-- e.g. OpenCode, Codex, Claude Code, human --> |
| Model / provider | <!-- e.g. provider/model-id; write "human" if none --> |
| Session / run ID | <!-- optional traceability ID --> |
| Human operator | <!-- GitHub handle of the person responsible --> |

## Summary

<!-- What changed, and why? Keep it to a few sentences. -->

## Change type

- [ ] Documentation
- [ ] Repository tooling / CI
- [ ] Application code
- [ ] Dependency change
- [ ] Security- or privacy-relevant change
- [ ] Runtime gate or capability change

## Scope

- **Files / areas changed:**
- **Explicitly out of scope:**
- **Linked issue / task / decision:** <!-- e.g. RT-003, DEC-07, #12 -->

## Verification

List the exact commands run and their real results. Write `not run` where
applicable; never imply a check passed without evidence.

| Command / check | Result |
| --- | --- |
| `npm run check` | <!-- pass/fail + counts --> |
| Link / anchor audit | <!-- pass/fail --> |
| Tests | <!-- command + result, or "not run" --> |
| Build | <!-- command + result, or "not run" --> |

Evidence (logs, screenshots, output excerpts):

```text
<!-- paste or link redacted evidence -->
```

## Roadmap (AGENTS.md section 11)

- **Roadmap item(s) this PR works on:** <!-- e.g. R-00.2, or "none: roadmap PR" -->
- [ ] I read `roadmap.md` before starting and again before opening this PR.
- [ ] Items finished by this PR are ticked in `roadmap.md` with an Evidence link, or none are finished yet.
- [ ] This PR stays on the current phase (or has an approved `[exception: link]`).

## Quality scores (AGENTS.md section 9)

| Correctness | Security | Honesty | Scope | Clarity | Average | Scored by |
| --- | --- | --- | --- | --- | --- | --- |
| <!-- 0-10 --> | | | | | | <!-- self / reviewer agent + model / human --> |

## AI-agent safety checklist

- [ ] No secrets, tokens, private keys, `.env` files, or personal data added.
- [ ] No runtime microphone, audio, screen, or context egress enabled.
- [ ] No new high-risk tool, host shell, plugin, or external action granted.
- [ ] No new dependency without justification and review.
- [ ] Voice or model output is not treated as identity or new authority.
- [ ] Runtime gates RT-G00–RT-G05 are not claimed closed without evidence.
- [ ] Future phases/tasks remain `not started` unless the change is the actual
      approved implementation.
- [ ] Documentation status, PASS/FAIL claims, and links are accurate.
- [ ] Documentation checked for stale status, commands, evidence, and
      application-state descriptions; updated in this PR or confirmed unchanged.
- [ ] Rollback path is stated below.

## Runtime and privacy impact

<!--
Describe any change to: microphone/audio capture, provider egress, retention,
authentication, budgets, permissions, or job execution. Write "none" for
documentation-only changes.
-->

## Rollback

<!-- How can this change be reverted safely? -->

## Human approval

- [ ] This change requires human review before merge.
- Approver / date: <!-- GitHub handle and date -->
