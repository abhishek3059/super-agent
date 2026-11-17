# Jarvis operator preview

This preview adds the workspace and the initial OpenAI tool-call check to the
voice foundation. It preserves the existing offline, Gemini and local voice
modes. The [roadmap](../../roadmap.md) and [delivery-scope PR](https://github.com/abhishek3059/super-agent/pull/51)
define the remaining product and runtime gates.

## Launch the workspace

Use the backend and frontend in the [local setup guide](../../apps/voice-foundation.md).
Open the exact loopback console address shown there. In local connection
settings paste the launcher token and select **Connect workspace**. This
opens a separate authenticated WebSocket and does not request a microphone.

The UI displays five named worker slots, whether each can accept work, and
up to five jobs with active work kept visible. The default app has no worker connection. In an
integration test, provision the app with a `JarvisRuntime` and a verified
Hermes transport for each selected slot. The home installation's gateway,
subscription credentials and desktops are never automatically imported.
The [local Hermes smoke test](../../spikes/a7-hermes-runs/README.md) starts
temporary gateway processes with a synthetic model and no active account.

Change **Skin** between Ember, Carbon and Paper. When a test worker is ready,
choose it, enter a synthetic request and select **Send request**. An admitted
job has an ID. A completed job has a matching Hermes receipt and bounded
result. **Stop job** records a request, followed by a confirmed result or an
unknown outcome. Browser refresh can reattach to the same running server.
Job state is in memory and is lost on server shutdown.

## OpenAI synthetic tool check

The standalone check uses the [OpenAI Realtime WebSocket](https://developers.openai.com/api/docs/guides/voice-websockets?voice-api=realtime)
and the pinned `gpt-realtime-2.1` model. It has one network recipient,
`api.openai.com`, with TLS, no redirects, no ambient proxy, no fallback and a
35-second deadline. Use it only after the implementation permission and the
project API key are in place. The authorized test input is a built-in phrase
spoken by the OS synthesizer. The check enables a local arithmetic tool.
It never requests a microphone, accepts a WAV path, or sends job and memory
contents. The provider receives the generated PCM and the calculator result.
Provider processing and retention follow the operator project's [API data controls](https://developers.openai.com/api/docs/guides/your-data).
Consult the selected account settings before sending actual user audio.
The live OpenAI check has not been run in this work bundle.

Use the backend environment with `OPENAI_API_KEY` supplied only to this
process. From the checkout:

```sh
PYTHONPATH=apps/api/src python -B -m super_agent_voice.openai_live_check --send-synthetic-audio
```

Look for `calculator_verified`, `completed`, and `closed` set to true and a
positive `output_bytes`. This checks the calculated result and that PCM comes
back. It does not verify what the returned audio says, device playback or
latency during operator speech. Logs contain timings and states only.

## Evidence and product gaps

- The client verifies a server proof before sending its own proof or requesting
  microphone capture. Voice and workspace proofs use separate message domains.
  This protects the trusted loopback console against an impersonating listener.
  Same-user compromise, active traffic relay and connection-slot exhaustion
  still require separate mitigations.
- The workspace integration tests cover replay, overlapping jobs, confirmation
  of cancellation and reconnect. A browser smoke check exercised the production
  Angular build, the local proof, theme selection, request and receipt using a
  scripted worker. The voice session stayed disconnected.
- The five workers still need separately contained runtimes and desktop view and
  takeover. The release also requires persistent job recovery and memory in the
  workspace, scoped peer handoff, supported account configuration, a live voice
  job and playback run, capability verification and the 95/100 product score.
