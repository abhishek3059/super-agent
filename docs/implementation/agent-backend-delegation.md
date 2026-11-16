# Agent backend slice 6: delegate_task in the local conversation loop

Date: 2026-11-16. Branch `feat/agent-backend`. Build step 6 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
It adds one tool to the local text adapter, off by default. It uses no real model and no network,
adds no endpoint, changes no authentication, Host, Origin or CORS handling, and ticks no roadmap item.

## What was built

- `apps/api/src/super_agent_voice/delegation.py` (86 lines): `Service`, `run_read_tool`, and `TOOL` (the schema).
- `apps/api/src/super_agent_voice/local_adapter.py`: `delegate_enabled()` (the `SUPER_AGENT_DELEGATE` flag), the tool
  added to `available_tools()`, a dispatch branch in `call_tool`, a one-sentence system prompt addition when on,
  and a flag check at session start. `gemini_adapter.py` is untouched.
- `policy.py`: one reason code, `delegation_unavailable`.
- `apps/api/tests/test_delegation.py`: 55 tests.
- Decisions recorded in the [design](../design/agent-backend.md): tool name `delegate_task` (decision 5, conflict C1,
  and the brain documents now say `delegate_task`), separate `~/.super-agent/ledger.db` (decision 4), first model
  Gemini text on the free tier (decision 1, built in slice 7, not here). Decided by `abhishek3059` in chat on 2026-11-16.

## Flow

```text
local text model -> delegate_task(task_type, instruction)
  -> call_tool (flag must be exactly "on") -> asyncio.to_thread -> Service.handle
  -> Service.delegate: spec built in code -> policy.admit -> Runner.submit -> receipt at once
                                                               |
                                      worker thread: graph.make_work(... run_read_tool ...) -> ledger
```

The tool result the conversation model sees is `{"job_id", "state"}` and nothing else, or
`error: not delegated (<code>).`. It never sees job output.

## Tool contract

| | |
| --- | --- |
| Arguments | exactly `task_type` (enum of `policy.TASK_TYPES`) and `instruction` (string, at most 1,000 characters). Any other key, a missing key, or a non-object is refused `spec_invalid`. |
| Chosen by code | the data class, the idempotency key, the locality flag, the limits, the tools, the deadline. The model can supply none of them; each was tried as an extra argument in tests. |
| Success | `{"job_id": "...", "state": "queued"}` |
| Refusal | `error: not delegated (<code>).` The code is a `policy.REASONS` entry. No exception text, no spec text. |

## Data-class rule

`Service(model, data_class="personal")`. In the conversation loop the class is always `personal`, because live
conversation content is real data. Admission refuses `personal` with a cloud planner (`personal_data_cloud_planner`),
so with a cloud model a delegated job is refused and nothing is written: the [REQ-13](../../prd.md#req-13) boundary
working as designed. The constructor takes the class for other trusted callers (slice 7's opt-in check will pass
`synthetic`) and validates it (`data_class_invalid`). `planner_is_local` is `model.is_local is True`, in a
try/except; anything else, including a flag that raises, is cloud. `tier1_is_synthetic` and `memory_is_synthetic`
are left at their default False, with no configuration for them.

## Reason codes

Existing codes pass through from `policy.admit`: `spec_invalid`, `task_type_invalid`, `instruction_invalid`,
`personal_data_cloud_planner`, `queue_full`, `idempotency_key_invalid`, `ledger_error`, and others. Added:
`delegation_unavailable` (no model configured, the service is closed, or an unexpected error).

## The tool runner

`run_read_tool(name, args) -> str` is the `run_tool` the graph takes. It runs a name only if it is in
`READ_TOOLS`: `calculate`, `current_time`, the tier 1 names, and `memory.NAMES - memory.WRITES`. Everything else
(including every memory write, a non-string name, and `delegate_task` itself) returns `error: no such tool.`
Dispatch goes to existing code: `tools.run_tool`, `tier1.run_t1`, `memory.run`. Results pass through unchanged
(untrusted data; the graph bounds and checks them).

`tier1.run_t1` is async and the graph calls tools from a LangGraph worker thread, which has no running event loop.
The smallest bridge is `asyncio.run(tier1.run_t1(...))`, one short-lived loop per call. It is tested from a
`ThreadPoolExecutor` thread with a fake `run_t1`; no real app or file was touched.

## Startup and shutdown

Creating a `Service` calls `Runner.recover()` once (a `running` or `cancel_requested` job becomes `unknown`, queued
jobs are failed `restart_queued`, nothing is replayed) and `ledger.purge(now)` once (the 14-day retention had no
caller until now). Nothing schedules the purge after that, so a long-running process purges only at its start.
`close()` marks the service closed and calls `Runner.close()` (`shutdown(wait=False, cancel_futures=True)`), so it
does not wait for a running job. Later calls are refused `delegation_unavailable`.

The adapter holds one process-wide service, created on the first `delegate_task` call (off the event loop), and
never closes it: jobs are meant to outlive a session.

## Choices where the brief or the design was unclear

- **Idempotency key.** The conversation loop has no tool-call identifier: `ollama_reply` does not pass one to
  `call_tool`. So the key is a fresh `uuid4().hex` per call. A retried or repeated tool call is therefore a new job,
  not a duplicate of the first. Only the queue cap bounds repeats. `Service.delegate` takes the key as an argument,
  so a caller with a stable identifier can use it.
- **No model configured.** The adapter builds `Service()` with no model, because no real model exists until slice 7.
  In a real run with the flag on, every delegation is answered `error: not delegated (delegation_unavailable).`
  Only tests inject a `ScriptedModel` (by setting `local_adapter._SERVICE`).
- **Where the flag is checked.** `call_tool` checks it per call, and `LocalVoiceAdapter.start()` checks it once, like
  `SUPER_AGENT_MEMORY`. With it off, `delegate_task` gets the existing `error: no such tool.`
- **Receipt state.** `state` is the state in the admission, so it is `queued` for a new job. A repeated key (only
  possible from a caller that passes a stable key) returns whatever state the ledger held then.
- **Refusal text.** One fixed sentence with the code. The arguments check (`spec_invalid`) is in the service, not in
  the adapter, so any caller gets it.
- **A new reason code** rather than reusing `input_invalid`, so "not available" is distinguishable.
- **Test network guard.** Same idea as `test_graph.py`, but loopback connects are allowed because `asyncio.run`
  on Windows opens a loopback socket pair for its self-pipe.

## Known limits

- With the flag on, no job can run in a real session yet (no model). The path to a running job is tested only with
  the scripted fake.
- **Obligation for the result-return slice.** Returning a job's result to the conversation loop has its own
  data-boundary question: a job that read personal data (tier 1 or memory tools, which a local planner may use)
  must not be briefed to a cloud conversation model. That slice must decide it before it returns any output.
- The memory read tools are granted by admission to a local planner whether or not `SUPER_AGENT_MEMORY` is on, and
  `run_read_tool` does not check the flag (that check lives in `local_adapter`, which imports this module). A local
  planner could read an existing `memory.db` with memory off. Not fixed here; it needs a trusted flag passed into admission.
- A turn that already read a file, note or mail (untrusted text) can still call `delegate_task`. The job is read-only
  and its output is not returned, but injected text could cause a job to be created. No guard like the memory
  write guard was added.
- No per-turn cap on delegations beyond the adapter's two tool calls per round, three rounds, and the queue cap
  (7 non-terminal jobs; `admit` is not atomic, so two concurrent calls can both pass it).
- The tier 1 tools are macOS-only and are filtered by the runner while their group is disabled; this slice did not
  run a tier 1 tool end to end. Only the dispatch (fake `run_t1`, worker thread) is tested.
- `recover()` fails every queued job in the ledger. Two server processes sharing one `ledger.db` would fail each
  other's jobs at startup. Two-process behaviour was not tested.
- The service is created on the first call, so the first call pays for `recover` and `purge` on the real ledger.
  If creation fails, the call returns the fixed refusal and creation is retried on the next call.
- A job admitted but not submitted (the service closed in between) stays `queued` until the next startup fails it.
- The tool schema and the added prompt sentence were not tried with a real Ollama model.
- The Gemini Live adapter does not offer `delegate_task`.
- Slice 5 limits apply unchanged (no preemption of a hung tool or model call, and the others in the
  [graph record](agent-backend-graph.md#known-limits)).

## Tests and result

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest apps/api -p no:cacheprovider
```

Real result on this host (Windows, Python 3.14.4): `859 passed, 110 skipped` (baseline `804 passed, 110 skipped`,
plus the 55 new tests). `test_delegation.py`, `test_graph.py` and `test_runner.py` together, 5 runs in a row: 137
passed each time. See the commit report for the `npm run check` result.

`test_delegation.py` covers: a receipt returned while the job is held open and the job later `succeeded` with the
exact receipt (real `Runner`, real ledger, real graph, real `calculate`); the conversation-loop call returning only
job ID and state while the job is held open (named as the scripted-fake form of the design's "real API call"
test; no real API is called); flag off (not offered, not callable, service never reached) and flag on (offered, enum
of task types); five bad flag values stop the session at start; a cloud model, four truthy-but-not-`True` flags and a
flag that raises are cloud, with nothing written; no model; eleven bad argument shapes, each its own code, nothing
written, no instruction text in any refusal; eight model-supplied extras refused; fresh key per call and
`personal` data class from code; constructor data class set and validated; queue full; a repeated key returning the
same job without a second run; a bad call key; the tool runner refusing every memory write and five bad names,
running `calculate` and a memory read, and running a tier 1 tool through `run_t1` from a worker thread; startup
recovery of a running and a queued job and one `purge` call; purge deleting an old job; the event loop ticking at
least ten times while `delegate` blocks 0.4 s in the ledger; `close()` returning in under a second with a job held open.

Mutations tried on 2026-11-16 (each restored): calling `_delegate` inline instead of `to_thread` fails the
event-loop test only; `bool(is_local)` fails the three truthy-flag cases; allowing memory writes in `READ_TOOLS`
fails all five write cases; removing `recover()` fails the recovery test; removing `purge` fails both purge tests;
removing the exact-keys check fails the extra-argument and missing-key cases.

## Not built

Returning job results or notifying the conversation loop, `query_ledger`, `cancel_task` and `steer_task`, any real
planner model (slice 7), the clarify step (open decision 7), wiring into `app.py` or the Gemini adapter, the
scheduled purge, the evaluation set, and any roadmap tick. Open decisions 2, 7 and the R-02.4 consequence stay open.
