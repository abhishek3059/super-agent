# Tier 1 read access and the local speech model: out-of-order work

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Scope | Build tier T1 read-only tools ([design](../design/tier1-read-tools.md)) and use LFM3-Audio-2B as the assistant's ears and mouth with a Qwen3.5-4B brain, all local, opt-in, on branch `feat/t1-local-tools`. |
| Roadmap position | R-A.4 and R-A.5 start after RT-G02 (PH-02 exit). PH-01 is still current, so this is ahead of the path. |
| `jeevesh2515` | **Requested and approved, 2026-11-13**, in chat with Claude Code (`claude-opus-5-5`): "We'll start with tier 1 ... Make sure the agent can now do at least tier 1." |
| `abhishek3059` | Not required: under [DEC-21](../../descisions.md#dec-21) (2026-11-14) one maintainer's approval is enough. He also reviewed PR #43 on 2026-11-14. |
| Effect | Nothing is ticked and no gate moves. Every T1 tool is off unless the operator enables it. |

## Decided and still open

1. Decided by `jeevesh2515`'s approval above: T1 may merge before PH-02's
   policy layer exists, as an exception to R-A.4 and R-A.5. R-A.4 and R-A.5
   stay unticked.
2. Open: acceptance of the independent security review, which R-A.4 requires.
3. Open: Whether the LFM3-Audio weights (LFM Open License v1.0, free under $10M
   revenue, not bundled) may be the default voice once the spike is accepted.
