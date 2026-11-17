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

This change had not passed the shared reviewer at that point.

## After pass 4: containment

The maintainer chose containment. Each bot's gateway and browser now run inside the macOS sandbox. The in-app sign-in, which ran Hermes outside it, was removed. Evidence is in the [run record](../implementation/jarvis-hq-local-run.md#containment).

## Pass 5: REVISE (average 5.6)

| Correctness | Security | Honesty | Scope | Clarity |
| --- | --- | --- | --- | --- |
| 6 | 3 | 4 | 7 | 8 |

The sandbox rule order was correct, but the unsandboxed server could be used to get out. Findings, and what was done:

1. `save_file` wrote through a link the bot planted, so a bot could write any of the operator's files. Fixed: writes in a bot's folders replace links instead of following them, and the parent folder must be inside the bot's own.
2. The server rewrote a bot's settings, persona and memory through planted links on each start. Fixed the same way. The bot's home is now written fresh and never read back.
3. The server signalled a pid read from the bot's home. Fixed: pids are kept in the server's own folder and must match the process's command line.
4. The profile allowed writes anywhere outside a few folders (Homebrew, `/usr/local`, `/Applications`, `/tmp`). Fixed: writes are denied everywhere except the bot's own folders and devices.
5. Local sockets were open (for example an ssh agent). Fixed: only the bot's own sockets and the system's name lookup and log.
6. Folders moved by settings (`ENGINES_DIR`, `DB_PATH`, the operator's Hermes home) were not closed. Fixed: closed by name.
7. `HERMES_URL` handed the first bot to the operator's own, unsandboxed Hermes. Switched off in code.
8. The R-H.5 tick was unsupported. The evidence now includes the attacks through the server, checked from outside, and self-checks that plant links.
9. Ego Browser support was out of scope. The maintainer asked for it in chat on 2026-11-17 as the fallback browser.
10. The UI still offered the removed sign-in. It now shows the terminal command instead; the private-desktop switch was removed too.
11. `launchctl submit` was untested. A self-check now tries it inside the sandbox.

## Not verified by the reviewer

The reviewer could not run the `apps/hq` commands. The typecheck, self-check, build, audit and local run results come from the author's [run record](../implementation/jarvis-hq-local-run.md). Dependency release ages against the 14-day rule, the upstream license and the OpenAI model names were not checked.

## Pass 6: REVISE (average 6.0)

| Correctness | Security | Honesty | Scope | Clarity |
| --- | --- | --- | --- | --- |
| 6 | 5 | 6 | 6 | 7 |

Pass 6 reviewed the containment work before it was pushed, while the pull request branch had moved on with a different design from another session. The maintainer chose this design. Findings, and what was done:

1. The staged work was not what the pull request contained. This branch now carries the latest `develop` and replaces the other design; that design is kept on a backup branch.
2. A bot could listen on another bot's port before that bot started. Fixed: listening is denied except on the process's own port and in its own folders. Tried live: refused.
3. A race let a bot redirect the server's memory edit to another bot's or the operator's memory file. Fixed by design: every read, write, listing and download in a bot's folders now runs inside a sandbox that can reach only that folder.
4. The live view and screenshots trusted whatever answered on the port. Fixed: only the browser the server started, and only page addresses on its own port. The view's refresh timer now starts after the browser is up.
5. A deleted bot's helper folder could be reused by the next bot on that port. Fixed: helper and temporary folders are named from the bot id and removed on delete.
6. The README understated the temp-folder opening for Chrome's lock. Corrected: it includes the operator's own Chrome lock folder if the same browser is used.
7. The download route followed links. Fixed with the sandboxed read in 3.
8. `delete_routine` acted before checking the owner. Fixed.
9. One self-check could not fail. Replaced; it now fails with the validation removed.
10. Dead code from the removed primary engine and sign-in. Removed.
11. The R-H.5 tick. Findings 2 and 3 are fixed and the evidence is in this branch.

## Pass 7: REVISE (average 6.6)

| Correctness | Security | Honesty | Scope | Clarity |
| --- | --- | --- | --- | --- |
| 7 | 4 | 6 | 8 | 8 |

Pass 7 confirmed the pass 6 fixes. New findings, and what was done:

1. A bot could remove its own folder and put a link to anywhere in its place; the server then built the next sandbox around the link target. Fixed: the sandbox denies writes to each folder itself (so it cannot be removed or renamed), and the server refuses a bot folder that is a link. Tried live and in a self-check.
2. The R-H.5 tick rested on finding 1. The evidence now includes that attempt.
3. The README overstated the folder protection and said nothing of what `HQ_UNCONTAINED=1` gives up. Corrected.
4. A bot that deleted its own home kept its gateway running after the bot was deleted. Fixed: removal no longer stops early.
5. All bots' server-side file commands shared one temporary folder. Fixed: one per folder.
6. Downloads promised a length the stream might not match and had no timeout. Fixed: no length promised, the read stops after a minute or when the client goes.
7. The `npm test` description was stale. Updated.

## Pass 8: REVISE (average 7.6)

| Correctness | Security | Honesty | Scope | Clarity |
| --- | --- | --- | --- | --- |
| 8 | 6 | 8 | 8 | 8 |

Pass 8 confirmed every pass 7 fix. New findings, and what was done:

1. Deleting a bot ran the unsandboxed server's recursive delete in folders a leftover bot process could still change. Fixed: contents are deleted from inside the bot's sandbox and the server removes only the empty folder. Self-check and live run with planted links.
2. A download cut short by the timeout looked complete. Fixed: it now ends with an error.
3. Gateways and browsers left by an earlier server version kept running under older rules. Fixed: the server stops them all when it starts.
4. A comment claimed parents were checked. Corrected.
5. Per-folder temporary folders were left behind. Removed with the folder now.

The reviewer judged that, with finding 1 fixed, what remains needs a person: the independent security review (R-H.4), the live voice run (R-H.3) and the recorded maintainer approval (R-H.1).

## Pass 9: PASS (average 8.6)

| Correctness | Security | Honesty | Scope | Clarity |
| --- | --- | --- | --- | --- |
| 9 | 8 | 9 | 8 | 9 |

All pass 8 findings resolved. The reviewer ran `npm test` in `apps/hq` (15 of 15 on macOS) and the typecheck. Low findings, none blocking:

1. The delete self-check also passes against the old delete, so it does not guard the race. Noted in the test.
2. A bot can lock files in its folder so the delete fails and folders are left behind. The README now says so, and the helper folder is removed even then.
3. A delete can block the server for up to about 50 seconds. Not changed.
4. A failed `ps` makes a live process look gone. Fails closed at the next start. Not changed.
5. The startup stop runs after the server starts listening. Not changed.
6. No CI on this head yet.

What remains needs a person: the independent security review (R-H.4), the live voice run (R-H.3) and the recorded maintainer approval (R-H.1).
