# Dual-loop foundation and distributed JARVIS evolution

| Field | Value |
| --- | --- |
| Date | 2026-11-11 |
| Status | Target architecture proposal from the maintainers. Not a decision, closes no gate, authorizes nothing at runtime. Phase numbers below are mapped to the repository phases in [the completion plan](../implementation/completion-plan.md#4-phase-mapping); [phases.md](../../phases.md) and [roadmap.md](../../roadmap.md) stay authoritative. |
| Prerequisites | PH-00 (done) and PH-01 (in progress) |

## Part 1: single-host foundation and dual-loop architecture

A native voice-to-voice stream is easy to get from modern APIs (Gemini Live
over WebSockets, see [DEC-01](../../descisions.md)). The hard part is the
system: an agent that keeps chatting in the foreground while it runs
multi-step research in the background, remembers personal context without
breaking privacy, uses the computer safely, and runs scheduled local tasks.

### 1.1 System 1 / System 2

Most voice assistants freeze during tool calls because tools run inside the
audio turn loop. super-agent splits the work into two loops joined by an
application-owned ledger.

```text
SYSTEM 1: foreground voice companion (low-latency audio loop)
  Browser audio and control UI + native transport adapter + conversation coordinator
  Invariant: never runs heavy tools, scrapers, or shell commands on this loop
  Tools: ledger calls only (propose_task, query_ledger, cancel_task)
        |
        | typed task spec, < 50 ms, via the SQLite ledger
        v
THE BRIDGE: SQLite tiny ledger and admission broker (DEC-03, DEC-06)
  Ledger holds jobs, idempotency keys, leases, and receipts
  Turn-boundary notification queue holds finished receipts until a pause
        |
        | async execution off the audio thread (DEC-04)
        v
SYSTEM 2: background planner and worker graph
  Bounded trusted worker executor + bounded planner + local MCP adapters
  Writes verified receipts and structured summaries back to the ledger
```

- **System 1** handles live conversation, turn-taking, barge-in (WF-03), and
  presence. For a complex request it validates a typed proposal against the
  policy and admission broker, writes a job to the ledger, gets a `job_id` in
  under 50 ms ([REQ-04](../../prd.md#req-04)), and goes back to the
  conversation.
- **System 2** runs in worker processes off the voice event loop, executes
  research or tool calls, and writes verified receipts back to SQLite
  ([REQ-05](../../prd.md#req-05)).
- **Turn-boundary queue.** When a job finishes, the result verifier places a
  `completion_ready` event in a pending queue. At the next natural pause
  (WF-02) System 1 bridges the result: "By the way, I finished the Goa flight
  search. Want the options now, or keep talking about your weekend?"

### 1.2 Four pillars

1. **Parallel background research.** Upgrade the synthetic sample workers to
   a research graph: search, fetch, synthesize with citations. Every claim
   System 1 speaks must link to a verified tool receipt in the ledger.
2. **Companion with slot filling.** No raw transcripts or audio are stored by
   default ([REQ-14](../../prd.md#req-14)). Instead an inspectable semantic
   profile table holds distilled, user-confirmed preferences such as
   `travel.home_city`. Before dispatch, System 1 checks the task schema
   against the profile, asks for missing slots in conversation, then locks
   and dispatches the typed proposal.
3. **Local scheduling and wake.** A schedule table stores `schedule_id`,
   `cron_or_timestamp`, `task_payload_json`, `last_run_at`, `next_run_at`,
   and `misfire_policy` (`RUN_IMMEDIATELY_ON_WAKE`, `ASK_USER_ON_WAKE`,
   `SKIP`). On OS resume the daemon reconciles missed runs and briefs the
   user ([REQ-18](../../prd.md#req-18)).
4. **Three permission rings** enforced by the policy broker:

| Ring | Scope | Gate | Examples |
| --- | --- | --- | --- |
| 0, read-only | Non-mutating queries, web search, metrics, allowed directories | Autonomous, voice triggered | Docs search, git status, calendar read |
| 1, bounded workspace | Writes inside `~/SuperAgentWorkspace/`, drafts, local schedules | Autonomous with audit receipt and undo | Trip reports, research notes |
| 2, host and external | Shell outside sandbox, deletions, email, installs | Out-of-band confirmation card on a screen; voice alone never authorizes ([DEC-08](../../descisions.md)) | Sending mail, deleting files |

## Part 2: distributed central brain and edge hubs

After the single-host phases and their gates are evidenced, the ledger,
policy broker, scheduler, and conversation coordinator move to an always-on
central brain reached over a private mesh.

```text
                CENTRAL BRAIN (home mini-PC, the Mac, or a free VPS)
                conversation coordinator | scheduler daemon
                central policy and admission broker
                unified SQLite ledger + semantic profile
                              ^
        private WireGuard / Tailscale mesh, no public ports
        |                     |                         |
  MOBILE EDGE           WORKSTATION               REMOTE SERVER
  audio I/O             audio I/O, files, IDE     headless daemon
  notification bus      Ring 2 desktop card       unattended jobs, crawls
  presence beacon       sleep-aware node          bounded remote workers
```

- **Mobile edge:** streams audio to the brain; an Android
  `NotificationListenerService` with a strict local allowlist (bank, UPI,
  2FA, account security) sanitizes alerts into structured events before
  forwarding; a presence beacon tells the brain where to route audio.
- **Workstation:** MCP daemon for local files and tools; renders Ring 2
  confirmation cards; reports sleep and wake.
- **Remote server:** 24/7 unattended jobs so the laptop can sleep.

### Cross-device workflows

- **WF-11 notification triage:** phone event, urgency policy (low goes to a
  digest, critical interrupts), presence lookup, then a spoken nudge at the
  next pause, a chime when idle, or the digest when away.
- **WF-12 distributed routing:** the coordinator resolves the target node,
  checks it is awake, dispatches a bounded job through that node's MCP
  daemon, and speaks the verified receipt back. A sleeping target gets the
  job queued or offered on the remote runner.

### Distributed security invariants

1. Mesh only: no public IPs, forwarded ports, or plain HTTP.
2. Per-device asymmetric identity paired in a setup ritual.
3. Rings 0 and 1 autonomous within quotas; Ring 2 needs a physical
   confirmation on an active screen (DEC-08, RT-G05).
4. Raw audio and verbatim transcripts are never saved (REQ-14, DEC-05);
   only distilled profile attributes and verified receipts persist.
