# Agent backend slice 4: planner model seam

Date: 2026-11-16. Branch `feat/agent-backend`. Build step 4 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
This is code only. It is not wired into `app.py` or the runner, and no roadmap
item is ticked. No real model, no network, no LangGraph (slice 5 adds [the graph](agent-backend-graph.md)).

## What was built

- `apps/api/src/super_agent_voice/planner.py`: standard library only.
- `apps/api/tests/test_planner.py`: 101 tests (many are parametrized).
- `PlannerModel`: a `typing.Protocol` with `is_local: bool` and
  `complete(prompt: str) -> object`, which returns the reply as parsed JSON or
  raises `ModelError`. Trusted code reads `is_local` for
  `policy.admit(planner_is_local=...)`. `ModelError` carries one code from
  `unavailable`, `timeout`, `malformed`.
- `ScriptedModel(replies, is_local=True, texts=None)`: the fake for tests and evaluation tier A.
  Slice 5 added `complete_text(prompt)` to the protocol and the `texts` queue, `text_prompts` record, for the summarize step.
  It replays queued replies in order, raises a queued `ModelError`, records every
  prompt in `prompts`, and raises `unavailable` when it runs out.
- `request_plan(model, prompt, admission, limits, calls_used) -> Plan`: trusted
  code around one model call. The reply is hostile data. It is first normalized by a
  JSON round trip (`json.loads(json.dumps(reply, allow_nan=False))`, any exception
  including `RecursionError` is `plan_invalid`, and a reply over 120,000 characters of escaped JSON text is refused),
  so only plain dict, list, str, int, float, bool and None reach the checks. It is then
  validated into an immutable `Plan` (frozen dataclasses, tuples, args as canonical JSON
  text). Any failure raises a `PolicyError` with a fixed code; nothing else escapes,
  because the validation is also wrapped to fail closed.

## Order of checks

1. The prompt must be a `str`. If the `Admission` was granted to a local planner and
   `model.is_local is not True` (a flag that raises, or is missing, counts as not local, and the
   error holds no flag text), the call is refused (`planner_locality_invalid`). A local
   model with a cloud-granted admission is allowed. Then `policy.check_model_call(calls_used, len(prompt), limits)`
   (budget and input size). The model is not called if either fails.
2. Any exception from the model becomes `PolicyError("model_error")`. The text is dropped.
3. The reply must be an object with exactly one key, `steps`, a non-empty list. More
   than `limits.steps_per_job` steps is `step_limit` (via `policy.check_step_index`).
4. Each step is validated in order (below). The plan must hold exactly one `finish`, last.

## Step catalog schemas

| Type | Required keys | Optional | Rules |
| --- | --- | --- | --- |
| `read_tool` | `type`, `tool`, `args` | `after` | `tool` is a `str` in `admission.tools`. `args` is an object whose ensure_ascii JSON text is at most 1,000 characters (a non-BMP character counts 12), and it must encode as UTF-8. |
| `summarize` | `type` | `after` must be present and non-empty | depends on earlier steps |
| `ask_user` | `type`, `question` | `after` | `question` is a non-blank `str` of at most 300 characters, UTF-8 encodable |
| `finish` | `type`, `after` | none | exactly one in the plan, the last step, and `after` must be a non-empty list (added after review: it collects the result, so it must name its inputs) |

Any other key on a reply or a step is refused, so a step cannot carry `tools`,
`limits`, `scope`, `deadline` or anything else. `after` is a list of distinct `int`
indexes (a bool is refused) of earlier steps only. Naming only earlier steps makes a
cycle impossible by construction, so there is no separate cycle check.

## Reason codes

Existing: `step_type_unknown`, `step_limit`, `model_call_limit`, `input_too_large`,
`input_invalid`, `planner_locality_invalid` (model locality does not match the admission). Added to `policy.REASONS`: `plan_invalid` (reply or step shape, `after`,
args, question, finish rules), `tool_out_of_scope` (a tool not in the admitted set),
`model_error` (the model raised anything). Messages are the code only.

## Choices where the design was unclear

- The seam has no response-schema parameter. Nothing in this slice consumes one; the
  Gemini slice adds it when it has a use.
- The method is called `complete`, and it is synchronous. The runner's work runs on
  a worker thread, so no async is needed yet.
- Widened scope is judged against `admission.tools`, so a real tier 1 or memory tool
  that this job was not granted, and any memory write tool (never in a scope), is
  `tool_out_of_scope`. A tool with a non-string name is also `tool_out_of_scope`.
- Tool arguments are not validated against each tool's own schema here. `tools.py`,
  `tier1.py` and `memory.py` validate arguments when the tool runs, so this slice
  only bounds their size and encoding. `graph.py` (slice 5) validates every tool argument before any step runs (design section 4); this slice only bounds size and encoding.
- The args bound (1,000 characters of escaped JSON text), the question bound (300 characters) and
  the reply bound (120,000 characters of escaped JSON text) are fixed constants in `planner.py`,
  because `Limits` has no field that fits. They are my choice. Arithmetic for the reply bound:
  the worst valid plan at the 32 step ceiling is 31 `ask_user` steps, each with a 300 character
  non-BMP question (12 escaped characters each, 3,600) and an `after` naming every earlier step,
  plus `finish`. That measures 114,882 characters (a test builds it). `read_tool` steps at the args
  cap measure far less (about 35,000 for 31 of them). 120,000 is above the worst case.
- `after` is optional on every type except `summarize` and `finish`.
- `args` is stored as canonical (escaped, sorted) JSON text, and steps hold tuples, so every field of a
  `Plan` is an immutable str, int, tuple or None.
- A reply with the right shape but a bad `type` value reports `step_type_unknown`
  before key checks.

## Known limits

- Nothing here checks that a `read_tool` step's `args` fit that tool; `graph.py` does that right after this check.
- The plan is not checked for usefulness: a `summarize` may depend on an `ask_user`,
  for example. The graph slice decides what runs.
- The prompt is only length checked. Assembling it (and keeping personal data out of
  a cloud prompt) is not part of this slice.
- The seam is synchronous and has no timeout of its own. A real model must enforce its
  own timeout and raise `ModelError("timeout")`.
- The JSON round trip turns a non-string dict key such as `1` into `"1"` before the checks. A
  real adapter returns parsed JSON, which never has such keys, and the top-level and step key
  checks still refuse them where they matter.
- The normalization trusts that the reply is plain parsed JSON for time and memory: a seam that
  returns an endless iterable or a huge lazy object could hold the call before any size check.
- Duplicate keys in a JSON object are merged by the parser, so a reply with a repeated key is not refused.
- `calls_used` is the caller's count. This slice does not keep it.

## Tests and result

Command (venv built from `apps/api/requirements.lock`):

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest apps/api -p no:cacheprovider
```

Covered: a valid plan round trip, immutability, `ask_user`, unknown step types, tools
outside the set, real tools not granted to a cloud planner, memory write tools, extra
and missing keys on the reply and steps, bad `after` values (forward, self, duplicate,
negative, bool, float, string, non-list), a `summarize` with no dependency, zero and
too many steps, finish rules, bad `args`, bad `question` values, replies of the wrong
shape (list, string, None, NaN), seam errors, an arbitrary exception whose text must
not appear, the scripted fake running out, budget and size refused before any
model call, hostile replies (20,000 deep nesting in args and in the reply, objects with raising
`__repr__` and `__hash__`, a huge int in `after`, non-string keys, an oversized reply, a `str`
subclass with lying `__hash__` and `__eq__`), and the locality rule in both directions. Real result: see the commit report; it is not copied here so this file
cannot go stale.

## Not built

A real model (the Gemini text adapter), a response schema, memory context in the prompt, wiring into `app.py`, the
per-day provider request counter, and any roadmap tick. Prompt assembly, the graph, step execution and
argument validation are in [slice 5](agent-backend-graph.md).
