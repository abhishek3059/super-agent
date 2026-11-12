# Local voice stack: hardware approval and out-of-order work

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Scope | Run the voice assistant with no cloud provider on the operator's Mac: a local adapter behind the existing voice seam, opt-in through `SUPER_AGENT_ADAPTER=local`. Conversation only, no tools. |
| Roadmap position | This is PH-07 work ([RT-012](../../tasks/012-private-native-audio-feasibility.md)), done while PH-01 is the current phase. |
| `jeevesh2515` | **Approved, 2026-11-12**, in chat with Claude Code (`claude-fable-5-2`): the hardware (MacBook Air M5, 16 GB), about 9 GB of model downloads, English first, and doing this work now. |
| `abhishek3059` | **Pending.** Approval is the review of the PR that carries this record. |
| Effect | Nothing is ticked. PH-07 stays `not started` and no gate moves. The default adapter is still the fake one. |

## Why now

`jeevesh2515` asked whether the assistant could stay private and inside the
computer instead of using Gemini. A local path also answers the open question
in the capability ladder proposal ([PR 35](https://github.com/abhishek3059/super-agent/pull/35)) about sending
real voice and personal data to a cloud provider, and it keeps the $0 budget.

## What was downloaded

`qwen3.5:9b` through Ollama (6.6 GB), two whisper.cpp models (0.7 GB), and the
Kokoro ONNX model and voices (0.1 GB). All sit outside the repository. Nothing
was installed with a package manager; whisper.cpp 1.8.6 and Ollama 0.32.5 were
already on the machine.

## What still needs a decision from both maintainers

1. Whether this work may merge ahead of PH-02 and PH-03, and whether it counts
   toward R-07.1 and R-07.2 when PH-07 opens.
2. Whether Kokoro may be used: its Python package depends on GPL-3.0 code.
3. Whether the local path replaces Gemini as the PH-01 provider for R-01.10,
   or stays a parallel option.

Measurements: [spike A4](../../spikes/a4-local-voice/README.md).
