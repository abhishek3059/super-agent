# Governance gate, slices 2 to 4

| Field | Value |
| --- | --- |
| Date | 2026-11-20 |
| Design | [governance gate](../design/governance.md) section 3 and section 5, slices 2, 3 and 4 |
| Authority | OD-G1 (`policy.py` is the gate) and OD-G6 (PH-02, no exception) in the [decisions record](../approvals/governance-decisions.md) |
| Roadmap | R-02.7. Slice 1 is in PR 62. Slice 2b (GR-1) is not built: OD-G5 is open. R-02.7 stays unticked until slice 2b lands. |
| Branch | `feat/ph02-ledger-policy`, stacked on PR 64 |

## What was built

| Slice | Change | Behaviour |
| --- | --- | --- |
| 2: switches and default deny | A bad `SUPER_AGENT_MEMORY` value also counts as off here, so it cannot break other tools. `policy.Turn` gains `enabled`, the tool names switched on this turn. `decide` denies any other name with the new code `tool_disabled`. `local_adapter.call_tool` asks the gate for every call except tier 1, which keeps its own enabled-name check and audit (design section 2.4). | Messages unchanged ("no such tool"). Fail closed: a bad `SUPER_AGENT_DELEGATE` that appears mid-session now switches off only delegation instead of raising. `start()` still refuses it. |
| 3: job-side moves | `policy.check_planner_locality` and `policy.offered_tools` replace the inline checks in `planner.request_plan` and `Runner._tools`. The planner and runner still collect the facts. `policy.TIER1_NAMES` is tested equal to `tier1.T1_NAMES`. | None. A fact that cannot be read counts as not local or off; bad input offers no tools. |
| 4: distiller | `policy.may_distill(learning_on, memory_on, model_local, from_user)`, asked in `LocalVoiceAdapter.close()` before the distiller thread starts. Content filters stay in `distill.py`. | Fail closed: a cloud model name now stops the run before any ledger job, instead of a job that fails with `model_refused`. |

## Tests

New tests are for the gate functions plus two adapter tests and one distiller
test. Existing adapter, delegation, planner, runner and distill tests pass
unchanged. The `decide` table tests in `tests/test_policy.py` pass the new
`enabled` set.

| Slice | Tests |
| --- | --- |
| 2 | `test_policy.py::test_decide_table` (new `tool_disabled` rows), `test_decide_bad_input_fails_closed` (bad `enabled` values); `test_local_adapter.py::test_every_tool_call_passes_the_gate_and_unknown_names_do_nothing`, `test_a_bad_delegate_flag_mid_session_turns_off_only_delegation` |
| 3 | `test_policy.py::test_check_planner_locality`, `test_offered_tools_narrows_the_grant_by_the_live_switches`, `test_offered_tools_bad_input_offers_nothing`, `test_the_gate_knows_every_tier1_name` |
| 4 | `test_policy.py::test_may_distill`; `test_distill.py::test_close_does_not_start_the_distiller_for_a_cloud_model` |

Results on this branch are in the PR body.

## Not built

Slice 2b (GR-1: `delegate_task` only when the user's own words ask for a
task). OD-G5 asks for a design that understands intent and emotional meaning
instead of a word list. That design does not exist yet, so no pattern was
added.
