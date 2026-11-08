# Super-agent — documentation pack

Design and planning documentation for a Jarvis-like personal assistant with
native voice-to-voice conversation, hands-free active-session use, and bounded
background task delegation.

> **Documentation only.** There is no application scaffold, runnable assistant,
> application dependency, provider account, or executed application build/test in
> this repository. Husky is installed for repository checks only. All runtime
> gates remain open.

## Start here

| Document | Purpose |
| --- | --- |
| [PRD](prd.md) | Requirements REQ-01–REQ-18, acceptance criteria, runtime gates |
| [Architecture](architecture.md) | Proposed components, trust boundaries, job states, data paths |
| [Phases](phases.md) | Milestone plan PH-DOC–PH-07 with entry and exit gates |
| [Progress](progress.md) | Dated documentation milestone and dispositions |
| [Build](build.md) | Build position; future commands are proposed and not runnable |
| [Decisions](descisions.md) | Decision register DEC-01–DEC-17 |
| [Flows](flow.md) | Ten numbered workflows WF-01–WF-10 |
| [Tasks](tasks/README.md) | Twelve future task records, all `not started` |
| [Council meetings](council%20meetings/README.md) | Three archived deliberation records |

## Supporting records

- [Signed design contract](docs/design/super-agent.md)
- [Discovery brief](docs/delivery/super-agent-brief.md)
- [Council deliberation source](docs/delivery/council.md)
- [Delivery status](docs/delivery/super-agent.md)
- [Independent design review](docs/reviews/super-agent.md) — PASS (revision 3)
- [Initial review archive](docs/reviews/super-agent-initial.md) — preserved FAIL
- [Design-stage security assessment](docs/security/super-agent.md) — PASS
- [Implementation report](docs/implementation/super-agent.md)
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
- Cloud models are authorized for development only. Runtime microphone/context
  egress, provider eligibility, account access, budgets, retention, and the first
  real task pair are unresolved gates (RT-G00).
- Raw audio and persistent transcripts are off by default.
- The observed 8 GB RAM / 4 GB VRAM laptop has no verified native-local or
  always-on/locked-screen capability.
- Only fixed, trusted, read-only synthetic workers are planned initially; no
  arbitrary code, host shell, plugins, or external actions.
