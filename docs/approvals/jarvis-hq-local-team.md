# Jarvis HQ local team

On 2026-11-17, maintainer `jeevesh2515` directed Codex to formalize DEC-23
under [DEC-22](../../descisions.md#dec-22), implement the contained local
workspace and shared-ledger handoff, and update
[PR #56](https://github.com/abhishek3059/super-agent/pull/56). The earlier
2026-11-16 direction was to build a Bot HQ-style workspace with Jarvis,
Hermes specialists and a separate browser per worker.

## Approved scope

- Local synthetic development on the operator's machine, including the
  private loopback ledger endpoint and the five HQ worker roles.
- Per-bot workspaces under `~/.super-agent/hq/engines/<botId>/workspace`.
  Workers require macOS containment and an explicitly configured local
  inference endpoint. The server keeps the owner and ledger credentials.
- Existing Bot HQ code is reused under the
  [third-party notices](../../apps/hq/THIRD_PARTY_NOTICES.md).

## Open gates

The approval leaves the main roadmap phase unchanged. Real personal voice
and provider data use remain subject to R-A.2. The operator previously
indicated willingness to fund OpenAI voice, recorded in the original PR
history. Live billing and provider validation were outside this run.
Track H still requires supported runtime evidence, independent review and
the merge checks. The bounded prototype does not grant T4 authority.
