# Jarvis HQ: shared reviewer record

| Field | Value |
| --- | --- |
| Date | 2026-11-17 |
| Change | `apps/hq` and its documents, staged on `feat/jarvis-hq` |
| Reviewer | Shared reviewer ([.claude/agents/reviewer.md](../../.claude/agents/reviewer.md)), Claude Code, `claude-opus-5-5`, in a session separate from the author |
| Author | Claude Code (`claude-fable-5-2`) for `jeevesh2515` |

## Pass 1: REVISE (average 4.4)

| Correctness | Security | Honesty | Scope | Clarity |
| --- | --- | --- | --- | --- |
| 5 | 2 | 5 | 4 | 6 |

Fourteen findings. The main ones, and what was done:

1. Script injection in the unauthenticated `/api/apps/callback` page, which on this app meant code execution from one link. Fixed: the slug is validated and `<` is escaped.
2. A chat message cannot suspend an AGENTS.md section 5 invariant. Addressed by proposing [DEC-23](../../descisions.md#dec-23), an AGENTS.md edit and roadmap track H.
3. A worker can read the session secret and so sign in as the operator. Not fixed. Stated in the app README and tracked as R-H.4 and R-H.5.
4. The server's voice key was copied into every bot home. Fixed.
5. Provider error text, which can repeat part of a key, was logged. Fixed: status codes only.
6. A stale pid file could get an unrelated process killed on macOS. Fixed: the process must be a gateway.
7. to 14. Broken `npm run dev`, tools offered without their service, a prompt contradiction, unanswered socket upgrades, an unverified sign-in token risk, missing roadmap entry, dead code and loose version ranges. All addressed.

## Pass 2: REVISE (average 7.0)

| Correctness | Security | Honesty | Scope | Clarity |
| --- | --- | --- | --- | --- |
| 7 | 6 | 8 | 6 | 8 |

Pass 2 confirmed findings 1 and 4 to 14 resolved, 2 resolved in form, and 3 accepted as documented. New findings, and what was done:

1. Approvals failed open: any answer other than `deny` counted as allow. Fixed: only `allow` or `always` allows, anything else is refused.
2. Roadmap rule 8 asks for roadmap changes in their own pull request. Not split. The [approval record](../approvals/jarvis-hq-local-team.md) now asks the maintainer to waive it for this pull request.
3. xAI search is a second paid service and connected apps mean real accounts; DEC-23 covers neither. Both are now switched off in code.
4. One Hermes command still inherited the server's environment, keys included. Fixed.
5. The connected-app callback cannot see the session cookie after a cross-site redirect. Not fixed. The feature is switched off.
6. AGENTS.md described the exception as in force while DEC-23 is a proposal. Reworded.
7. DEC-23 cited a review with no record. This file is that record.

## Pass 3: REVISE (average 7.8)

| Correctness | Security | Honesty | Scope | Clarity |
| --- | --- | --- | --- | --- |
| 8 | 7 | 8 | 8 | 8 |

Pass 3 confirmed the pass 2 fixes in code. New findings, and what was done:

1. The "services stay off" self-check could not fail, because the settings were loaded before it set the variables. Fixed, and shown to fail against the old code.
2. The approval record still said xAI and Composio turn on with keys. Corrected.
3. This file was not staged. Staged.
4. The approval self-check covered only the predicate. A check of the route was added.
5. Messages still told the operator to set a Composio key. Reworded; the screens now say the feature is switched off.
6. Security stays at 7 while workers are uncontained. Accepted only under DEC-23, tracked as R-H.4 and R-H.5.

## Pass 4: REVISE (average 8.2)

| Correctness | Security | Honesty | Scope | Clarity |
| --- | --- | --- | --- | --- |
| 8 | 7 | 9 | 8 | 9 |

All five pass 3 fixes hold. Two low findings were fixed afterwards: the approval route check now pins every malformed body to 400, and a stale "no keys" reason in the run record was corrected.

What keeps the verdict at REVISE:

1. **Containment.** Workers run as the operator and can read the session secret, so a steered bot could sign in as the operator and answer its own approval cards. This holds Security at 7. With Security at 9 the average would pass.
2. **Approvals not yet given.** The OpenAI spend, the AGENTS.md section 5 edit, DEC-23, track H and the rule 8 waiver each need one maintainer. A pull request opened or approved by a maintainer supplies that.

The reviewer's reading of the rules: a maintainer cannot simply declare the risk accepted and merge. Either the risk is reduced in code (containment, or keeping the session secret and approval answers out of a worker's reach), or the gate itself is changed by a reviewed rule change with its own decision entry.

This change has not passed the shared reviewer.

## Not verified by the reviewer

The reviewer could not run the `apps/hq` commands. The typecheck, self-check, build, audit and local run results come from the author's [run record](../implementation/jarvis-hq-local-run.md). Dependency release ages against the 14-day rule, the upstream license and the OpenAI model names were not checked.
