# App status, gaps and proposed features (2026-11-19)

Status: proposal and status snapshot. It authorizes nothing and ticks nothing. Roadmap
state at writing: `Current phase` is PH-02 ([roadmap.md](../../roadmap.md) line 6), and no PH-02 item is ticked.
Facts below were checked against `origin/develop` at commit 6eac576. Items marked "unverified" were not.

## 1. Summary

- Today this is a private voice chatbot with a notebook.
- Beside it sits a background job engine (ledger, runner, LangGraph, verifier) that voice cannot fully talk to.
- It forgets between sessions except for word-matched notes, cannot report what its jobs did, and never speaks first.
- Emotional care is one prompt line ([local_adapter.py](../../apps/api/src/super_agent_voice/local_adapter.py) line 44), with no detection.
- On a 4 GB GPU the model is small, so the fix is plumbing (state, briefs, timing), not a smarter model.

## 2. What works today

| Area | What works | Evidence |
| --- | --- | --- |
| Voice console and Gemini Live | Local console, live adapter, synthetic data only | [R-01.8 record](r01-8-live-check.md), [acceptance](r01-10-acceptance.md) |
| Handshake and keepalive | Server proves the session token before the console sends it (R-01.F9); muted sessions stay alive (R-01.F10) | [F9](r01-f9-handshake-proof.md), [F10](r01-f10-idle-keepalive.md) |
| PH-01 | Closed by PR 58 | [phase PR log](phase-prs.md) |
| Governance gate | Slice 1 of `policy.decide` merged (PR 62). Slices 2 to 4 are open (R-02.7) | [slice 1 record](governance-gate-slice1.md) |
| Memory | Facts and reminders in SQLite, opt-in, forget and undo; retrieval is shared-word overlap in `context` ([memory.py](../../apps/api/src/super_agent_voice/memory.py) line 545) | [local memory test](local-memory-test.md) |
| Distiller | Local distiller writes `inferred` notes (PR 61); it skips other people on purpose ([distill.py](../../apps/api/src/super_agent_voice/distill.py) line 25) | [distiller record](memory-distiller.md) |
| Task layer | Ledger, runner, LangGraph, verifier; read-only tools only; off by default | [graph](agent-backend-graph.md), [runner](agent-backend-runner.md), [ledger](agent-backend-ledger.md) |

Branch only, not merged, no PR (`origin/feat/local-planner`, commit 5a1ff92): a local Ollama planner. Per the
branch doc, `qwen3.5:4b` on a 4 GB GTX 1650 Ti took about 30 s per job. Two of three real runs succeeded and one hit
the 25 s model timeout. Three runs is not a quality measure. I read this from the branch doc and did not rerun it.

## 3. Gaps

| Group | Gap | Roadmap | Effort |
| --- | --- | --- | --- |
| Memory | No cross-session recap; history is the last 12 messages in RAM ([local_adapter.py](../../apps/api/src/super_agent_voice/local_adapter.py) line 236) | BR-6 brief in R-M.19; day book R-M.8; no plain recap item | M |
| Memory | Retrieval is word overlap, so "my sister" misses "Priya" | OD-4 (full-text search first), R-M.1 | S-M |
| Memory | No contradiction, decay, or supersede | R-M.14 [human], R-M.15, R-M.16 | M |
| Understanding | No intent or emotion reading to pick the response type; GR-1 blocked | OD-G5 open, slice 2b | M |
| Understanding | No clarifying-question flow; graph refuses `ask_user` ([graph.py](../../apps/api/src/super_agent_voice/graph.py) line 93) | R-04.2 | M |
| Proactivity | Job results never reach the conversation | R-M.17 | M |
| Proactivity | Prompt forbids ending with a question or an offer ([local_adapter.py](../../apps/api/src/super_agent_voice/local_adapter.py) line 46) | not on roadmap | S |
| Proactivity | No scheduled or triggered jobs | not on roadmap | M |
| Task | No `query_ledger`, `cancel_task`, `steer_task` in voice | R-M.4, R-M.5 | M |
| Task | Read-only tools only, no writes | R-A.6 to R-A.9 | L |
| Task | Admission bypass in `Runner.claim_and_run` | R-02.F1 | S |
| Voice | No wake word or always-on; accent breaks STT; latency unmeasured | PH-06, PH-07, R-03.5 | L |
| Trust | Turn-level checks not all in the gate; file ACLs; accept-before-auth DoS | R-02.7, R-03.F2, R-02.F4 | S each |
| Personalization | No persona, standing orders, profile store or inspect screen | R-M.1, R-M.6, R-M.19 | S-M |

## 4. Proposed features

All are proposals. None is approved.

### 4.1 Resume a stopped task the next day from memory
- Wants: "Carry on with the trip plan" works after a restart.
- Exists: the ledger keeps job state. The graph has no checkpointer ([graph.py](../../apps/api/src/super_agent_voice/graph.py) line 6), so only ledger records survive.
- Missing: a recap of stopped jobs at session start, and resume from a paused step.
- Roadmap: R-03.2 (restart without blind replay), R-M.8 day book. No plain recap item.
- Blocking decision: whether recap gets its own roadmap item; retention (OD-3, OD-17, OD-18).

### 4.2 "What can I do today?" from profile and likes
- Exists: facts, reminders, distiller `inferred` notes.
- Missing: a profile read path, a recommendation rule set, calendar read (T1).
- Roadmap: R-M.6 profile store, R-M.9 (proposed only), R-A.5 read connectors.
- Blocking decision: OD-1 (personal data stays local) and OD-15 (auto-learning scope).

### 4.3 Follow-up suggestions after a finished job
- Example: after a vacation booking, "want me to plan each day?"
- Exists: nothing. SYSTEM_PROMPT says never end with a question or an offer.
- Missing: result handler (R-M.17) and a timing rule (BR-6).
- Roadmap: not on roadmap as a prompt change.
- Blocking decision: the owner must say whether to relax that rule for follow-ups after a job result only.

### 4.4 Emotional etiquette
- Wants: detect restless or angry tone, comfort, ask how the user feels, calm; never start a task while venting.
- Exists: one prompt line to acknowledge a feeling. GR-1 ([governance.md](../design/governance.md) line 161) ties delegation to the user's own words.
- Missing: intent and emotion reading that picks the response type, failing closed (an unclear turn never starts a task).
- Roadmap: OD-G5, slice 2b, R-A.3. A design doc can be written now.
- Blocking decision: OD-G5 approach. Reading is by meaning, not a word list.

### 4.5 Learning relations on the go
- Example: "my mom likes apples", "Alice is my mom". Store entity, alias, relation. Local only.
- Exists: the distiller skips facts about other people on purpose ([distill.py](../../apps/api/src/super_agent_voice/distill.py) line 25, and the third-party rule near line 30).
- Missing: an entity, alias, and relation store, and a way to inspect and correct it.
- Roadmap: not on roadmap (nearest: R-M.6, R-M.12).
- Blocking decision: the owner must allow facts about other people, since the distiller design bars them (design 9.5 rule 3).

### 4.6 Spoken ask-and-resume inside background jobs
- Design: [ask-and-resume](../design/ask-and-resume.md). Proposal, no roadmap item yet.

### 4.7 Planner choice
- Options: local Ollama planner (branch only), or a cloud planner through Gemini or OpenRouter. The Claude API is not planned.
- A cloud planner never sees personal values. Placeholders are filled locally.
- OpenRouter would be a new recipient and needs maintainer approval. Free-model tool-calling quality is unverified.
- Blocking decision: OD-7 (which model serves the planner) and the recipient approval.

## 5. Owner decisions needed

- R-M.1 and the open decisions in [brain overview](../design/brain/overview.md) section 10, especially OD-1, OD-3, OD-4, OD-6, OD-7, OD-11, OD-15.
- OD-G5 approach, and whether follow-up offers may break the "never end with a question" rule.
- Whether facts about other people may be stored (4.5).
- Whether a cross-session recap gets a roadmap item (4.1).
- Planner: local only, or a cloud planner, and OpenRouter as a recipient (4.7).
- The open questions in the ask-and-resume design doc.

## 6. Suggested order

1. R-02.F1: route `claim_and_run` through `policy.admit`. One PR.
2. R-02.7 slice 2: switches and default-deny into `decide`.
3. R-M.1 plus R-A.2 decision record: owner records the open decisions. Docs only.
4. Finish PH-02: R-02.5, R-02.F3, R-02.F2 if PR 56 merges, then R-02.6.
5. OD-G5 design doc; build slice 2b with R-A.3.
6. R-02.F4, then R-M.3 and R-M.4 (voice can delegate and query).
7. R-M.17 result handler plus a session-open brief.
8. Ask-and-resume, after R-M.17, first with read-only tools.

Do not build yet: T2 and T3 writes (no stop controls), wake word, native speech-to-speech, embeddings, scheduled
autonomous jobs, anything T4.
