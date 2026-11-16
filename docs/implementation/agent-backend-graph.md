# Agent backend slice 5: dynamic graph

Date: 2026-11-16. Branch `feat/agent-backend`. Build step 5 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
This is code only. It is not wired into `app.py`, it uses no real model and no
network, and no roadmap item is ticked.

## What was built

- `apps/api/src/super_agent_voice/graph.py`: `make_work(ledger, model, run_tool, limits, clock)` returns the
  `work(job, admission, should_stop)` callable the [runner](agent-backend-runner.md) accepts. `run_tool(name, args)`
  is injected, may raise, and returns text that is treated as untrusted data.
- `apps/api/tests/test_graph.py`: 55 tests (many parametrized). Uses `ScriptedModel`, a fake tool runner, a real
  `Runner` and the real ledger on a temporary `DB_PATH`.
- Smallest changes elsewhere, each with tests:
  - `runner.py`: the work now receives an `Admission` (built with `dataclasses.replace`, `tools` set to the
    runner-filtered set) instead of the bare tool set. A `PolicyError` raised by the work puts its fixed
    `code` in the failure receipt. Reason stays `work_error`. Nothing else in the runner changed.
  - `ledger.py`: `append_note` (below).
  - `planner.py`: `PlannerModel.complete_text(prompt)` and, on `ScriptedModel`, a `texts` queue and `text_prompts`.
  - `tier1.py`: one public line, `PARAMS` (tool name to declared parameters), so argument checks do not read a private name.
  - `policy.py`: six reason codes (below).
- The dependency is `langgraph==1.2.19`. Vetting facts, with their source and date, are in
  [design section 9](../design/agent-backend.md#9-langgraph-as-a-dependency). They were checked by the
  orchestrator on 2026-11-16 against PyPI metadata and `pip-audit`, not by the author of this slice.

## Flow

1. **Tracing guard** (below). Refuse before any model call; the graph also runs with tracing disabled.
2. **Plan.** The prompt holds the step catalog, the admitted tool names, the task type, and the instruction as a
   JSON string (escaped, so it cannot close its own delimiter) labelled untrusted. `planner.request_plan` makes
   the one planning call (it also refuses a cloud model under a local-granted admission, with no model call) and
   validates shape, step types, step limit, `after` references and tool scope.
3. **Validate everything before any step runs.** An `ask_user` step fails the job with `clarify_unsupported`.
   Every `read_tool` step's arguments go through `_check_args`, a pure pre-check against the tool's declared
   parameters (see choices). Then, and only then, the graph is built.
4. **Build.** One `StateGraph` node per step. A step with `after` entries gets one edge from the list of them
   (LangGraph waits for all). A step with none starts from `START`. The last step (`finish`, guaranteed by
   `planner`) leads to `END`. State is one key, `outputs`, merged by a reducer, so steps in the same superstep
   each add their own key. The shared model-call counter and the first-failure slot sit behind one lock. Compiled
   with no arguments: no checkpointer, no store, no cache. A test spies on `compile` and checks `checkpointer is None`.
5. **Each node**, in trusted code: stop if `should_stop()`; run the step; check output size
   (`check_step_output`) and the step deadline (`check_step_deadline`); write one ledger step record; on any
   failure remember the first code and make every later node return without running.
   - `read_tool`: runs the tool, one retry through `check_retry` (a raise, a non-`str` result, a result starting
     `error:` or an unencodable result counts as a failure). A second failure is `retries_exhausted`. The step
     deadline is checked before each attempt.
   - `summarize`: one model call (`check_model_call`, then count) over a prompt that holds the outputs of its
     `after` steps as one JSON list labelled untrusted data. The reply must be a plain `str`, non-blank and UTF-8
     encodable (`model_reply_invalid`), and within the step output size (`output_too_large`). A raising model is `model_error`.
   - `finish`: joins the outputs of its `after` steps with a blank line, and refuses (`output_too_large`) if the
     receipt would not fit the ledger's receipt size.
6. **Verify, then receipt.** After the graph ends: if any node saw a stop, the work returns `{"stopped": true}`,
   and the runner ends the job as `cancelled`, or `failed` (`job_deadline` or `stop_unconfirmed`), never `succeeded`. If
   any node failed, the work raises `PolicyError(code)`. Otherwise the verifier reads the ledger's events and
   requires exactly one record per plan step, every one `ok`, with the planned type and tool, each recorded after
   the records of its `after` steps, and the finish record's character count equal to the result. Anything else
   is `verify_failed`. Only then does the work return `{"result": <finish text>, "steps": [{"i", "type"}...]}`.

Trust assumption: model text and tool text can appear only in the success receipt's `result` field, which is
the content of the delegated task. No ledger reason, step record or failure receipt ever holds model, tool or
exception text.

## Step records

Design section 10 item 5 says "each node edge writes one ledger transition". The eight states and the revision
compare-and-set cannot take a state change per step, so a step record is an event that changes no state.

`ledger.append_note(job_id, reason, receipt)` appends an event with `from_state == to_state` and the current
revision. It is allowed only while the job is `running` or `cancel_requested`, validates reason and receipt like
`transition` (1 to 64 characters; an object under 4,000 bytes of canonical JSON, no NaN), and raises `LedgerError`
otherwise. It does not bump the revision. A bump would make parallel steps race `Runner.cancel` and
`Runner._finish`, which use compare-and-set with one retry, and could turn a normal finish into `unknown`.
The cost: a step event shares its revision number with the transition before it, so the revision alone
does not order events; `seq` does.

A step record is `{"step", "type", "tool", "outcome": "ok"|"failed", "chars", "reason" (failed only)}` with reason
`step`. `reason` is a fixed `policy.REASONS` code.

## Tracing guard

`langsmith` would send run data to a cloud service when tracing is on, which is an unapproved recipient
([REQ-13](../../prd.md#req-13)). What was verified, on 2026-11-16, in the installed `langchain-core 1.7.3` and
`langsmith 0.14.16` source:

- `langsmith.utils.tracing_is_enabled()` is the decision function. Its inputs are a context override, a
  mid-trace run, a global fallback, and the environment through `get_env_var("TRACING_V2")` or
  `get_env_var("TRACING")`, which reads both `LANGSMITH_*` and `LANGCHAIN_*` names. `get_env_var` is `lru_cache`d, so it
  can go stale inside one process.
- Client behaviour is also set by `LANGSMITH_ENDPOINT`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING_MODE` and similar.

- `langchain_core.tracers.context.tracing_v2_callback_var` (a `ContextVar`, public name) holds the tracer that
  `tracing_v2_enabled()` installs. `_tracing_v2_is_enabled()` there returns True when the variable is set, but
  `langsmith.utils.tracing_is_enabled()` does not look at it and returns False in that case. This was a gap in the
  first version of the guard: the reviewer showed that calling `work` inside `tracing_v2_enabled()` posted tool
  output and summary text to LangSmith.
- `langsmith.tracing_context(enabled=False)` makes `tracing_is_enabled()` False for a block. It does not clear
  `tracing_v2_callback_var`, so that variable is also set to `None` for the run.

What the code does, in two layers:

1. **Check at job start** (`_tracing`, before any model call): refuse with `tracing_enabled` when any environment
   variable starting `LANGSMITH_` or `LANGCHAIN_` has a non-blank value (case-insensitive, read fresh), or
   `tracing_is_enabled()` is true, or `tracing_v2_callback_var.get()` is not `None`. It is blunt on purpose: it also
   blocks harmless `LANGCHAIN_*` variables. It runs once, at the start of a job. Tracing switched on after that, from
   another thread or context, is not seen by it.
2. **Disabled for the run** (`_run_graph`): compile and invoke run with `tracing_v2_callback_var` set to `None` and
   inside `tracing_context(enabled=False)`, so a missed switch still attaches no tracer to the graph.

Tests (all run under an autouse fixture that makes `socket.connect`, `connect_ex`, `create_connection` and
`getaddrinfo` raise and fails the test at teardown if any was called; the two defence tests also replace every
tracer client with a `MagicMock` and point `LANGSMITH_ENDPOINT` at `127.0.0.1:9`, so a regressed defence has no real
client to flush on a background thread after the patches are undone): six variable names (one lower case); `tracing_context(enabled=True)`;
`tracing_v2_enabled()` with a fake client, calling `work` directly in the caller's thread, with zero model calls, zero
tool calls and zero socket attempts; and two tests that replace `_tracing` with a function that returns False
(the environment switch, and the LangChain context) and count tracer `on_chain_start` calls on the graph, which must be zero.
Checked on 2026-11-16 with the defence removed in a temporary edit, under a wrapper script outside the repo whose
`sys.addaudithook` stays active until the process exits: both defence tests failed on the tracer count (5 runs seen),
and the hook saw 0 `socket.connect` and 0 name-lookup events. Removing only `tracing_context(enabled=False)` fails the
environment-switch test only, and removing only `set(None)` fails the LangChain-context test only. The hook sees real
socket calls only, not calls the fixture already refused, which the fixture's own teardown check covers.
The `lru_cache` on `langsmith.utils.get_env_var` is cleared before and after each test, because a value cached by
an earlier test had made the variable-name cases pass without the check.

Mutations tried on 2026-11-16 (each restored): removing the `tracing_v2_callback_var` check fails the LangChain-context test; removing the
environment check fails the `LANGSMITH_API_KEY`, `LANGCHAIN_API_KEY` and `LANGSMITH_ENDPOINT` cases, each alone and
together (the `*_TRACING*` cases still pass through `tracing_is_enabled()`, which is the second place that catches
them); removing `tracing_context(enabled=False)` or the `set(None)` fails the matching defence test.

The leak path was first checked by hand with a throwaway script (not in the repo), pointed at a listener on 127.0.0.1:
with `LANGSMITH_TRACING=true`, a dummy key and `LANGSMITH_ENDPOINT` set to the listener, an unguarded compiled
`StateGraph` made two requests (`GET /info`, `POST /runs/multipart`). Other LangGraph variables (`LANGGRAPH_*`) are not read.

Not covered by the guard: `langchain_core.globals.set_debug` and `set_verbose`, switched on in process, would print tool
output and summary text to stdout. That is local only, not network egress.

## Reason codes

Existing codes are reused: `plan_invalid`, `step_type_unknown`, `step_limit`, `tool_out_of_scope`, `model_error`,
`model_call_limit`, `input_too_large`, `output_too_large`, `step_deadline`, `retries_exhausted`,
`planner_locality_invalid`, `ledger_error`. Added to `policy.REASONS`: `tool_args_invalid`, `clarify_unsupported`,
`tracing_enabled`, `model_reply_invalid`, `step_failed` (an unexpected error inside a step), `verify_failed`.
A failed job ends with reason `work_error` and receipt `{"error": "work_error", "code": <code>}`. `job_deadline`
comes from the runner. Messages are the code only.

## Choices where the brief or the design was unclear

- **Argument pre-check.** No tool exposes a pure validator: `tools.py`, `tier1.py` and `memory.py` validate only
  while running. `_check_args` checks, from each tool's declared parameters: no undeclared key, every required key
  present, strings are `str` (at most 2,000 characters, `calculate` at most 100), a required string is not blank,
  integers are `int` and not `bool`, booleans are `bool`. It is stricter than the tools, which also accept digit
  strings for integers, so such a plan fails closed. `current_time` has no schema in `tools.py`, so it is declared
  here as taking no arguments. A tool with no declared parameters (any name outside these four sources) fails
  closed. Not pre-validated (the tool still decides at run time): paths, arithmetic grammar, query cleaning and
  numeric ranges (tier 1 clamps them). A run-time `error:` result fails the step.
- **Memory context is not added** to the planner prompt in this slice (design section 8). It needs its own
  slice and the synthetic-data rule from section 7.
- **`ask_user` fails closed** because open decision 7 (the clarify wait state) is a maintainer decision.
- **Seam change.** `PlannerModel.complete_text` is a second method (plain text for summarize), not a kind parameter,
  so the plan call and the text call stay separately scriptable.
- **Result shape.** The result is the finish step's text only. `planner` now requires `finish` to name at least one
  step in `after` (a lone finish succeeded with an empty result while other steps ran). A plan whose finish names
  only a summary returns only the summary.
- **Dead-end steps.** A step that nothing depends on still runs, and the verifier still requires its record.
  It may still be running when `finish` completes; the job ends only when the graph does.
- **Stop is not a failure.** A node that sees `should_stop()` returns without a record. The work returns `{"stopped": true}`
  and the runner's existing logic decides the end state.
- **No step-timeout preemption.** Step deadlines are checked after the call returns (and before a retry).

## Known limits

- Nothing is preempted. A tool call or model call that never returns leaves the job `running` until the process
  restarts and `recover()` marks it `unknown`: no step deadline, job deadline or cancel can end it, because they
  are only checked when a call returns.
- A synchronous tool call cannot be interrupted. A step that hangs holds its thread until it returns, then
  fails with `step_deadline`; the job deadline is the runner's and also only takes effect when work returns or polls.
- The planning call and each summarize call are not preempted either; a real adapter must enforce its own timeout.
- The step record is written after the step ends. A crash between the tool call and the record leaves no record,
  and the restart rule makes the job `unknown`; that is intended, and it was not tested with a real crash.
- Records are written by the same process that runs the steps. The verifier checks that the records agree with
  the plan, not that the tools did what they say. A bug in a node that writes a wrong record is not caught.
- The summarize prompt is delimited and labelled, not guaranteed safe: a model can still follow text inside the
  data. The only defence for the result is that the result is data. No privileged action follows from it.
- A summarize over two full-size outputs (4,000 characters each) is over the 8,000 character model input cap and
  fails with `input_too_large`.
- The result is joined text of at most the receipt size (4,000 bytes of canonical JSON, so about 660 non-ASCII characters
  at 6 escaped bytes each). A longer result fails the finish step with `output_too_large`.
- The lock around the model-call counter is not covered by a test: a deterministic test would need two summarize
  steps to race at the budget edge, and thread timing cannot be forced without hooks in the code. Removing the lock
  leaves the suite green.
- Parallel steps run on LangGraph's thread pool; the shared state is the reducer, the counter and failure slot
  under one lock, and the ledger lock. A concurrency stress beyond the suite was not run.
- The tracing check runs at the start of a job only (see Tracing guard); the run-time disable is the second layer.
- The pre-existing `opentelemetry-api` advisory (design section 9) was not changed.
- `recursion_limit` is set to the step count plus 2; a plan cannot loop, so it is never reached.

## Tests and result

Command (venv built from `apps/api/requirements.lock` plus the new pins):

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest apps/api -p no:cacheprovider
```

Real result on this host (Windows, Python 3.14.4): `804 passed, 110 skipped`; `test_graph.py`, `test_runner.py` and `test_planner.py`
together, 5 runs in a row: 183 passed each time. See the commit report for the `npm run check` result; it is not copied here
so this file cannot go stale.

Covered in `test_graph.py`: a valid plan (two independent reads that must run in the same superstep, a summarize
over both, a finish) with the exact receipt, one record per step, and dependency order; a dead-end step; the step-record events
(state and revision unchanged, one terminal transition); prompt delimiting of the instruction and step outputs;
single-defect plans rejected (a lone `finish`, or `finish` with an empty `after`, is also `plan_invalid`, in `test_planner.py`) with no tool and no further model call (unknown step type, forward reference, self
reference, too many steps, a tool outside the admitted set, a tool the runner removed); six invalid-argument cases
rejected while an earlier valid step must not run; an `ask_user` plan; a raising tool (retried once, then failed, no
exception text in any event); a tool that works on retry; an `error:` result; an oversized tool output; model-call
budget exhausted at the summarize step; a step deadline; a job deadline; cancel during a step; nine hostile
summarize replies; the verifier refusing a missing, a duplicated and a failed record; a ledger write failure; the
tracing guard (six environment names and in-process); a local-granted admission with a cloud model; no checkpointer.
Verifier and receipt-size tests: a record out of dependency order, a finish record whose count differs from the result, and a finish whose receipt cannot fit (each fails alone when its check is removed). The `ledger` tests for `append_note` and the runner tests for the admission and the failure code are in their files.
Each negative test was built from the valid plan with one defect and asserts the exact code.

## Not built

Wiring into `app.py`, the clarify step and its wait state (open decision 7), memory context in
the prompt, a real model (the Gemini text adapter), the per-day provider request counter, the evaluation
set, and any roadmap tick. Built later, in [slice 6](agent-backend-delegation.md): `delegate_task` in the local
text adapter and the real tool runner that dispatches to `tools.py`, `tier1.py` and `memory.py`.
