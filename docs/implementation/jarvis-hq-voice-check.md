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

R-H.3 remains open. No OpenAI connection, live spoken result, or live
barge-in was tested in this run. The browser call is also pending.
