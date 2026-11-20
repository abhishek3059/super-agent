# Governance gate: maintainer decisions

| Field | Value |
| --- | --- |
| Roadmap item | R-02.7 |
| Date | 2026-11-19 (OD-G1; OD-G2 to OD-G5 later the same day) |
| Decided by | `abhishek3059`, in chat with Claude Code (`claude-opus-5-5`), which wrote this record from his answers to multiple-choice questions. One maintainer's decision is enough ([DEC-21](../../descisions.md#dec-21)). |
| Inputs | [governance design](../design/governance.md), section 6.3 |

| Decision | State | Detail |
| --- | --- | --- |
| OD-G1: `policy.py` is the single gate | **Approved** | In answer to a question that proposed building slice 1 with `policy.py` as the single gate, he answered: "Yes, build slice 1 (Recommended)". |
| OD-G2: brain tone may tighten a decision; meaning of confirm in voice | **Approved** | Answer: "Tighten only, confirm=refuse (Recommended)". The chosen option's text: a tone signal may only make a decision stricter, never looser, and until T3 exists a `confirm` verdict in voice is a refusal with a spoken reason. |
| OD-G3: `Runner.claim_and_run` bypass | **Approved** | Answer: "Route through the gate (Recommended)". The chosen option's text: keep it for the Hermes workers, make it call `policy.admit`, and fix its tool names to real ones. Tracked as R-02.F1. |
| OD-G4: HQ jobs through `admit` | **Approved** | Answer: "Yes, must pass admit (Recommended)". HQ jobs pass `policy.admit`. From the design (section 6.1), not the answer: an error counts as block, as the gate fails closed. Was tracked as R-02.F2. PR #56 merged on 2026-11-19 (`c662a12`) as the self-contained `apps/hq` app with its own job store and no change to `apps/api`, so there is no HQ admission path and R-02.F2 was removed from the roadmap. OD-G4 applies again only if HQ is later connected to the owner ledger. |
| OD-G5: GR-1 request pattern | **Open, direction given** | Offered a word list, a word list with an ask fallback, or a local model classifier. He chose none and wrote: "we need to think on the idea on understanding the user intentions on the problem, understand what the user is meaning emotionally what type of response to give". So the pattern needs a design for understanding intent and emotional meaning, and for choosing the type of response. OD-G5 is a precondition of slice 2b (GR-1) only, not of slices 1, 2, 3 or 4, which change no behaviour. |
| OD-G6: which item, which phase, whether an exception is needed | Proposed answer | [PR 59](https://github.com/abhishek3059/super-agent/pull/59), which adds this record, proposes R-02.7 in PH-02 with no exception tag, because PH-02 is current after PR #58 and policy limits already live in R-02.3. The answer takes effect when a maintainer approves or merges that PR. |
