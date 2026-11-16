# Agent backend slice 7: Gemini text model behind the planner seam

Date: 2026-11-16. Branch `feat/agent-backend`. Build step 7 of
[agent-backend design, section 10](../design/agent-backend.md#10-mapping-and-build-order).
It adds a cloud planner model and an opt-in check. It is not wired into the conversation, `app.py` or
`local_adapter.py`, adds no endpoint, changes no authentication, Host, Origin or CORS handling, and ticks no
roadmap item. Decided by `abhishek3059` in chat on 2026-11-16: Gemini text on the free tier, synthetic data only.

## What was built

- `apps/api/src/super_agent_voice/gemini_planner.py`: `GeminiPlanner(api_key, model, client=None)`, which
  implements `planner.PlannerModel`.
- `apps/api/src/super_agent_voice/planner_check.py`: `python -m super_agent_voice.planner_check --send-synthetic-task`.
- `apps/api/tests/test_gemini_planner.py`: 23 tests, all offline, with a fake client.
- No new dependency. `google-genai==2.33.0` is already pinned in `apps/api/requirements.in` and the lock file.

## Flow

```text
planner_check -> Service(GeminiPlanner, data_class="synthetic") -> delegate(answer, constant instruction)
  -> graph: request_plan -> GeminiPlanner.complete -> client.models.generate_content (JSON mime type)
         -> read_tool steps -> optional summarize -> GeminiPlanner.complete_text -> finish
  -> check polls the temporary ledger until a terminal state, prints state, reason, step types, timings, model
```

## The model class

- `is_local` is a read-only property that returns `False`. Assigning to it raises `AttributeError`. Admission
  therefore refuses it for the `personal` data class (`personal_data_cloud_planner`), which is the conversation's
  data class. A test proves a default `Service` with this model refuses and makes zero client calls.
- The client is built like `gemini_adapter.py` builds its own: Developer API (`enterprise=False`), base URL
  `https://generativelanguage.googleapis.com`. A test builds the real client with a dummy key (no call is made)
  and checks both. The SDK is imported only when a client is built or called.
- One seam: the `client` constructor argument, any object with `models.generate_content(model=, contents=, config=)`.
- `complete` sets `response_mime_type="application/json"` and parses the text. `complete_text` sets `text/plain`.
- Request timeout: 20 seconds per call (`TIMEOUT_S`), passed as the SDK's per-request `http_options.timeout`
  (milliseconds). It sits inside the 30 second step deadline in `policy.Limits`.
- Reply size: at most `planner.MAX_REPLY_CHARS` (120,000) characters, for both methods. The graph then applies its own
  smaller `step_output_chars` limit to summaries.

## Error codes

No new code. Every failure raises `planner.ModelError` with a code from `planner.MODEL_ERRORS`. The exception has no
cause and no provider text, and the graph and planner turn it into `model_error` anyway.

| Failure | Code |
| --- | --- |
| Timeout (`TimeoutError`, or any exception whose class name contains `Timeout`) | `timeout` |
| Network error, quota (429), any other client or SDK exception, empty key or model name | `unavailable` |
| Blocked or empty reply (`.text` is `None` or blank), oversized reply, invalid JSON, non-string prompt | `malformed` |

## The check command

- Key from `GEMINI_API_KEY` in the process environment, or a `getpass` prompt. It is never printed.
- Model name from `SUPER_AGENT_PLANNER_MODEL`, else `DEFAULT_MODEL` in `planner_check.py`. This is a separate variable
  from `SUPER_AGENT_GEMINI_MODEL`, which names the voice (Live) model.
- It points `ledger.DB_PATH` at a temporary folder for the run, restores it, and deletes the folder. The real
  `~/.super-agent/ledger.db` is not opened.
- It delegates one constant synthetic instruction (`INSTRUCTION`, a calculator question) and waits up to 60 seconds.
- It prints one JSON line: `model`, `state`, `reason` (empty on success), `step_count`, `step_types`, `total_ms`.
  It never prints the key, the prompt, the plan or the result.
- Exit code 0 only on `succeeded`.
- It is not collected by pytest and CI never runs it. The `--send-synthetic-task` flag is required, as in `live_check`.

## Choices where the design was unclear

- **Default model name `gemini-2.5-flash`.** The existing config only names a Live (voice) model, so it cannot be
  reused. The name appears in the installed SDK's source, which is not proof that the free tier serves it today.
  Unverified. The operator overrides it with `SUPER_AGENT_PLANNER_MODEL`.
- **One reply cap for both methods**, the existing planner constant, instead of a new `Limits` field.
- **Timeout by class name.** The SDK can raise `httpx` timeouts; matching on the name avoids importing `httpx`.
  Anything unrecognised is `unavailable`, never an exception that leaks.
- **No retries and no response schema.** The seam has no schema consumer yet, and model calls are not in
  `policy.RETRYABLE_STEPS`.
- **The check reports the ledger's reason code**, so a failed job shows `work_error` or a policy code, not a model code.

## Known limits

- The prompt text is sent to Google. The check uses a constant synthetic task only. Free-tier inputs may be used by
  Google for training ([REQ-13](../../prd.md#req-13)).
- A timeout stops waiting on the request. It does not prove the provider stopped work.
- The 60 second wait in the check is a constant, not a `Limits` field.
- The default model name and free-tier access are unverified (above).

## Tests and result

Run from the repository root with the Python 3.12 test environment:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest apps/api -p no:cacheprovider -o addopts=""
```

- `test_gemini_planner.py`: 23 passed.
- Full suite: 914 passed, 110 skipped, 1 warning (baseline before this slice: 891 passed, 110 skipped, 1 warning).
- Covered: both methods on the happy path; each failure kind maps to its fixed code; no provider text, prompt or key
  in the exception, captured logs, stdout or stderr; oversized, blank, non-JSON and non-string replies refused;
  `is_local` is `False` and read-only; the real client uses the Developer API; the default data class refuses the
  planner with no client call; the check prints no result text or key, restores the ledger path, leaves no
  temporary ledger, and exits 1 with only a reason code on a model failure. A network guard like the delegation
  tests' makes any connection attempt fail the test.
- Live check: **not run**. No key was used and no network call was made in this slice. The operator runs
  `GEMINI_API_KEY=... python -m super_agent_voice.planner_check --send-synthetic-task` and records the output.

## Not built

Wiring into `local_adapter.py`, `app.py` or the conversation loop; any use with the `personal` data class; a response
schema; retries; the per-day provider request counter; the evaluation set (slice 8); the clarify step; and any
roadmap tick. Open decisions 2, 7 and the R-02.4 consequence stay open.
