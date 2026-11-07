# Super-agent — documentation pack

Design and planning documentation for a Jarvis-like personal assistant with
native voice-to-voice conversation, hands-free active-session use, and bounded
background task delegation.

> **Documentation only.** There is no application scaffold, runnable assistant,
> installed dependency, provider account, or executed build/test in this
> repository. All runtime gates remain open.

## Start here

| Document | Purpose |
| --- | --- |
| [PRD](prd.md) | Requirements REQ-01–REQ-18, acceptance criteria, runtime gates |
| [Architecture](architecture.md) | Proposed components, trust boundaries, job states, data paths |
| [Phases](phases.md) | Milestone plan PH-DOC–PH-07 with entry and exit gates |
| [Progress](progress.md) | Dated documentation milestone and dispositions |
| [Build](build.md) | Build position; future commands are proposed and not runnable |
| [Decisions](descisions.md) | Decision register DEC-01–DEC-16 |
| [Flows](flow.md) | Ten numbered workflows WF-01–WF-10 |
| [Tasks](taks/README.md) | Twelve future task records, all `not started` |
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
