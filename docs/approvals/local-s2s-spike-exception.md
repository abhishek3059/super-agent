# Local speech-to-speech spike A5: approval and out-of-order work

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Scope | Spike A5 only: measure open-weight native speech-to-speech models on `jeevesh2515`'s MacBook Air M5 (16 GB). Measurement only, no product code. Plan: [spike A5](../../spikes/a5-local-s2s/README.md). |
| Roadmap position | This is PH-07 work ([RT-012](../../tasks/012-private-native-audio-feasibility.md)), done while PH-01 is the current phase. |
| `abhishek3059` | **Requested, 2026-11-13**, in chat with Claude Code. He said to keep the Gemini adapter "as of now we switch to local setup ... try some inferencing" and "yes create a document of this spike". Recorded as his approval to plan and run it. |
| `jeevesh2515` | **Pending.** Approval is the review of [PR 41](https://github.com/abhishek3059/super-agent/pull/41). He also runs the spike on his machine, so his approval covers the hardware, the downloads below, and his own voice in the tests. |
| Effect | Nothing is ticked. PH-07 stays `not started` and no gate moves. |

## Why

`abhishek3059` wants a local path that does not rely on speech-to-text,
because it fails on his accent. A council review on 2026-11-13 also found that
spoken audio is the real privacy gap on the cloud route. See the spike for the
question and the evidence.

## Downloads (rough, from research; not yet verified)

- LFM3-Audio-2B MLX 4-bit: about 1.5 to 2 GB (estimate, unverified).
- MiniCPM-o 4.5 Q4_K_M GGUF set: about 9 GB (reported for the full stack).
- Moshi MLX q4 baseline: size not shown on its page; a 7B model at 4-bit is
  likely several GB (recalled, unverified).

All files stay outside the repository.

## What still needs a decision from both maintainers

1. The pass and fail thresholds in the spike (proposed, not agreed).
2. Whether the LFM Open License v1.0 (custom, $10M revenue cap) is acceptable
   even for a local test.
3. Whether the 14-day rule needs an exception for LFM3, whose repos were 8 to
   17 days old on 2026-11-13.
4. Whether the results count toward R-07.1 and R-07.2 when PH-07 opens.
