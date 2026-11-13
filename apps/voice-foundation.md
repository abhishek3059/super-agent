# Voice foundation scaffold

The browser console is a local-only scaffold. It uses a deterministic adapter
that echoes PCM audio. It does not construct the separate Gemini adapter,
persist audio, or provide tools or actions.

## Current state (2026-11-12)

The fake adapter is the default. A local private adapter is opt-in (see below). A Gemini Live
adapter exists behind the same seam with offline tests
([record](../docs/implementation/r01-7-gemini-adapter.md)), but the application
never constructs it. An opt-in command, `live_check`, ran it once against the
real service with synthetic speech ([record](../docs/implementation/r01-8-live-check.md)).
You can run the local scaffold and test start, mute, barge-in, and stop. By
default the console cannot connect to Gemini and personal microphone audio stays
local. The opt-in Gemini mode below is a testing exception.

## Local private mode (opt-in, macOS)

`SUPER_AGENT_ADAPTER=local` swaps the fake adapter for a fully local pipeline:
Silero for speech detection, whisper.cpp for speech-to-text, a local model
through Ollama, and Kokoro for speech. The only network peer is Ollama on
`127.0.0.1:11434`. The model is told the date and time and has one tool, a
calculator; it cannot read your data or act. The console shows what it heard
and said for the session only. It needs `whisper-cli` and `ollama` on the
PATH and the four model files (Whisper, Kokoro and its voices, Silero) whose
download commands are in
[spike A4](../spikes/a4-local-voice/README.md). Status and approvals:
[record](../docs/approvals/local-voice-exception.md).

```bash
python -m pip install --only-binary=:all: -r apps/api/requirements.lock -r apps/api/requirements-local.lock
OLLAMA_HOST=127.0.0.1:11434 ollama serve    # separate terminal
SUPER_AGENT_ADAPTER=local PYTHONPATH=apps/api/src python -m uvicorn super_agent_voice.app:create_app --factory --host 127.0.0.1 --port 8000 --ws-max-size 65600 --ws-max-queue 4
```

Optional settings: `SUPER_AGENT_LOCAL_MODEL` (default `qwen3.5:9b`),
`SUPER_AGENT_WHISPER_MODEL` (a file name in `~/.super-agent/models`),
`SUPER_AGENT_TTS=say` with `SUPER_AGENT_SAY_VOICE` (the built-in macOS voice,
no extra packages), `SUPER_AGENT_KOKORO_VOICE`, and `SUPER_AGENT_VAD=rms`
(volume threshold, no extra packages).

## Gemini Live mode (opt-in, testing only)

`SUPER_AGENT_ADAPTER=gemini` sends your real microphone audio to Google's free
tier, which may use inputs for training. Speak nothing personal or sensitive.
The model has two tools, a calculator and the local clock, and the console shows
transcripts for the session only. Fake stays the default. Approval status:
[record](../docs/approvals/gemini-live-testing-exception.md). The key comes from
the process environment only; never put it in a file in the repository.

Windows launcher (prompts for the key with masked input, sets the adapter, and
restores your environment on exit):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-voice-windows.ps1 -Gemini
```

Alternative, manual steps:

```powershell
$env:GEMINI_API_KEY = Read-Host "Gemini API key" -MaskInput   # PowerShell 7; this shell only
$env:SUPER_AGENT_ADAPTER = "gemini"
# optional: $env:SUPER_AGENT_GEMINI_MODEL = "gemini-3.8-live"
$env:PYTHONPATH = "apps\api\src"
& "$voiceVenv\Scripts\python" -m uvicorn super_agent_voice.app:create_app --factory --host 127.0.0.1 --port 8000 --ws-max-size 65600 --ws-max-queue 4
```

Startup fails if `GEMINI_API_KEY` is missing. Tool calls and transcripts need a
live run to confirm; the offline tests use fakes only.

## Synthetic live check (opt-in)

Sends synthetic speech to Google's free tier, which may use inputs for
training. Never run it with personal audio. It is not part of any test run.

```bash
# --wav takes a 16 kHz mono 16-bit file of synthetic speech; without it, macOS `say` is used
GEMINI_API_KEY="$(cat ~/.super-agent/gemini-key)" PYTHONPATH=apps/api/src \
  python -m super_agent_voice.live_check --send-synthetic-audio
```

On Windows (PowerShell), speech comes from Windows SAPI and the command asks
for the key if `GEMINI_API_KEY` is not set:

```powershell
$env:PYTHONPATH = "appspi\src"; & "$env:LOCALAPPDATA\Temp\super-agent-voice-venv\Scripts\python.exe" -m super_agent_voice.live_check --send-synthetic-audio
```

The output is timing, state, tool names, and character counts only. The key
stays in the process environment. A good result: the last line shows
`"reached_gemini": true` and `"tools_ok": true`, and `unsupported-model` fails
closed. The `tool-calculate` step lists `calculate` and `tool-clock` lists
`current_time` under `tools`.

The backend also prints state-only status lines (adapter name, connect time,
per-turn audio size, time to first audio since the previous turn boundary,
allowlisted tool names, interruptions, session close). They never include
audio, transcripts, tool arguments, or keys. `adapter=gemini-live` there shows
the session reached Gemini.

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

The R-01.3 Mac offline check is complete, although it covered the earlier
scaffold at `4f51e00`. The revised-scaffold human microphone test, R-01.4, is
still pending. No personal microphone audio may be forwarded to a cloud
provider in this cycle.
