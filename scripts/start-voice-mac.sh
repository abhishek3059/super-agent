#!/usr/bin/env bash
# Starts the fully local assistant on a Mac: Ollama (loopback only), the voice
# backend, and the console. Stop everything with Ctrl+C.
# Usage: scripts/start-voice-mac.sh [cascade|lfm3]   (default lfm3)
set -euo pipefail
cd "$(dirname "$0")/.."
mode="${1:-lfm3}"
venv="${SUPER_AGENT_VENV:-$HOME/.super-agent/venv}"
[[ -x "$venv/bin/python" ]] || { echo "No Python environment at $venv; see apps/voice-foundation.md"; exit 1; }
[[ -f "$HOME/.super-agent/voice-token" ]] || PYTHONPATH=apps/api/src "$venv/bin/python" -m super_agent_voice.generate_token

# One model in memory at a time keeps the brain and the speech model inside 16 GB.
export OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=30m
pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
listen="$(lsof -nP -iTCP:11434 -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $9}' | sort -u)"
if [[ -z "$listen" ]]; then
  ollama serve >/dev/null 2>&1 & pids+=($!)
  sleep 2
elif [[ "$listen" != "127.0.0.1:11434" ]]; then
  # An Ollama started elsewhere may listen on every network interface.
  echo "Ollama is already listening on: $listen. Quit it, then run this again."; exit 1
fi
echo "Tier 1 read access: ${SUPER_AGENT_T1:-off}${SUPER_AGENT_T1_FOLDERS:+ (folders: $SUPER_AGENT_T1_FOLDERS)}"

export SUPER_AGENT_ADAPTER=local PYTHONPATH=apps/api/src
if [[ "$mode" == "lfm3" ]]; then export SUPER_AGENT_STT=lfm3 SUPER_AGENT_TTS=lfm3; fi
"$venv/bin/python" -m uvicorn super_agent_voice.app:create_app --factory \
  --host 127.0.0.1 --port 8000 --ws-max-size 65600 --ws-max-queue 4 & pids+=($!)
npm start --prefix apps/web & pids+=($!)
echo "Open http://127.0.0.1:4200 and paste the token: pbcopy < ~/.super-agent/voice-token"
wait
