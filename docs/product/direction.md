# Super-agent: product direction (brainstorm outcome)

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Status | Proposal from a brainstorm session. Not yet agreed by both maintainers. Closes no runtime gate. |
| Inputs | [PRD](../../prd.md), [architecture](../../architecture.md), [phases](../../phases.md) |

## One-line positioning

The voice assistant you can trust with background work: every delegated task
is visible, steerable, stoppable, and logged. "Jarvis with an audit trail."

## Why this angle

Mainstream assistants (ChatGPT voice, Gemini Live, Siri) already win on voice
quality and breadth. An open-source project cannot outspend them there. They
are weak at multi-step background work: tasks are forgotten, progress is not
reported honestly, and there is no way to stop or steer a task midway.

The existing design already solves that gap: the application-owned job ledger
and receipts ([REQ-05](../../prd.md#req-05)), honest `unknown` outcomes
([RT-A04](../../prd.md#rt-a04)), distinct stop controls
([REQ-07](../../prd.md#req-07)), and limits enforced outside the model
([REQ-10](../../prd.md#req-10)). The product leads with that strength.

## Decisions from the session

| Topic | Decision |
| --- | --- |
| Positioning | General trusted assistant, launched to developers first |
| First community | Developers who run AI coding agents (Claude Code, OpenCode, Codex) |
| Voice | Native realtime voice from the first slice |
| Voice provider | Gemini Live, behind the replaceable transport seam ([REQ-15](../../prd.md#req-15)) |
| First real task pair | (a) read: "What are my agent jobs doing?" (b) act: approve or deny one pending agent permission request |
| 6-month goal | Popular open-source project plus first paid users |

These answer part of [RT-G00](../../prd.md#rt-g00) (first real task pair,
provider choice). Account access, region, quota, pricing, host, budgets, and
retention windows are still open.

## Jobs to be done

- When an agent is running a long task, I want to ask how it is going without
  opening the terminal, so I can keep doing other work.
- When an agent is blocked waiting on my permission, I want to answer it from
  wherever I am, so the job does not sit idle for hours.
- When I hand off work, I want an honest record of what happened, so I can
  trust the assistant with more next time.

## Wedges, in build order

1. **Agent status and approval** (first task pair). Read job state; approve or
   deny a pending permission.
2. **Voice control for agents.** Start, steer, and cancel named agent jobs.
3. **Morning standup and triage.** Spoken summary of CI, PRs, and issues.
4. **Agent safety layer.** Budgets, egress allowlist, kill switch, receipts,
   usable around any agent. Strongest paid-tier candidate.

## Assumptions to test (riskiest first)

| # | Assumption | Why it matters | Cheapest test |
| --- | --- | --- | --- |
| A1 | Developers want to supervise agents from outside the terminal | Kills the wedge if false | Ask 15 to 20 agent users; count how often they miss permission prompts |
| A2 | Agent permission prompts can be captured and answered reliably | No integration, no product | Spike: a Claude Code hook that forwards a pending permission to a local endpoint and returns the answer |
| A3 | Gemini Live gives acceptable latency, function calling, and cost for this account and region | Provider is the voice core | One-day spike against the Live API with one tool call; record latency and price |
| A4 | Voice approval can be safe | Voice is not identity ([REQ-09](../../prd.md#req-09)) | Design review: voice may approve only low-risk request classes; anything else needs a device tap |
| A5 | Developers will star and contribute | Drives the OSS goal | Launch the A2 spike as a small standalone tool and measure interest |

A4 is a real tension: approving a permission grants authority. The default must
be that voice approves only pre-classified low-risk requests and everything
else asks for an explicit on-device confirmation.

## Open-source and revenue path

- **Free, self-hosted:** the full assistant, local ledger, and all wedges.
- **Paid hosted tier:** managed voice minutes, cross-device sync, push
  notifications.
- **Paid team tier:** the safety layer with shared policy, audit export, and
  admin controls.

Revenue comes after real daily users. Treat it as the third step, not the first.

## Security baseline for an open-source launch

No project can promise zero vulnerabilities. The commitment is a process:

- `SECURITY.md` with a private reporting channel.
- CodeQL, Dependabot, and secret scanning enabled in CI.
- A threat model kept next to the architecture, updated per phase.
- Independent security review before each release, building on the
  [RT-A05](../../prd.md#rt-a05) negative tests.

## Set aside for now

- Everyday-consumer features (calendar, email, shopping) until the dev launch
  has traction.
- Accessibility-first variant: promising, revisit after v1.
- Local private voice models ([REQ-17](../../prd.md#req-17) notes no verified
  local capability on the observed laptop).

## Next steps

1. Both maintainers review and agree on this direction.
2. Run spikes A2 and A3 (each about one day) and record results here.
3. Do A1 user conversations in parallel.
4. Update the PRD and phases to reflect the chosen task pair and provider.
5. Plan PH-00 and PH-01 as separate PRs.
