# Voice foundation scaffold

The browser console is a local-only scaffold. It uses a deterministic adapter
that echoes PCM audio. It does not construct the separate Gemini adapter,
persist audio, or provide tools or actions.

## Current state (2026-11-12)

The fake adapter is the only adapter the application uses. A Gemini Live
adapter exists behind the same seam with offline tests
([record](../docs/implementation/r01-7-gemini-adapter.md)), but the application
never constructs it. An opt-in command, `live_check`, ran it once against the
real service with synthetic speech ([record](../docs/implementation/r01-8-live-check.md)).
You can run the local scaffold and test start, mute, barge-in, and stop, but the
console cannot connect to Gemini. Personal microphone audio stays local.

## Synthetic live check (opt-in)

Sends synthetic speech to Google's free tier, which may use inputs for
training. Never run it with personal audio. It is not part of any test run.

```bash
# --wav takes a 16 kHz mono 16-bit file of synthetic speech; without it, macOS `say` is used
GEMINI_API_KEY="$(cat ~/.super-agent/gemini-key)" PYTHONPATH=apps/api/src \
  python -m super_agent_voice.live_check --send-synthetic-audio
```

The output is timing and state only. The key stays in the process environment.
On macOS, the default command also generates two fixed speech clips to check
conversational interruption. The command reports whether it received a
provider `Interrupted` event after queuing the second clip. With `--wav`
the command skips that part.

## Backend

Keep the two `--ws-max-*` flags: without them uvicorn buffers up to 16 MiB per
message before the application can reject it. Do not run the backend at debug log level: it refuses to start and refuses
connections, because frame logging would record the session token.

The backend reads the local token from `~/.super-agent/voice-token`, written
with mode 0600 by the generator below. Do not create a project `.env` file and
do not type the token into a shell command. On Windows the file relies on the
profile directory's ACL; an explicit owner-only ACL is not implemented yet.

### Windows: start both services

From any PowerShell working directory, call the launcher by its path. It uses
its own location to find the repository, installs the locked dependencies,
creates a fresh local token, starts the backend, waits for its health check,
and then runs the frontend. `Ctrl+C` stops both services.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-voice-windows.ps1
```

When calling it outside the repository, replace the relative path with the
full path to the script. The manual commands below remain useful for diagnosis.

```powershell
$voiceVenv = Join-Path $env:LOCALAPPDATA "Temp\super-agent-voice-venv"
python -m venv $voiceVenv
& "$voiceVenv\Scripts\python" -m pip install --only-binary=:all: -r apps\api\requirements-dev.in
$env:PYTHONPATH = "apps\api\src"
& "$voiceVenv\Scripts\python" -m super_agent_voice.generate_token
& "$voiceVenv\Scripts\python" -m uvicorn super_agent_voice.app:create_app --factory --host 127.0.0.1 --port 8000 --ws-max-size 65600 --ws-max-queue 4
```

## Browser client

In a second PowerShell window:

```powershell
npm ci --ignore-scripts --prefix apps/web
npm start --prefix apps/web
```

Open exactly `http://127.0.0.1:4200`, select the blue start control or settings
button, paste the token into the in-memory connection dialog, and select
**Connect locally**. Do not use `localhost`: the page loads through that alias,
but the reviewed backend Origin policy rejects its session. Browser permission
is requested only after the backend authenticates the session.

The browser UI follows the [live voice interface design](../docs/design/live-voice-interface.md).
It keeps the token in memory only, fixes the WebSocket endpoint to the reviewed
loopback address, and maps its colors and labels to real session state. The
copied standalone reference is a design artifact only; its simulated research
states, browser token persistence, and external assets are not used.

The current browser audio processor is a scaffold seam, not accepted audio
quality. Mute suppresses outbound PCM. The spectrum is an input-level display,
not speech detection and not voice activity detection. A loud input
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
npm run test:ui --prefix apps/web
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

`npm run test:ui` covers the status labels, timer formatting, and spectrum
mapping used by the live voice interface. `npm run test:epoch` keeps the 8
focused playback-epoch cases separate.

The R-01.3 Mac offline check covered the earlier scaffold at `4f51e00`.
The [R-01.4 operator test](../docs/approvals/r01-4-microphone-test.md) covered
the revised local scaffold at `a790530`. Personal microphone audio stays local.
