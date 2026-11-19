# Roadmap record: governance, boundary fixes, and track M

Date: 2026-11-19. Status: roadmap edit, plus the governance design
([docs/design/governance.md](../design/governance.md)) and its
[decisions record](../approvals/governance-decisions.md). No item is ticked, no gate or
phase moves, and `phases.md` is unchanged.

## Reason

The owner's past discussions (a 2026-11-19 brainstorm inventory, a working
note outside the repo and not citable here) named work that is on no roadmap item.
[AGENTS.md](../../AGENTS.md) section 11 rule 1 says such work needs a roadmap
PR before it starts. [PR 59](https://github.com/abhishek3059/super-agent/pull/59) adds the items. It builds nothing. PH-02 became current when
[PR 58](https://github.com/abhishek3059/super-agent/pull/58) merged on 2026-11-19.

## Items and sources

| Item | Source |
| --- | --- |
| R-02.7 governance gate, slices 1 to 4, GR-1 | [governance design](../design/governance.md) section 5 and 6.2 (added by [PR 59](https://github.com/abhishek3059/super-agent/pull/59)). No exception tag: PH-02 is current and policy limits already live in R-02.3. OD-G1 to OD-G4 approved, OD-G5 open and blocking slice 2b only, OD-G6 answered: see the [decisions record](../approvals/governance-decisions.md) |
| R-02.F1 `claim_and_run` bypass | [boundary review](../reviews/r01-10-boundary-review.md) B4; governance OD-G3 |
| R-02.F2 HQ jobs bypass | governance design section 6.1 (PR #56), OD-G4; conditional on PR #56 merging |
| R-02.F3 two ledger paths | inventory gap 6; PR #55 next to the SQLite ledger in [agent backend](../design/agent-backend.md) |
| R-02.F4 F2 closure | [decisions](../approvals/r01-10-decisions.md) section 3 (three triggers); [F2 acceptance](../approvals/r01-6-f2-risk-acceptance.md). R-M.3 and R-M.4 need it |
| R-03.F1 to R-03.F4 | boundary review B3, B5, B6, B7 (in PH-03 next to R-03.4, negative security tests) |
| R-M.1 to R-M.12 | [brain overview](../design/brain/overview.md) section 12, numbers kept, IR-9 and IR-10 kept on R-M.12 |
| R-M.13 explicit facts and reminders | merged in commit 774bca4 (`memory.py`); left unticked, evidence is for a later PR |
| R-M.14, R-M.15 contradiction handling | [memory design](../design/brain/memory.md) section 6; the decision item is `[human]` |
| R-M.16 decay and forget | memory design section 9; BR-8 |
| R-M.17 result handler | owner direction of 2026-11-16, given in chat; it has no repo record |
| R-M.19 etiquette | overview section 2 (BR-1 to BR-8); persona choice (OD-11) stays in R-M.1 |

## Left out on purpose

- Auth, JWT, Postgres accounts, and the friends-testing milestone (deferred by the owner on 2026-11-15).
- LangGraph as its own items: it is covered by the agent backend exception and R-02.x, R-04.x.
- Local speech-to-speech and Ollama text-mode testing as named tasks (R-07.x covers the optional part).
- The distiller exception record `docs/approvals/memory-distiller-exception.md` is added by the `feat/memory-distiller` PR; R-M.12 carries it as its exception tag and stays unticked.
- R-03.F5 (`/health` adapter name): the boundary review B8 says no change is needed for development.
- R-M.18 (persona): a duplicate of R-M.1, which already records OD-11. The number is not reused.
- Backend items R-02.7 and R-02.F1 to F3 carry no exception tags. If a maintainer judges R-02.7 outside PH-02, the tag is added in review.
