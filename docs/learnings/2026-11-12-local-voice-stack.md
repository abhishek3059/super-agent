# A fully local voice stack runs on a 16 GB Mac

| Field | Value |
| --- | --- |
| Date | 2026-11-12 |
| Evidence | [Spike A4](../../spikes/a4-local-voice/README.md), [approval record](../approvals/local-voice-exception.md) |

## What happened

The operator asked for a private alternative to Gemini. We measured
whisper.cpp, Qwen3.5 9B through Ollama, Kokoro, and macOS `say` on a MacBook
Air M5, then built a local adapter behind the existing voice seam.

## What we learned

- It works for conversation at about two seconds from end of speech to first
  audio. That is slower than the 0.9 s measured for Gemini Live in spike A3.
- A small model will say it did something it never did unless the prompt
  forbids it. Tool rules belong in the prompt and in code.
- Python's default HTTP opener sends loopback requests through a configured
  proxy. An independent review caught this; the offline tests had not.
- The adapter seam held: no change was needed in authentication, the session
  gate, or teardown.

## What to do differently

- Test "does anything leave the machine" as behaviour, not by reading a URL
  constant.
- Measure on the real machine before quoting a latency estimate. The research
  estimate was 1.0 to 1.6 s.

## Still unknown

Accuracy on a real voice and in noise, behaviour on speakers without
headphones, memory headroom with other apps closed, and whether the 4B model
is good enough to halve the delay.
