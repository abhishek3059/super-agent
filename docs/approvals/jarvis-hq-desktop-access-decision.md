# Jarvis HQ desktop, sign-in and read access decision

On 2026-11-20, maintainer `jeevesh2515` chose the following in chat with
Claude Code (Opus 5.5), from options the agent offered for roadmap item
R-H.6:

- **Computer:** a desktop page and a browser bar inside each bot's existing
  sandboxed Chrome. No Linux desktop, no paid hosted computer.
- **Accounts:** Sign in with ChatGPT through Hermes' Codex OAuth on OpenAI's
  own page, and a Claude Anthropic API key. Claude Pro or Max sign-in was
  declined. Anthropic's
  [legal and compliance page](https://code.claude.com/docs/en/legal-and-compliance)
  (read 2026-11-20) does not permit third-party apps to offer Claude.ai
  login.
- **System access:** read-only folders the operator lists, plus read-only
  facts about the Mac. Read-and-write folders and full, unsandboxed access
  were offered and declined.
- **Skills:** bots load `~/.claude/skills` and `~/.hermes/skills`
  read-only, and share the skills they create through one HQ folder.

Recorded effects on the reviewed boundary:

- This narrows the [R-H.5](../../roadmap.md#parallel-track-h-jarvis-hq-local-team-dec-23)
  statement that a bot cannot read the operator's files. Bots now read the
  listed folders and the skill folders. Secret and HQ folders stay closed
  in code. Read access plus internet egress means a bot can send what it
  reads outward.
- The shared skills folder lets one bot's skill steer another bot.
- Anthropic API worker use is billed per use. No spend cap was stated in
  chat. Before a real key is saved, the maintainer must record a cap or
  approve the spend in the PR.

Not yet done: an independent security review of the sign-in route, the key
endpoint, the read access and the shared skills folder. R-H.6 stays
unticked until that review and the PR merge. This record grants no merge or
release approval and enables no capability tier.
