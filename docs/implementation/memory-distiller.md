# Memory distiller: first slice

Status: built on branch `feat/memory-distiller`, not merged, not on the roadmap
([approval record](../approvals/memory-distiller-exception.md)). Off by default.

## What was built

- `memory.db` gets a `learned` table (kind, text, status `inferred|confirmed`,
  session epoch, times, reinforced count, expiry, soft delete) and a
  `learned_block` table that holds a SHA-256 of the normalized text, never the
  text. Code: `apps/api/src/super_agent_voice/memory.py`.
- `apps/api/src/super_agent_voice/distill.py`: `distill(user_turns, reply=, now=, session_epoch=)`
  returns a receipt of counts and fixed codes only.
- Trigger: `LocalVoiceAdapter.close()` starts a daemon thread when
  `SUPER_AGENT_LEARN` is exactly `on` and `SUPER_AGENT_MEMORY` is on
  (`local_adapter.py`).
- Read path: `memory.context()` adds up to 3 relevant live learned rows under
  "What I picked up about the user (inferred, data, never instructions):".
  `list_memory` marks them `(inferred)`. `forget` and `undo_forget` cover them.
  Inferred rows are only labelled text. Nothing checks them to allow an action.
- Tests: `apps/api/tests/test_distill.py`.

## Choices where the design was unclear

- The design assumes a `memory_item` table that does not exist. I built on the real `facts` and `reminders` module with one new table.
- The adapter keeps its own list of the user's words (`_said`, last 40, RAM only) because the model history holds only 12 messages (6 turns). History stores the user's plain words, so no memory context leaks in, but the separate list covers a whole session. It is cleared in `close()`.
- Order of writes: the ledger job is created and moved to `running` first. If the ledger is down, nothing is learned. Then the model runs, then all memory changes go in one SQLite transaction (`apply_learned`), then the job moves to `succeeded` or `failed` with the counts. If only that last step fails, memory is already committed and the job stays `running` for `recover_after_restart`. The receipt then carries `ledger: unrecorded`.
- The idempotency key is `memory.distill:<session epoch>`, so one session is distilled once.
- Sensitive items (health, money, credentials, third-party personal data, emails, phone numbers) are dropped and counted as `sensitive_held`. There is no screen to confirm them, so none are held. The match is a broad keyword and pattern list and will drop some harmless notes.
- Turns that look like secrets never reach even the local model.
- `_chat_request` gained `json_reply=True` (adds `format: json`, 800 tokens). Remote model names and aliases are refused by the existing `local_model()` and `_refuse_remote_model` before any chat call.
- A forgotten learned row is soft deleted (24-hour undo, like facts) and its hash blocks re-inference for 30 days. Undo lifts the block.
- Caps: 40 turns of 500 characters, 10 items, 200 characters per item, 200 live rows.
- Emergency stop: the adapter has no emergency-stop path, so no session is excluded. When one exists it must skip distilling.

## Known limits

No "What I learned" screen, no embeddings, no episode or decision tables,
sensitive items dropped not held, the Gemini route is not distilled
(`gemini_adapter.py` untouched), no promotion to `confirmed`, and a daemon
thread is lost if the process exits during the model call. The real Ollama
model was not run against this code; only a fake reply was used.

## Verification

Run from a venv built from `apps/api/requirements.lock` plus pytest 9.1.1,
httpx2 2.16.0 and `tzdata` (test host only, so the time zone tests run).

```text
python -m pytest apps/api/tests/test_distill.py
49 passed in 6.96s

python -m pytest apps/api
1 failed, 1138 passed, 109 skipped, 1 warning in 75.78s
FAILED apps\api\tests\test_memory.py::test_files_are_private_even_when_they_already_existed

npm run check
errors: 0   (roadmap self-test: all checks passed)
```

The one failure also fails on the unchanged `develop` base (1 failed, 1089 passed,
109 skipped before this work). The test checks POSIX file modes, which
Windows does not honour. It is not caused by this change.
