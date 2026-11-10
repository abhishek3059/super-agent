# Voice foundation scaffold

This is an offline scaffold. It uses a deterministic local adapter that echoes
PCM audio. It does not use Gemini, persist audio, or provide tools or actions.

## Current state (2026-11-10)

The backend uses the streaming adapter seam from the design (section 4). The
app still runs only the deterministic fake adapter by default. A Gemini Live
adapter exists behind the seam and is covered by offline tests with injected
fakes ([R-01.7 record](../docs/implementation/r01-7-streaming-seam.md)), but it
is not wired into the app and the `google-genai` SDK is not installed. The
opt-in synthetic live command (R-01.8) and the live test (R-01.9) do not exist
yet, so the console cannot connect to Gemini. Personal microphone audio stays
local.

## Backend

Use a private process environment token. Do not create a project `.env` file.

```powershell
$voiceVenv = Join-Path $env:LOCALAPPDATA "Temp\super-agent-voice-venv"
python -m venv $voiceVenv
& "$voiceVenv\Scripts\python" -m pip install --only-binary=:all: -r apps\api\requirements-dev.in
$env:SUPER_AGENT_LOCAL_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:PYTHONPATH = "apps\api\src"
& "$voiceVenv\Scripts\python" -m uvicorn super_agent_voice.app:create_app --factory --host 127.0.0.1 --port 8000
```

## Browser client

In a second PowerShell window:

```powershell
npm ci --ignore-scripts --prefix apps/web
npm start --prefix apps/web
```

Open `http://127.0.0.1:4200`, paste the same local token into the in-memory
field, and select **Start**. Browser permission is requested only then.

The current browser audio processor is a scaffold seam, not accepted audio
quality. Mute suppresses outbound PCM. Interrupt stops local playback and
advances the backend playback epoch. Stop closes tracks, audio context, and
WebSocket resources.

## Checks

```powershell
& "$voiceVenv\Scripts\python" -m pytest apps\api
npm run test:epoch --prefix apps/web
npm run build --prefix apps/web
npm audit --prefix apps/web
npm run check
```

Jeevesh confirmed the cycle and accepted Mac test responsibility. Manual Mac
execution and microphone evidence are still pending. No personal microphone
audio may be forwarded to a cloud provider in this cycle.
