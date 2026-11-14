# Design reference: lessons from Roamies

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Subject | [KenKaiii/Roamies](https://github.com/KenKaiii/Roamies), a desktop AI sidekick for macOS, Windows and Linux, AGPL-3.0, created 2026-10-28 |
| Method | Read-only review of its public docs, history and source through the GitHub API by three Claude Code subagents (`sonnet`, `haiku`) for `jeevesh2515` on 2026-11-14. Nothing was cloned, installed or run. Key claims were spot-checked against the source by `claude-opus-5-5`. |
| Status | Reference only. It decides nothing, ticks nothing, and authorizes no work. |

## The licence rule

Roamies is licensed under AGPL-3.0, and this repository is MIT. **Do not copy
any of its code, prompts, text or assets into this repository.** That includes
its safety rules, memory code, system prompt, Claude Code bridge, and its AGPL
support packages (`@kenkaiiii/gg-agent`, `gg-ai`, `gg-core`, `ggcoder`).
Copying any of it would make the combined work AGPL. Running it unmodified, as
a separate app, creates no obligation (AGPL section 2). This is a reading of
the licence, not legal advice.

Reuse the ideas below by designing from this note and our own requirements,
not by working from memory of their source files.

## Ideas worth adopting

### 1. Memory and reminders (next feature)

- Facts and commitments are separate kinds of memory, each with a cap.
- The model saves a commitment only by calling a tool. Code, not the model,
  parses due times and repeat rules such as "every weekday at 9".
- A separate pass that extracts facts runs with no tools and drops anything
  that looks like a secret.
- The user can see everything stored and forget any of it.

**Our version:** fully local (Roamies sends saved memory to the cloud provider
on every request), opt-in, logged, with an undo for forget. It is tier T2 work
under [DEC-18](../../../descisions.md#dec-18).

### 2. Contained Claude Code (reference for PH-05)

Roamies runs Claude Code through Anthropic's Agent SDK in this configuration:
- all of Claude Code's built-in tools switched off;
- no user settings, CLAUDE.md or outside MCP servers loaded;
- one in-process tool server holding only the app's own tools;
- a permission callback that allows only those tools and denies everything
  else.

That matches what [RT-010](../../../tasks/010-contained-opencode-adapter.md)
asks for: the coding agent thinks, and every action goes through our policy
layer. Caveats:
- the Agent SDK is proprietary;
- the model is a cloud model;
- that path therefore needs its own approval under the $0 cap and the data
  rules.

### 3. Safe, ask and block (input to the PH-02 policy design)

Every tool call is sorted into allowed, needs a yes, or refused.
- Actions are off until the user enables them.
- Shells and interpreters are refused.
- Destructive or outward buttons ("delete", "pay", "send") always ask.
- Web fetches refuse private network addresses on every redirect.
- Reads of secret stores and other apps' data are refused.

**Our version:** the same three outcomes, decided in code ([REQ-10](../../../prd.md#req-10)).
- Use allowlists, not pattern matching of shell text; Roamies' command
  classifier is regex-based, and such classifiers are hard to make complete.
- Approvals happen on the device, never by voice ([REQ-09](../../../prd.md#req-09)).

### 4. Desktop presence (target for PH-06)

- A tray or menu-bar app with no window.
- Hold-a-key push-to-talk and tap-to-type.
- An optional on-device wake word that is off by default.
- A read-only look at the front window through the macOS Accessibility API.

Push-to-talk would also remove most of our echo and false-interruption
problems.

## What not to adopt

- Sending saved memory, the front window's title, and screenshots to a cloud
  model with every request.
- Storing AI keys and sign-in tokens in a plain-text file; Roamies keeps them
  in `~/.gg/auth.json`.
- Voice-triggered clicking and typing with only on-screen confirmation.
- Treating "the model chose to do something your settings allow" as out of
  scope for security. Our rules fail closed.
- A webview with no content security policy and no permission files.
- Paid provider keys or subscriptions as a requirement.

## Facts worth knowing

- **No external API:** Roamies talks to its own sidecar over stdin and stdout
  and opens no network port. Its Claude Code setup refuses outside MCP
  servers. So super-agent cannot drive it without a fork, and that fork would
  be AGPL.
- **Release signing:** macOS builds are signed and notarized, and update
  bundles carry a signature. The Windows installer is not code-signed.
- **Maturity:** about 143 commits in its first 17 days, mostly by one author.
  CI runs tests on three operating systems.
