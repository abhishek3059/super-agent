# Local voice stack: hardware approval and out-of-order work

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Scope | Run the voice assistant with no cloud provider on the operator's Mac: a local adapter behind the existing voice seam, opt-in through `SUPER_AGENT_ADAPTER=local`. Conversation plus one calculator function; it cannot read data or act (see the second-session decisions below). |
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
Kokoro ONNX model and voices (0.1 GB). All sit outside the repository. The Silero speech-detection model (2.3 MB, MIT) was added in the second
session. whisper.cpp 1.8.6 and Ollama 0.32.5 were already on the machine. The
second session also installed Python packages with pip, listed in
`apps/api/requirements-local.lock`.

## Decisions on 2026-11-12 (second session)

`jeevesh2515` said in chat with Claude Code (`claude-fable-5-2`):

- **Kokoro is approved, GPL-3.0 dependency included.** He stated the approval is
  from both maintainers. `abhishek3059`'s part is recorded here as reported by
  `jeevesh2515`; it is confirmed when `abhishek3059` approves the PR.
- **Add a few necessary tools and improve the console.** The agent added only
  what stays inside tier T0: the model is told the date and time, and it can
  call one fixed calculator function. Neither reads personal data, uses the
  network, or changes anything. DEC-18 says T0 has no tools, so the calculator
  is a small widening of T0 that both maintainers should confirm in review.
  Calendar, email, files, reminders, and any action remain T1 to T3 and were
  not built: each needs its approved design and security review first.

## Decision on 2026-11-13 (OD-8)

`abhishek3059` asked in review of PR 36 for macOS `say` to be the default voice
and Kokoro to be opt-in, because Kokoro's packages include GPL-3.0 code and the
repository is MIT. He accepted the calculator as a small widening of T0.
`jeevesh2515` passed that request to Claude Code (`claude-opus-5-5`) in chat and asked it to continue with it; he did not object to the change. The default
install no longer pulls any GPL-3.0 package; Kokoro's packages moved to
`apps/api/requirements-kokoro.lock`.

## What still needs a decision from both maintainers

1. Whether this work may merge ahead of PH-02 and PH-03, and whether it counts
   toward R-07.1 and R-07.2 when PH-07 opens.
2. Whether DEC-18 should state that a fixed calculator is allowed in T0 (both maintainers accepted it for this PR).
3. Whether the local path replaces Gemini as the PH-01 provider for R-01.10,
   or stays a parallel option.

Measurements: [spike A4](../../spikes/a4-local-voice/README.md).
