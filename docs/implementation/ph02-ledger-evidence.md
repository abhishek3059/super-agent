# PH-02 evidence record: ledger, policy, and fixed workers (R-02.1 to R-02.5)

| Field | Value |
| --- | --- |
| Date | 2026-11-20 |
| Branch | `feat/ph02-ledger-evidence` (PR 64) |
| Host | Windows 11 Home, Python 3.14, SQLite ledger |
| Scope | Evidence for R-02.1 to R-02.5 and fixes R-02.F1, R-02.F5, R-02.F6. Nothing here ticks a roadmap item. |
| Suite result | 1092 passed, 110 skipped (develop at 664fd2a was 1071 passed, 110 skipped) |

All paths are under `apps/api/`. Code cites are in `src/super_agent_voice/`, tests in `tests/`.
Test names are exact. All runs used synthetic data and no network (the `no_network` fixture
in `test_delegation.py` fails any non-loopback connection).

## Criteria

| Criterion | Code | Tests | Result |
| --- | --- | --- | --- |
| AC1.1 Eight states, other transitions refused | `ledger.py:39` (`NEXT`) | `test_ledger.py::test_allowed_transitions`, `test_every_other_transition_is_rejected`, `test_unknown_state_rejected` | Met |
| AC1.2 Revision bump, event per transition, receipt for terminal states | `ledger.py:293` (`transition`) | `test_ledger.py::test_events_follow_every_change`, `test_receipt_required`, `test_receipt_stored_in_event_and_terminal_stamp`, `test_event_and_state_change_are_atomic` | Met |
| AC1.3 Only the ledger sets state; success needs the verifier | `graph.py` `_verified`, `runner.py:150` (`_run` writes the terminal state) | `test_graph.py::test_verifier_refuses_success_when_a_record_is_missing_duplicated_or_failed`, `test_verifier_refuses_records_out_of_dependency_order`, `test_ledger_write_failure_fails_the_job_closed` | Met |
| AC1.4 State survives restart, no blind replay | `ledger.py:356` (`recover_after_restart`), `runner.py:131` (`recover`) | `test_ledger.py::test_restart_recovery_never_replays`, `test_runner.py::test_recover_marks_running_unknown_and_fails_queued`, `test_delegation.py::test_close_mid_job_then_recover_marks_unknown` | Met in process. No test restarts a separate OS process. The ledger is an on-disk SQLite file, and the tests reopen it through a new Service. |
| AC2.1 Same key, same job, no duplicate, deadline not extended | `ledger.py:259` (`create_job`), `policy.py` `_deadline_of` | `test_ledger.py::test_idempotent_create`, `test_same_key_different_spec_is_error`, `test_policy.py::test_same_key_same_spec_returns_the_same_job`, `test_repeat_keeps_the_original_deadline` | Met |
| AC2.2 Old revision refused, concurrent writers | `ledger.py` `_move` (compare-and-set in SQL) | `test_ledger.py::test_stale_revision_rejected`, `test_lost_update_is_caught_in_sql`, `test_delegation.py::test_two_threads_update_same_job_one_wins` (10 rounds, two real threads) | Met |
| AC2.3 Closed or replaced session refused (R-02.F5) | `delegation.py:70-120` (`open_session`, `close_session`, `_check_session`, `delegate`, `cancel`), `local_adapter.py:125-144` and `:283`, `:344`, `:402` | `test_delegation.py::test_delegate_needs_the_live_session_and_the_job_records_it`, `test_a_replaced_session_is_refused_and_its_running_job_keeps_running`, `test_cancel_from_a_stale_session_is_refused`, `test_a_closed_session_does_not_accept_no_session`, `test_closing_a_stale_session_leaves_the_live_one_working`, `test_only_the_jobs_own_session_can_cancel_it`, `test_cancel_of_an_unknown_job_is_unknown_job`, `test_the_adapter_opens_and_closes_its_session` | Met for delegate and cancel. Result delivery from an old session is not built (R-M.17). |
| AC3.1 Spec schema | `policy.py:129` (`_spec`), `policy.py:150` (`_vetted`) | `test_policy.py::test_bad_specs_fail_closed`, `test_instruction_limit_follows_limits_object`, `test_free_text_never_reaches_the_error`, `test_instruction_too_large_as_stored_is_instruction_invalid` | Met |
| AC3.2 Each limit enforced with a negative test | `policy.py` `check_*` (lines 244-292), `Runner` pool size, `policy.admit` queue cap | `test_policy.py::test_step_index_breach`, `test_step_deadline`, `test_job_deadline`, `test_retries_above_two_cannot_be_built_and_a_third_retry_is_refused`, `test_model_call_and_size_budgets`, `test_queue_cap_rejects_and_writes_nothing`; `test_runner.py::test_concurrency_cap`; `test_delegation.py::test_concurrent_admit_respects_queue_cap` (20 threads, exactly 3 admitted) | Met |
| AC3.3 No paid call reachable, model-call count is the budget | `policy.py` `check_model_call`, `graph.py` `summarize` | `test_policy.py::test_model_call_and_size_budgets`, `test_graph.py::test_model_call_budget_exhausted_mid_plan_fails_before_the_model_is_called` | Met. See Budget below. |
| AC3.4 No limit raised by spec, model, or environment | `policy.py` `CEILING` and `Limits.__post_init__` | `test_policy.py::test_ceiling_is_allowed_and_one_above_is_not`, `test_spec_cannot_claim_locality_or_memory`; `test_delegation.py::test_limits_ignore_environment` | Met |
| AC4.1 Two fixed workers, unknown tool refused before any step | `policy.py` `TASK_TYPES` (answer, summarize), `TOOL_SCOPE` | `test_policy.py::test_scope_tables_cover_exactly_the_task_types`, `test_tools_come_from_the_task_type_only`; `test_graph.py::test_a_plan_with_one_defect_is_rejected_and_nothing_runs` | Partly met. There are exactly two task types. `runner.py:31` (`HERMES_WORKERS`) still defines five workers from PR 55. They are read-only and cut to the task scope, but the count is not two. Open as R-02.F3. |
| AC4.2 Synthetic data, personal data with a cloud planner refused | `policy.py:150` (`_vetted`) | `test_policy.py::test_data_class_truth_table`; `test_delegation.py::test_a_cloud_model_gets_personal_data_cloud_planner_and_nothing_is_written`; `test_runner.py::test_claim_and_run_goes_through_admit` | Met |
| AC4.3 No code, shell, plugin, write, or outbound action reachable | `policy.py` `TOOL_SCOPE`, `delegation.py` `READ_TOOLS` | `test_policy.py::test_no_scope_contains_a_write_tool`; `test_delegation.py::test_no_admitted_tool_can_write_or_reach_network` (every task type, local and cloud, synthetic flags, and every Hermes worker) | Met for the named tools. The Tier 1 app reads (calendar, notes, mail) run `osascript` read scripts and are macOS-only. |
| AC4.4 Bounded inputs and outputs, structured receipt checked by the verifier | `policy.py` `check_step_output`, `graph.py` `_fits`, `_verified` | `test_graph.py::test_tool_output_over_the_size_limit_fails_the_step`, `test_finish_whose_receipt_cannot_fit_fails_the_step_not_the_ledger_write`, `test_verifier_accepts_good_records` | Met |
| AC5.1 Job work on the runner pool, not the event loop | `runner.py` (`ThreadPoolExecutor`, `submit`) | `test_runner.py::test_event_loop_answers_while_a_job_runs`, `test_submit_returns_before_the_work_finishes` | Met |
| AC5.2 delegate returns in under 200 ms | `delegation.py:89` (`delegate`) | `test_delegation.py::test_delegate_returns_under_200ms_while_job_is_gated` | Met: 11.3 ms measured (second run 15.4 ms, first 11.6 ms). The job was held open by a gate. |
| AC5.3 Second voice turn completes, loop lag under 100 ms | same | `test_delegation.py::test_voice_turn_completes_while_job_running`, `test_event_loop_lag_under_100ms_during_job` | Met: max loop gap 32.2 ms over 14 ticks (earlier runs 31.9, 34.3 ms) against a 10 ms ticker. The job is gated about 0.3 s and uses a fake planner, so this is not a measurement against a real model. |
| AC5.4 Failing or hung job does not stall the session, closing keeps the record consistent | `graph.py:55` (`_call`), `runner.py:150` | `test_delegation.py::test_hung_tool_fails_the_step_and_frees_the_job`, `test_close_mid_job_then_recover_marks_unknown`, `test_abandoned_tool_threads_are_capped` | Met for hung tools. A hung planner model call is not covered (Known limits). A late finish can move an `unknown` job to a terminal state (ledger allows it), and the test checks the record stays consistent. |
| R-02.F1 claim_and_run goes through admission | `policy.py:231` (`admit_claimed`), `runner.py:95` (`claim_and_run`), `runner.py:31` (workers) | `test_runner.py::test_claim_and_run_goes_through_admit`, `test_claim_and_run_executes_claimed_job`, `test_hermes_worker_definitions` | Met. A job that fails the checks is failed with `{"executed": false}`. The fake `memory_recall` and `memory_save` names are gone. |
| R-02.F5 Stale-session rejection | see AC2.3 | see AC2.3 | Met |
| R-02.F6 Hung tools cannot stall jobs | `graph.py:50-85` (`_call`, cap of 4 abandoned threads), `tier1.py:394` (`_osascript`, 20 s timeout and kill) | `test_delegation.py::test_hung_tool_fails_the_step_and_frees_the_job`, `test_abandoned_tool_threads_are_capped`, `test_the_cap_counts_abandoned_threads_across_concurrent_calls`, `test_healthy_parallel_reads_are_not_capped`; `test_tier1.py::test_default_runner_timeout_kills` | Met on Windows. The only job-path subprocess is `_osascript`, which times out under the 30 s step deadline and is killed (the test mocks the process, so it does not need macOS). `local_adapter.py:518` is the speech helper and `live_check.py:70,81` is the opt-in live check. Neither is in a job tool path. |

## Measured numbers

Measured 2026-11-20 on Windows 11 with the scripted fake planner and a gate, using `pytest -s`.

| Measure | Result |
| --- | --- |
| `delegate` return time while the job is gated | 11.3 ms (runs: 11.6, 15.4, 11.3) |
| Max event-loop gap during a running job, 10 ms ticker | 32.2 ms over 14 ticks (runs: 31.9, 34.3, 32.2) |

## Budget (AC3.3)

- The model-call count per job is capped at 12 by default (ceiling 100). The plan call counts as one.
- Each model call is limited in input size (8000 characters by default), and each step output in size (4000 characters by default).
- No paid call is reachable through the planner choices that exist today: a scripted fake and the Gemini planner (`gemini_planner.py`), which is cloud and read-only, so admission refuses personal data for it. The local planner is PR #65 and is not merged. The $0 cap is a project decision, not something this code enforces by price.

## R-02.5 real run

Pending: runs after PR #65 (local planner) merges.

## Known limits

- The cap on abandoned tool threads (4) can be filled by a hung macOS network mount inside a Tier 1 root. Tools then refuse with `tool_threads_stuck` until the threads return or the process restarts. This fails closed.
- In-flight tool calls can overshoot the cap by at most the number of calls running at once, because the cap counts only abandoned threads.
- The admit lock is per process (`policy.py:181`). A shared PostgreSQL ledger needs its own cap.
- A planner model call has only the model's own timeout. The thread timeout covers tool calls only.
- `Runner.claim_and_run` and `Runner.recover` act on any queued job, including jobs queued by other workers.
- `Service(model=None)` does not run recovery. Two existing tests require this, and recovery there could fail other workers' jobs.
- HQ jobs from PR 56 will share the global queue cap. This is for R-02.F2.
- When PR 56 merges, `_spec` at `policy.py:129` must become `validate_spec`.
- The thread timeout abandons a stuck thread, it does not kill it. Upgrade to a subprocess worker if the cap is ever hit in practice.

## Not met or open

- AC4.1 exactly two workers: five Hermes definitions remain (R-02.F3).
- AC1.4 across a real process restart: tested in process only.
- The real-model run for R-02.5: pending.
