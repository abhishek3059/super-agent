# Voice foundation scaffold

This is an offline scaffold. It uses a deterministic local adapter that echoes
PCM audio. It does not use Gemini, persist audio, or provide tools or actions.

## Current state (2026-11-09)

The fake adapter is the only adapter implemented. The Gemini Live adapter and
the opt-in synthetic live command are not implemented (R-01.7 to R-01.9). You
can run the local scaffold and test start, mute, barge-in, and stop, but it
cannot connect to Gemini. Personal microphone audio stays local.

## Backend

The backend reads the local token from `~/.super-agent/voice-token`, written
with mode 0600 by the generator below. Do not create a project `.env` file and
do not type the token into a shell command. On Windows the file relies on the
profile directory's ACL; an explicit owner-only ACL is not implemented yet.

```powershell
$voiceVenv = Join-Path $env:LOCALAPPDATA "Temp\super-agent-voice-venv"
python -m venv $voiceVenv
& "$voiceVenv\Scripts\python" -m pip install --only-binary=:all: -r apps\api\requirements-dev.in
$env:PYTHONPATH = "apps\api\src"
& "$voiceVenv\Scripts\python" -m super_agent_voice.generate_token
& "$voiceVenv\Scripts\python" -m uvicorn super_agent_voice.app:create_app --factory --host 127.0.0.1 --port 8000
```

## Browser client

In a second PowerShell window:

```powershell
npm ci --ignore-scripts --prefix apps/web
npm start --prefix apps/web
```

Open `http://127.0.0.1:4200`, paste the contents of the token file into the in-memory
field, and select **Start**. Browser permission is requested only then.

The current browser audio processor is a scaffold seam, not accepted audio
quality. Mute suppresses outbound PCM. The microphone meter is an input level
meter, not speech detection and not voice activity detection. A loud input
while model audio plays barges in automatically and advances the backend
playback epoch; the separate **Stop playback** button is a manual fallback.
Stopping (or any redacted error) stops the microphone tracks and closes or
detaches the WebSocket, and **Start** is available again from the recorded
stopped or error state. Stopping also attempts the audio-context close, but
the release is not forced and stays unconfirmed if the close hangs, throws,
or rejects; the session is already fully detached when that happens, so the
page state is correct either way. A restart accepts the fresh epoch 0 the
backend sends. If the browser initially suspends the audio context, the
session resumes it before any microphone PCM ships and before the page claims
a listening state.

## Checks

```powershell
& "$voiceVenv\Scripts\python" -m pytest apps\api
npm run test:epoch --prefix apps/web
npm run test:voice --prefix apps/web
npm run build --prefix apps/web
npm audit --prefix apps/web
npm run check
```

`npm run test:voice` runs 39 offline service-level cases against the real
transpiled service with hand-written fake WebSocket, AudioContext, and
getUserMedia objects: it covers silence until ready, audible-gated speaking
and the 24 kHz metadata rate, untagged and stale-epoch dropping, mute and
unmute, automatic barge-in (once per pending interrupt), stop with a silent
event source, late permission grants and rejections against stopped and newer
sessions, a duplicate ready failing closed, deferred or failing audio-context
closes versus a concurrent restart, restart from the error state, the fresh
epoch 0 after restart, capture factory failures, an initially suspended
context resuming before listening and before any microphone PCM ships, stale
socket handler regression, muted restart inheritance, a closing socket
without its close event never publishing listening, audible playback during a
deferred resume keeping speaking after the resume, and invalid metadata,
odd, oversized, untagged, and malformed payloads. No microphone, provider
call, or key is involved.

Jeevesh confirmed the cycle and accepted Mac test responsibility. Manual Mac
execution and microphone evidence are still pending. No personal microphone
audio may be forwarded to a cloud provider in this cycle.
