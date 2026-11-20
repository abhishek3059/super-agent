# R-02.F7: provider-neutral hosted planner

| Field | Value |
| --- | --- |
| Date | 2026-11-21 |
| Branch | `feat/ph02-ledger-evidence` (PR 64) |
| Scope | One OpenAI-compatible planner client behind the planner seam, with offline tests and an opt-in live check. It does not change admission and it is not the R-02.5 run. |

## What changed

- `apps/api/src/super_agent_voice/hosted_planner.py`: `HostedPlanner`, a standard-library client for `POST {base_url}/chat/completions`. Approved hosts only, key from the environment, bounded timeout and retry, fixed error codes.
- `apps/api/src/super_agent_voice/planner_check.py`: new `--hosted` flag. It runs one synthetic task through `HostedPlanner` on a temp ledger and prints UTC time, host, model, state, seconds, ledger transitions and the failure code. `run_check` now also returns the transitions, and takes the instruction as a parameter.
- `apps/api/tests/test_hosted_planner.py`: 28 offline tests with a fake opener and a network guard.
- `roadmap.md`, `scripts/roadmap-ids.txt`: item R-02.F7.

## How to enable

Set these in the process environment. The key itself stays in its own variable and is never printed.

```text
SUPER_AGENT_PLANNER_BASE_URL=https://api.openai.com/v1
SUPER_AGENT_PLANNER_MODEL=<model name>
SUPER_AGENT_PLANNER_KEY_ENV=<NAME of the variable that holds the key>
<that variable>=<the key>
```

Live check (opt-in, never run by tests or CI):

```text
python -m super_agent_voice.planner_check --send-synthetic-task --hosted
```

Only `api.openai.com` and `integrate.api.nvidia.com` are accepted (https, no userinfo, query or fragment). Any other value fails closed with `unavailable`. Personal data is still refused for this planner, because `is_local` is always False.

## Limits and timing

Per attempt 20 s, at most 2 retries (timeout, 429, 5xx only), fixed backoff 1 s then 2 s. Worst case is 63 s, inside the 75 s `step_deadline_s` default. A test asserts this from the constants.

## Results

| Run | Result |
| --- | --- |
| `pytest tests/test_hosted_planner.py` | 28 passed in 3.32s |
| `pytest` (whole API suite) | 1131 passed, 110 skipped, 1 warning in 168.83s |
| Live check | not run: no provider key on this machine on 2026-11-21 |

## Known limits

- Unverified, not checked against a primary source: that `integrate.api.nvidia.com/v1` accepts the OpenAI chat-completions shape and `response_format: json_object`, and which models on either provider honour `response_format`. The first live run answers this.
- Unverified: current OpenAI and NVIDIA terms, retention and free-tier training rules for the planner prompts. The two hosts are approved in DEC-24 (PR #72, not yet merged; this PR should merge after #72). The provider record must exist before any real run.
- The response read is capped at about 4 bytes per allowed character; a larger body is cut and then fails as `malformed`.
- Retry covers 429 and 5xx. The `Retry-After` header is ignored.
- Wiring: the local route is retired by maintainer direction, but `local_adapter._service()` still builds `Service(OllamaPlanner())` as the only wired delegate path. `HostedPlanner` is used only by `planner_check --hosted` until a cloud orchestrator exists (R-M.20, PR #72). The documented local failure modes (the `response.close()` loop block and the shared-Ollama timeout) remain in that code.
- Redirects are refused (a 3xx is `unavailable`), so the key cannot be resent to another host. Only port 443 is accepted.
- The R-02.5 hosted run is not done. R-02.5 stays unticked.
