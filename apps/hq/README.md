# Jarvis HQ

A team of AI agents you talk to in one window, running on your own machine.
Jarvis is the main contact. Scout, Forge, Quill and Atlas are specialists.
Each one is a [Hermes](https://github.com/NousResearch/hermes-agent) agent with
its own memory, working folder and browser.

This app is adapted from [Bot HQ](https://github.com/nickvasilescu/bot-hq)
(MIT). See [third-party notices](THIRD_PARTY_NOTICES.md). It is experimental
and has had no independent security review. Bots run inside the macOS
sandbox. It runs under a bounded
exception, [DEC-23](../../descisions.md#dec-23). The maintainer's direction is
[recorded here](../../docs/approvals/jarvis-hq-local-team.md).

## What it does

- **Chat that shows the work.** Each bot's steps appear while it works.
- **Handoffs that always come back.** A bot hands work to another with
  `send_to_bot`. The app returns the result or the failure to the bot that
  asked. It does not depend on the model remembering to reply.
- **A browser per bot.** Each bot drives its own headless Chrome with its own
  profile. You can watch it live and take over the mouse and keyboard.
- **Memory, tasks, routines and a Library** per bot, from Hermes and the app.
- **Group chats** between you and several bots.
- **Live voice** with OpenAI Realtime, when you supply a key. The voice agent
  hands real work to the same bot and speaks the result.
- **Skins.** Arc (the default), Ember, Carbon and Paper, plus light and dark.

## Run it

You need macOS, Node.js 22 or newer, Google Chrome (or Chromium, Brave or
Ego Browser), and a working `hermes` command with at least one model
provider set up in `~/.hermes`.

```bash
cd apps/hq
npm ci
npm run build
npm run jarvis
```

`npm run jarvis` starts the server on `http://127.0.0.1:8787` and opens it in
your browser, signed in. `npm run open` opens another signed-in window later.
A bot's Hermes gateway starts the first time you use that bot.

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
| `HQ_DATA_DIR` | `~/.super-agent/hq` | Database, bot homes, browser profiles, files |
| `OPENAI_API_KEY` | none | Turns on voice, dictation and voice preview |
| `OPENAI_VOICE_MODEL` | `gpt-realtime-2.1` | Realtime model |
| `HERMES_BIN` | `hermes` | The Hermes command |
| `CHROME_BIN` | auto | Browser for the bots: Chrome, Chromium, Brave or Ego Browser, first found |
| `MAX_BOTS` | `8` | Team size limit |

## Where things live

Nothing is written into the repository. Under `~/.super-agent/hq` (mode 0700):
`hq.db`, `session-secret`, `engines/<bot>` (each bot's Hermes home),
`profiles/<bot>` (its Chrome profile), `files/<bot>` (its working folder and
Library) and `server.log`.

A new bot's Hermes home starts from your own `~/.hermes`: the model settings,
`auth.json`, and the provider keys in `.env` (names ending `_API_KEY` or
`_BASE_URL`). Messaging tokens are not copied. The voice key in the data
folder is not handed to bots. Your own Hermes gateway and its files are
never changed. To add a sign-in, run `hermes auth add <provider>` in your own
terminal and restart the bot; the in-app sign-in button is off because it
would run outside the bot's sandbox. Unverified risk: a provider that rotates sign-in tokens may
sign out your own Hermes when a copy refreshes.

## Security boundary

- The server listens on 127.0.0.1 only. It refuses any request whose `Host`
  is not the loopback address and any browser request from another origin.
- The launcher authenticates the local server using a fresh challenge.
  Only the holder of `session-secret` can complete sign-in and mint a
  one-time link. The session cookie is `HttpOnly` and `SameSite=Strict`.
- A watch-mode viewer cannot send input. A control-mode viewer can send only
  mouse and key events.
- Approval cards accept only an explicit allow. Anything else is refused.
- Hermes' desktop-control toolset is not enabled.

### Containment

Each bot's Hermes gateway and its browser run inside the macOS sandbox
(`sandbox-exec`), and so does everything they start. Inside it a bot:

- can write only inside its own Hermes home, its working folder, its browser
  profile and its own temporary folder, and cannot remove or rename those
  folders themselves. Nothing else on the disk is
  writable, so it cannot replace a program you run later (Homebrew,
  `/usr/local`, `/Applications`);
- can read the Hermes program and system files, and nothing in your home
  folder, the app's data folder (session secret, database, other bots'
  folders), the shared temporary folders, other users' folders or other
  disks;
- can reach the internet, this server's tool endpoint and its own browser,
  and no other local port or local socket (so not another bot, and not your
  `ssh-agent`);
- can listen only on its own port and in its own folders, so it cannot take
  another bot's port before that bot starts;
- cannot open apps, send Apple events, start launchd jobs, read the Keychain
  or the clipboard, or see or signal other processes.

The server itself is not sandboxed, so it does not trust anything a bot can
write:

- Every file it writes, reads, lists or sends you from a bot's folders (the
  bot's settings, persona and sign-ins on each start, files saved with
  `save_file`, memory, the Library) goes through a short shell command inside
  a sandbox that can reach only that folder. A link or folder a bot swaps in
  inside it can only lead back into that folder, and the server refuses to
  use a bot folder that is itself a link.
- The ids of the processes it started are kept in its own folder, so a bot
  cannot point the server at another process to stop.
- A process on a bot's port that the server did not start is refused, not
  adopted. The live view and screenshots connect only to the browser the
  server started, and only to a page address on that browser's own port.
- Deleting a bot stops its gateway and browser and removes its folders. The
  contents are deleted from inside the bot's sandbox, so a link left in them
  is removed, never followed. A bot that locked files in its own folder
  (`chmod`, `chflags`) can stop that delete; the folder is then left behind
  and the server logs it. A new bot never reuses those folders.
- Before listening, the server stops the recorded gateways and browsers
  left by earlier runs. If process identity cannot be checked, the server
  retains the PID record and fails startup. A bot delete stays retryable
  when its process cannot be checked or stopped.

Without a sandbox the app refuses to start a bot. That means macOS only,
unless you set `HQ_UNCONTAINED=1` and accept uncontained bots. In that mode
none of the protections above apply, including the server's file handling.

**What containment does not cover.**

- A bot holds the model keys and sign-ins copied into its own home, and it
  can reach the internet. A steered bot can spend those keys or send them,
  and anything else in its own folder, somewhere else.
- Web pages and files a bot reads can still try to steer it, and one bot can
  message another. Nothing a bot does in its own shell or browser asks for
  approval.
- A bot can read system files outside the closed folders.
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
- `sandbox-exec` is a macOS tool that Apple marks as deprecated. It has had
  no independent review here.

Use synthetic speech and data while R-A.2 and R-H.4 are open. The
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
profile, live escape attempts inside the sandbox (macOS only), planted and
swapped links, and process-id checks.
