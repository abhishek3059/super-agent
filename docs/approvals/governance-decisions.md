# Governance gate: maintainer decisions

| Field | Value |
| --- | --- |
| Roadmap item | R-02.7 |
| Date | 2026-11-19 |
| Decided by | `abhishek3059`, in chat with Claude Code (`claude-opus-5-5`), which recorded it at his instruction. One maintainer's decision is enough ([DEC-21](../../descisions.md#dec-21)). |
| Inputs | [governance design](../design/governance.md), section 6.3 |

| Decision | State | Detail |
| --- | --- | --- |
| OD-G1: `policy.py` is the single gate | **Approved** | In answer to a question that proposed building slice 1 with `policy.py` as the single gate, he answered: "Yes, build slice 1 (Recommended)". |
| OD-G2: brain tone may tighten a decision; meaning of confirm in voice | Open | A precondition of R-02.7. |
| OD-G3: `Runner.claim_and_run` bypass | Open | A precondition of R-02.7. Tracked as R-02.F1. |
| OD-G4: HQ jobs through `admit` | Open | A precondition of R-02.7. Tracked as R-02.F2, which applies only if PR #56 merges. |
| OD-G5: GR-1 request pattern | Open | A precondition of R-02.7. |
| OD-G6: which item, which phase, whether an exception is needed | Proposed answer | The roadmap PR that adds this record proposes R-02.7 in PH-02 with no exception tag, because PH-02 is current after PR #58 and policy limits already live in R-02.3. The answer takes effect when a maintainer approves or merges that PR. |
