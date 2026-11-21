# Jarvis HQ synthetic voice check

2026-11-17. This is the opt-in [R-H.3](../../roadmap.md#parallel-track-h-jarvis-hq-local-team-dec-23)
probe, using macOS `say`, `afconvert`, and a fresh loopback HQ instance.
The [R-H.1 record](../approvals/jarvis-hq-dec-23-approval.md) authorizes up to
US$5 per month of OpenAI voice spend. R-A.2 remains open. Keep the owner,
chat history, bot memory, work and speech synthetic.

## OpenAI contract checked on 2026-11-17

- Realtime session model, ephemeral client-secret request at
  `POST /v1/realtime/client_secrets`, and the browser WebSocket protocols.
  [Model](https://developers.openai.com/api/docs/models/gpt-realtime-2.1),
  [client secret](https://developers.openai.com/api/reference/resources/realtime/subresources/client_secrets/methods/create),
  [WebSocket guide](https://developers.openai.com/api/docs/guides/voice-websockets?voice-api=realtime)
- GA events include `response.function_call_arguments.done`,
  `response.output_audio.delta` and `input_audio_buffer.speech_started`.
  The client cancels by response ID. It delegates only completed function
  calls from completed responses. For browser playback it also clears
  queued audio and truncates the unheard portion.
  [Client events](https://developers.openai.com/api/reference/resources/realtime/client-events),
  [server events](https://developers.openai.com/api/reference/resources/realtime/server-events),
  [interruption guidance](https://developers.openai.com/api/docs/guides/realtime-conversations)
- `gpt-transcribe` is supported for input transcription and dictation.
  `gpt-4o-mini-tts` is supported for the separate speech preview endpoint
  and scheduled for shutdown on January 6, 2027. Preview and dictation are
  outside this probe.
  [Transcription](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create),
  [speech preview](https://developers.openai.com/api/docs/guides/text-to-speech)

## Results

Offline check: `PASS offline synthetic-audio and request checks`.
A simulated Realtime run passed the full probe state sequence.

Actual loopback HQ with the key disabled:

```text
[1803 ms] synthetic PCM ready
[1832 ms] fresh synthetic owner and team verified
[1833 ms] FAIL mint Realtime session (HQ /api/voice/session HTTP 409)
```

That run did not reach OpenAI.

## Live run, 2026-11-19

The operator's OpenAI key came from the process environment only and was never
printed. HQ ran on a fresh owner-only data folder (`HQ_DATA_DIR`), port 8797,
owner "Voice Check", with synthetic speech from macOS `say`. Four runs, one
fresh folder each:

| Run | Result | Cause | Fix |
| --- | --- | --- | --- |
| 1 | FAIL at 84 s | Each bot's first gateway start installs Hermes dependencies (about 50 s). The egress proxy also refused part of that download burst as `busy`. | Probe deadline 84 s to 234 s. Egress lookup cap 32 to 256. |
| 2 | FAIL at 234 s | Gateways from run 1 still held the engine ports. HQ could not see them: a relaunched Hermes runs as `python3 -I -c <script>`, with no home path in its arguments. | `gatewayPid` also accepts a listener whose working folder is the bot's home. New self-check case in `lifecycle.test.ts`. |
| 3 | FAIL at 234 s | The chain worked, but example.com no longer has an `<h1>`. Scout correctly said so. | The probe asks for the page title (still "Example Domain"). |
| 4 | **PASS** in 123 s | | |

Run 4 output: [saved output](evidence/rh3-voice-check-output-20261119.txt).
Run 4 used the code in the commit that adds this record (9a450dd plus these
fixes). Only runs 1 to 4 used OpenAI, about a minute of Realtime audio each.
Their cost was not measured here. Check it on the OpenAI usage page against
the US$5 monthly cap.
It covers connect, a `send_task` tool call handed to Jarvis, the handoff to
Scout, Scout's browser result, the spoken result, barge-in with
`response.cancel`, and no further audio after the cancel. The probe then
ended the call. R-H.3 is met.

The run 2 bug also affects normal use. After the 60-second cache expired,
HQ lost track of a relaunched gateway. It then refused to start the bot
("Port is taken by a process this app did not start") until someone killed
that gateway by hand.

Observed and not fixed here:

- The operator's Hermes default model, `nvidia/nemotron-3-super-120b-a12b`,
  returns HTTP 410 (retired 2026-10-03). Bots reach a fallback provider,
  which costs about 40 seconds per turn. Fix this in the operator's
  `~/.hermes/config.yaml`, not in HQ.
- Hermes warns that the bot home "is read-only" and falls back to JSONL
  sessions. Its own kanban ticks fail. The sandbox causes this: it denies
  writes to the home folder itself so a bot cannot swap it, and Hermes's
  writability check then fails. HQ does not use the Hermes kanban.
- Hermes' shutdown-watchdog socket path is too long (`AF_UNIX path too
  long`). Liveness probes lose one signal and nothing else.
- Each fresh bot installs its own Hermes dependencies, about 1 GB per bot.

The browser call (a person speaking through the web client) was not part
of this probe.

## Browser worklet fix, 2026-11-20

Chrome reproduced `AbortError` when loading the microphone worklet from a
blob URL under HQ's same-origin script policy. The built web app now serves
the processor as a hashed same-origin JavaScript asset. Chrome registered
it under the existing policy and emitted a 960-sample PCM frame at 24 kHz.

The browser checks used synthetic input. With voice disabled on the local
server, clicking Start voice chat reported the missing provider before
opening the microphone. With availability simulated, the browser
released the microphone after both a worklet failure and a rejected
session request. A live provider call was not run.

## Preview OpenAI connection, 2026-11-20

The restarted preview reported voice enabled. It minted a Realtime client
secret, received OpenAI's `session.created` event and closed the call.
The probe sent no audio or chat content. The operator separately reported
that a manual voice call worked. The manual call was not independently
observed and no audio or transcript was retained as evidence.
