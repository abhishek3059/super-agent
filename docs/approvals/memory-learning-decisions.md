# Memory learning decisions: OD-15 to OD-18

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Scope | The open decisions OD-15 to OD-18 in the [brain overview](../design/brain/overview.md#10-open-maintainer-decisions): learning from conversation, transcripts, retention, and job checkpoints. Design only. |
| `abhishek3059` | **Approved, 2026-11-13**, in chat with Claude Code (`claude-opus-5-5`): "yes I agree with the recommendations, record my approval". |
| `jeevesh2515` | **Pending.** His approval is the review of [PR 40](https://github.com/abhishek3059/super-agent/pull/40). |
| Effect | Nothing is built, ticked, or enabled. Until both maintainers approve, the decisions stay open. OD-18 also needs the [PH-00 setup decisions](ph-00-setup-decisions.md) amended by both maintainers, because that record sets a 24-hour job-metadata purge. |

## What was approved

| ID | Choice | Short form |
| --- | --- | --- |
| OD-15 | (c) | The memory distiller writes `inferred` records automatically after each session. Sensitive categories need confirmation on screen. Rules: [memory, section 9](../design/brain/memory.md#9-proposed-revision-2026-11-13-learning-from-conversation). |
| OD-16 | (a) | The raw transcript is discarded after distilling. |
| OD-17 | 90 days, adjustable | Episodes and unreinforced `inferred` records last 90 days. Decisions and commitments stay until they are done or forgotten, then follow the 90-day rule. |
| OD-18 | (b) | Task specs, verified checkpoints, and the stop reason are kept for 30 days, so an interrupted job can be resumed ([evaluation, section 12](../design/brain/evaluation.md#12-acceptance-scenario-the-interrupted-trip)). |

## Why

`abhishek3059` wants the companion to learn his preferences, decisions, and
habits from conversation, on the device, and to pick up interrupted work
days later. Without these choices the assistant remembers only what it is
told explicitly, and an interrupted task is lost after 24 hours.

## Still to do after both approve

1. A DEC entry in [descisions.md](../../descisions.md) records the change to
   memory principles 2 and 3 (a new `session_end` origin for the distiller).
2. An amendment to the PH-00 retention record for OD-18.
3. Roadmap items for the memory layer, through a roadmap PR (the proposed
   R-M lines in the overview, section 12).
