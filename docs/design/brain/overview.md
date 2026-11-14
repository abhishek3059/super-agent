# Brain design: overview

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Author | Claude Fable 5.2 (`claude-fable-5-2`), operator `abhishek3059` |
| Status | **Proposal.** Design only. Builds nothing, enables no tier, ticks no roadmap item, closes no gate. |
| Brief | `docs/implementation/fable-brain-backend-handover.md` on branch `docs/fable-brain-backend-handover` (commit `4f61f24`, not yet on `develop`) |
| Companion documents | [memory](memory.md), [data layer](data-layer.md), [recommendations](recommendations.md), [threat model](threat-model.md), [evaluation](evaluation.md) |

This is the design of the assistant's brain: who thinks, what each model call
may see, which tools the voice loop holds, and how a vague request becomes a
typed task. The goal the operator set is an assistant that behaves like a real
butler. Section 2 turns that into rules that code can enforce.

Numbers in this pack (token budgets, limits, retention windows) are
**provisional and unmeasured**, as [REQ-17](../../../prd.md#req-17) requires.

## 1. What exists today

Facts, with their source. Everything else in this pack is proposed.

| Fact | Source |
| --- | --- |
| Current phase is PH-01. R-01.4 and R-01.10 are unticked. PH-02 (ledger) is not started. | [roadmap.md](../../../roadmap.md) |
| A voice adapter seam exists: `start`, `enqueue_audio`, `end_audio_stream`, `interrupt`, `events`, `close`. | [adapter.py](../../../apps/api/src/super_agent_voice/adapter.py) |
| The Gemini adapter uses one fixed system instruction and passes no tools. It has no reconnect, session resumption, or context compression. | [gemini_adapter.py](../../../apps/api/src/super_agent_voice/gemini_adapter.py) |
| One voice session at a time, capped at 15 minutes, limits enforced in code. | [config.py](../../../apps/api/src/super_agent_voice/config.py) |
| There is no ledger, no memory store, no planner, and no worker in the repository. | [architecture.md](../../../architecture.md) status row |
| A fully local adapter (speech to text, an Ollama model, text to speech) is proposed in open [PR 36](https://github.com/abhishek3059/super-agent/pull/36). It keeps a 12-message in-memory history, gives the model no tools, and is not merged. | PR 36, `local_adapter.py` |
| Cloud calls may carry synthetic data only. Personal microphone audio stays local. Budget is $0. Job metadata is deleted 24 hours after a terminal state. | [PH-00 setup decisions](../../approvals/ph-00-setup-decisions.md) |
| [DEC-18](../../../descisions.md#dec-18) (the capability ladder) is proposed and awaits `abhishek3059`. | [capability ladder decision](../../approvals/capability-ladder-decision.md) |
| Persistent memory is named as an extension that needs its own approval. | [RT-G05](../../../prd.md#rt-g05) |

## 2. The butler service standard

A good butler is known by conduct, not by how much he can do. Each rule below
has an enforcement point in code. A prompt may describe a rule; it never
enforces one ([REQ-10](../../../prd.md#req-10)).

| ID | Rule | Enforced by |
| --- | --- | --- |
| BR-1 | **Standing orders.** A confirmed preference fills a blank in a task without asking again. The butler says so in a few words: "From Testville, as usual." | Slot filler (section 7); disclosure flag on the task draft |
| BR-2 | **Ask once, never nag.** At most one question per turn and three per task. A slot answered once in a session is not asked again. | Clarification state machine (section 7) |
| BR-3 | **A one-off is not a habit.** A statement that contradicts a standing order applies to this task only. The profile changes only on an explicit, confirmed correction. | Memory conflict rules ([memory](memory.md#6-conflicts)) |
| BR-4 | **Discretion.** Every memory has a speakability class. The voice loop is never given a value it must not say. | Context assembler filter (section 5); [memory](memory.md#4-speakability) |
| BR-5 | **The day book.** The butler reports only what the ledger shows. "Done" needs a `succeeded` snapshot. `unknown` is said as "I can't confirm that." | Tool results and snapshot templates (section 6) |
| BR-6 | **Good timing.** Finished work waits for a pause. A session opens with a short brief of what changed while the user was away. | Turn-boundary queue and brief (section 8) |
| BR-7 | **Knows his station.** One voice speaks. The planner and workers are staff and are never heard directly. Beyond the enabled tier the butler offers to prepare, never to act. | Component split (section 3); policy broker |
| BR-8 | **Forgets completely.** "Forget that" is a job with a receipt that covers the row and every derived copy. | Forget job ([memory](memory.md#7-forgetting)) |

How the butler addresses the user is itself a standing order
(`identity.preferred_address`). With none set, the butler uses no honorific
and no name. The butler's own name and tone are a maintainer choice (OD-11).

## 3. Who does what

The logical components come from [architecture.md](../../../architecture.md).
This design adds two code components with no model inside them: the **memory
service** and the **context assembler**.

| Component | Has a model | Reads | Writes | Never |
| --- | --- | --- | --- | --- |
| Conversation coordinator (System 1, "the butler") | Yes, the voice model | Its assembled context only | Tool calls: `propose_task`, `query_ledger`, `cancel_task`, `steer_task` | Runs a tool, reads a file, reads the memory store directly, states an outcome without a snapshot |
| Context assembler | No | Ledger snapshots, memory service, session memory, task schemas | One prompt per model call, within a budget | Passes a value whose speakability or data class forbids the destination |
| Memory service | No | Memory store | Profile content, only while executing an admitted `memory.*` job; its own bookkeeping | Accepts a write from a model, a worker, or a planner step |
| Policy and admission broker | No | Proposals, grants, limits | Admission decisions | Trusts a prompt |
| Planner (System 2) | Yes, a text model | Admitted task, its grant, step receipts, assembled context | Typed steps for the same task | Adds an operation, scope, or recipient the grant lacks; writes memory |
| Workers | Optional, per operation | Bounded inputs named in the action | Receipts | Proposes tasks; writes memory; talks to the user |
| Result verifier and notification coordinator | No | Receipts, task spec | Outcome, a bounded speakable summary, notification records | Marks success from model confidence |

Two rules follow from the table:

1. **Models propose, code decides.** Every model output is a typed proposal
   that the broker validates ([DEC-07](../../../descisions.md#dec-07)).
2. **Profile content changes only by a user-origin job.** Five fixed
   operations exist in the capability registry (interface request IR-1):

   | Operation | Allowed origin | Confirmation |
   | --- | --- | --- |
   | `memory.remember`, `memory.correct` | `user_turn` | Readback; the screen for a sensitive key |
   | `memory.forget` (one record) | `user_turn` | Readback; the screen for a sensitive key |
   | `memory.forget` (everything), `memory.export` | `user_turn` | The screen, always |
   | `memory.purge` | `system` | None. It deletes only rows past their expiry. |

   No operation is admitted from a planner step, a worker, or a schedule.
   Code also keeps bookkeeping that is not profile content: day-book rows,
   usage and contradiction counters, and suggestion cooldowns. The full list
   is in [memory](memory.md#1-principles).

The butler is deliberately the smallest thinker. A voice turn must answer
fast, so System 1 gets a small context and no retrieval model. Anything that
needs real thought becomes a job for the staff.

## 4. Model routing at $0

### 4.1 Data class decides the route

Every model call has a **data class**, set by code when the context is
assembled:

- `synthetic`: fixtures and repository documents with no personal content.
- `personal`: anything containing a profile value, a day-book entry, library
  content, or text from the user's real speech.

The default is `personal`. A call is `synthetic` only when every block in it
is marked synthetic at its source. The cloud client refuses any other class.

| Call | `synthetic` | `personal` |
| --- | --- | --- |
| Voice (System 1) | Gemini Live, or the local adapter | Local adapter only |
| Planner (System 2) | Gemini Flash-Lite, then local Ollama | Local Ollama only |
| Worker reasoning | Same chain as the planner | Local Ollama only |
| Recommendation phrasing | Local Ollama (tests use a scripted model) | Local Ollama only |

The model names come from the
[completion plan, section 5](../../implementation/completion-plan.md#5-free-brain-stack-research-2026-11-11).
Its free-tier limits are marked unverified there and stay unverified here.
That plan also lists Groq and OpenRouter. They are left out of the chain
because the PH-00 record names Gemini as the only approved cloud recipient.
Adding one is a maintainer decision (OD-12).

### 4.2 Fallback and quota exhaustion

- **Voice never falls back silently** ([REQ-01](../../../prd.md#req-01)). The
  user picks the adapter at session start. If it fails, the session ends with
  the existing fixed error category and the console shows it.
- **Planner and worker calls** on `synthetic` data walk the chain in order.
  Each attempt records provider and model in the action record (IR-3). A
  quota error (HTTP 429 or a provider limit) moves to the next provider and
  marks the exhausted one unavailable until its reset time.
- **Local-only calls have no fallback.** If Ollama is unreachable or times
  out, the step fails. The retry rule from PH-00 applies: at most two
  automatic retries, idempotent read-only steps only. Then the job is
  `failed` with reason `model-unavailable`, and the butler says so.
- **Quota is a budget.** Requests per provider per day are counted and
  reserved by the broker like spend (IR-5). At zero remaining, admission of
  new `synthetic` cloud work stops; it does not spill to a paid tier.
- **The butler degrades honestly.** With no thinking model available, System
  1 can still answer `query_ledger` and accept `cancel_task`, because both
  are code paths.

### 4.3 Consequence for real use

Real personal use runs fully local until the maintainers decide otherwise
(OD-1). That makes PR 36's adapter the path for a real butler, and it means
the context budgets in section 5 must fit a small local model. Which Ollama
model serves the planner is open (OD-7); no tool-calling accuracy has been
measured on this project's schemas.

There is a tension to settle first. PR 36's adapter is a chain of speech to
text, a chat model, and text to speech. [REQ-01](../../../prd.md#req-01)
says no mandatory chain of that kind, and
[architecture.md](../../../architecture.md#deferred-adapter-seams) says
future private inference must be genuinely native. Using the cascade as the
private path needs an explicit decision (OD-13). This design does not
assume the answer; it only notes that per-turn context assembly needs the
user's words as text, which today only the cascade provides.

## 5. Context assembly

The context assembler is the only code that builds a prompt. It takes a call
type, a session, and optionally a job, and returns ordered blocks. Each block
has a trust label, a data class, and a size cap.

### 5.1 Trust labels

| Label | Meaning | Placement |
| --- | --- | --- |
| `system` | Written by this project | System role |
| `confirmed` | A value the user confirmed (standing orders) | Data block, labelled |
| `ledger` | Verified ledger facts | Data block, labelled |
| `untrusted` | Document text, tool output, web content, day-book summaries, the user's current words as transcribed | Data block, labelled as content to read, never to obey |

Labels and delimiters help a model behave. They are not the defence. The
defence is that the model's output is a typed proposal checked against a
grant it cannot change.

### 5.2 Budgets and order of priority

Blocks are filled in priority order. When the budget is short, the assembler
cuts from the bottom of the list. Blocks 1 to 3 are never cut; if they do not
fit, the call is refused.

**System 1 voice turn. Budget 2,000 input tokens.**

| Priority | Block | Cap (tokens) | Source |
| --- | --- | --- | --- |
| 1 | Persona and rules (BR-1 to BR-8 in prose) | 350 | Fixed text |
| 2 | Tool schemas | 350 | Section 6 |
| 3 | Open task draft and pending question | 200 | Session memory |
| 4 | Job snapshots: up to 5, active or finished since the last brief | 250 | `query_ledger` |
| 5 | Standing orders named by the open draft's schema, `aloud` class only, up to 12 | 200 | Memory service |
| 6 | Day-book entries returned by a `query_ledger` call with filter `history` in this turn, up to 3 | 250 | Memory service, full-text query built by code from the model's search terms |
| 7 | Recent turns, newest kept | remainder, at least 400 | Session memory |

**Planner step. Budget 6,000 input tokens.**

| Priority | Block | Cap |
| --- | --- | --- |
| 1 | Planner rules and the step schema | 500 |
| 2 | Admitted task specification and revision | 400 |
| 3 | Grant summary: allowed operations, datasets, limits left | 300 |
| 4 | Receipts of completed steps, summarized by the verifier | 1,200 |
| 5 | Standing orders named by the task schema (values by reference where `screen` or `sealed`) | 300 |
| 6 | Retrieved library chunks or document text | remainder |

**Worker reasoning step. Budget 6,000 input tokens.** Rules and output
schema (400), the action's validated arguments (300), then the bounded input
content. A worker gets no profile and no day book unless the action's
arguments carry a specific value.

**Which voice adapter this applies to.** Per-turn assembly needs the user's
words as text. Only the local cascade in PR 36 produces them. The Gemini
adapter is native audio: it takes one system instruction at session start
and yields no transcript. On that path blocks 1, 2, and 4 are set once at
session start, later facts reach the model only as tool results, block 7
does not exist, and code learns the user's intent only from tool arguments.
The native cloud path carries `synthetic` data only (section 4), so blocks 5
and 6 hold fixture data there.

Rules that hold for every call:

- **Token counting.** Until a tokenizer is measured for the chosen local
  model, the assembler estimates four characters per token and keeps a 10%
  margin. This is a known shortcut; replace it when OD-7 is settled.
- **Speakability.** A voice context receives `aloud` values only. A `screen`
  value appears as a reference such as `{slot: contact.home_address}`. Code
  substitutes the value when the task draft locks. A `sealed` value never
  enters any model context. See [memory](memory.md#4-speakability).
- **Per-item caps.** No single untrusted item may exceed its block cap. It is
  truncated with a marker, never allowed to push out a higher block.
- **No cache across sessions.** An assembled context is built per call and
  discarded. It records the memory epoch it was built from; a planner step
  whose epoch is older than the current one is rebuilt before use.
- **Nothing is logged.** Logs carry block names, sizes, and IDs, never
  content. This is the rule roadmap item R-01.8 already sets for the live
  check (timing and state only).

## 6. System 1 tool contracts

The voice model holds exactly four tools. Each is a thin call into the ledger
operations named in
[architecture.md](../../../architecture.md#conceptual-records-and-interfaces).
Schemas are shown as field lists; exact JSON Schema is implementation work.

Shared rules: every mutating call carries a `request_id` derived by code,
not by the model. For `propose_task` it comes from the draft ID. For
`cancel_task` and `steer_task` it comes from the session epoch, the turn
number, the tool name, and the job ID. A model that repeats a call within a
turn therefore repeats the ID. The session epoch, subject, and origin are
attached by code. A call
from a stale epoch is rejected. A repeated `request_id` returns the recorded
disposition.

### `propose_task`

| | |
| --- | --- |
| Arguments | `operation` (registry ID), `args` (object matching the operation schema), `slot_refs` (list of profile keys to fill by reference), `deadline_seconds` (optional) |
| Returns | `disposition`: `admitted`, `needs_slots`, `needs_readback`, or `rejected`; `job_id` and `revision` when admitted; `missing_slots`; `reason_code` |
| Butler may say | "Started" only on `admitted`. On `rejected`, the reason in plain words and a safe alternative if one exists. |

`needs_slots` and `needs_readback` are answered by the clarification state
machine before anything reaches the ledger. Only a locked draft is admitted.

### `query_ledger`

| | |
| --- | --- |
| Arguments | `job_id`, or `filter` (`active`, `recent`, or `history`) with `limit` up to 5. `history` reads the day book, takes up to 5 search `terms`, and returns at most 3 entries. |
| Returns | Snapshots: `job_id`, `short_name`, `operation`, `state`, `revision`, `updated_at`, `speakable_summary`, `speakability`, `evidence_ref` |
| Butler may say | The state and the `speakable_summary`, nothing more. `unknown` is reported as uncertain. |

Speakability applies to snapshots as it does to memory. Each operation's
registry entry has a class. For a `screen` operation the voice context
receives the state and the operation's generic label only; the short name
and summary are shown on screen. Code also replaces a `speakable_summary`
with the bare state if it contains any value that was substituted for a
reference in that job's arguments.

### `cancel_task`

| | |
| --- | --- |
| Arguments | `job_id` |
| Returns | `disposition`: `cancel_requested`, `already_terminal`, or `not_found`; current `state` |
| Butler may say | "I've asked it to stop" on `cancel_requested`. "Cancelled" only once a later snapshot shows `cancelled`. |

### `steer_task`

| | |
| --- | --- |
| Arguments | `job_id`, `base_revision`, `changes` (partial `args`) |
| Returns | `disposition`: `revised`, `stale_revision`, `not_steerable`, or `rejected`; new `revision` |
| Butler may say | The change as admitted. On `stale_revision` the butler re-reads the snapshot and asks again. |

**Naming a job.** The user says "cancel the report one", not a job ID. The
model picks a `job_id` from the snapshots in its context. Code checks that
the job belongs to the subject and is in the snapshot list given to that
turn. If two snapshots match, the butler asks which.

**Memory needs no fifth tool.** "Remember that I prefer short summaries" is
`propose_task` with operation `memory.remember`. It gets a job ID, a receipt,
and the same idempotency as any job.

**What the model cannot do** is absent, not forbidden by prompt: there is no
tool to read the memory store, list files, fetch a URL, or change a grant.

## 7. From a vague request to a typed task

Each operation in the registry has a **task schema**: its slots, their types,
which are required, and for each slot an optional profile key that may fill
it.

```text
idle -> drafting -> filling -> ready -> (readback) -> locked -> proposed
                      ^  |
                      +--+  one question per turn, three per task
```

1. **Drafting.** The model calls `propose_task` with what it understood.
   Code validates the operation and types.
2. **Filling.** For each missing required slot, in schema order: use a value
   stated in this session; else an active standing order with that key; else
   ask. A slot filled from a standing order is flagged for disclosure (BR-1).
3. **Ready.** All required slots have values. Scope-bearing slots (a path, a
   dataset ID, a recipient) must be inside the grant. A standing order can
   fill a blank; it cannot open a door.
4. **Readback.** Required when any slot came from a standing order confirmed
   by voice only, when the request was ambiguous, or when the operation is
   `memory.*`. The butler states the values and waits for a yes. A `screen`
   value is named by its meaning ("your home address") and shown on screen.
5. **Locked.** Code freezes the draft, substitutes values for references,
   and sends the proposal to the broker.
6. **Proposed.** The broker admits or rejects. The draft is deleted either
   way.

A draft lives in session memory and dies with the session. After three
questions without a complete draft, the butler stops asking and offers the
screen form instead.

**How a yes reaches code.** The model never reports a confirmation. A draft
in `readback` holds the values that were read back, and it locks only on
one of two events that code observes itself:

- **Screen.** The user presses Confirm on the draft card. The browser sends
  a control message naming the draft over the authenticated session socket.
- **Voice, local cascade only.** The user turn that directly follows the
  end of the readback's playback is transcribed. Code matches the whole
  turn against a short fixed list of yes and no phrases. Any other turn
  leaves the draft in `readback`. So does a barge-in before the readback
  finishes playing: the user must hear all of it before a yes counts.

Code sets the record's `confirmation` field from the event that occurred. A
`confirmation` value in tool arguments is ignored. A native audio adapter
gives code no transcript, so voice confirmation is unavailable there and
the screen is required. A transcribed yes still does not prove who spoke
([threat model](threat-model.md), TM-08).

**Example with the approved task pair** (summarize a named local document,
from the [PH-00 setup decisions](../../approvals/ph-00-setup-decisions.md)):

- User: "Summarize the roadmap for me."
- Draft: operation `doc.summarize`, slot `document_id` resolved against the
  approved document list to `roadmap.md`. Slot `length` is optional with
  profile key `summary.length`.
- A standing order `summary.length = short` exists. No question is needed.
- Butler: "Short summary of the roadmap, as usual. Starting it now." The
  proposal is admitted and a job ID returns.

When `document_id` matches two documents, the butler asks one question:
"The roadmap, or the phases document?"

Building this flow is PH-04 work (R-04.2). This section is its design input
and does not replace that item.

## 8. Timing: the queue and the brief

- **Turn-boundary queue.** The notification coordinator holds a finished
  job's notification until the playback epoch is idle. The butler then offers
  it in one sentence and lets the user choose now or later. "Published" and
  "heard" stay separate facts, as the notification record already requires.
- **Opening brief.** When a session starts, code builds a brief from the
  ledger: jobs that reached a terminal state since the last session, jobs
  still running, and at most three suggestions (see
  [recommendations](recommendations.md)). The brief is capped at four spoken
  sentences. The rest is on screen.
- **Urgency.** A notification has a class: `now` (interrupts at the next
  phrase boundary), `pause` (waits for a pause), `brief` (waits for the next
  brief). Only failures of a job the user is waiting on and approval
  requests are `now`. The class is set by code from the job state, never by
  a model.

## 9. Constraint check

| Constraint from the brief | How this design meets it |
| --- | --- |
| $0, local models, local SQLite | Routing in section 4; storage in [data layer](data-layer.md). No paid path exists in the router. |
| No raw audio or verbatim transcripts stored | Session memory is in process and cleared at session end. Persistent stores hold confirmed values and receipt-derived entries only. |
| Content is data, never instructions | Trust labels (5.1), typed proposals, no memory write from job content (section 3). |
| Voice is not identity | Voice-only confirmation is marked on the record and triggers readback and disclosure; sensitive keys need the screen (OD-6). Standing orders cannot widen a grant. |
| The ledger owns truth | Memory writes and suggestions are jobs or ledger-recorded events. The butler speaks from snapshots. |
| Tiers | Nothing here enables T1 or T2. The library layer is an input to R-A.4. |

## 10. Open maintainer decisions

All open decisions for the whole pack are listed here. Nothing below is
decided by this document.

| ID | Decision | Options | Recommendation |
| --- | --- | --- | --- |
| OD-1 | R-A.2: may real voice or personal data go to a cloud provider? | (a) Local only for `personal`. (b) A paid no-training tier for `personal`. (c) Free cloud tiers for `personal`. | (a). It costs nothing and matches PH-00. (b) changes the $0 cap. (c) lets a provider train on personal data and should be rejected. |
| OD-2 | Which gate governs persistent memory? | (a) Its own gate under RT-G05, approved through R-M.1. (b) Treat all memory as T1 and wait for R-A.4. (c) Treat the self-declared profile as T0. | (a). The profile is data the user states about themself, not a connector, so T1 is too late; T0 says "no personal data access", so (c) contradicts it. |
| OD-3 | How long may a day-book entry outlive its job? PH-00 deletes job metadata after 24 hours. | (a) 24 hours, so no long-term episodic memory. (b) 30 days. (c) 90 days. (d) Until the user forgets it. | (b), user-adjustable down to (a). The entry is a minimal distilled record, not job metadata, but the PH-00 record needs an amendment to say so. |
| OD-4 | Retrieval dependency. | (a) SQLite full-text search only. (b) Add a local embedding model with brute-force search. (c) Add a vector extension. | (a) first. Move to (b) only if the paraphrase scenarios in [evaluation](evaluation.md) fail. See [data layer](data-layer.md#5-retrieval). |
| OD-5 | Encryption at rest. | (a) OS disk encryption plus file permissions. (b) An encrypted SQLite build. (c) Field-level encryption with an OS-held key. | (a) for the first build, stated plainly to the user. Decide (b) before T1 (R-A.4). Costs and licences are in the [data layer](data-layer.md#6-encryption-at-rest). |
| OD-6 | Is a spoken "yes" enough to confirm a memory? | (a) Always. (b) For low-sensitivity keys, on the local cascade only; the screen for sensitive ones and on a native audio adapter. (c) Never; always the screen. | (b). (a) lets ambient speech write sensitive memory. (c) breaks hands-free use for harmless preferences. |
| OD-7 | Which local model serves the planner and the butler. | Decided by a measurement spike on this project's schemas (the unrun spike A3c in [free-stack.md](../../free-stack.md)). | Run the spike before R-M.2. Check the model's licence under AGENTS.md section 6. |
| OD-8 | Kokoro's GPL-3.0 dependency in PR 36's text-to-speech step. The repository is MIT. | (a) Keep Kokoro as an optional component the user installs separately. (b) Default to the operating system's built-in voice. (c) Find another permissively licensed local voice. | (b) as the default, with (a) as an opt-in, so the MIT repository ships no GPL code. The licence details were not checked in this work; the decision belongs in PR 36's review. |
| OD-9 | Any paid tier. | Keep $0, or approve a named paid service. | Keep $0. Nothing in this design needs a paid service. |
| OD-10 | One SQLite file or two. | (a) Memory tables inside the ledger file. (b) A separate `memory.db`. | (b). Each session owns its schema, and deleting all memory is deleting one file. |
| OD-11 | The butler's name, tone, and default form of address. | Maintainer choice. | No name and no honorific by default. |
| OD-12 | A second cloud recipient for `synthetic` planner calls (Groq or OpenRouter, from the completion plan). PH-00 approves Gemini only. | (a) Gemini only, then local. (b) Approve a named second recipient under [REQ-13](../../../prd.md#req-13). | (a). Synthetic work is for tests, where the local model is an adequate fallback. |
| OD-13 | May the local cascade (speech to text, chat model, text to speech) be the private voice path? [REQ-01](../../../prd.md#req-01) rules out a mandatory chain of that kind. | (a) Approve the cascade as a labelled interim private path through an exception record. (b) Wait for a genuinely native local model (PH-07). (c) A paid native cloud tier with no training, which also needs OD-1 and OD-9. | (a), decided in PR 36's own exception record. Without it, no real personal use is possible at $0, and the per-turn design in section 5 has no adapter to run on. |
| OD-14 | Is user-requested forgetting allowed, given that [DEC-18](../../../descisions.md#dec-18) places permanent deletion at T4? | (a) Forgetting the assistant's own memory is a privacy control, not a T4 capability over the user's data. (b) Treat it as T4 and require a separate design. | (a). [REQ-14](../../../prd.md#req-14) and [RT-A06](../../../prd.md#rt-a06) require bounded retention and deletion. Forget-everything and export still need the screen. The maintainers should record this reading. |
| OD-15 | Automatic learning from conversation (proposal in [memory, section 9](memory.md#9-proposed-revision-2026-11-13-learning-from-conversation)). The operator asked for it on 2026-11-13. | (a) Explicit only, as in memory sections 1 to 8. (b) End-of-session proposals the user confirms on screen. (c) Automatic `inferred` records, with sensitive ones confirmed on screen. | (c), as the operator asked, with every safety rule in memory section 9.5: local model only, user speech only, `inferred` never authorizes, sensitive on screen, transcript discarded. It changes memory principles 2 and 3 and needs a DEC approved by both maintainers. **`abhishek3059` approved the recommendation on 2026-11-13; `jeevesh2515` pending ([record](../../approvals/memory-learning-decisions.md)).** |
| OD-16 | What happens to the raw transcript after distilling. | (a) Discard it. (b) Keep it encrypted locally for N days. | (a). It keeps [REQ-14](../../../prd.md#req-14) intact and removes the largest store of personal text. (b) would need encryption at rest (OD-5) and its own retention approval. **`abhishek3059` approved the recommendation on 2026-11-13; `jeevesh2515` pending ([record](../../approvals/memory-learning-decisions.md)).** |
| OD-17 | Retention of episodes, decisions, and `inferred` records. | (a) 30 days. (b) 90 days. (c) Until forgotten. | 90 days, adjustable, for episodes and `inferred` records unless reinforced. Decisions stay until marked done or forgotten, then follow the 90-day rule. Habits need about 30 days of data to show, so 30 days would discard a habit as it forms. Still local, still deletable on the "What I learned" screen. **`abhishek3059` approved the recommendation on 2026-11-13; `jeevesh2515` pending ([record](../../approvals/memory-learning-decisions.md)).** |
| OD-18 | Job spec and checkpoint retention beyond the 24-hour job-metadata purge in the [PH-00 setup decisions](../../approvals/ph-00-setup-decisions.md). The trip scenario ([evaluation, section 12](evaluation.md#12-acceptance-scenario-the-interrupted-trip)) cannot pass with 24 hours. | (a) Keep 24 hours. (b) 30 days for task specs, verified checkpoints, and the stop reason. (c) Until the user forgets them. | (b). It covers "continue the thing from two days ago" without holding job data indefinitely. It needs an amendment to the PH-00 record, approved by a maintainer. **`abhishek3059` approved the recommendation on 2026-11-13; `jeevesh2515` pending ([record](../../approvals/memory-learning-decisions.md)).** |

## 11. Interface requests for the ledger

The ledger contract in [architecture.md](../../../architecture.md) is treated
as fixed. These are requests to its owners, not changes made here. Each says
what the brain needs and what it will do if the answer is no.

| ID | Request | Why | If declined |
| --- | --- | --- | --- |
| IR-1 | The capability registry accepts `memory.remember`, `memory.correct`, `memory.forget`, `memory.export`, and `memory.purge` as fixed operations. A task proposal records its **origin** (`user_turn`, `planner_step`, `schedule`, `system`), set by code from the call path, and the broker refuses an operation whose origin its registry entry does not allow (the table in section 3). A registry entry also carries a speakability class for the operation's results. | Memory writes must be jobs, and must be impossible from job content. | Memory writes cannot be built safely; R-M.4 is blocked. |
| IR-2 | When a job reaches a terminal state (`succeeded`, `failed`, or `cancelled`; an `unknown` job emits only once it reconciles), and before the 24-hour purge, the ledger emits one `job_terminal` event with job ID, revision, state, operation, the verifier's bounded summary, and an evidence digest. | The day book is built from verified receipts, not from narration. | No day book; the butler has no memory past 24 hours. |
| IR-3 | The task record carries `data_class` set by code at admission. The action record carries the provider and model that served each attempt. | Routing must be auditable, and a receipt should say which model produced it. | The router keeps its own log, which is a second source of truth. |
| IR-4 | The task snapshot includes `short_name` and `speakable_summary` (at most 200 characters, produced by the verifier), the operation's `speakability`, and `evidence_ref`. | The butler must speak from ledger fields, not compose outcomes. | The butler states only the state name. |
| IR-5 | The broker reserves and counts provider requests per day, like spend. | Free-tier quota is the only budget at $0. | The router counts locally and may overrun after a restart. |
| IR-6 | The reconcile and purge operation calls registered secondary-store purgers and records their row counts in a purge receipt. | [RT-A06](../../../prd.md#rt-a06) requires secondary-store purge; memory indexes are secondary stores. | The memory service runs its own sweeper with no ledger receipt. |
| IR-7 | The emergency-stop latch is readable by the memory service. | Emergency stop must also stop memory writes and day-book distillation. | Memory jobs are still blocked at admission, but an in-flight write could finish. |
| IR-8 | The notification record accepts kind `suggestion` and a class (`now`, `pause`, `brief`). | Suggestions must be ledger-recorded events with an outcome. | Suggestions are recorded only in the memory store. |
| IR-9 | A `resume_task(job_id)` operation that creates a new linked job (a `resumes` field) starting from the last verified checkpoint. The broker admits it like any task. | A stopped job can continue without replaying completed effects ([RT-A04](../../../prd.md#rt-a04)). Needed by the trip scenario in [evaluation](evaluation.md#12-acceptance-scenario-the-interrupted-trip). | Resuming means a fresh task from the spec, and the planner must skip completed work by itself. |
| IR-10 | The ledger records the stop reason and actor (`user`, `failure`, `host_sleep`, `emergency_stop`) and keeps verified step checkpoints with the task spec for the OD-18 window. | The butler must say truthfully who stopped a job. | The butler cannot say who stopped it and states only the state name. |

## 12. Roadmap proposal (proposed text only)

This is a proposal for a new parallel track. It is not a roadmap edit. Adding
it needs a roadmap PR that changes `roadmap.md` and
`scripts/roadmap-ids.txt` together and that a maintainer approves.

**Parallel track M: brain and memory.** This track gates no phase and moves
no gate. R-M.1 can happen any time. No item is built before its dependency is
ticked.

| Proposed item | Text | Depends on |
| --- | --- | --- |
| R-M.1 `[human]` | A maintainer approves the brain and memory design and record every open decision in section 10, including the persistent-memory approval under RT-G05. | Nothing |
| R-M.2 | Local model measurement spike on the tool and step schemas; model and licence recorded. | R-M.1 |
| R-M.3 | Context assembler and model router with data-class enforcement and session memory only, with tests. | R-02.3, R-M.2, R-A.2 |
| R-M.4 | System 1 tools `propose_task`, `query_ledger`, and `cancel_task` wired to the ledger, tested with a scripted model. | R-02.1, R-02.2, R-M.3 |
| R-M.5 | `steer_task` wired to revisions. | R-03.1, R-M.4 |
| R-M.6 | Profile store: remember, correct, and export as ledger jobs, with an inspect screen and the confirmation paths. Synthetic data only until R-M.7 is ticked. | R-02.1 to R-02.3, R-M.1, R-M.4 |
| R-M.7 | Forgetting and retention purge, with the residue tests passing. The profile store may hold real data only after this item. | R-03.3, R-M.6 |
| R-M.8 | Day book written from verified receipts. | R-02.6, R-M.7, OD-3 recorded |
| R-M.9 | Advice-only recommendations with cited evidence. | R-M.6, R-M.8, R-A.3 |
| R-M.10 | Library layer built behind the policy layer. | R-A.4, R-A.5, R-M.7 |
| R-M.11 | Evaluation suite run on the built layers and recorded. | The items it covers |
| R-M.12 (proposed, needs OD-15 approved) | Memory distiller: a `memory.distill` job with origin `session_end`, local model only, `inferred` records, episodes and decisions stores, and the "What I learned" screen, with the trip scenario EV-A1 to EV-A10 as acceptance. | R-M.7, R-M.8, OD-15 to OD-18, IR-9, IR-10 |

Relation to existing items: the clarifying-question build stays in R-04.2;
section 7 is its design input. The T0 persona stays in R-A.3; section 2 is
its design input. The library's scopes and allowlists are approved in R-A.4,
not here.
