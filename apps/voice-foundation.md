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

`SUPER_AGENT_ADAPTER=local` swaps the fake adapter for a fully local
assistant. The only network peer is Ollama on `127.0.0.1:11434`; model names
containing `cloud` are refused because Ollama would forward them off the
machine.

| Part | Default | Faster, more natural option |
| --- | --- | --- |
| Hearing | whisper.cpp `base.en` | LFM3-Audio-2B (`SUPER_AGENT_STT=lfm3`) |
| Brain | `qwen3.5:4b` in Ollama (`SUPER_AGENT_LOCAL_MODEL`) | `qwen3.5:9b` if nothing else is loaded |
| Voice | macOS `say` | LFM3-Audio-2B (`SUPER_AGENT_TTS=lfm3`), or Kokoro (`kokoro`, GPL dependencies) |
| Speech detection | Silero | `SUPER_AGENT_VAD=rms` |

The brain can do arithmetic and, if you enable it, read your files, calendar,
notes, and mail (tier T1, [design](../docs/design/tier1-read-tools.md)). It
cannot change, send, or delete anything. T1 is off unless you set
`SUPER_AGENT_T1` (any of `files,calendar,notes,mail`) and, for files,
`SUPER_AGENT_T1_FOLDERS`.

With `SUPER_AGENT_MEMORY=on` it also remembers facts and sets reminders in a
local file, `~/.super-agent/memory.db`, and can forget them (tier T2,
[design](../docs/design/local-memory-reminders.md)). Due reminders are spoken
between turns while a session is open.

### Start it on a Mac

One-time setup (Python 3.12, about 9 GB of models outside the repository):

```bash
python3.12 -m venv ~/.super-agent/venv
~/.super-agent/venv/bin/python -m pip install --only-binary=:all: -r apps/api/requirements.lock \
  -r apps/api/requirements-local.lock -r apps/api/requirements-lfm3.lock
OLLAMA_HOST=127.0.0.1:11434 ollama pull qwen3.5:4b
```

Model files go in `~/.super-agent/models` ([spike A4](../spikes/a4-local-voice/README.md)
for Whisper and Silero) and `~/.super-agent/models/a5` (LFM3-Audio, see the
spike A5 record).

Then, from the repository:

```bash
SUPER_AGENT_MEMORY=on SUPER_AGENT_T1=files SUPER_AGENT_T1_FOLDERS="$HOME/super-agent-t1-demo" \
  scripts/start-voice-mac.sh lfm3
```

Open <http://127.0.0.1:4200>, run `pbcopy < ~/.super-agent/voice-token`, paste
the token, and connect. Use `cascade` instead of `lfm3` for whisper.cpp and
`say`.

Memory: the launcher keeps one Ollama model loaded at a time. LFM3-Audio and
the 4B brain together use about 5 GB; the 9B brain next to LFM3-Audio was
killed on a 16 GB Mac. Close heavy apps first. To let the assistant read
Calendar, Notes, or Mail, allow the macOS Automation prompt the first time.
Tier 1 tools are macOS-only: on any other system, setting `SUPER_AGENT_T1`
stops the session before it starts.

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

On macOS and Windows, the default command also generates two fixed speech clips to check
conversational interruption. The command reports whether it received a
provider `Interrupted` event after queuing the second clip. With `--wav`
the command skips that part and prints `barge-in` as skipped.

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

`npm run test:voice` runs 41 offline service-level cases against the real
transpiled service with hand-written fake WebSocket, AudioContext, and
getUserMedia objects: it covers refusal to capture with an unexpected or missing
provider, silence until ready, audible-gated speaking
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
