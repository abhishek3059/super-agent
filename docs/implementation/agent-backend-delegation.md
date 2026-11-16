# Agent backend slice 6: delegate_task in the local conversation loop

Date: 2026-11-16. Branch `feat/agent-backend`. Build step 6 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
It adds one tool to the local text adapter, off by default. It uses no real model and no network,
adds no endpoint, changes no authentication, Host, Origin or CORS handling, and ticks no roadmap item.

## What was built

- `apps/api/src/super_agent_voice/delegation.py` (88 lines at the time of writing): `Service`, `run_read_tool`, and `TOOL` (the schema).
- `apps/api/src/super_agent_voice/local_adapter.py`: `delegate_enabled()` (the `SUPER_AGENT_DELEGATE` flag), the tool
  added to `available_tools()`, a dispatch branch in `call_tool`, a one-sentence system prompt addition when on,
  and a flag check at session start. `gemini_adapter.py` is untouched.
- `policy.py`: one reason code, `delegation_unavailable`.
- Follow-up commit, `fix(api): honour the memory opt-out and untrusted-text guard for delegation`: `memory.flag()` and
  `memory.enabled()`, the runner's memory filter, a memory check in `run_read_tool`, and the untrusted-text guard
  (sections below).
- `apps/api/tests/test_delegation.py`: 76 tests (55 in the first commit, 16 in the memory follow-up, 5 more in the test-isolation follow-up). `apps/api/tests/test_home_guard.py`: 2 tests.
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
A memory read tool also needs `memory.enabled()` (fail closed: a bad `SUPER_AGENT_MEMORY` value counts as off), so a
user who switched memory off cannot have a background job read it, even if a tool name reached this function.
Dispatch goes to existing code: `tools.run_tool`, `tier1.run_t1`, `memory.run`. Results pass through unchanged
(untrusted data; the graph bounds and checks them).

`tier1.run_t1` is async and the graph calls tools from a LangGraph worker thread, which has no running event loop.
The smallest bridge is `asyncio.run(tier1.run_t1(...))`, one short-lived loop per call. It is tested from a
`ThreadPoolExecutor` thread with a fake `run_t1`; no real app or file was touched.

## Memory opt-out

Admission grants the memory read tools and `memory_context` to a local planner. The runner is where tools are offered,
as for tier 1 groups, so `Runner._tools` drops every memory tool name and the admission handed to the work carries
`memory_context=False` unless `memory.enabled()` is true ([runner record](agent-backend-runner.md#memory-tools)).
The switch moved from `local_adapter.memory_enabled()` into `memory.flag()` so the runner can read it without an import
cycle; `local_adapter.memory_enabled()` delegates to it and still raises on a bad value (its tests are unchanged).
With memory off, a plan that names `list_memory` fails `tool_out_of_scope` before any step runs. Three layers hold:
the runner filter, the planner's scope check, and `run_read_tool`.

## Untrusted-text guard

`call_tool` already refuses memory writes in a turn that read tier 1 content (`_READ_UNTRUSTED`). `delegate_task`
follows the same rule: after a tier 1 read in the same turn it returns the fixed `DELEGATE_AFTER_READ` text and does
not reach the service, so nothing is written. Text from a file, note or mail could otherwise start a background job
over the user's data (AGENTS.md section 5). The flag is per turn (a task context variable), so the next turn starts
clean. It is checked after the `SUPER_AGENT_DELEGATE` flag, so with the tool off the answer is still `no such tool`.

## Startup and shutdown

Creating a `Service` calls `Runner.recover()` once (a `running` or `cancel_requested` job becomes `unknown`, queued
jobs are failed `restart_queued`, nothing is replayed) and `ledger.purge(now)` once (the 14-day retention had no
caller until now). Nothing schedules the purge after that, so a long-running process purges only at its start.
`close()` marks the service closed and calls `Runner.close()` (`shutdown(wait=False, cancel_futures=True)`), so it
does not wait for a running job. Later calls are refused `delegation_unavailable`.

The adapter holds one process-wide service, created on the first `delegate_task` call (off the event loop), and
never closes it: jobs are meant to outlive a session. Nothing calls `Service.close()` outside tests.

## Choices where the brief or the design was unclear

- **Idempotency key.** The conversation loop has no tool-call identifier: `ollama_reply` does not pass one to
  `call_tool`. So the key is a fresh `uuid4().hex` per call. A retried or repeated tool call is therefore a new job,
  not a duplicate of the first. Only the queue cap bounds repeats. `Service.delegate` takes the key as an argument,
  so a caller with a stable identifier can use it.
- **No model configured.** The adapter builds `Service()` with no model, because no real model is wired in. Slice 7 added `GeminiPlanner` for the opt-in check only ([record](agent-backend-gemini-planner.md)).
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
- `admit` alone still grants memory tools to a local planner whatever the flag says; the opt-out is enforced by the
  runner filter and `run_read_tool`, not at admission. A new caller that bypasses the runner would not get it.
- The untrusted-text guard covers tier 1 reads only (the same set as the memory-write guard). Text from any other
  source is not marked.
- The runner's pool threads are not daemon threads, so a job stuck in a tool or model call can delay process exit.
  Checked on 2026-11-16 with a throwaway script outside the repo (Python 3.14.4, Windows): a `ThreadPoolExecutor`
  worker reported `daemon=False`, and after `shutdown(wait=False, cancel_futures=True)` the process still exited only
  when a 4 second `time.sleep` in the worker finished (interpreter exit joins pool threads). `Service.close()` does not
  wait, but it cannot stop a running job either.
- The adapter never closes the process-wide service (nothing calls `close()` outside tests), so the pool and any held
  job live until the process exits.
- Assistant replies from an earlier turn stay in the conversation history. They can paraphrase untrusted text, while
  the untrusted-read flag resets each turn, so a later turn can act on a paraphrase the guard never saw.
- A `list_memory` or `list_reminders` read does not set the flag, although memory can hold text that came from earlier
  untrusted content (a remembered file excerpt, for example).
- Importing `local_adapter` now imports `delegation`, `graph` and LangGraph even with `SUPER_AGENT_DELEGATE` off. A local
  environment installed before LangGraph joined `apps/api/requirements.lock` fails to import the local adapter until it
  is reinstalled with the same `pip install --only-binary=:all: -r apps/api/requirements.lock ...` line
  ([setup](../../apps/voice-foundation.md)). CI installs from the lock file, so it is not affected. The import time was not measured.
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

Real result on this host (Windows, Python 3.14.4): `885 passed, 110 skipped` twice in a row (baseline `804 passed,
110 skipped`, plus 76 delegation tests, 3 runner tests and 2 home-guard tests). `test_delegation.py`, `test_graph.py`
and `test_runner.py` together, 5 runs in a row: 161 passed each time. See the commit report for the `npm run check` result.

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
Follow-up: a local planner is offered the memory tools only when `SUPER_AGENT_MEMORY` is exactly `on` (six values,
including unset, `maybe`, `ON` and empty, read from the planner prompt), never a memory write; a plan naming
`list_memory` with memory off fails `tool_out_of_scope` with no step record and no memory read; the same plan runs with
memory on; `run_read_tool("list_memory")` is refused unless memory is on; the admission given to the work carries
`memory_context` only when memory is on; a tier 1 read followed by `delegate_task` in one turn is refused with the
service untouched and the ledger empty; a turn with no read still delegates, and the next turn after a refused one is clean.

Mutations, all re-run at the head of the test-isolation follow-up (2026-11-16), each in a copy of `apps/api`
outside the repository with the home folder pointed at a temporary folder, never in the worktree. The unmutated copy
passed 106 tests (`test_delegation.py` plus `test_runner.py`).

| Mutation | Result |
| --- | --- |
| `_delegate` called inline instead of through `to_thread` | the event-loop test fails (1) |
| `bool(is_local)` instead of `is True` | the three truthy-flag cases fail (3) |
| `READ_TOOLS` includes every memory name (`memory.NAMES`, writes too) | the five memory-write cases with memory **on** fail; with memory off they still pass, because the memory-off check refuses first (that was the gap: since the memory follow-up the test ran with memory off, so this mutation passed everything; the test now sets memory on and off explicitly) |
| `recover()` removed | the recovery test fails (1) |
| `purge` removed | the recovery test and the purge test fail (2) |
| exact-keys check removed | three argument-shape cases and eight extra-argument cases fail (11) |
| runner memory filter and `memory_context` clearing removed | eleven tests fail (3 runner, 8 delegation) |
| untrusted-text guard removed | the two guard tests fail (2) |
| the memory check in `run_read_tool` removed | the three memory-off and bad-flag cases of the `run_read_tool` test fail (3) |

## Tests stay out of the real home folder

Found by the shared reviewer: the suite wrote to the operator's real `~/.super-agent/`. Two causes. First, a test that
ended with a job still running left a worker thread behind; the fixture's `close()` does not wait, the test's
monkeypatches were undone, and the worker's later ledger calls went to the default `ledger.db` in the real home folder.
Second, `memory.AUDIT_LOG` was not redirected, so tests that ran memory tools appended lines to the real
`tool-audit.log`. Reproduced before the fix against a throwaway home folder: running only `test_delegation.py` with
`HOME` and `USERPROFILE` set to a temporary folder left `ledger.db` (28,672 bytes) and `tool-audit.log` in
`<temp>/.super-agent`.

What `apps/api/tests/conftest.py` does now:

1. **Redirect before import.** It records the real data folder, then points `HOME` and `USERPROFILE` at a fresh temporary
   folder before any `super_agent_voice` import. Every default path (`ledger.DB_PATH`, `memory.DB_PATH`,
   `memory.AUDIT_LOG`, `tier1.AUDIT_LOG`, `config.TOKEN_FILE`, `local_adapter.MODEL_DIR`, and the lfm3 model path) is
   computed from `Path.home()` (at import time, except the lfm3 path, which is computed at call time), so none of them can name the real folder. Both variables are set
   because Python reads `USERPROFILE` on Windows and `HOME` on macOS and Linux. `test_home_guard.py` checks that none of those
   constants points into the real folder.
2. **Session guard.** A session fixture lists the real folder (name, size and modification time of every entry,
   never contents) before the run and fails the suite if the listing differs afterwards. It also fails if anything
   was written to the redirected default folder, which means a test used a default path instead of its own temporary one.
3. **Per-test guard.** The same listing is compared around every test, so the test that touched the real folder is the one
   that fails. `test_home_guard.py` shows the comparison notices a created, a changed and a removed file.
4. **No worker outlives its test.** An autouse fixture records every `Runner` a test builds and, in its teardown,
   waits for each runner's pool (`shutdown(wait=True)`). It asks for `monkeypatch`, so its teardown runs before the
   test's monkeypatches are undone. The delegation tests' `services` fixture also releases any held model gate first, so
   the wait ends at once instead of at the five second test timeout.
5. `memory.AUDIT_LOG` and `tier1.AUDIT_LOG` are redirected to the test's temporary folder.

Checked by removing the drain wait and the gate release in a copy outside the repo: the session guard then fails with
"a test wrote to a default data path". With both in place it does not.

`test_runner.py` and `test_graph.py`: I checked them for a worker that outlives its test by running both files in a copy outside the repo with a probe in the drain fixture that listed the ledger's non-terminal jobs at each runner's teardown (78 runners). Seventy-one had none. Seven had a row left in a non-final state, but none had a live worker: two are `unknown` (a final state in the ledger that the probe's terminal set does not include), one job was admitted and never submitted (`queued`), and four tracing tests call `work` directly with a hand-moved job and never start a runner thread (`running`). So neither file leaves a worker running, and the drain finished each pool at once (the two files took 10 seconds together). Their own fixtures already close their runners, and the drain is now the safety net for them as well.

Real listing of `~/.super-agent/` (name, size, modification time; no contents) around two full suite runs
(`885 passed, 110 skipped` each), taken with `ls` before and after, identical:

```text
before
28672 2026-11-16 19:44:15.790812700 ledger.db
33973 2026-11-16 19:44:15.470567900 tool-audit.log
43 2026-11-14 00:57:31.009880800 voice-token
after
28672 2026-11-16 19:44:15.790812700 ledger.db
33973 2026-11-16 19:44:15.470567900 tool-audit.log
43 2026-11-14 00:57:31.009880800 voice-token
```

## Not built

Returning job results or notifying the conversation loop, `query_ledger`, `cancel_task` and `steer_task`, any real
planner model in the conversation (slice 7 built one for the opt-in check only), the clarify step (open decision 7), wiring into `app.py` or the Gemini adapter, the
scheduled purge, the evaluation set, and any roadmap tick. Open decisions 2, 7 and the R-02.4 consequence stay open.
