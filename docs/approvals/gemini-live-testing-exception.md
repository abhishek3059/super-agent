# Gemini Live in the console: testing exception to the data boundary

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Scope | Real microphone audio from the voice console goes to Gemini Live, for testing by the maintainers only. Opt-in through `SUPER_AGENT_ADAPTER=gemini`; the model has two tools, a calculator and the local clock. |
| Departs from | The PH-00 data boundary (R-00.4, "personal microphone audio stays local"), [AGENTS.md](../../AGENTS.md) section 5, [REQ-13](../../prd.md#req-13), and the open decision R-A.2 (see [DEC-18](../../descisions.md#dec-18)). |
| `abhishek3059` | **Approved, 2026-11-13**, in chat with Claude Code: "it's testing time as of now; we don't require a privacy feature because nobody is using it". |
| `jeevesh2515` | **Approved, 2026-11-13**, in a [PR #41 review](https://github.com/abhishek3059/super-agent/pull/41#pullrequestreview-5893054740). |
| Effect | Nothing is ticked and no gate moves. The default adapter is still the fake one. |

## Conditions

1. Nobody speaks personal or sensitive topics. The free tier may use inputs for training.
2. Opt-in only. The fake adapter stays the default and CI never uses Gemini.
3. The key comes from the process environment only. It is never logged, printed, or committed. Transcripts are shown in the console for the session only and are never logged.
4. Tools are limited to the calculator and the clock. Like the calculator in [PR 36](https://github.com/abhishek3059/super-agent/pull/36), this is a small widening of tier T0 that both maintainers should confirm in review.
5. This exception expires when R-A.2 is decided. Until then it covers testing only, not users.

## Still open

Whether the data-boundary decision (R-A.2, OD-1) allows real voice to a cloud provider for anyone beyond the maintainers. This record does not answer it.
