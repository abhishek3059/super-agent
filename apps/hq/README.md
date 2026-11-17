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

Voice is off until the server has an OpenAI key. Put it in the data folder,
not in the repository:

```bash
mkdir -p ~/.super-agent/hq && umask 077 && printf 'OPENAI_API_KEY=%s\n' 'paste-key-here' > ~/.super-agent/hq/.env
```

Restart the server after that. OpenAI bills voice by usage. The browser gets
a key that expires in five minutes. The long-lived key stays on the server.
**Status: the voice path has not been run against OpenAI yet.** The
client-secret request was compared with `src/resources/realtime/client-secrets.ts`
in [openai-node](https://github.com/openai/openai-node) and with the
[Realtime WebRTC guide](https://developers.openai.com/api/docs/guides/realtime-webrtc)
on 2026-11-17. The model names and the tool-call event names are unverified
until a real call is made.

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
- Sign-in is a one-time link. Only someone who can read `session-secret` in
  the data folder can mint one. The session cookie is `HttpOnly` and
  `SameSite=Strict`.
- A watch-mode viewer cannot send input. A control-mode viewer can send only
  mouse and key events.
- Approval cards accept only an explicit allow. Anything else is refused.
- Hermes' desktop-control toolset is not enabled.

### Containment

Each bot's Hermes gateway and its browser run inside the macOS sandbox
(`sandbox-exec`), and so does everything they start. Inside it a bot:

- can write only its own Hermes home, its working folder, its browser
  profile and its own temporary folder. Nothing else on the disk is
  writable, so it cannot replace a program you run later (Homebrew,
  `/usr/local`, `/Applications`);
- can read the Hermes program and system files, and nothing in your home
  folder, the app's data folder (session secret, database, other bots'
  folders), the shared temporary folders, other users' folders or other
  disks;
- can reach the internet, this server's tool endpoint and its own browser,
  and no other local port or local socket (so not another bot, and not your
  `ssh-agent`);
- cannot open apps, send Apple events, start launchd jobs, read the Keychain
  or the clipboard, or see or signal other processes.

The server itself is not sandboxed, so it does not trust anything a bot can
write:

- Files it writes into a bot's folders (the bot's settings, persona and
  sign-ins on each start, files saved with `save_file`, memory edits) are
  written fresh. A link a bot planted there is replaced, never followed.
  Files it reads there are read the same way.
- The ids of the processes it started are kept in its own folder, so a bot
  cannot point the server at another process to stop.
- A process on a bot's port that the server did not start is refused, not
  adopted.

Without a sandbox the app refuses to start a bot. That means macOS only,
unless you set `HQ_UNCONTAINED=1` and accept uncontained bots.

**What containment does not cover.**

- A bot holds the model keys and sign-ins copied into its own home, and it
  can reach the internet. A steered bot can spend those keys or send them,
  and anything else in its own folder, somewhere else.
- Web pages and files a bot reads can still try to steer it, and one bot can
  message another. Nothing a bot does in its own shell or browser asks for
  approval.
- A bot can read system files outside the closed folders.
- Chrome makes its profile lock in the system's per-user temporary folder,
  whatever the settings say. The browser's sandbox opens only folders there
  named after the browser, which every bot's browser shares.
- Chrome's own inner sandbox cannot run inside ours, so it is off. Pages in
  one bot's browser are less isolated from each other. They are still inside
  that bot's sandbox.
- `sandbox-exec` is a macOS tool that Apple marks as deprecated. It has had
  no independent review here.

Use synthetic data until the independent security review (roadmap R-H.4)
is done.

## What has been tested

See the [local run record](../../docs/implementation/jarvis-hq-local-run.md).
Voice has not been run. Connected apps (Composio) and X search (xAI) come
from upstream and are switched off in code: DEC-23 does not approve a second
paid service or real accounts. Their code is still present and untested here.

## Develop

```bash
npm run typecheck
npm test
npm run build
```

`npm run dev` runs the server and Vite on port 5173. `npm test` runs the self-checks for the request guards, the viewer input
filter, the handoff reply rule and the owner key.
