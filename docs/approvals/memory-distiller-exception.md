# Memory distiller: out-of-order work

| Field | Value |
| --- | --- |
| Date | 2026-11-18 |
| Scope | The first slice of the memory distiller ([memory design, section 9](../design/brain/memory.md#9-proposed-revision-2026-11-13-learning-from-conversation)), on branch `feat/memory-distiller`. Record: [memory distiller](../implementation/memory-distiller.md). |
| Roadmap position | Not on the roadmap, and off the current phase (PH-01, R-01.10 still open). Roadmap items for the memory layer need a separate roadmap PR. |
| `abhishek3059` | **Requested and chose, 2026-11-18**, in chat with Claude Code (`claude-opus-5-5`): he asked for the self-learning pattern to be implemented now and chose "Learn the user", meaning build the approved memory distiller. The design was approved on 2026-11-13 ([OD-15 to OD-18](memory-learning-decisions.md)). |
| `jeevesh2515` | Not required: under [DEC-21](../../descisions.md#dec-21) one maintainer's approval is enough. |
| Effect | Nothing is ticked and no gate moves. Off by default: it runs only with `SUPER_AGENT_LEARN=on` and `SUPER_AGENT_MEMORY=on`. |

## Still open

1. A DEC entry for the change to memory principles 2 and 3 (follow-up, not added here).
2. Roadmap items through a roadmap PR.
3. The "What I learned" screen, which the design requires before sensitive items can be held and confirmed.
