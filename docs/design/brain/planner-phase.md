# Brain design: planner phase (proposal)

| Field | Value |
| --- | --- |
| Date | 2026-11-21 |
| Operator | `abhishek3059` |
| Status | **Proposal.** Design only. Builds nothing, enables no tier, ticks no roadmap item, closes no gate. Nothing here is measured. |
| Depends on | [DEC-24](../../../descisions.md#dec-24) ([R-A.2 record](../../approvals/r-a2-cloud-personal-data.md)) |
| Related | [overview](overview.md), [memory](memory.md), [data layer](data-layer.md), [ask and resume](../ask-and-resume.md), [governance](../governance.md), [PR #71](https://github.com/abhishek3059/super-agent/pull/71) (hosted transition, R-03.F1, R-03.F4), R-04.2, R-M.3, R-M.12, R-M.17 |

## 1. Why

Today the job gets raw words. `graph._plan_prompt` receives only the task type
and the instruction text. The planner knows nothing about the user, so it
cannot fill a gap or tell a task from a chat turn.

Evidence that raw words make weak plans:

- [Local planner record](../../implementation/local-planner.md): a 4B model
  invented tool arguments, omitted `finish`, and timed out in 1 run of 3.
- Observed in the 2026-11-20 local R-02.5 attempts, not yet verifiable in a
  merged record: in 1 run of 4 the conversation model answered directly
  instead of delegating, and the planner and the conversation starved each
  other on one local Ollama. The record is being added to
  `docs/implementation/ph02-ledger-evidence.md` in
  [PR #64](https://github.com/abhishek3059/super-agent/pull/64), which is not
  merged yet.

## 2. The flow

```text
  user speaks
      |
      v
  voice orchestrator  --- acknowledges at once; voice never waits
      |
      v   (off the voice loop)
  PLANNER PHASE  <--- memory: L1 session, L2 profile, L3 episodes
      | intent gate -> brief -> missing info? --> ask by voice, resume
      v
  ledger admission (policy.admit decides type, tools, data class, limits)
      |
      v
  sub-agent job graph (follows the brief)
      |
      v
  JSON receipt
      |
      v
  result handler (R-M.17) -> orchestrator -> speaks the result
```

A graph library such as LangGraph is welcome for the job graph and the planner
phase, but the design does not depend on one.

## 3. Planner phase steps

1. **Intent gate.** The phase first decides whether the turn is a task, chat,
   or an emotional turn. If it is unclear, no task starts (fail closed). This
   is GR-1 in the [governance design](../governance.md) and depends on OD-G5,
   which is still open.
2. **Personalized brief.** The phase works out what the user means, fills gaps
   from memory, and writes a brief with a fixed schema:
   `{goal, inputs, constraints, success_criteria, missing}`. The raw request
   is stored beside the brief. Both go in the ledger.
3. **Missing information.** Anything in `missing` goes to the
   [ask-and-resume](../ask-and-resume.md) path: the job asks by voice, the
   spoken answer arrives, then the job resumes. The clarifying-question build
   itself stays in R-04.2.
4. **The brief is untrusted model output.** `policy.admit` still decides task
   type, tools, data class, and limits. The brief can describe the work better.
   It never adds a tool, a scope, or a recipient.

## 4. Memory for the planner

| Layer | Holds | Access |
| --- | --- | --- |
| L1 session | The current conversation | In context |
| L2 profile | Typed slots, relational | Exact key |
| L3 episodes and decisions | What happened and what was decided | Vector search plus FTS5 |
| L4 library | Documents | Inside the job, not the planner |

Why not one user vector: it cannot answer an exact fact such as a name or a
preference, and it cannot be corrected or forgotten piece by piece. Typed
slots can be read, fixed, and deleted one by one.

Retrieval choice, using the options in [data layer](data-layer.md) section 5:

- Start with (a) FTS5 plus (b) embeddings stored in `memory.db`, with cosine
  search in Python. Embeddings come from the approved cloud provider, not from
  local Ollama.
- Each embedding is deleted with its source row and counted by forget.
- Move to (c) `sqlite-vec` or pgvector only past tens of thousands of chunks.
- Retrieved text is data, never instructions.

## 5. Context assembly and providers

The context assembler (R-M.3) builds provider-neutral blocks, each with a
trust label, a data class, and a size cap. A thin renderer per provider turns
them into that provider's request. The section 5.2 budgets in
[overview](overview.md) were sized for a small local model and must be
revisited for cloud models (open decision PP-3).

The planner must work with any LLM provider. The proposal is one
OpenAI-compatible chat-completions client, configured by base URL, model, and
the name of the environment variable that holds the key, with an allowlist of
approved hosts. It is planned as R-02.F7 in
[PR #64](https://github.com/abhishek3059/super-agent/pull/64).

## 6. Gaps in the code today

1. L1 history and the distiller trigger live in `LocalVoiceAdapter` and must
   move to the cloud orchestrator (R-M.20).
2. `policy.admit` and `policy.may_distill` refuse personal data and cloud
   models. [DEC-24](../../../descisions.md#dec-24) changes the policy, not the code.
3. There is no embeddings or episodes store (R-M.21).
4. There is no context assembler (R-M.3).
5. There is no planner phase (R-M.22).
6. There is no result handler (R-M.17).

## 7. Open decisions

| ID | Question | Leaning |
| --- | --- | --- |
| PP-1 | Where does the orchestrator live: Python `apps/api`, or `apps/hq` where OpenAI Realtime already works? | `apps/api`, because the ledger and policy are there. Assumed, not decided. |
| PP-2 | Which embedding provider and model? | Open. |
| PP-3 | Context budgets for cloud models. | Open. |
| PP-4 | Which OpenAI and NVIDIA NIM models? | Open. R-M.2 measures them. |
| PP-5 | Provider terms on training use and retention. | Open and unverified. |

## 8. Unverified

- OpenAI Realtime mid-session `session.update` and input transcripts.
- NVIDIA NIM and Gemini offering OpenAI-compatible endpoints.
- Any latency number. 1 to 5 seconds for a cloud planner call is an unmeasured
  estimate.

## 9. Relationship to other work

- [PR #71](https://github.com/abhishek3059/super-agent/pull/71) proposes the
  hosted transition (R-03.F1, R-03.F4). This proposal does not edit those items.
- R-04.2 keeps the clarifying-question build.
- R-M.3, R-M.12, and R-M.17 are inputs. R-M.20 to R-M.22 are the new build items.
- [DEC-24](../../../descisions.md#dec-24) allows the personal data this design
  reads, for maintainer testing only.
