# Spike A3: Gemini Live latency and tool calling

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Evidence | [Spike A3 README](../../spikes/a3-gemini-live/README.md) |

## What happened

On the free tier, `gemini-3.8-live` called a job-status tool in 5 of 5 runs.
Median time from question to first spoken audio was 873 ms, including the tool
round trip. Text input and made-up data only.

## What we learned

- The model ends one turn when it requests a tool and speaks in a second turn after the tool response. The first version of the script stopped at the first `turnComplete` and measured nothing. Clients must wait for the turn that carries audio.
- All 5 replies called a job that was waiting for approval "running". Job-state wording needs a prompt or tool-schema fix before users rely on it.
- Replies ran 10 to 13 seconds, which is long for voice.
- Pinning the SDK to a release at least 14 days old (2.31.0, not the day-old 3.0.0) cost nothing and followed [AGENTS.md](../../AGENTS.md).
- Session experience, not in the spike README: a command typed with `!` in the Claude session has no keyboard input, so a silent `read` for the API key saved nothing. Run secret prompts in a real terminal tab.

## What to do differently

Add a "keep answers short, state exact job status" instruction in the next test. Never judge a live session by one `turnComplete`.

## Still unknown

Real microphone input, barge-in, paid-tier cost, other networks, and how the audio actually sounds. No person has listened to the saved audio yet.
