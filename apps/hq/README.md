# Jarvis HQ

A team of AI agents you talk to in one window, running on your own machine.
Jarvis is the main contact. Scout, Forge, Quill and Atlas are specialists.
Each one is a [Hermes](https://github.com/NousResearch/hermes-agent) agent with
its own memory, working folder and browser.

This app is adapted from [Bot HQ](https://github.com/nickvasilescu/bot-hq)
(MIT). See [third-party notices](THIRD_PARTY_NOTICES.md). It is experimental.
Bots run inside the macOS sandbox, which had an
[independent security review](../../docs/reviews/jarvis-hq-security-review.md)
on 2026-11-19: fifteen findings closed and one accepted as documented. The
review probed the sandbox from inside its profile; macOS's sandbox mechanism
itself was not attacked directly. On Linux and Windows (WSL2) they run inside
bubblewrap instead, [described below](#windows-wsl2); that backend has not had
an independent review. It runs under a bounded
exception, [DEC-23](../../descisions.md#dec-23). The maintainer's direction is
[recorded here](../../docs/approvals/jarvis-hq-local-team.md).

## What it does

- **Chat that shows the work.** Each bot's steps appear while it works.
- **Handoffs that always come back.** A bot hands work to another with
  `send_to_bot`. The app returns the result or the failure to the bot that
  asked. It does not depend on the model remembering to reply.
- **A computer per bot.** Each bot drives its own headless Chrome with its own
  profile. It opens on a desktop page with a clock, a search box and app
  tiles, including a Files tile for the bot's working folder. The large view
  adds a browser bar: tabs, back, forward, reload, home and an address bar.
  Typed text that is not an `http` or `https` address becomes a Google
  search. You can watch it live and take over the mouse and keyboard.
- **Memory, tasks, routines and a Library** per bot, from Hermes and the app.
- **Group chats** between you and several bots.
- **Live voice** with OpenAI Realtime, when you supply a key. The voice agent
  hands real work to the same bot and speaks the result.
- **Skins.** Arc (the default), Ember, Carbon and Paper, plus light and dark.

## Run it

You need macOS (or Linux, or Windows with WSL2: see
[Windows (WSL2)](#windows-wsl2)), Node.js 22 or newer, Google Chrome (or Chromium, Brave or
Ego Browser), and a compatible Hermes gateway. The local run used Hermes
v0.22.2. Configure a supported hosted default model in `~/.hermes` or in
the HQ seed specified by `HERMES_HOME_PRIMARY`.
A new bot installs its own copy of the Hermes dependencies on first start.
That takes about 50 seconds and 1 GB of disk per bot.

```bash
cd apps/hq
npm ci
npm run build
npm run jarvis
```

`npm run jarvis` starts the server on `http://127.0.0.1:8787` and opens it in
your browser, signed in. `npm run open` opens another signed-in window later.
A bot's Hermes gateway starts the first time you use that bot.

## Windows (WSL2)

HQ runs on Windows inside WSL2, as a Linux app. Bots are contained with
bubblewrap. Nothing runs on the Windows side except your browser.

1. Install WSL2 with Ubuntu (`wsl --install -d Ubuntu` in PowerShell) and open
   the Ubuntu shell. Keep the repository on the Linux disk (`~/dev/...`), not
   under `/mnt/c`.
2. Install Node.js 22 or newer inside Ubuntu, then the sandbox:
   `sudo apt install bubblewrap procps`. `procps` gives HQ `ps`, which it uses
   to check the processes it started.
3. Install Google Chrome for Linux inside Ubuntu (the `.deb` from Google puts
   it at `/usr/bin/google-chrome-stable`), or `chromium` from a `.deb`
   source. Set `CHROME_BIN` for another place, but it must sit under `/usr`
   or `/opt`: the sandbox mounts nothing else. The Snap `chromium` does not run
   inside bubblewrap.
4. Install Hermes inside Ubuntu, as in [Run it](#run-it), with its config in
   `~/.hermes` or in the seed `HERMES_HOME_PRIMARY` names.
5. Then the same commands: `cd apps/hq && npm ci && npm run build && npm run jarvis`.
   The launcher opens the signed-in page in your Windows browser (`wslview`
   if installed, else `cmd.exe /c start`). WSL2 normally forwards
   `127.0.0.1` to Windows (`localhostForwarding` in `.wslconfig`); if the page
   does not load, check that setting. This launcher path is not tested on a
   real WSL2.

What the Linux backend enforces, per bot, for its gateway and its browser:

- **Files.** It starts from an empty root. Only `/usr`, `/etc`, `/opt` and the
  system links (`/bin`, `/lib`, ...) are mounted, read-only, plus the folders
  it is given: the read folders read-only, the write folders read-write, and
  its own temporary folder. Your home folder, the app's data folder, other
  bots' folders and your Windows drives (`/mnt/c`) are never mounted, so they
  do not exist for it. Nothing else is writable, including the root. The
  folders it can write cannot be removed or renamed from inside (a mount point
  cannot be unlinked). Programs find `HOME` set but missing.
- **Processes.** Its own process and IPC namespace and its own `/proc`: no other
  process is visible or can be signalled. `--die-with-parent` and a new session
  stop it outliving the server or typing into your terminal. WSL's Windows
  interop needs `/proc/sys/fs/binfmt_misc` and the Windows drives, and it has
  neither, so it should not be able to start Windows programs (not tested on
  a real WSL2).
- **Network.** An empty network namespace: no internet and no loopback ports of
  yours. The app carries only the listed ports over unix sockets that live in a
  folder of its own under `run/` in the data folder (mode 0700): the tool
  endpoint and the internet proxy go in, and the bot's own API or debugging
  port comes out. The proxy still refuses loopback and private addresses.
  If a port is already taken, the bot does not start.
- **Environment.** The same small environment as on macOS: none of the
  server's keys.

What it does not do, or does differently:

- No Keychain, clipboard, Apple events, preferences or launchd on Linux, so
  nothing to close. `system_info` is a macOS tool and answers only partly.
- There is no seccomp filter beyond what bubblewrap sets. A bot can use the
  kernel's system calls as your user could inside a user namespace. It
  can write into the memory-backed `/tmp` of its own sandbox, which is empty
  at each start and invisible to everyone else.
- The bridge runs in the server, so bots stop when the server stops, unlike
  macOS where the stale ones are stopped at the next start.
- The bot's side of its listening socket is a file in a folder only that bot can
  write. The server connects to it only if it is still a socket.

Containment needs unprivileged user namespaces. Ubuntu 24.04 can restrict them
with AppArmor; HQ then refuses to start bots and says why (for example
`bwrap: setting up uid map: Permission denied`). Either allow them:

```bash
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
echo 'kernel.apparmor_restrict_unprivileged_userns=0' | sudo tee /etc/sysctl.d/60-hq-userns.conf
```

or give `bwrap` an AppArmor profile that allows `userns` (Ubuntu's
`bwrap-userns-restrict` profile is the reference). To check it works:
`bwrap --ro-bind / / --unshare-all --die-with-parent true && echo ok`.

## Voice

Voice is off until the server has an OpenAI key. Save
`OPENAI_API_KEY` in the owner-only file `~/.super-agent/hq/.env` (mode
0600) and restart the server. The browser gets a five-minute client
secret. The long-lived key stays on the server.

For the opt-in check, build HQ and start it with a new `HQ_DATA_DIR`
outside the repository and the default HQ directory. Set
`HQ_OWNER_NAME="Voice Check"`, `HQ_NO_SCHEDULER=1` and matching
`PORT` and `APP_URL` on the loopback host. Use a Hermes seed with only
the intended test model credentials. Load the OpenAI key from the
owner-only file into the server process. Do not sign in or seed chat
before the probe. From `apps/hq`, with the same directory and port, run:

```bash
node scripts/voice-check.mjs
```

Use synthetic speech and a fresh workspace. A populated workspace can
include owner identity, chat, bot memory and routines in the call prompt.
`node scripts/voice-check.mjs --self-check` runs the offline audio and
request checks. The paid probe runs separately from `npm test` and CI.
See the [voice run record](../../docs/implementation/jarvis-hq-voice-check.md)
for current results and the provider contract.

## Settings

All optional, read from the environment or from `~/.super-agent/hq/.env`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `8787` | Server port on 127.0.0.1 |
| `HQ_MCP_PORT` | `PORT + 1` | The bots' tool endpoint, the only app port bots can reach |
| `HQ_EGRESS_PORT` | `PORT + 2` | The bots' internet proxy |
| `HQ_DATA_DIR` | `~/.super-agent/hq` | Database, bot homes, browser profiles, files |
| `OPENAI_API_KEY` | none | Turns on voice, dictation and voice preview |
| `OPENAI_VOICE_MODEL` | `gpt-realtime-2.1` | Realtime model |
| `HERMES_BIN` | `hermes` | The Hermes command |
| `CHROME_BIN` | auto | Browser for the bots: Chrome, Chromium, Brave or Ego Browser, first found |
| `MAX_BOTS` | `8` | Team size limit |
| `HERMES_HOME_PRIMARY` | `~/.hermes` | The Hermes seed. Set it to a folder only HQ uses, other than `~/.hermes`, to turn on account sign-in in HQ |
| `HQ_READ_DIRS` | none | Folders bots may read, never change, separated by `:` (for example `~/dev:~/Documents`) |
| `HQ_SKILL_DIRS` | none | Skill folders every bot loads, read-only (for example `~/.claude/skills:~/.hermes/skills`) |
| `HQ_SYSTEM_INFO` | off | `1` turns on the read-only `system_info` tool |

## Where things live

Nothing is written into the repository. Under `~/.super-agent/hq` (mode 0700):
`hq.db`, `session-secret`, `engines/<bot>` (each bot's Hermes home),
`profiles/<bot>` (its Chrome profile), `files/<bot>` (its working folder and
Library) and `server.log`.

The gateway seed is `~/.hermes` or the folder in `HERMES_HOME_PRIMARY`.
Its default must name a supported hosted provider. HQ supports NVIDIA NIM,
OpenAI Codex and Anthropic API. Anthropic API worker use is capped at
US$5 per month under [DEC-23](../../descisions.md#dec-23) rule 5. It copies
credentials for those providers when the seed names them in its model or
provider settings, and, for a dedicated seed only, when the seed holds a
sign-in or key for them.
HQ uses the provider's built-in endpoint and omits automatic worker fallbacks.
If the seed's previous default relied on a fallback, update it to a current
chat model or choose an available model in Engine settings. The November 20
local test used Hermes v0.22.2 for gateway compatibility.

Connect accounts in the Hermes seed, or from Engine settings when the seed
is one only HQ uses (`HERMES_HOME_PRIMARY` set to a folder other than
`~/.hermes`). HQ never offers this for
the operator's own `~/.hermes`, and it never copies a credential from that
profile unless the profile's settings name its provider. **Sign in with
ChatGPT** runs `hermes auth add openai-codex --type oauth` against the
dedicated seed. Hermes runs as the operator, outside the bot sandbox, as it
would in a terminal. HQ opens OpenAI's sign-in page in your browser. The
tokens stay in the seed's `auth.json` and never reach the web page. For
Claude, paste an Anthropic API key. HQ adds it to the seed's `.env` with
mode 0600, keeps every other line, and refuses to touch a `.env` it cannot
read as a plain file. In a dedicated seed, any supported provider with a
sign-in or key there reaches every bot. Anthropic and OpenAI API keys are
billed per use. HQ does not offer Claude Pro or Max sign-in. Anthropic says it
"does not permit third-party developers to offer Claude.ai login into their
own applications" and directs developers to API keys
([Claude Code legal and compliance](https://code.claude.com/docs/en/legal-and-compliance),
read 2026-11-20). OpenAI documents Sign in with ChatGPT for Codex and for
registered third-party clients, but recommends API keys for automation and
does not state that a personal plan may power another app
([Codex sign-in](https://learn.chatgpt.com/docs/auth), read 2026-11-20).
Treat the ChatGPT route as personal use on your own machine. After a change,
HQ restarts the bot. Use **Restart agent** for other bots to refresh their inventory. Engine settings disable unconnected
routes and validate saved model IDs against the worker's catalog. Choosing a
different provider or model starts another Hermes conversation. The HQ
transcript stays visible.

The server-side OpenAI voice key lives in the HQ data directory. Worker keys
come from the Hermes seed and the voice key is never copied into it. Use
dedicated, revocable, spend-capped worker keys. HQ changes Hermes files only
in a dedicated seed, and only through the sign-in and key controls above.
A provider that rotates copied sign-in tokens may sign out the owner profile.

## Security boundary

- The server listens on 127.0.0.1 only. It refuses any request whose `Host`
  is not the loopback address and any browser request from another origin.
- The launcher authenticates the local server using a fresh challenge.
  Only the holder of `session-secret` can complete sign-in and mint a
  one-time link. The proofs name the server's own address, so a process on
  another port cannot relay them. The browser then holds a bearer token in
  its session storage, stored hashed on the server. The app page sends a
  content security policy that allows only its own scripts.
- A watch-mode viewer cannot send input. A control-mode viewer can send only
  mouse and key events.
- Approval cards accept only an explicit allow. Anything else is refused.
- Hermes' desktop-control toolset is not enabled.

### Containment

Each bot's Hermes gateway and its browser run inside a sandbox, and so does
everything they start. macOS uses `sandbox-exec`. Linux and WSL2 use
bubblewrap (`bwrap`) with a port bridge, under the same rules. HQ refuses to
start a bot where neither works, unless you set `HQ_UNCONTAINED=1` and accept
uncontained bots. The list below is the macOS behaviour; the
[Windows (WSL2)](#windows-wsl2) section says how Linux differs. Inside it a bot:

- can write only inside its own Hermes home, its working folder, its browser
  profile and its own temporary folder, and cannot remove or rename those
  folders themselves. Nothing else on the disk is
  writable, so it cannot replace a program you run later (Homebrew,
  `/usr/local`, `/Applications`);
- can read the Hermes program and system files, the folders in
  `HQ_READ_DIRS` and your skill folders (`HQ_SKILL_DIRS`, plus where linked
  skills really live), and nothing else in your home folder, the app's data
  folder (session secret, database, other bots' folders), the shared
  temporary folders, other users' folders or other disks. HQ drops any
  listed folder that is, holds or sits inside your home folder itself,
  `~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.config`, `~/Library`, `~/.hermes` and
  `~/.claude` (except their `skills` folders), `~/.super-agent` or the Hermes seed. A bot
  that reads a folder can also send what it read to the internet, so list
  only folders you would share;
- can read and write one shared skills folder, `shared-skills` in the data
  folder, which every bot loads. One bot's skill can steer another bot, so
  read shared skills before you rely on them;
- has no direct network access. It reaches its own browser, the app's tool
  endpoint and an internet proxy, each on a loopback port of its own; it
  never reaches the app's own API. The proxy resolves each name itself and
  refuses loopback, private, link-local and other non-public addresses, so
  the internet is open and local services are not (not another bot, not your
  own browser's debugging port, not your `ssh-agent`);
- can listen only on its own port and in its own folders, so it cannot take
  another bot's port before that bot starts;
- cannot open apps, send Apple events, start launchd jobs, change your
  default apps, read or write your preferences, read the Keychain or the
  clipboard, or see or signal other processes.

The read folders, skill folders and `system_info` are off by default. They
expose the operator's real data to the bot's hosted model, and
[DEC-23](../../descisions.md#dec-23) allows synthetic data only until
R-A.2 is decided. Turn them on only with folders that hold synthetic data,
or after a maintainer amends DEC-23.

Facts about the Mac come from the `system_info` tool, which the server runs
outside the sandbox. It takes only a topic (overview, disk, battery,
processes, apps), each a fixed command list. Process lists show names only,
never arguments or environment.

The server itself is not sandboxed, so it does not trust anything a bot can
write:

- Every file it writes, reads, lists or sends you from a bot's folders (the
  bot's settings, persona and sign-ins on each start, files saved with
  `save_file`, memory, the Library) goes through a short shell command inside
  a sandbox that can reach only that folder. A link or folder a bot swaps in
  inside it can only lead back into that folder, and the server refuses to
  use a bot folder that is itself a link.
- The ids of the processes it started are kept in its own folder with their
  start times, so a bot cannot point the server at another process to stop,
  and a reused id is not mistaken for one of them.
- A process on a bot's port that the server did not start is refused, not
  adopted. The live view and screenshots connect only to the browser the
  server started, and only to a page address on that browser's own port.
- Deleting a bot stops its gateway and browser and removes its folders. The
  contents are deleted from inside the bot's sandbox, so a link left in them
  is removed, never followed. A bot that locked files in its own folder
  (`chmod`, `chflags`) can stop that delete; the folder is then left behind
  and the server logs it. A new bot never reuses those folders, or a
  deleted bot's ports.
- Before listening, the server stops the recorded gateways and browsers
  left by earlier runs. If process identity cannot be checked, the server
  retains the PID record and fails startup. A bot delete stays retryable
  when its process cannot be checked or stopped.

Without a sandbox the app refuses to start a bot. That means macOS, or Linux
and WSL2 with a working `bwrap`, unless you set `HQ_UNCONTAINED=1` and accept uncontained bots. In that mode
none of the protections above apply, including the server's file handling.

**What containment does not cover.**

- A bot holds the model keys and sign-ins copied into its own home, and it
  can reach the internet. A steered bot can spend those keys or send them,
  and anything else in its own folder, somewhere else.
- Web pages and files a bot reads can still try to steer it, and one bot can
  message another. Nothing a bot does in its own shell or browser asks for
  approval.
- A bot can read system files outside the closed folders.
- Through the proxy a bot can reach any public address and port, and it can
  still look up names through the system resolver, so data can leave as DNS
  queries.
- Chrome makes its profile lock in the system's per-user temporary folder,
  whatever the settings say. The browser's sandbox opens folders there named
  after the browser (`com.google.Chrome.*`). Every bot's browser shares them,
  and so does your own Chrome if you use the same browser: a bot's browser
  could disturb your Chrome's lock. Using a different browser for the bots
  (`CHROME_BIN`) avoids that.
- A process a bot detaches from its gateway's process group keeps running in
  that bot's sandbox after the bot is stopped or deleted.
- Chrome's own inner sandbox cannot run inside ours, so it is off. Pages in
  one bot's browser are less isolated from each other. They are still inside
  that bot's sandbox.
- `sandbox-exec` is a macOS tool that Apple marks as deprecated. The security
  review probed this app's profile from inside it; the macOS sandbox
  mechanism itself was not attacked or reviewed.
- The Linux backend (bubblewrap and the port bridge) has had no independent
  review. Its self-checks were written by its author and ran in a Linux
  container, not yet on a real WSL2. [DEC-23](../../descisions.md#dec-23) and
  AGENTS.md section 5 name the macOS sandbox, so a maintainer should confirm
  they cover this backend before you rely on it.

Use synthetic speech and data while R-A.2 (real voice and personal data to
a cloud provider) is open. The
[maintainer approval](../../docs/approvals/jarvis-hq-dec-23-approval.md)
authorizes up to US$5 per month in OpenAI voice spend. The app does not enforce
that account limit.

## What has been tested

See the [local run record](../../docs/implementation/jarvis-hq-local-run.md).
See the [voice run record](../../docs/implementation/jarvis-hq-voice-check.md)
for the synthetic check. Connected apps (Composio) and X search (xAI) come
from upstream and are switched off in code: DEC-23 does not approve a second
paid service or real accounts. Their code is still present and untested here.

## Develop

```bash
npm run typecheck
npm test
npm run build
```

`npm run dev` runs the server and Vite on port 5173. `npm test` runs the
self-checks: the request guards, the viewer input filter, the handoff reply
rule, the owner key and approvals, the services that stay off, the sandbox
profile, live escape attempts inside the sandbox (macOS and Linux each run
their own, and skip the other's), the Linux port bridge, planted and swapped
links, and process-id checks.
