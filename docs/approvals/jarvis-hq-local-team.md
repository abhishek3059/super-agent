# Jarvis HQ local team: maintainer direction and exception

| Field | Value |
| --- | --- |
| Date | 2026-11-16 |
| Scope | Build `apps/hq`: a local multi-bot workspace adapted from Bot HQ, with Hermes workers, per-bot browsers, bot-to-bot handoff, memory, skins and OpenAI live voice. |
| `jeevesh2515` | **Directed, 2026-11-16**, in chat with Claude Code (`claude-fable-5-2`), which recorded it at his instruction. One maintainer's approval is enough ([DEC-21](../../descisions.md#dec-21)). |
| `abhishek3059` | Not asked. Review of the pull request is open to him. |
| Effect | Records the direction. It is **not** by itself an approval. See the [2026-11-17 decision](jarvis-hq-dec-23-approval.md) for the subsequent approval and its scope. |

## What the maintainer said

This is the agent's summary of the chat, not a quotation, and it links to no
GitHub comment. In chat on 2026-11-16 he asked for the project to work like Bot HQ, with
Jarvis in front and four or five bots that coordinate with it, each with its
own computer, chat and memory, on the Hermes harness, using the AI
subscriptions already set up on his machine. He said he will pay for the
OpenAI live voice model. He asked for anything in Bot HQ that costs nothing
to be reused, for skins, and for the work to be finished end to end. He gave
permission to build it.

## Scope originally submitted for approval

1. **Reuse of Bot HQ code** under its MIT license, with notices kept in
   [apps/hq/THIRD_PARTY_NOTICES.md](../../apps/hq/THIRD_PARTY_NOTICES.md).
2. **One paid service: OpenAI voice** (Realtime, speech and transcription),
   billed to his own key, as [AGENTS.md](../../AGENTS.md) section 6
   requires. No other paid service is requested. The upstream xAI search and Composio connected apps are switched off
   in code and need a separate approval.
3. **Hermes workers on his own machine**, started from his existing Hermes
   model settings and sign-ins.
4. **Work outside the current phase.** PH-01 is still open. This is a
   deliberate parallel build at his direction.
5. **A waiver of roadmap rule 8 for this pull request.** The rule asks for
   roadmap changes in their own pull request. Here DEC-23, the AGENTS.md
   edit, track H and the app arrive together, because he asked for the work
   to be delivered end to end. A maintainer who wants them apart can ask
   for the split before approving.

## What it does not approve, and what stays open

- **The capability ladder is not satisfied.** Hermes workers can run shell
  commands and drive a browser as the operator's user. That is above the
  tiers enabled under [DEC-18](../../descisions.md#dec-18), and the designs
  and independent security reviews that T1 to T3 require have not been done
  for this app. The code does give the workers that capability. DEC-23
  records a bounded exception for it. No tier is enabled.
- **Containment** (updated 2026-11-19). Each bot runs inside the macOS
  sandbox and cannot read the operator's files, the session secret or
  another bot's folder; it reaches the internet only through a proxy that
  refuses local addresses. An [independent security review](../reviews/jarvis-hq-security-review.md)
  closed fifteen findings and accepted one (DNS and any public port remain
  reachable). A bot still holds its own copied model
  keys for the configured providers.
- **Data boundary.** The [PH-00 boundary](ph-00-setup-decisions.md) kept
  personal microphone audio local, and roadmap item R-A.2 (real voice and
  personal data to a cloud provider) is still unticked. Turning on voice
  sends microphone audio to OpenAI. The app leaves voice off until a key is
  supplied. Use synthetic speech and synthetic data until R-A.2 is decided.
- **Purchases, money movement, credential handling and permanent deletion**
  (T4) stay out of scope. The app adds no tool for them. It cannot stop a
  Hermes worker from attempting them through its shell or browser.
- The existing voice foundation in `apps/api` and `apps/web` is unchanged.
