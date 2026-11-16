# Agent backend: background delegation (design)

| Field | Value |
| --- | --- |
| Date | 2026-11-15 |
| Author | Drafted by Claude Sonnet 5.5 (`claude-sonnet-5-5`); architecture and revisions by Claude Fable 5.2 (`claude-fable-5-2`); operator `abhishek3059` |
| Status | **Proposal.** This document builds nothing, ticks no roadmap item, and closes no gate. Slices built from it have their own records, linked in section 10. |
| Approval | [Agent backend exception](../approvals/agent-backend-exception.md) |
| Builds on | [brain overview](brain/overview.md), [brain evaluation](brain/evaluation.md), [tier 1 read tools](tier1-read-tools.md), [RT-004](../../tasks/004-task-ledger-and-policy.md), [RT-005](../../tasks/005-fixed-sample-workers.md), [RT-009](../../tasks/009-bounded-real-task-planner.md) |

This is the design of one slice: the user delegates a task, the assistant
answers at once, and the work runs in the background under a ledger. All
numbers are provisional and unmeasured ([REQ-17](../../prd.md#req-17)).
Claims about external packages are marked UNVERIFIED.

## 1. What exists today

| Fact | Source |
| --- | --- |
| Current phase is PH-01. R-01.10 is unticked (R-01.4 is ticked). PH-02 and PH-04 are not started. | [roadmap.md](../../roadmap.md) |
| No ledger, planner, or worker exists. | [brain overview, section 1](brain/overview.md#1-what-exists-today) |
| The voice adapter seam is `VoiceAdapter` (`start`, `enqueue_audio`, `end_audio_stream`, `interrupt`, `events`, `close`). | [adapter.py](../../apps/api/src/super_agent_voice/adapter.py) |
| Adapters: Gemini Live and a local cascade. | [gemini_adapter.py](../../apps/api/src/super_agent_voice/gemini_adapter.py), [local_adapter.py](../../apps/api/src/super_agent_voice/local_adapter.py) |
| Local memory (facts, reminders) lives in `~/.super-agent/memory.db`; it has a `context(query)` function and its own tool schemas. | [memory.py](../../apps/api/src/super_agent_voice/memory.py) |
| Tier 1 read-only tools (files, calendar, notes, mail) are opt-in through `SUPER_AGENT_T1`. They read real local data. | [tier1.py](../../apps/api/src/super_agent_voice/tier1.py), [tier 1 design](tier1-read-tools.md) |
| Fixed tools: `calculate`, `current_time`. | [tools.py](../../apps/api/src/super_agent_voice/tools.py) |
| Cloud calls may carry synthetic data only. Budget is $0. Job metadata was deleted 24 hours after a terminal state; amended to 14 days on 2026-11-15. | [PH-00 setup decisions](../approvals/ph-00-setup-decisions.md) |

## 2. Flow

The conversation loop (voice or text) decides the user delegated a task. It
calls one tool, `delegate_task`, with a typed task spec. Code does the rest.

```text
 user (voice or text)
        |
        v
 conversation loop (model) --- delegate_task(spec) ---+
        ^                                              v
        |                              +---------------------------+
        |   receipt at once            | ledger (SQLite)           |
        +------------------------------|  create job: queued       |
        |                              |  idempotency key, rev 1   |
        |                              +-------------+-------------+
        |                                            | background runner
        |                                            | (off the event loop)
        |                                            v
        |                     +----------------------------------------+
        |                     | one LangGraph graph per job            |
        |                     | clarify? -> plan -> execute -> verify  |
        |                     |            -> write receipt            |
        |                     +-------------------+--------------------+
        |                                         | app code writes a ledger
        |                                         | transition at every node edge
        |                                         v
        |                     +---------------------------+
        +-- job ended: brief -| ledger: succeeded/failed/ |
            the user          |  cancelled/unknown        |
                              +---------------------------+
```

Steps:

1. **Delegate.** `delegate_task` validates the spec against a schema. The
   ledger creates a job in `queued` with an idempotency key and returns a
   receipt (job ID, revision, state). The conversation continues.
2. **Run.** A background runner takes the job, off the conversation event
   loop ([RT-A02, RT-A03](../../prd.md#rt-a03)). The ledger moves it to
   `running`.
3. **Clarify, only if needed.** If the spec is ambiguous, the graph asks one
   question, surfaced to the user through the conversation loop. The eight
   states have no state for this wait; see open decision 7.
4. **Plan, execute, verify.** The planner emits typed steps from a fixed
   catalog. Each step runs with a scoped tool set. A verifier checks the
   result against receipts, not against model confidence.
5. **Receipt and brief.** The graph writes a receipt. The ledger records the
   terminal state. The conversation loop is told, and brings it up at the
   next turn boundary ([brain overview, section 8](brain/overview.md#8-timing-the-queue-and-the-brief)).

## 3. The ledger owns truth

- SQLite file, owned by the app. It holds the job, its state, its revision,
  its idempotency key, and its receipts.
- States are the eight in [architecture.md](../../architecture.md#canonical-job-states):
  `queued`, `running`, `waiting_for_approval`, `cancel_requested`,
  `succeeded`, `failed`, `cancelled`, `unknown`. This design adds none.
- LangGraph is only the executor under the ledger. Its checkpointer is not
  the source of truth. App code writes a ledger transition at each node
  boundary, in the same transaction as the step receipt.
- On restart the ledger decides what resumes. A `running` job with no proof of
  stop becomes `unknown`. Recovery to `queued` follows the
  [architecture rule](../../architecture.md#canonical-job-states): only with
  evidence of a safe read-only retry. No blind replay.
- Retention: job history is deleted 14 days after a terminal state. The
  operator decided this on 2026-11-15, and the
  [PH-00 record](../approvals/ph-00-setup-decisions.md#amendments) is amended
  in the same change. The ledger's purge function implements it and is tested ([ledger record](../implementation/agent-backend-ledger.md)); nothing schedules the purge yet. Until the 30 days approved under OD-18 is reconciled with this decision, 14 days governs everything the ledger stores.

## 4. "Subagent" means a bounded worker run

One job is one graph run. It has its own model context and a fixed, scoped
tool set that policy code picks from the task type. It is not a new process
with new authority.

- The model never grants or widens scope.
- No arbitrary shell, plugins, or dynamic code ([REQ-08](../../prd.md#req-08)).
- The planner emits typed steps chosen from a **fixed step catalog**. Code
  rejects a step type that is not in the catalog, and a step whose arguments
  fail the schema.
- The first catalog is small: `read_tool` (one allowlisted read-only tool
  call), `summarize` (a model call over bounded step output), `ask_user` (the
  clarify question), and `finish`. Exact schemas are implementation work.

**The graph is dynamic; the step types are not.** The operator decided on
2026-11-15 that tasks are model-planned and each job gets its own graph. The
planner returns a plan: a list of typed steps and which steps depend on which.
Code validates the whole plan before anything runs (every step type in the
catalog, every argument valid, no cycle, step count within the limit) and then
builds the LangGraph graph from it. A plan that fails validation is rejected
and the job fails closed. The shape of the graph changes per task. What a step
may do, and which tools it may touch, is still fixed by the catalog and policy
code.

## 5. Limits outside the model (REQ-10)

All enforced in code. A breach fails closed: the job goes to `failed`, or to
`unknown` if the outcome cannot be proven.

| Limit | First value (provisional) |
| --- | --- |
| Steps per job | 8 |
| Per-step deadline | 30 seconds |
| Per-job deadline | 5 minutes |
| Retries per step | 1, read-only steps only |
| Model calls per job | 12 |
| Input size per model call | 8,000 characters |
| Output size per step | 4,000 characters |
| Concurrent jobs | 2 |
| Jobs queued | 5 |
| Instruction length | 1,000 characters (added by slice 2) |

Slice 2 admits a job only while non-terminal jobs are below concurrent plus
queued (7). Every value also has a hard ceiling in code
([record](../implementation/agent-backend-limits.md)).

Budgets are not reset by a revision or by steering
([RT-004 failure considerations](../../tasks/004-task-ledger-and-policy.md)).
Free-tier request counts are the only budget at $0, so the runner also counts
provider requests per day.

## 6. Model seam

A small planner-model interface, in the style of the existing
[adapter seam](../../apps/api/src/super_agent_voice/adapter.py): one method
that takes an assembled prompt and a response schema and returns a typed reply
or a fixed error category.

First implementation: the **Gemini text API on the free tier**. The key comes
from the process environment only. Synthetic data only, because Gemini is the
approved recipient for generated synthetic content only
([R-00.4](../approvals/ph-00-setup-decisions.md)). A local text model, and any
paid model, sit behind the same seam later. A scripted fake model implements
it for tests, as in [evaluation tier A](brain/evaluation.md#1-two-tiers-of-test).

What testers do:

- **A normal laptop:** text input, the Gemini text model, synthetic data.
- **A capable machine** (one that can run a local speech-to-speech model):
  voice runs locally through an existing local adapter, and the same
  `delegate_task` tool is offered to it. Real personal data never goes to a
  cloud model.

UNVERIFIED (not checked against a primary source this session): a Claude Pro
chat subscription does not include API usage, so calling a Haiku model from the
backend would be a paid API. That needs a maintainer's approval under the $0
rule. This design therefore does not choose Haiku. No model decision is final.
The Gemini verification record covers the Live session; that it also covers the
text API on the free tier is not verified here.

## 7. Tools in the first slice

The first slice uses existing read-only tools only: `calculate` and
`current_time` in [tools.py](../../apps/api/src/super_agent_voice/tools.py),
and, behind opt-in, the tier 1 tools in
[tier1.py](../../apps/api/src/super_agent_voice/tier1.py) and the read-only
parts of [memory.py](../../apps/api/src/super_agent_voice/memory.py).

Limit: tier 1 tools and the memory layer read real personal data. While the planner model is a cloud
model, that data must not reach it ([REQ-13](../../prd.md#req-13)). So tier 1
tools, the memory tools, and memory context are offered to a job only when the planner model is local, or when
trusted deployment configuration states that the allowlisted folders (tier 1 file tools) or the memory file hold
synthetic data only. That flag covers the allowlisted folders only: the calendar, notes and mail tools read the
user's real apps, and they need a local planner. Neither statement comes from the task spec, which the conversation model writes; the spec's data class
can only make admission stricter. Code enforces this at admission, not by prompt. See conflict C2.

"Research" over the open web needs a search or fetch provider. That is a new
recipient and an egress decision at $0, so it is out of the first slice and is
open decision 2.

## 8. Brain in this slice

- **Context assembly.** A code component builds the planner prompt from the
  task spec, step receipts, and a read-only call to the existing memory layer
  ([`memory.context`](../../apps/api/src/super_agent_voice/memory.py)). Memory
  content is data, labelled untrusted, per
  [brain overview, section 5.1](brain/overview.md#51-trust-labels). The planner
  cannot write memory. With a cloud planner, memory context is left out unless the memory file is synthetic (section 7). `memory.py` states that nothing in it reaches the network, and this design keeps that.
- **Evaluation set.** About 20 synthetic delegated tasks, each with an expected
  receipt, used to measure any later prompt or model change. It follows the
  tier A and tier B split in [evaluation](brain/evaluation.md#1-two-tiers-of-test).
- **"Self-improving" in this project means, in order:** a memory distiller
  (proposed as R-M.12 in [brain overview](brain/overview.md#12-roadmap-proposal-proposed-text-only)),
  the evaluation set, measured prompt changes, and only later any training, on
  synthetic data. Nothing here trains a model.

## 9. LangGraph as a dependency

**Added 2026-11-16** by the commit `build(api): add langgraph 1.2.19 behind the job runner`, after the
maintainer's decision (open decision 6). `langgraph==1.2.19` is pinned in
`apps/api/pyproject.toml`, `requirements.in` and `requirements.lock`.

Checked by the orchestrator (Claude Fable 5.2) on 2026-11-16 against PyPI metadata, installed package
metadata and `pip-audit`; not checked by a maintainer:

- Resolved with `pip install --only-binary=:all: --uploaded-prior-to 2026-11-02T00:00:00Z -r apps/api/requirements.lock
  langgraph==1.2.19` on Python 3.14.4, Windows. `pip check`: no broken requirements. No existing pin changed.
- 16 packages were added, all released at least 14 days before 2026-11-16 (`langgraph` itself on 2026-10-30), so
  [AGENTS.md section 6](../../AGENTS.md) is met. Licences, from installed package metadata:

| Package | Version | Licence |
| --- | --- | --- |
| `langgraph` | 1.2.19 | MIT |
| `langgraph-checkpoint` | 4.3.1 | MIT |
| `langgraph-prebuilt` | 1.1.1 | MIT |
| `langgraph-sdk` | 0.4.11 | MIT |
| `langchain-core` | 1.7.3 | MIT |
| `langchain-protocol` | 0.0.20 | MIT |
| `langsmith` | 0.14.16 | MIT |
| `jsonpatch` | 1.39 | BSD-3-Clause |
| `jsonpointer` | 3.7 | Modified BSD |
| `orjson` | 3.13.0 | MPL-2.0 AND (Apache-2.0 OR MIT) |
| `ormsgpack` | 1.13.0 | Apache-2.0 OR MIT |
| `PyYAML` | 6.0.3 | MIT |
| `requests-toolbelt` | 1.0.0 | Apache 2.0 |
| `uuid_utils` | 0.19.0 | BSD-3-Clause |
| `xxhash` | 4.0.2 | BSD-2-Clause |
| `zstandard` | 0.25.0 | BSD-3-Clause |

- Flag: `orjson` includes MPL-2.0, a file-level copyleft licence. It is used unmodified as a dependency. No
  package has a non-commercial or custom licence.
- `pip-audit` on the resolved set: 0 known vulnerabilities in the 16 new packages. It reports one in a package
  that was already pinned before this change: `opentelemetry-api 1.45.1`, CVE-2026-126360, fixed in 1.45.2. That
  is pre-existing, this change does not touch it, and bumping it is a maintainer decision.
- `langgraph-api` (the Elastic-licensed server) is not in the installed set (`import langgraph_api` fails), and it
  must not be installed. `langgraph-checkpoint-sqlite` is not installed either, and the graph is compiled with no
  checkpointer, so the ledger stays the truth.
- `langsmith` is a tracing client. With tracing environment variables set it sends run data to a cloud service,
  which would be an unapproved recipient ([REQ-13](../../prd.md#req-13)). The graph work refuses to run when any
  such variable is set (built by the next commit).

Still UNVERIFIED: that a SQL-injection issue was disclosed in March 2026 in the SQLite checkpointer package (not
used here), and any claim about LangGraph not listed above.

## 10. Mapping and build order

| Part | Roadmap items | Requirements |
| --- | --- | --- |
| Ledger: states, receipts, idempotency, revisions | R-02.1, R-02.2 | REQ-05, REQ-06 |
| Limits and admission in code | R-02.3 | REQ-10 |
| Read-only step catalog, scoped tool sets (not the two fixed workers; see decided item 3) | R-02.4 in part | REQ-08 |
| Background runner off the event loop | R-02.5 | REQ-04 |
| Clarify node (bounded part) | R-04.2 | REQ-16 |
| Typed steps, step catalog, verifier (bounded part) | R-04.3 | REQ-08, REQ-10, REQ-16 |
| Model seam, synthetic data only | R-02.3 | REQ-13, REQ-15 |
| Local API binding and token | existing boundary | REQ-11 |

Proposed build order, each slice with its test:

1. **Ledger.** SQLite tables, state machine, idempotency key, revision. Test:
   illegal transitions rejected; a repeated key returns the same job; a restart
   turns a `running` job into `unknown`. No model, no LangGraph. Built:
   [implementation record](../implementation/agent-backend-ledger.md).
2. **Limits and admission.** Schemas, size caps, queue caps, deadlines. Test:
   each limit breach fails closed. Built:
   [implementation record](../implementation/agent-backend-limits.md).
3. **Runner.** A background runner with a stub graph. Test: the conversation
   loop answers while a job runs; cancel moves to `cancel_requested`. Built:
   [implementation record](../implementation/agent-backend-runner.md).
4. **Model seam with a scripted fake.** Test: hostile model output (unknown
   step type, widened scope) is rejected in code. Built:
   [implementation record](../implementation/agent-backend-planner.md).
5. **Dynamic graph.** Plan validation, then a graph built from the validated
   plan: execute, verify, receipt on the fake model, then clarify. Test: each
   node edge writes one ledger transition; a plan with an unknown step type, a
   cycle, or too many steps is rejected before any step runs.
6. **`delegate_task` wired to the conversation loop**, text first. Test: a real
   API call through the agent returns a receipt at once.
7. **Gemini text model** behind the seam. Test: opt-in live check, synthetic
   data, key from the environment, timing and state logged only.
8. **Evaluation set** of about 20 tasks. Test: a deterministic run on the fake
   model passes 100%; a model run reports a rate.

## 11. Conflicts and open decisions

### Conflicts found with existing documents

| ID | Conflict | Where | Handling here |
| --- | --- | --- | --- |
| C1 | The brain design gives the conversation model four tools: `propose_task`, `query_ledger`, `cancel_task`, `steer_task`. This design names the entry tool `delegate_task`. | [brain overview, section 6](brain/overview.md#6-system-1-tool-contracts) | Not resolved. Proposal: `delegate_task` is the same admission step as `propose_task`, and the other three tools stay. A maintainer picks one name. |
| C2 | Tier 1 tools read real local data. Sending their output to a cloud planner breaks the synthetic-only boundary. [DEC-18](../../descisions.md#dec-18) also places T1 after the PH-02 policy layer, and the tier 1 design notes it is not behind that layer yet. | [tier1-read-tools.md](tier1-read-tools.md) known limits; [REQ-13](../../prd.md#req-13) | Section 7: tier 1 only with a local planner or synthetic folders, enforced at admission. This slice is the policy layer tier 1 waits for, so it must not weaken it. |
| C3 | PH-02 means two deterministic trusted workers. A model-planned graph is PH-04 work, and PH-04 entry needs RT-G04 and an approved real task pair. | [phases.md](../../phases.md) PH-02, PH-04 | Covered by the exception for the bounded parts only. Open decision 3. |
| C4 | [REQ-08](../../prd.md#req-08) says initial workers are small trusted fixed functions. Decided item 3 starts with model-planned tasks instead. | [prd.md](../../prd.md#req-08) | Not resolved. Every step in the catalog is still a fixed trusted function, but the requirement text and the PH-02 gate describe fixed workers. A maintainer changes that text or the workers get built. See decided item 3. |
| C5 | PH-00 deletes job metadata 24 hours after a terminal state. The brain design says some scenarios need longer. | [PH-00 setup decisions](../approvals/ph-00-setup-decisions.md); brain OD-18 in [overview](brain/overview.md#10-open-maintainer-decisions) | Resolved for job history: 14 days, decided 2026-11-15 (item 8). The 30 days approved for task specs and checkpoints under OD-18 is longer than 14 days and is not reconciled here. |
| C6 | The brain design treats the ledger contract as fixed and lists interface requests IR-1 to IR-10 (an origin field, `job_terminal` events, and others). This slice builds the ledger, so it must decide them. | [brain overview, section 11](brain/overview.md#11-interface-requests-for-the-ledger) | Build only the fields the slice needs. The rest wait. |

### Open decisions for a maintainer

1. **First model.** Gemini text on the free tier (proposed), a local text
   model, or a paid Haiku model (needs approval under the $0 rule; the Claude
   Pro claim above is unverified).
2. **Web research provider.** A search or fetch service is a new recipient and
   egress decision under [REQ-13](../../prd.md#req-13). Keep it out of the
   first slice, or approve a named one.
3. **Fixed workers first. Decided 2026-11-15 by `abhishek3059`: no.** Tasks are
   model-planned with a dynamic graph from the start (section 4). Consequence,
   still open: R-02.4 and the PH-02 exit gate in [phases.md](../../phases.md)
   ask for two trusted fixed workers
   ([RT-005](../../tasks/005-fixed-sample-workers.md)). This slice does not
   build them, so it cannot tick R-02.4 as written. Either they are built
   later, or the gate changes in a roadmap PR.
4. **Ledger file location.** A separate `~/.super-agent/ledger.db` next to
   `memory.db` matches option (b) of brain OD-10 in the
   [overview](brain/overview.md#10-open-maintainer-decisions). Confirm.
5. **Tool name.** `delegate_task` or `propose_task` (conflict C1).
6. **LangGraph checks. Decided 2026-11-16 by `abhishek3059`: add LangGraph 1.2.19** as the executor
   (chat). The orchestrator's checks are in section 9. Still open for a maintainer: the pre-existing
   `opentelemetry-api` advisory, and the one UNVERIFIED claim.
7. **Clarify wait state.** The eight states have no "waiting for the user's
   answer" state, and `waiting_for_approval` is defined for configured approval
   checkpoints only. Options: reuse it with a distinct reason code, or run the
   clarify step before admission so a job starts only with a complete spec. The
   second adds no state and is proposed.
8. **Retention. Decided 2026-11-15 by `abhishek3059`: 14 days** for job
   history. Still open: whether 14 days also replaces the 30 days approved
   under OD-18 for task specs and checkpoints.

## 12. What this does not do

This document itself adds no code, no dependency, no tick, and no gate. It approves no auth, remote
access, paid service, new recipient, or higher capability tier.
