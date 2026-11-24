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
  and Hermes v0.22.2 under `/opt` with `HERMES_BIN` set to it, as in
  [launcher step 4](../../apps/hq/README.md#windows-wsl2). The shell
  installer's `hermes` alone cannot start in a bot's home. Install
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
sudo apt install git bubblewrap procps python3 python3-venv build-essential
node --version
bwrap --version
/opt/hermes-hq/bin/hermes --version
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
git fetch origin develop
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
export HERMES_BIN=/opt/hermes-hq/bin/hermes
HERMES_HOME="$HERMES_HOME_PRIMARY" "$HERMES_BIN" model
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

## WSL2 run, 2026-11-24

An agent ran this guide remotely on the Windows host, from `develop` at
`c925edc`. It used synthetic prompts, the dedicated pilot seed and the
NVIDIA hosted model `nvidia/nemotron-3.5-lightning-30b-a3b`. The worker key
was taken from the Windows user environment into the seed's mode 0600
`.env`. The key was not printed.

| Field | Value |
| --- | --- |
| WSL | 3.0.5.0, kernel 6.18.58.1-1 |
| Ubuntu | 24.04.5 LTS, x86_64, running as root |
| Versions | Node v22.23.4, bubblewrap 0.9.0, Google Chrome 158.0.8127.36, Hermes v0.22.2 under `/opt` |
| Windows opener | Not run. The agent opened the printed sign-in link in a separate browser. |

| Check | Result |
| --- | --- |
| Worker | Pass after the fixes below. Jarvis replied `PILOT_READY`. |
| Browser | Pass. The bot reported `Example Domain`. The Desktop view was not checked. |
| Files | Pass. `hello.txt` held `PILOT` in the bot's own folder. |
| Picker and restart | Not run. |
| Handoff | Pass. Scout replied `TEAM_READY` and Jarvis reported it. |
| Voice | Not run. No voice key in the pilot data directory. |
| Memory | Not run. Ollama and PostgreSQL were not running. |

Problems found and fixed in this guide and the
[launcher prerequisites](../../apps/hq/README.md#windows-wsl2):

- `npm ci` failed with `gyp ERR! stack Error: not found: make`.
  `better-sqlite3` 13.0.3 builds from source, so `build-essential` is now a
  prerequisite.
- With the shell installer's `hermes`, every bot stopped while starting:
  exit 127 (`python3: not found`), then exit 1
  (`No module named 'ruamel'`) once the runtime was visible. That install
  keeps its Python packages per Hermes home. It failed the same way outside
  the sandbox with any `HERMES_HOME` outside `~/.hermes`. A source checkout
  of v0.22.2 under `/opt` with its locked environment fixed it.
- That environment first lacked `aiohttp`. The gateway logged
  `API Server: aiohttp not installed`, and the bot did not come up within 90
  seconds. The locked `messaging` extra supplies it.

Still open: the `linux-sandbox` test "a listen port that is already taken
stops the bot from starting" failed in 2 of 9 full-suite runs and passed
when run alone. A load test failed 4 of 40 times. Each time, the server's
`SIGKILL` reached `bwrap` just after it forked its sandboxed child, and that
child kept running. The bot then holds no bridge, but the process leaks
until it ends.
