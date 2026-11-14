# Voice streaming backend slice: real command output

Backend-only record for the signed local slice PH-01. Earlier implementation
passes used the free developer profile; the parent continued the final source
and integration-test fixes. No claim is made that the parent model was
unavailable. Frontend and dependency files were not changed by this correction.

## Current correction

The [teardown addendum](../design/voice-streaming-teardown.md) revision 2
supersedes the earlier shield-loop implementation described below.

- Worker, close, and final-wire waits use one monotonic handler deadline.
  An expired presence wait does not wait indefinitely for cancellation.
- Gate release requires actual worker quiescence and a successful close
  result, not merely a settled close call. Unresolved cleanup retains the slot.
- A single strongly owned supervisor reconciles residual tasks. It never
  overlaps close attempts; one failed close permits at most one idempotent
  retry. Permanent failure retains the slot for operator recovery.
- Final wire operations are serialized and stop when one remains pending.
  An undelivered operation is not claimed as sent. A residual wire task may
  outlive the handler even after adapter closure has been confirmed.
- A supervisor starts its deferred wire budget after reconciliation, not
  while the handler's cleanup still uses its original deadline. Completed
  supervisors are removed from the app's ownership list, with outcomes
  retrieved.
- The control-overflow integration test now uses a synchronous producer
  burst after authentication. Sending 33 controls from another thread did
  not guarantee overflow because the sender could drain them between sends.

Parent command:

```text
& $voicePython -m pytest apps/api/tests/test_voice_api.py -q --tb=short
..............................................                           [100%]
```

Exit 0. The teardown unit file has since returned with eight reported passing
cases. The parent ran the combined suite on 2026-11-11: **66 passed in 3.96s**,
exit 0. The [saved output](evidence/voice-streaming-backend-2026-11-11.txt)
covers 12 existing stream unit cases, 8 new teardown cases, and 46 API cases.
The [consolidated final code review](../reviews/voice-streaming-backend.md)
returned PASS on 2026-11-11, average 8.52, with no confirmed blocker or major
finding. The reviewer independently reran all 66 cases successfully. Its three
non-blocking observations are logged separately, not additional scope.
Handler wait bounds do not mean resource lifetime is bounded: a never-settling
worker or close call can keep the slot retained until operator restart.
Future native-provider termination is not established by the fake contract.

The test developer's observation about cleanup resuming just after the
handler deadline is recorded in the [uncertainty log](../reviews/voice-streaming-uncertain-findings.md).
Terminal assertions await the owning supervisor. No additional scheduling
fix is claimed or needed solely because a bounded handler returns first.

## Historical first correction

The sections below record the earlier 46-test snapshot. Their implementation
description is superseded by the current correction, not current acceptance.

## Environment

- Python: `3.14.4` at `LOCALAPPDATA\Temp\super-agent-voice-venv\Scripts\python.exe`
- pytest: `9.1.1`, plugins: anyio-4.15.1
- Windows; no commits, no staging, no push (working tree left dirty)

## Baseline (before fixes)

`python -m pytest apps/api -v` reported 1 failed, 44 passed, 2 errors after the
first restructuring pass; the four originally failing cases were reproduced
individually with `-vv` first:

```
apps\api\tests\test_voice_api.py::test_only_one_active_session_is_allowed FAILED
apps\api\tests\test_voice_api.py::test_auth_timeout_reports_session_timeout_and_releases_gate FAILED
apps\api\tests\test_voice_api.py::test_muted_audio_is_not_sent_to_adapter PASSED
apps\api\tests\test_voice_api.py::test_invalid_control_and_oversized_audio_fail_closed FAILED
```

## Root causes (with evidence)

1. **Product bug (cancellation safety, contract CT-03/CT-04/CT-05).** An
   external cancel (the TestClient portal's cancel scope; also a real server
   shutdown) landed inside the unshielded teardown awaits in
   `apps/api/src/super_agent_voice/app.py`. `CancelledError` escaped the
   `finally`, skipping `gate.release()` and `adapter.close()`. Traced directly:

   ```
   >>> voice_socket CANCELLED: args=("Cancelled via cancel scope ... by <Task pending name='anyio.from_thread.BlockingPortal._call_func' ...>",)
       at app.py:256 _voice_socket
   >>> first client context exited
   >>> (follow-up connection denied: gate still held)
   ```

2. **Test-structure bug.** Three follow-up `connect(client)` calls ran after
   `with make_client()` had exited (closed portal), so any server-side fault
   surfaced as `CancelledError` from `fut.result()`. They now stay inside the
   open client context and synchronize on the server close sequence
   (stop -> `stopping` -> close frame).
3. **Receive-ordering bug in tests.** The oversized-audio branch sends the
   redacted `session.error` (invalid-audio) before closing with 1009; the test
   must consume the error before asserting the close code.
4. **Windows/pytest env-var limit.** The 65 KB parametrized auth message
   overflowed the 32767-char `PYTEST_CURRENT_TEST` env value:
   `ValueError: the environment variable is longer than 32767 characters`
   at setup/teardown. Fixed by giving that param a short id (`oversized-text`).
5. **Shared closed adapter.** `test_abrupt_disconnect_completes_cleanup_and_releases_gate`
   reused one adapter instance across two sessions, so the second session
   correctly failed with `provider-unavailable`. The test now uses a factory
   that hands out fresh adapters and asserts the first instance is closed.

## Changes

- `apps/api/src/super_agent_voice/app.py`: teardown now runs as a cleanup task
  awaited through a shield loop; external cancellation cannot skip
  `gate.release()`, `adapter.close()`, the final error/state message, or the
  close frame. Cleanup failure never overwrites the original failure category
  (CT-03 unchanged; no second-1013 invariant weakened: 1013 remains the slot
  response before authentication).
- `apps/api/src/super_agent_voice/config.py`: explicit bounded
  `auth_timeout_seconds: float = 5` (CT-04); auth deadline is
  `min(total deadline, auth deadline)`.
- `apps/api/tests/test_voice_api.py`:
  - `test_only_one_active_session_is_allowed`: synchronizes on the server
    close sequence; follow-up reconnect stays inside the client context.
  - `test_auth_timeout_reports_session_timeout_and_releases_gate`,
    `test_total_budget_expiring_during_auth_reports_max_duration`,
    `test_close_failure_keeps_original_category_and_releases_gate`: same
    structure change; the CT-03 test uses a fresh-adapter follow-up.
  - `test_invalid_control_and_oversized_audio_fail_closed`: consumes the
    invalid-audio error before asserting the 1009 close.
  - `make_client` accepts a `factory`; added coverage:
    adapter-never-created count after bad Host/Origin/token
    (`test_adapter_never_created_without_valid_auth`), invalid auth shapes
    (`test_invalid_auth_messages_fail_before_adapter`, parametrized, with the
    oversized param given a short id), total-budget expiring during adapter
    start (`test_total_budget_expiring_during_adapter_start_reports_max_duration`),
    and the cancellation regression
    (`test_abrupt_disconnect_completes_cleanup_and_releases_gate`).
- `apps/api/tests/test_stream_units.py`: unchanged this pass; 12 unit tests
  for the queue/receiver/close behavior (CT-01 barrier, CT-02 drop-oldest,
  mute/clear_playback, adapter lifecycle).

## Earlier runs (real output, before the teardown addendum)

```
python -m pytest apps/api -v
apps\api\tests\test_stream_units.py ............                         [ 26%]
apps\api\tests\test_voice_api.py ..................................      [100%]
============================= 46 passed in 2.59s ==============================
```

Repeat run (`-q`): `46 passed` (all dots, second consecutive green run).

The four originally failing tests individually with `-vv`:

```
apps\api\tests\test_voice_api.py::test_only_one_active_session_is_allowed PASSED
apps\api\tests\test_voice_api.py::test_auth_timeout_reports_session_timeout_and_releases_gate PASSED
apps\api\tests\test_voice_api.py::test_muted_audio_is_not_sent_to_adapter PASSED
apps\api\tests\test_voice_api.py::test_invalid_control_and_oversized_audio_fail_closed PASSED
============================== 4 passed in 1.16s ==============================
```

## Not done

- No commits, staging, or push; no dependency changes; no secrets, keys,
  provider reads, or network calls.
- Frontend (owned by another developer), `angular.json`, governance docs,
  CI/workflow files, and the parent summary doc untouched.
- Roadmap not ticked: evidence here is real output, not a merged PR; ticking
  stays with the parent per the roadmap protocol.
