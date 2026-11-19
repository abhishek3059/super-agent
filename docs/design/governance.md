# Governance gate (design)

| Field | Value |
| --- | --- |
| Status | **Proposal, accepted in part.** OD-G1 to OD-G4 are approved ([decisions record](../approvals/governance-decisions.md)); OD-G5 is open with a direction from the owner and blocks only slice 2b. Design only, no code. |
| Date | 2026-11-18 |
| Requested by | Maintainer `abhishek3059`, in chat, 2026-11-18 |
| Roadmap | On the roadmap as R-02.7 in PH-02, the current phase since PR #58 merged on 2026-11-19 (section 6.2). |
| Related | [brain overview](brain/overview.md), [brain memory](brain/memory.md), [agent backend](agent-backend.md), [tier 1 read tools](tier1-read-tools.md), [local memory](local-memory-reminders.md), [DEC-18](../../descisions.md#dec-18) |

## 1. The recommendation

The request was one "governance" module that holds intent routing,
guardrails, central authorization, and self-learning. This proposal splits it
in three, because only one of the three can authorize anything.

- **The gate decides.** Every proposed action asks one deterministic gate. It
  answers allow, deny with a fixed reason code, or needs confirmation. It never
  calls a model, does no I/O, and fails closed
  ([REQ-10](../../prd.md#req-10), [AGENTS.md](../../AGENTS.md) section 5).
- **The brain proposes.** Intent routing, tone, and persona stay in the brain
  ([brain overview](brain/overview.md) sections 2, 3 and 7). Model output is
  only a proposal that the gate checks.
- **Memory learns.** Self-learning stays in memory (the distiller,
  [brain memory](brain/memory.md) section 9). The gate only bounds it.

**The gate is `policy.py`.** A new module is not justified.
`apps/api/src/super_agent_voice/policy.py` already holds admission, limits,
tool scope, the closed reason set `REASONS` (lines 18-28) and the rule that
refusals carry a fixed code (lines 31-38). It already has no model, no
network, and no clock of its own (lines 3-8). What is missing is the
turn-level checks that today live inside `local_adapter.call_tool`. They move
into `policy.py`. Nothing else is renamed.

## 2. Inventory of existing checks

Line numbers are on `origin/develop` at the time of writing, except the
distiller, which is on local branch `feat/memory-distiller` only. "Gate" means
the check moves into or already lives in `policy.py`. "Stays" means it stays
where it is, as defence in depth or because it needs data the gate must not
touch. "Brain" means it is judgment, not authorization.

### 2.1 Already in the gate (`policy.py`)

| Check | Lines | Decides | Fate |
| --- | --- | --- | --- |
| `Limits.__post_init__`, `CEILING` | 42-70 | No limit exceeds a hard ceiling or is not an int | Gate, as is |
| `_spec` | 124-142 | Spec has exactly three keys, known task type and data class, storable instruction | Gate, as is |
| `admit` | 145-200 | Clock, idempotency key, trusted bool flags, personal data never to a cloud planner, queue cap, tool grant by task type and source | Gate, as is |
| `TOOL_SCOPE`, `TIER1_*_TOOLS`, `MEMORY_TOOLS` | 80-96 | Which tools a task type may get. The spec never names tools | Gate, as is |
| `check_step_index`, `check_retry`, `check_step_deadline`, `check_job_deadline`, `check_model_call`, `check_step_output` | 205-256 | Step, retry, time, model call and output budgets | Gate, as is |

### 2.2 Turn-level checks in `local_adapter.py`

| Check | Lines | Decides | Fate |
| --- | --- | --- | --- |
| `_READ_UNTRUSTED` set by a tier 1 read | 137, 141-143 | Records that this turn read untrusted text | Stays. It is fact collection: the adapter owns turn state |
| `DELEGATE_AFTER_READ` | 133, 147-148 | No `delegate_task` in a turn that read untrusted text | **Gate, slice 1** |
| `memory.AFTER_READ` | 155-156 (string in `memory.py` 532) | No memory write in a turn that read untrusted text | **Gate, slice 1** |
| `_HEARD`, `_ASKED`, `NOT_ASKED` | 127-135, 157-159, set at 357 | A memory write runs only if the user's own words asked for that kind of change | **Gate, slice 1** |
| `delegate_enabled`, `memory_enabled` "no such tool" | 76-80, 144-146, 150-152 | A switched-off tool does nothing | Gate, slice 2 |
| `local_model` "cloud" name refusal | 502-509 | A model name containing "cloud" is refused | Stays. It is a provider fact found by inspecting config |
| `_refuse_remote_model` | 512-530 | Ollama reports the model as remote, so refuse | Stays. It does network I/O; the gate does none. Its result is a fact the gate can take later |
| `system_prompt`, `available_tools` | 97-109 | What the model is told and offered | Stays. Offering is not authorizing; the gate checks the call |

### 2.3 Jobs: planner, runner, graph, delegation

| Check | File and lines | Decides | Fate |
| --- | --- | --- | --- |
| Plan shape, `_step`, tool in admitted scope | `planner.py` 100-134, 125 | A model plan uses only known step types and admitted tools | Stays. It parses model output into a typed `Plan`; it already raises `PolicyError` |
| Planner locality | `planner.py` 150-161 | A grant made for a local planner is never used by a cloud model | Gate, slice 3 (pure, small) |
| Model call and step count | `planner.py` 162, 181 | Calls `policy.check_model_call`, `check_step_index` | Gate already |
| `Runner._tools` | `runner.py` 176-185 | Re-filters the grant by the live tier 1 and memory switches; bad config offers none | Gate, slice 3 |
| `Runner._late`, `should_stop` | `runner.py` 113-121, 194-202, 231-235 | Deadline or cancel stops work; errors mean stop | Stays. Execution control, uses the gate's deadline check |
| `Runner.claim_and_run` | `runner.py` 92-107 | Builds an `Admission` directly, with `planner_is_local=True` and tools from `HERMES_WORKERS` | **Bypasses `admit`.** Called only by `tests/test_runner.py` 395-415. Its `memory_recall` and `memory_save` names (line 52) are not memory tool names. Open decision OD-G3 |
| `_check_args` | `graph.py` 33-47 | Step arguments match the declared schema and size | Stays. Argument shape next to the tool schemas, not authorization |
| `_tracing`, `_run_graph` | `graph.py` 50-58, 89-90, 191-198 | No job runs with LangSmith or LangChain tracing on | Stays. Fact collection reads env and library state; the rule is one line |
| Clarify unsupported, verify | `graph.py` 94, 201-216 | No `ask_user` step yet; receipt matches the plan | Stays |
| `Service` data class, local flag | `delegation.py` 44-46, 66-69 | Data class from trusted code; a broken locality flag is not local | Stays. It produces the trusted facts that `admit` takes |
| `READ_TOOLS`, `run_read_tool` | `delegation.py` 20, 32-40 | A job tool call reaches only read tools, and memory only while on | Stays. Last-line allowlist, deliberately duplicated |

### 2.4 Data boundaries: tier 1, memory, distiller, app

| Check | File and lines | Decides | Fate |
| --- | --- | --- | --- |
| `_config`, enabled-name check | `tier1.py` 80-103, 482-488 | Bad settings offer nothing; disabled names do nothing | Stays. Config and defence in depth |
| `_resolve`, `_read_head`, `_hidden`, size caps | `tier1.py` 173-238 | Paths stay inside allowlisted roots, no symlink or FIFO tricks | Stays. Needs the filesystem; the gate must stay pure |
| Fixed error strings, audit | `tier1.py` 459-508 | No content in errors or the audit log | Stays |
| `_text`, `_clean`, `_SECRET`, caps | `memory.py` 31, 54-62, 120-136, 326-347 | Text is bounded, cleaned, not secret-shaped; store sizes capped | Stays. Content validation at the store, the last line before a write |
| `flag`, `enabled` | `memory.py` 516-530 | The memory switch; a bad value is off | Stays. The gate takes the result as a fact |
| Turn filter, `_SECRET` on input | `distill.py` 111-118 | A spoken secret never reaches even the local model | Stays (memory) |
| `_items`, `_SENSITIVE` | `distill.py` 32-43, 65-98 | Model reply is schema-checked; secret and sensitive items dropped | Stays (memory). Learning filters are content rules, not authorization |
| Distiller job creation | `distill.py` 122-126 | Writes a ledger job without `admit` | Bounded by the gate, slice 4 (section 5) |
| Host, Origin, token | `app.py` 204, 471, 525-530 | Local API boundary ([REQ-11](../../prd.md#req-11)) | Stays. It is transport authentication, reviewed in [R-01.6](../reviews/r01-6-security-review.md). No reason found to move it |

## 3. Gate interface

Two entry points already exist and stay: `admit` for a new job and the
`check_*` functions for steps. One is added for actions inside a voice turn.

```python
@dataclass(frozen=True)
class Turn:
    """Facts set by trusted code for one conversation turn. Never model claims."""
    heard: str | None      # the user's own transcript this turn, None outside a voice turn
    read_untrusted: bool   # a tier 1 read already ran this turn
    memory_on: bool        # memory.enabled()
    delegate_on: bool      # delegate_enabled(), already validated at session start

@dataclass(frozen=True)
class Decision:
    verdict: Literal["allow", "deny", "confirm"]
    code: str | None       # a REASONS code when not "allow", else None

def decide(tool: object, turn: object) -> Decision: ...
```

Rules for `decide`:

1. It is pure: no model, no I/O, no clock. It never raises. Any bad input
   (unknown tool type, a non-bool fact, a non-`Turn`) is
   `Decision("deny", "input_invalid")`.
2. Tool names it does not govern return allow. Their own handlers and the
   checks in section 2.4 still run. This keeps slice 1 small; a default-deny
   list of known names is slice 2.
3. `"confirm"` exists in the type because a later tier needs it (T3,
   on-device approval). Until a reviewed confirmation path exists, every
   caller treats `"confirm"` as deny. No rule returns it in slices 1 to 3.
4. New codes join `REASONS`: `untrusted_read_in_turn`, `not_asked`,
   `tool_disabled`. Callers map a code to their existing user-facing string,
   so no message changes.

No registry, no plugin hook, no rule objects. The inventory has five
turn-level rules; a few `if` lines cover them.

## 4. What the gate does not do

- **Routing.** Which worker, which task type, whether a question needs a
  tool: the brain proposes. The gate checks the resulting call.
- **Tone and persona.** How to answer, and whether now is a good moment, is
  model judgment in the persona prompt (roadmap R-A.3, T0).
- **Learning.** What is worth remembering is the distiller's model call plus
  memory's content filters. The gate only says whether the distill job may run.

Why: a model can be wrong, and text it reads can steer it (prompt injection,
[AGENTS.md](../../AGENTS.md) section 5). Its judgment may make the assistant
quieter or stricter. It must never be the reason something is allowed.

### 4.1 The emotional-turn rule

The concern: do not start a task when the user is being emotional.

What code can tell: the words in the user's own transcript, their length,
and whether a fixed request pattern appears. What code cannot tell: emotion.
Words like "angry" or "tired" do not mean the user is upset, and a calm
sentence can come from someone in distress. Prosody from audio is not
measured here and would still be a guess. So no rule may claim to detect
emotion.

The proposed rule targets the harm instead: an unwanted task.

> **GR-1.** `delegate_task` is allowed only when the user's own words in this
> turn contain an explicit request to do something (a fixed pattern, like
> `_ASKED` for memory in `local_adapter.py` 128-132). Otherwise the gate
> returns `deny` with `not_asked`. The model's claim that the user asked does
> not count.

This is the same mechanism memory writes use today, so it is proven code.
Venting ("I'm so done with this week") does not start a job. "I'm furious,
just find that email" does, because the user asked. That is intended.

The other half is model judgment and is labelled as such: the T0 persona
prompt tells the model not to propose tasks while the user is venting, and to
acknowledge first. If that judgment fails, GR-1 still holds. A brain "tone"
signal may later be passed to the gate as a tightening-only fact (it can turn
allow into confirm, never the reverse). OD-G2 decided this on 2026-11-19.

GR-1 changes behaviour, so it is its own slice (slice 2b), not part of the
no-change migration.

## 5. Migration in slices

Each slice moves checks behind the gate with no change in behaviour. All
existing tests pass unchanged; new tests are added only for `decide`.

**Slice 1: the three untrusted-text and asked-for rules.** One session.

- `policy.py`: add `Turn`, `Decision`, `decide`; add `untrusted_read_in_turn`
  and `not_asked` to `REASONS`. Move the `_ASKED` patterns here unchanged.
- `local_adapter.py`: `call_tool` builds a `Turn` from `_HEARD`,
  `_READ_UNTRUSTED` and the switches, calls `decide`, and maps a deny to
  `DELEGATE_AFTER_READ`, `memory.AFTER_READ` or `NOT_ASKED` exactly as today.
  `_ASKED` is deleted from `local_adapter.py`. The switch checks stay for now.
- `tests/test_policy.py`: add table tests for `decide`, including bad inputs
  failing closed and `"confirm"` never returned.
- Must pass unchanged: `tests/test_local_adapter.py`
  (`test_a_turn_that_read_a_file_cannot_write_memory`,
  `test_memory_changes_only_when_the_users_words_asked_for_them`),
  `tests/test_delegation.py`
  (`test_a_turn_that_read_untrusted_text_cannot_delegate_and_nothing_is_written`,
  `test_a_turn_with_no_untrusted_read_can_delegate_and_the_guard_resets_each_turn`),
  and the full `tests/` suite.

**Slice 2: switches and default deny.** Move the "no such tool" switch checks
into `decide` with `tool_disabled`, and make unknown tool names deny. Tests:
`test_memory_is_off_by_default_and_offered_only_when_on` and the delegation
switch tests, unchanged.

**Slice 2b (behaviour change): GR-1.** Add the delegation request pattern.
Needs its own tests and a note in the [brain overview](brain/overview.md)
butler table. Pairs with R-A.3.

**Slice 3: job-side moves.** Move the planner locality check
(`planner.py` 150-161) and `Runner._tools` (`runner.py` 176-185) into pure
`policy.py` functions that the planner and runner call. Tests:
`test_planner.py`, `test_runner.py`, `test_delegation.py`, unchanged.

**Slice 4: bound the distiller.** After `feat/memory-distiller` merges, the
distill job asks the gate before its ledger write: memory on, model local,
user turns only. Its content filters stay in `distill.py`.

## 6. Conflicts and open decisions

### 6.1 Overlap with open PR #56 (`feat/jarvis-hq`)

PR #56 renames `policy._spec` to `policy.validate_spec`, excludes `hq_role`
jobs from the `admit` queue count, adds a `pending_limit` to
`ledger.create_job`, skips HQ jobs in `Runner.recover`, and adds `hq_jobs.py`.
`hq_jobs._operate` calls `validate_spec` and `ledger.create_job` directly, so
HQ jobs are admitted outside `admit`, with their own cap of 7 and a fixed
`synthetic` data class. That is a second admission path. Slice 1 does not
touch any of these lines, so it can land before or after PR #56. Slices 3
and 4 should wait for it. Whether HQ submission should call `admit` is
OD-G4.

### 6.2 Roadmap position

R-02.7 is in PH-02, with no exception tag. PH-02 is the current phase since
PR #58 merged, and policy limits already live in R-02.3. [PR 59](https://github.com/abhishek3059/super-agent/pull/59), which
adds it also adds the [decisions record](../approvals/governance-decisions.md).
The `governance-gate-exception.md` record proposed in an earlier draft is not
needed for slice 1 once that PR merges. If branch
`feat/governance-gate-slice1` carries that exception record, it becomes
historical.

### 6.3 Decisions only a maintainer can make

- **OD-G1.** Accept `policy.py` as the gate, instead of a new
  `governance.py`. Decided: approved on 2026-11-19, see the
  [decisions record](../approvals/governance-decisions.md).
- **OD-G2.** Decided 2026-11-19: a tone signal may only tighten a decision,
  and `confirm` in voice is a refusal until T3 exists. The question was
  whether a brain tone signal may tighten a decision (allow to confirm), and
  what confirmation means in voice before T3 exists.
- **OD-G3.** Decided 2026-11-19: route it through the gate. The question was
  that `Runner.claim_and_run` bypasses `admit` and hardcodes a local planner:
  delete it, or route it through the gate. Its worker tool names need fixing
  either way.
- **OD-G4.** Decided 2026-11-19: yes. The question was whether HQ jobs in
  PR #56 must pass `admit`.
- **OD-G5.** Open, and blocks slice 2b only. The question is the GR-1
  request pattern: a fixed word list misses some real requests (the user must
  rephrase) and is English only. The owner asked for a design that
  understands the user's intent and emotional meaning and picks the type of
  response, instead of a word list.
- **OD-G6.** The roadmap item, its phase, and whether an exception is needed.
  Answered as a proposal by the roadmap PR: R-02.7 in PH-02, no exception.
  It takes effect when a maintainer approves or merges that PR.
