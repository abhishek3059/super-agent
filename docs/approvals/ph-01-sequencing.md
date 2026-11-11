# PH-01 sequencing decision

| Field | Value |
| --- | --- |
| Date | 2026-11-10 |
| Scope | Order of the PH-01 roadmap items only |
| Proposal | `abhishek3059`, in the [R-01.4 observations](../implementation/r01-4-microphone-observations.md), "Proposed execution change, not approved" |
| `jeevesh2515` | **Approved, 2026-11-10**, in chat with Claude Code (`claude-opus-5-5`), which recorded it at his instruction |
| `abhishek3059` | **Approved**, by merging PR #27 on 2026-11-10T19:32Z (GitHub merge commit `2849361`; the rebased branch carries this record as commit `9092bd0`) |
| Gates | Unchanged. No PH-01 item is removed, waived, or ticked by this decision. [phases.md](../../phases.md) is unchanged because no gate moves. |

## Why

The R-01.4 microphone test cannot pass on the current offline scaffold. The fake
adapter echoes every frame, so silence shows `speaking`, and its own echo can
trigger the energy-based interruption. A microphone test now would measure that
defect, not the product. The observations record already says not to repeat
the same test until the defect is fixed.

## Decision

PH-01 work proceeds in this order (see [roadmap.md](../../roadmap.md)):

1. R-01.3 Mac offline checks (run 2026-11-10, awaiting tick).
2. R-01.5 credential design and its independent review.
3. R-01.7 streaming seam and Gemini Live adapter, with offline tests using the fake and scripted events.
4. **R-01.F1 (new fix item)**: input level shown separately from model speech, silent frames never set `speaking`, conversational barge-in is the tested path, with offline tests for silence, playback, interruption, stale output, mute, and stop.
5. R-01.4 local microphone test on the revised scaffold. Conversational barge-in is the acceptance path; the Interrupt button alone cannot satisfy it.
6. R-01.6 independent security review of the implemented boundary, completed **before** any live provider call.
7. R-01.8 opt-in synthetic-audio live command.
8. R-01.9 synthetic live test.
9. R-01.10 RT-002, RT-003, and RT-G01 evidence.

## What does not change

- PH-01 closes only when every item above is ticked with evidence.
- Live provider execution stays synthetic-only. Personal microphone audio to Gemini still needs a separate approval and a reviewed data boundary.
- The $0 budget, the AGENTS.md security invariants, and the independent reviews stay mandatory.
- R-01.4 is not waived. It moves later and is tested against the revised scaffold.
