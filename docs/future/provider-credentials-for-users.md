# Provider credentials for everyday users

Status: Proposal. Not approved. Not on the roadmap.

Recorded from a brainstorm on 2026-11-13 between `abhishek3059` and Claude Code.

## Problem

Testing uses a terminal prompt for the Gemini key and a token file for the
console. An everyday user should not deal with keys or terminals. Production
will add login, and Google OAuth is planned.

## Current rule

R-00.9 and [voice foundation design](../design/voice-foundation.md) say keys
live only in the process environment or an OS vault, never in the browser, the
repo, URLs, or logs. The [R-01.6 security review](../reviews/r01-6-security-review.md)
was accepted on that basis. See also the
[PH-00 setup decisions](../approvals/ph-00-setup-decisions.md).

## Key point

Google OAuth for login proves identity only. It does not give Gemini access.

## Options

### 1. Bring your own key in a settings screen

- How it works: the user pastes a Gemini key into an app settings screen. The
  backend stores it in the OS vault (Windows Credential Manager or DPAPI, macOS
  Keychain). The browser never stores it and the app never echoes it back.
- User effort: get a key from Google once, paste it once.
- Cost: the user's own quota. $0 for us.
- Privacy: audio goes to Google under the user's own account terms.
- Risks: browser extensions can read typed input. The "set key" endpoint is a
  new door. Without the token, Host, and Origin checks, a malicious page or
  process could swap in its own key and receive the user's conversations. The
  field must be cleared after sending.

### 2. Sign in with Google using Gemini API OAuth scopes

- How it works: the user's own Google account pays for use.
- User effort: one sign-in.
- Cost: the user's quota.
- Privacy: as option 1.
- Unverified: whether the Gemini API accepts user OAuth for this, and whether
  it needs a Google Cloud project on the user's side. Not checked against a
  primary source.

### 3. Hosted service

- How it works: the user signs in with Google. Our server holds the project's
  key and gives the browser short-lived session tokens for the Live API (Google
  calls these ephemeral tokens; unverified).
- User effort: none beyond sign-in.
- Cost: breaks the $0 budget.
- Privacy: makes us a data processor for users' voice.
- Risks: the Gemini terms describe the API as for developers, not consumer use
  (see [Gemini account verification](../implementation/gemini-account-verification.md)),
  so this depends on R-C.2 (the legal read).

### 4. Local model by default

- How it works: no key. Uses the local path in
  [PR #36](https://github.com/abhishek3059/super-agent/pull/36).
- User effort: none once installed.
- Cost: $0.
- Privacy: audio stays on the machine.
- Risks: needs capable hardware, English-first, weaker on accents today.

## Recommended direction (proposal)

Local default, plus bring-your-own-key in settings with OS-vault storage, plus
a hosted paid tier later. This ties to roadmap items R-C.3 (free versus paid
tiers) and R-C.2 (legal read of the Gemini terms).

## Connection token

Today the launcher writes a fresh token file and the user pastes it. Near term
option: the launcher copies the token to the clipboard and clears it after about
60 seconds. Same-user processes can already read the token file, so this adds
little exposure. Later option: the same-origin HttpOnly session-cookie flow
already reviewed in [credential design review](../reviews/r01-5-credential-design.md)
(not built), which is the natural step when login arrives.

## Before any of this is built

- A decision in [descisions.md](../../descisions.md) approved by both
  maintainers.
- A design update.
- An independent security review of any new endpoint.

This is an architecture decision. The operator reserves the Fable model or the
council skill for it.
