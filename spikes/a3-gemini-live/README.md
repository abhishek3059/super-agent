# Spike A3: Gemini Live latency and tool calling

Throwaway spike for assumption A3 in [product direction](../../docs/product/direction.md#assumptions-to-test-riskiest-first).
Not product code. Sends **text only and synthetic job data**: no microphone,
no personal context.

## What it does

1. Opens a Live session with `gemini-3.8-live` (audio output, one tool:
   `get_agent_jobs`).
2. Sends the text question "What are my agent jobs doing right now?".
3. Answers the tool call with two made-up jobs (one running, one waiting for
   approval).
4. Measures each step and saves the first spoken reply to the system temp
   folder as raw PCM.

## Run it

```bash
cd spikes/a3-gemini-live
npm ci --ignore-scripts
node live.mjs
```

Key: `GEMINI_API_KEY`, or the file `~/.super-agent/gemini-key` (mode 0600).
The key is never printed. Dependency: `@google/genai` pinned to 2.31.0
(released 2026-10-23; `npm audit` found 0 vulnerabilities).

Optional settings: `SUPER_AGENT_LIVE_MODEL`, `SUPER_AGENT_RUNS`.

## Results (2026-11-07, free tier, macOS on home network)

5 of 5 runs succeeded and called the tool. Medians:

| Step | Median |
| --- | --- |
| Connect (open session) | 451 ms |
| Question sent to tool call | 308 ms |
| Tool answered to first audio | 591 ms |
| **Question sent to first audio** | **873 ms** |
| Spoken reply length | 12.5 s |

Range of question-to-first-audio: 838 to 1142 ms.

Example transcript (run 4): "You have two agent jobs running. One is editing
`src/auth.ts` to refactor the auth module. The other is waiting for approval
to run `npm test` to fix a flaky test."

**Verdict: A3 holds for latency and tool calling.** First audio under about
1.1 s including a tool round trip, on the free tier.

## Findings

- The model ends one turn when it requests the tool, then speaks in a second
  turn after the tool response. Clients must not treat the first
  `turnComplete` as the end of the answer.
- Answers were faithful to the tool data in all 5 runs, but every run said
  "two agent jobs running" even though one was waiting for approval. Job
  state wording needs a prompt or tool-schema fix before users rely on it.
- Replies are long for voice (10 to 13 s). A system instruction asking for
  short answers is worth testing.

## Not tested yet

- Real microphone input, barge-in, and interruption handling.
- Cost on the paid tier, and free-tier session limits under longer use.
- Network variation (only one home network, one time of day).
- Listening quality: the saved audio was not reviewed by a person in this run.
