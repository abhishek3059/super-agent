#!/usr/bin/env bash
# Starts the Gemini Live console on a Mac: the voice backend and the console.
# Your real microphone audio goes to Google's free tier (testing only, see
# docs/approvals/gemini-live-testing-exception.md). Stop everything with Ctrl+C.
# The key is read from ~/.super-agent/gemini-key (mode 0600) and is never printed.
# Optional switches, each off unless set to "on" before you run this:
#   SUPER_AGENT_WEATHER  SUPER_AGENT_MEMORY  SUPER_AGENT_ACTIONS  SUPER_AGENT_RECAP
set -euo pipefail
unset GEMINI_API_KEY  # only the backend below gets the key, never the console
cd "$(dirname "$0")/.."
venv="${SUPER_AGENT_VENV:-$HOME/.super-agent/venv}"
[[ -x "$venv/bin/python" ]] || { echo "No Python environment at $venv; see apps/voice-foundation.md"; exit 1; }
[[ -f "$HOME/.super-agent/voice-token" ]] || PYTHONPATH=apps/api/src "$venv/bin/python" -m super_agent_voice.generate_token

key_file="$HOME/.super-agent/gemini-key"
[[ -f "$key_file" && ! -L "$key_file" ]] || { echo "No key file at $key_file"; exit 1; }
[[ "$(stat -f %Lp "$key_file")" == "600" ]] || { echo "$key_file must be mode 600: chmod 600 $key_file"; exit 1; }
key="$(<"$key_file")"
[[ -n "$key" ]] || { echo "$key_file is empty"; exit 1; }

pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
echo "Gemini Live: your microphone audio goes to Google's free tier."
echo "Weather: ${SUPER_AGENT_WEATHER:-off} (the place name goes to Open-Meteo)"
echo "Memory and reminders: ${SUPER_AGENT_MEMORY:-off} (newest facts and tool results go to Google)"
echo "Approved actions: ${SUPER_AGENT_ACTIONS:-off}${SUPER_AGENT_ACTION_APPS:+ (apps: $SUPER_AGENT_ACTION_APPS)}"
echo "Conversation recap: ${SUPER_AGENT_RECAP:-off} (kept in ~/.super-agent/recap.json for 7 days)"

export SUPER_AGENT_ADAPTER=gemini PYTHONPATH=apps/api/src
# The key goes to the backend only, not to the console process.
GEMINI_API_KEY="$key" "$venv/bin/python" -m uvicorn super_agent_voice.app:create_app --factory \
  --host 127.0.0.1 --port 8000 --ws-max-size 65600 --ws-max-queue 4 & pids+=($!)
echo "Open http://127.0.0.1:4200 and paste the token: pbcopy < ~/.super-agent/voice-token"
# In the foreground, so the script ends (and the backend is killed) when the console exits.
npm start --prefix apps/web
