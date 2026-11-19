# Roadmap record: governance, boundary fixes, and track M

Date: 2026-11-19. Status: roadmap edit only. No item is ticked, no gate or
phase moves, and `phases.md` is unchanged.

## Reason

The owner's past discussions (see the 2026-11-19 brainstorm inventory, a
working note outside the repo) named work that is on no roadmap item.
[AGENTS.md](../../AGENTS.md) section 11 rule 1 says such work needs a roadmap
PR before it starts. This PR adds the items. It builds nothing.

## Items and sources

| Item | Source |
| --- | --- |
| R-02.7 governance gate, slices 1 to 4, GR-1 | `docs/design/governance.md` section 5 and 6.2 (branch `docs/governance-gate`). No exception tag: PH-02 is now current and policy limits already live in R-02.3. |
| R-02.F1 `claim_and_run` bypass | [boundary review](../reviews/r01-10-boundary-review.md) B4; governance OD-G3 |
| R-02.F2 HQ jobs bypass | governance.md section 6.1 (PR #56), OD-G4 |
| R-02.F3 two ledger paths | inventory gap 6; PR #55 next to the SQLite ledger in [agent backend](../design/agent-backend.md) |
| R-03.F1 to R-03.F5 | boundary review B3, B5, B6, B7, B8 (in PH-03 next to R-03.4, negative security tests) |
| R-03.F6 | boundary review "F5 and F2 condition"; [F2 acceptance](../approvals/r01-6-f2-risk-acceptance.md); [decisions](../approvals/r01-10-decisions.md) |
| R-M.1 to R-M.12 | [brain overview](../design/brain/overview.md) section 12, numbers kept |
| R-M.13 explicit facts and reminders | merged in commit 774bca4 (`memory.py`); left unticked, evidence is for a later PR |
| R-M.14, R-M.15 contradiction handling | [memory design](../design/brain/memory.md) section 6; the decision item is `[human]` |
| R-M.16 decay and forget | memory design section 9; BR-8 |
| R-M.17 result handler | owner direction of 2026-11-16 (results reach the conversation only through a handler) |
| R-M.18, R-M.19 persona and etiquette | overview section 2 (BR-1 to BR-8), OD-11 for the persona choice |

## Left out on purpose

- Auth, JWT, Postgres accounts, and the friends-testing milestone (deferred by the owner on 2026-11-15).
- LangGraph as its own items: it is covered by the agent backend exception and R-02.x, R-04.x.
- Local speech-to-speech and Ollama text-mode testing as named tasks (R-07.x covers the optional part).
- The distiller exception record `docs/approvals/memory-distiller-exception.md` lives on `feat/memory-distiller`; R-M.12 names it and must not start until it is merged.
- The governance design document itself is on a separate branch and is not merged here.
- Backend items R-02.7 and R-02.F1 to F3 carry no exception tags. If a maintainer judges R-02.7 outside PH-02, the tag is added in review.
