# Voice foundation scaffold

This is an offline scaffold. It uses a deterministic local adapter that echoes
PCM audio. It does not use Gemini, persist audio, or provide tools or actions.

## Current state (2026-11-09)

The fake adapter is the only adapter implemented. The Gemini Live adapter and
the opt-in synthetic live command are not implemented (R-01.7 to R-01.9). You
can run the local scaffold and test start, mute, barge-in, and stop, but it
cannot connect to Gemini. Personal microphone audio stays local.

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
