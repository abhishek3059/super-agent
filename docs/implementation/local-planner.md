# Local Ollama planner

Status: implemented on a work branch, not merged. No roadmap item is ticked. Authority:
[agent backend exception](../approvals/agent-backend-exception.md) (a text model for personal testing
behind a replaceable seam, and a real API test that sends a delegated task through the agent).

## What changed

- `apps/api/src/super_agent_voice/ollama_planner.py`: `OllamaPlanner` implements the `PlannerModel` seam.
  It reuses `local_adapter._chat_request` (JSON mode for plans) and `_refuse_remote_model`.
  `is_local` is True only when `local_model()` and the `/api/show` check both pass; any error gives False,
  so admission refuses personal data. Failures raise `ModelError` with the seam's fixed codes
  (`unavailable`, `timeout`, `malformed`). The reply is untrusted and is still validated by `planner.py`.
  Timeout 60 s, inside a 75 s step deadline (`policy.Limits.step_deadline_s`). The first three runs below used a 25 s timeout inside a 30 s deadline.
- `local_adapter._delegate` builds `delegation.Service(OllamaPlanner())` (still only with
  `SUPER_AGENT_DELEGATE=on`; off by default).
- `graph._plan_prompt` now lists each allowed tool's parameter keys and says to end with `finish`.
  Without that the 4B model invented args (`operation`, `operands`) and omitted `finish`.
- `test_delegation.py`: the "no planner" test now stubs `OllamaPlanner` to `None` to keep its intent.

## How to enable

Run Ollama on loopback, set `SUPER_AGENT_DELEGATE=on`. The model is `SUPER_AGENT_LOCAL_MODEL`
(default `qwen3.5:4b`).

## Offline tests

`apps/api/tests/test_ollama_planner.py`: parsed JSON, malformed and empty replies, transport and timeout
errors, text reply, cloud or unvouched model is not local and personal data is refused, plan then finish
reaches `succeeded`. Full API suite on Windows, 2026-11-20, at the 60 s timeout: 1081 passed, 110 skipped, 0 failed
(shared reviewer run).

## Real run (loopback Ollama, `qwen3.5:4b`, synthetic data, temp ledger)

Task: "What is 17 times 23, and what time is it?" via `Service(OllamaPlanner(), data_class="synthetic")`.

| Run | State | Time | Result |
| --- | --- | --- | --- |
| 1 | succeeded | 31.1 s | steps read_tool, read_tool, summarize, finish; result contained 391 and the date |
| 2 | succeeded | 28.6 s | same steps; result contained 391 and the date |
| 3 | failed | 25.5 s | code `model_error` (the 25 s model timeout) |

Runs 1 to 3 were at the old 25 s timeout (30 s step deadline). The timeout is now 60 s inside a 75 s step deadline, and has not been re-measured.

Before the prompt change, two runs failed (`model_error` timeout, `tool_args_invalid`).

## Limits

- Latency on this machine is 12 to 20 s per model call, so a plan plus summary takes about 30 s and one run in
  three timed out. A faster model or a longer timeout is a decision for a maintainer.
- The summary text was weak (the model treated the tool outputs as a possible injection). The numbers were right.
- Three runs is not a quality measure.
