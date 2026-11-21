# Jarvis HQ maintainer pilot

Use this guide for the first integrated WSL2 run. It covers the hosted picker,
desktop and sign-in, semantic memory, and the Linux sandbox. The candidate
is PR #77, which includes the #76 memory branch for testing. The merge order
remains #73, #74, #75, #76, #77. The roadmap tracks physical WSL2 evidence
under R-H.7. A green Linux CI run does not establish that evidence.

## Before running

- Use your own accounts, a fresh data directory and synthetic text and audio.
  Leave real folders, skills, desktop context and scheduled jobs out of this
  run. Use the existing [DEC-23 approval](../approvals/jarvis-hq-dec-23-approval.md)
  for any opt-in OpenAI voice test. R-A.2 is decided for
  [maintainer testing only](../approvals/r-a2-cloud-personal-data.md).
  The acceptance checks below still use synthetic data.
- Keep Ubuntu's files on the Linux disk. Install Node.js 22, system Python
  and a Hermes runtime available to the sandbox. Hermes v0.22.2 is the known
  macOS baseline. Confirm the actual Linux version during the pilot. Install
  Chrome or a native Chromium package inside Ubuntu and follow the
  [launcher prerequisites](../../apps/hq/README.md#windows-wsl2).
- The Windows browser displays HQ. The Ubuntu browser runs separately inside
  each bot's sandbox.

In Windows PowerShell, check the WSL version and ensure Ubuntu is listed as
version 2. If Ubuntu is missing, install it with `wsl --install -d Ubuntu`,
complete the install and open its shell.

```powershell
wsl --status
wsl --list --verbose
```

In Ubuntu, install the system prerequisites and test the namespaces before
starting HQ.

```bash
sudo apt update
sudo apt install git bubblewrap procps python3 python3-venv
node --version
bwrap --version
command -v hermes
command -v google-chrome-stable || command -v chromium
bwrap --ro-bind / / --unshare-all --die-with-parent /usr/bin/true
```

A failed namespace probe blocks the contained pilot. Record the error and
host configuration. Keep the normal fail-closed setting and use the
[launcher notes](../../apps/hq/README.md#windows-wsl2) to diagnose it.

## Build and launch

In a fresh checkout under the Ubuntu home directory:

```bash
mkdir -p ~/dev
cd ~/dev
git clone https://github.com/abhishek3059/super-agent.git super-agent-pilot
cd super-agent-pilot
git fetch origin feat/hq-wsl2-containment
git switch --detach FETCH_HEAD
git rev-parse --short HEAD
npm run check
cd apps/hq
npm ci
npm run typecheck
npm test
npm run build
export HQ_DATA_DIR="$HOME/.super-agent/hq-pilot"
export HERMES_HOME_PRIMARY="$HOME/.hermes-hq-pilot"
export HQ_OWNER_NAME="Pilot Owner"
export HQ_NO_SCHEDULER=1
install -d -m 700 "$HQ_DATA_DIR" "$HERMES_HOME_PRIMARY"
HERMES_HOME="$HERMES_HOME_PRIMARY" hermes model
npm run jarvis
```

Keep the two directories dedicated to the pilot. In the Hermes model picker,
choose a supported hosted default and configure your worker credential there. The
[model picker guide](../../apps/hq/README.md#where-things-live) describes the
seed, sign-in and restart. Keep the voice key in the HQ data directory's
owner-only `.env`, separate from worker credentials. The launcher should open
a signed-in Windows browser at the loopback HQ origin. Check that the URL
bar shows `127.0.0.1` and that the app loads. Use `npm run open` from the same
environment to retry the signed-in window.

## Acceptance script

| Check | Action and expected observation |
| --- | --- |
| Worker | Open Jarvis and send a synthetic prompt asking it to reply `PILOT_READY`. Confirm its Hermes gateway starts, the picker shows the configured provider, and the reply arrives. |
| Browser | Ask the bot to open `https://example.com` and report the page title. Open its Desktop view and verify the URL and visible tab. |
| Files | Ask the bot to write a synthetic `hello.txt` in its own folder, then confirm it appears under Files. Separately confirm the normal sandbox tests fail closed on out-of-scope access. |
| Picker and restart | Switch between two connected chat models when available. Confirm the saved choice survives reload and the next synthetic turn uses it. Restart the agent from Settings and run another turn. |
| Handoff | Ask Jarvis to send a synthetic question to Scout. Check Scout's task and the returned result in Jarvis. |
| Voice | When the approved voice key is present, run the [synthetic voice probe](../../apps/hq/README.md#voice). Record session creation, spoken output, interruption and stop separately. |
| Memory | If configured, save the synthetic project codename `Bluefin`. Start a new chat with the same bot and ask for it. Check the citation. Ask Scout for that codename and check that it does not cite Jarvis's memory. |

In the test outcome, record commit, WSL version, Ubuntu version, CPU
architecture, Node/Hermes/browser/bubblewrap versions, and which Windows
browser opener worked. Record pass, fail, or not run for each row. Include
the first redacted error line and any workaround needed. Keep credentials,
session links, raw voice and personal paths out of the evidence.

## Optional semantic memory

Run PostgreSQL and the embedding endpoint so they are reachable on **Ubuntu
loopback**. Use Docker Desktop with WSL integration for the bundled
[pgvector service](../../apps/hq/docker-compose.memory.yml). Start Ollama in
Ubuntu and pull the approved `nomic-embed-text` model. From Ubuntu, check
`curl -fsS http://127.0.0.1:11434/api/tags` and
`docker compose -f docker-compose.memory.yml ps` before starting HQ. Add the
local PostgreSQL URI to the pilot's `.env` and restart HQ. Follow the
[semantic memory setup](../../apps/hq/README.md#memory) for the
Compose command and credential format. Memory matches may be sent to the
hosted worker in its context. Keep the acceptance fixture synthetic.
