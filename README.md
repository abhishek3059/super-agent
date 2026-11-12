# Super-agent — documentation pack

Design and planning documentation for a Jarvis-like personal assistant with
native voice-to-voice conversation, hands-free active-session use, and bounded
background task delegation.

> **Mostly documentation.** The runnable application code is a local voice
> scaffold in [`apps/`](apps/voice-foundation.md). Its browser console constructs
> only the fake streaming adapter. A Gemini Live adapter and locked SDK exist
> behind the seam, and an opt-in command has run it with synthetic speech. The
> browser is not wired to Gemini. There are no tools, workers, stored audio, or
> complete runnable assistant. RT-G01 and later runtime gates remain open.

## Start here

| Document | Purpose |
| --- | --- |
| [PRD](prd.md) | Requirements REQ-01–REQ-18, acceptance criteria, runtime gates |
| [Architecture](architecture.md) | Proposed components, trust boundaries, job states, data paths |
| [Roadmap](roadmap.md) | The path and checklist of record: phases with tickable items (agents tick with evidence) |
| [Phases](phases.md) | Milestone plan PH-DOC–PH-07 with entry and exit gates |
| [Progress](progress.md) | Dated documentation milestone and dispositions |
| [Build](build.md) | Current app-specific commands and the historical repository-root command proposal |
| [Decisions](descisions.md) | Decision register DEC-01–DEC-19 |
| [Flows](flow.md) | Ten numbered workflows WF-01–WF-10 |
| [Tasks](tasks/README.md) | Twelve task records; RT-001 is complete, RT-002 and RT-003 are in progress, and RT-004 and later tasks are `not started` |
| [Council meetings](council%20meetings/README.md) | Three archived deliberation records |

## Supporting records

- [Signed design contract](docs/design/super-agent.md)
- [Voice-foundation implementation design](docs/design/voice-foundation.md) (proposal)
- [Offline voice scaffold](apps/voice-foundation.md)
- [Discovery brief](docs/delivery/super-agent-brief.md)
- [Council deliberation source](docs/delivery/council.md)
- [Delivery status](docs/delivery/super-agent.md)
- [Independent design review](docs/reviews/super-agent.md) — PASS (revision 3)
- [Initial review archive](docs/reviews/super-agent-initial.md) — preserved FAIL
- [Design-stage security assessment](docs/security/super-agent.md) — PASS
- [Implementation report](docs/implementation/super-agent.md)
- [Learnings index](docs/learnings/README.md)
- [Zero-cost build stack](docs/free-stack.md) (research proposal)
- [Personal-agent architecture](docs/product/personal-agent-architecture.md) (brainstorm proposal)
- [Lucidchart architecture references](docs/References/README.md)

## Contributing (AI agents)

- Agent rulebook: [AGENTS.md](AGENTS.md). Every agent reads it first.
- Full workflow: [CONTRIBUTING.md](CONTRIBUTING.md).
- `develop` is the integration branch; `main` is production. Feature work goes
  through a PR into `develop`, then `develop` is merged into `main` for release.
- Pull requests use [`.github/pull_request_template.md`](.github/pull_request_template.md).
- Run `npm ci` once after cloning, then `npm run check` before committing.
- Hooks: `pre-commit` and `pre-push` run the repository check; `commit-msg`
  enforces Conventional Commits. CI runs the same check on GitHub.
- The tooling checks secrets, conflict markers, large files, and local Markdown
  links/anchors. It does not build or run the assistant.

## Scope boundaries

- Native live audio is the conversation interface; no mandatory external
  STT → text-chat → TTS pipeline.
- Voice is not identity. High-risk actions remain disabled without stronger
  out-of-band or device authentication.
- Cloud models are authorized for synthetic-only development. Personal
  microphone and context egress remain unapproved. Provider access, budgets,
  retention, and the first task pair are recorded. RT-G00 is resolved for the
  bounded PH-01 scope. Personal microphone and context egress remain
  unapproved.
- Raw audio and persistent transcripts are off by default.
- The observed 8 GB RAM / 4 GB VRAM laptop has no verified native-local or
  always-on/locked-screen capability.
- Only fixed, trusted, read-only synthetic workers are planned initially; no
  arbitrary code, host shell, plugins, or external actions.
