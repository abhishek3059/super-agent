# Super-agent: product direction (brainstorm outcome)

| Field | Value |
| --- | --- |
| Date | 2026-11-07 |
| Revision | 2, general personal-agent refinement dated 2026-11-08 |
| Status | Proposal from brainstorm sessions. Not yet agreed by both maintainers. Closes no runtime gate. |
| Inputs | [PRD](../../prd.md), [architecture](../../architecture.md), [phases](../../phases.md) |

## One-line positioning

A personalized, hands-free assistant that turns vague everyday intentions into
supervised work across digital services and specialized agents. Every job stays
visible, steerable, stoppable, and logged. "Jarvis with an audit trail."

## Why this angle

The intended product is not a voice-only coding assistant and is not limited to
research, travel, communication, coding, or any other example domain. Voice is
a primary hands-free interface. Visual, text, mobile, CLI, and IDE interfaces
remain available when the work needs sources, detailed review, or confirmation.

The assistant interprets vague requests, asks focused clarifying questions,
checks whether approved capabilities can perform the work, and coordinates
bounded jobs concurrently. Examples discussed during brainstorming illustrate
behavior; they do not define the product boundary.

The existing design already solves that gap: the application-owned job ledger
and receipts ([REQ-05](../../prd.md#req-05)), honest `unknown` outcomes
([RT-A04](../../prd.md#rt-a04)), distinct stop controls
([REQ-07](../../prd.md#req-07)), and limits enforced outside the model
([REQ-10](../../prd.md#req-10)). The product leads with that strength.

## Decisions from the session

| Topic | Decision |
| --- | --- |
| Positioning | General personalized assistant for supervised day-to-day work |
| Interaction | Voice-first and hands-free when useful, but not voice-only |
| Core behavior | Understand, clarify, plan, authorize, execute, monitor, verify, and report |
| Capability model | Reviewed adapters for research, planning, communication, services, computers, devices, and future specialized agents |
| Coding agents | Claude Code, Codex, OpenCode, and IDE harnesses are deferred capability adapters, not the initial product boundary |
| Voice provider | No runtime provider approved; Gemini Live remains one development candidate behind the replaceable transport seam |
| First real task pair | Not selected; future validation examples must not become permanent product limits |

These statements refine the proposal but do not resolve
[RT-G00](../../prd.md#rt-g00). The first real validation pair, provider,
account access, region, quota, pricing, host, budgets, recipients, and retention
windows remain open.

## Jobs to be done

- When I express an incomplete or vague goal, I want my assistant to ask the
  minimum useful questions and turn it into a clear plan.
- When several tedious tasks can proceed independently, I want them handled
  concurrently without losing visibility or control.
- When a task needs information, software, a service, or another agent, I want
  the assistant to use only capabilities I approved and report real evidence.
- When work has cost, privacy, identity, or external effects, I want an exact
  preview and appropriate confirmation before commitment.
- When I hand off work, I want an honest record of what happened, including
  failures and uncertainty.

## Wedges, in build order

1. **Conversation and clarification.** Convert vague intent into a structured,
   reviewable task specification.
2. **Supervised read-only work.** Retrieve information through approved sources,
   preserve evidence, and return spoken and visual answers.
3. **Parallel personal work.** Schedule multiple jobs, priorities, dependencies,
   updates, steering, cancellation, and approved personal context.
4. **Prepared actions.** Draft plans and external actions without committing them.
5. **Approved actions and presence.** Add communication, transactions, devices,
   telephony, computer operation, and specialized-agent harnesses only behind
   capability-specific authentication, policy, and verification.

## Assumptions to test (riskiest first)

| # | Assumption | Why it matters | Cheapest test |
| --- | --- | --- | --- |
| A1 | People benefit from a hands-free assistant that clarifies vague day-to-day work | Core value is unproven | Interview target users and test task-clarification prototypes |
| A2 | One clarification and task-specification loop can serve many domains | Avoids hard-coded vertical assistants | Evaluate varied synthetic requests and score missing or unnecessary questions |
| A3 | Read-only capabilities can return timely, sourced, useful answers | First broadly useful capability layer | Test approved sources with citations, freshness, injection, and failure cases |
| A4 | Personalization can help without silent surveillance | Personal context is central and sensitive | Test explicit profile controls, retention, deletion, and denied-context behavior |
| A5 | External actions can remain understandable and controllable | Required before communication, transactions, calls, devices, or coding harnesses | Test previews, exact grants, authenticated approval, cancellation, receipts, and uncertainty |

**Historical coding-adapter spike A2 (2026-11-07): limited evidence for a
future capability.** A Claude Code `PermissionRequest` hook
forwarded real permission requests to a loopback server; allow and deny from
outside the terminal both took effect. Interactive sessions, the timeout path,
and non-Bash tools are not tested yet. Details:
[spikes/a2-permission-hook](../../spikes/a2-permission-hook/README.md).

**Historical voice spike A3 (2026-11-07): limited development evidence.** On the free
tier, `gemini-3.8-live` called the job-status tool in 5 of 5 runs, and the
median time from question to first spoken audio was 873 ms (838 to 1142 ms),
including the tool round trip. Text input and synthetic data only; microphone,
barge-in, and paid-tier cost are not tested yet. Details:
[spikes/a3-gemini-live](../../spikes/a3-gemini-live/README.md).

Voice is not identity and never creates new authority. Voice may express intent
or operate within an already authenticated grant. New authority and
consequential commitments require the confirmation mechanism defined by a
separately approved capability design.

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

1. Both maintainers review the revised direction and the
   [personal-agent architecture proposal](personal-agent-architecture.md).
2. Import and visually verify the [Lucidchart JSON](../References/personal-agent-architecture.json).
3. Run user conversations and task-clarification tests across varied everyday
   requests without treating the examples as product limits.
4. Select a small validation pair and complete the dated PH-00/RT-001 decisions,
   including provider, recipients, host, budget, retention, and authorization.
5. Only after approval, update the canonical PRD, phases, decisions, and task
   records, then propose PH-01 implementation separately.
