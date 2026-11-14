# Approved actions (design)

| Field | Value |
| --- | --- |
| Status | Proposal, built on branch `feat/t3-approved-actions` ahead of the roadmap order. Not accepted. |
| Tier | A small slice of T3 under [DEC-18](../../descisions.md#dec-18): consequential actions, each needing on-device approval |
| Approval | [Out-of-order record](../approvals/t3-actions-exception.md) |
| Code | `apps/api/src/super_agent_voice/actions.py`, wired in `local_adapter.py` and `app.py`; the approval card is in `apps/web/src/app` |

## What the assistant can do

With `SUPER_AGENT_ACTIONS=on` on a Mac (off by default), and only when the
user asks, the assistant can ask to do one of three things. Nothing happens
until the user clicks Approve on the console card on this machine.

| Tool | Does | Runs |
| --- | --- | --- |
| `open_url` | Opens an https page in the default browser | `/usr/bin/open <address>` |
| `web_search` | Opens a DuckDuckGo search for the given words | `/usr/bin/open https://duckduckgo.com/?q=<words>` |
| `open_app` | Opens one app from an allowlist | `/usr/bin/open -a <App>` |

The allowlist is Calendar, Notes, Reminders, Music, Maps, Calculator, and
Safari. `SUPER_AGENT_ACTION_APPS` replaces it with a comma list; each name must
use only letters, digits, and spaces (at most 40), or the session refuses to
start. The assistant cannot read the page, the search results, or the app. It
only opens them for the user.

## Controls (in code)

1. **Opt-in and fail closed.** The tools exist only when
   `SUPER_AGENT_ACTIONS=on` and the machine is a Mac. Any value other than `on`
   or `off` refuses the session. On any other system the tools are not offered
   and a call returns "no such tool".
2. **A click is the only approval.** The backend asks through a
   `action.request` message and waits up to 30 seconds for an
   `action.decision` message sent by the console's Approve or Deny button.
   Only an exact `true` approves. A spoken "yes", model text, or a timeout
   never approves. Deny is focused when the card appears, so a stray Enter or
   Space denies. The page ignores a click event that a script made (it must be
   a real click), and no keyboard shortcut approves.
3. **The user must have asked.** The tool runs only when the user's words in
   that turn contain a request word (open, launch, start, search, look up,
   google, go to, show me, pull up). Otherwise it refuses.
4. **No action after reading outside text.** In a turn where a tier 1 tool
   read a file, note, email, or calendar entry, every action refuses. This
   covers that turn only; see the known limits.
5. **One action per turn.** A second call in the same turn is refused, even if
   the first was refused or denied.
6. **One request at a time.** A second request while one waits is refused. A
   decision counts only if its id equals the pending id (compared in constant
   time); a wrong, late, repeated, or guessed id is ignored silently.
7. **The summary is built by code.** The text on the card comes from the
   validated arguments, never from model words. The command is a fixed
   absolute program (`/usr/bin/open`) with an argument list: no shell, no
   user-written flags.
8. **Strict arguments.** Exactly one declared key, a string, at most 2000
   characters, then the checks below.
9. **Web address rules.** https only; at most 300 characters; ASCII only, with
   no spaces, control or invisible characters, or backslashes; no user name or
   password (`@`); port 443 or none; a real host name with a final label of
   letters (so IP addresses in any spelling, such as `127.1` or `0x7f.1`,
   `localhost`, and names without a dot are out); no `.local`, `.localhost`,
   or `.internal` host, nor `.lan`, `.home`, `.arpa`, `.corp`, `.intranet`,
   `.localdomain`, `.test`, `.example`, or `.invalid`; no punycode (`xn--`)
   label. The path is at most 64 plain characters (letters, digits, and
   `/._~-`), so a long or percent-encoded path is refused. The query string and
   fragment are dropped, because a model could hide file or memory text there.
   A summary over 200 characters is refused, never cut, so the card shows the
   whole cleaned address, which is exactly what opens. Approve is ignored for
   half a second after the card appears.
10. **Search rules.** One line of 1 to 100 characters with control, bidi, and
    zero-width characters removed. Code builds the search address and encodes
    the words, so they cannot add parameters or change the site.
11. **App rules.** The name must match the allowlist when case is ignored, and
    the allowlist's own spelling is what runs.
12. **Bounded run.** The command has a 5 second limit, no input, and output
    sent nowhere. A failure gives a fixed error string, never the error text.
13. **Every exit closes the card.** Approve, deny, timeout, interrupt, mute, a
    new utterance, and session close all end the request and send
    `action.closed`. The page also clears the card on stop, error, or
    disconnect.
14. **Logged, metadata only.** Each action appends time, tool name, and one of
    `approved`, `denied`, `timeout`, `refused`, or `error` to
    `~/.super-agent/tool-audit.log` (mode 0600). Never the address, words, or
    app name.
15. **Tool results are fixed strings** ("Done: it is open on the screen.", "the user did
    not approve, so nothing was done"), so the model cannot learn page or app
    content and is told to say when nothing happened.

## Threat notes

- **Prompt injection from read content.** Control 4 blocks actions in any
  turn that read outside text. A page the assistant opens is never read back.
- **Exfiltration through a URL.** The query and fragment are dropped (control
  9), the search address is built in code (control 10), and the user sees the
  full address before approving. The path is short and plain, but it can still
  carry a few words a model chose, and a host name can too. That is why the
  card shows the whole address and why the user, not the model, approves.
- **Voice is not identity.** A spoken "yes" or "approve it" starts a new turn,
  which cancels the waiting request, so speaking can only deny. Saying "open
  it" starts a new request that needs its own click.
- **Card spoofing by model text.** The card is drawn by the console from a
  separate message, not from the transcript, and uses text bindings only. The
  assistant could still say "approve below" in speech or in the transcript.
  The real card appears in its own place, above the microphone, with Approve
  and Deny buttons. If you do not see it, nothing is waiting.
- **Replay and late decisions.** A decision needs the pending random id
  (control 6). After the request ends, the id is gone, so a repeat does
  nothing.
- **Look-alike hosts.** Non-ASCII hosts are refused, so a look-alike letter
  cannot make the card show one host while the browser opens another.

## Known limits

- The no-action-after-reading rule covers one turn. If the assistant reads an
  email in one turn and the user says "open that link" in the next, the model
  may open an address it saw in the email. The card and the click still apply,
  so read the address on the card before approving.
- A host name that resolves to a local address only through public DNS (for
  example the `nip.io` kind) passes the spelling checks.

- There is no emergency stop or job log yet (PH-03). The user's stops are
  Deny, mute, interrupt, and ending the session. Each cancels a waiting
  request, but a command that already started (within its 5 seconds) is not
  recalled.
- The assistant's own spoken "Please approve that on your screen" can reach
  the microphone, be transcribed, and cancel the request. That fails closed
  (the action is denied), and the browser's echo cancellation usually prevents
  it.
- The path of an https address is not restricted. Only the user's reading of
  the card stops a harmful path. A site the user approves can do whatever any
  web page can do.
- `open_app` opens any app on the allowlist, and an app can do things on its
  own after it opens. Keep the list short.
- The request-word check is a regular expression on the transcript. It stops a
  model acting on its own, not a user who says one of the words by accident;
  the click still decides.
- The 5 second limit covers launching `open`, not what the browser or app does
  afterward.
- An address with a query string cannot be opened. Use the search tool or open
  the base page.
- Tested with fakes. No test opens a page or an app; see the manual test below.

## Five-minute manual voice test

Start with `SUPER_AGENT_ACTIONS=on scripts/start-voice-mac.sh lfm3` and connect
the console. The launcher prints `Approved actions: on`.

| Say | Expect |
| --- | --- |
| "Open the Calendar app" | A card reads `Open the app Calendar?`. Nothing opens yet. |
| (click Deny) | The card goes. The assistant says it did not open it. Calendar stays closed. |
| "Open the Calendar app", then click Approve | Calendar opens. The assistant says it opened it. |
| "Open Terminal" | No card. The assistant says it cannot (not on the list). |
| "Search the web for how tall is Mount Everest" | A card reads `Search the web for "how tall is Mount Everest"?`. Click Approve: a DuckDuckGo search opens. |
| "Open the page example dot com slash about" | A card with an `https://example.com/about` address. Click Deny. |
| "Open Notes", then say "yes, approve it" instead of clicking | The card goes (the new words cancel it). Notes does not open. |
| "Open Maps", then wait 30 seconds | The card goes. The assistant says there was no approval in time. Maps does not open. |
| "Open Maps", then press Mute | The card goes. Maps does not open. |
| "Tell me a joke" | A joke. No card. |
| "Open Notes and then open Maps" | At most one card for the turn; the second is refused. |
| With files enabled, "Read my notes file, then open Safari" | No card for Safari in that turn. |
| Check `tail -5 ~/.super-agent/tool-audit.log` | Lines with a time, a tool name, and `approved`, `denied`, `timeout`, or `refused`. No addresses or words. |
