# Voice streaming teardown: bounded shutdown and honest cancellation limits

| Field | Value |
| --- | --- |
| Date / revision | 2026-11-10 / 2 |
| Document | Narrow technical addendum to the signed streaming contract. Supersedes revision 1 of this file. |
| Author | Solution Architect subagent (GLM-5.3-Flash Free, zero-cost fallback). |
| Extends | [voice-streaming-slice.md](voice-streaming-slice.md) (CT terms) and [voice-foundation.md](voice-foundation.md) section 4 backend rules. Slice-contract alignment blocks were amended per section 8 below. |
| Phase context | PH-01 open work bundle (PR #24); fake adapter only; no provider, key, dependency, personal-cloud path, roadmap tick, or approval claim. Parent-reported backend 46 PASS and reviewer PASS with quality avg 8.2 are inputs, not facts re-verified here; this addendum is the concrete revision scope for the 8.2 gap. |
| What this is not | NOT maintainer approval. NOT an independent security PASS. NOT a runtime or provider gate. Quarantine is a specified failure state, not a capability. No plugin/SDK future design. |
| Scope | Teardown path only: `_finish`, the shield wait, adapter close bounding, gate release order, final wire ops, one residual supervisor. Auth-before-factory, mute handling, epoch tracking, queue bounds stay unchanged. Read-only source review; no source or test edits by this agent. |

## 1. Facts as inspected

Teardown-relevant code in [app.py](../../apps/api/src/super_agent_voice/app.py):

- `finally` creates one `_finish` task, then loops `await asyncio.shield(finish)`
  catching `CancelledError` and re-entering the wait until `_finish` is done
  ([app.py:288-296](../../apps/api/src/super_agent_voice/app.py)). The loop has no
  deadline: that re-entry loop is unbounded, not shielding itself.
- `_finish` cancels the four workers and awaits `asyncio.gather(*tasks,
  return_exceptions=True)` with no timeout ([app.py:261-263](../../apps/api/src/super_agent_voice/app.py)).
- `asyncio.wait_for(adapter.close(), timeout=2)` bounds the close
  ([app.py:264-267](../../apps/api/src/super_agent_voice/app.py)); `gate.release()` follows in the inner
  `finally` ([app.py:272-273](../../apps/api/src/super_agent_voice/app.py)).
- Final wire ops run after release, each an unbounded await
  ([app.py:276-286](../../apps/api/src/super_agent_voice/app.py)).
- CT-04 `auth_timeout_seconds` ([config.py:19-22](../../apps/api/src/super_agent_voice/config.py)), CT-01
  post-await recheck ([app.py:384-389](../../apps/api/src/super_agent_voice/app.py)), CT-05 pre-auth gate
  note ([app.py:171-180](../../apps/api/src/super_agent_voice/app.py)), and CT-09
  category preservation ([app.py:268-271](../../apps/api/src/super_agent_voice/app.py)) exist as designed.

## 2. Primitive semantics (primary-verified)

From the official Python 3.12.16 docs
(<https://docs.python.org/3.12/library/asyncio-task.html>, page updated
2026-10-26, fetched 2026-11-10 by this agent):

- `wait(aws, timeout=T)`: under-specified tasks "aren't done when the timeout
  occurs... simply returned in the second set", and "wait() does not cancel
  the futures when a timeout occurs". This presence wait is the only
  stdlib primitive that returns on time regardless of a cancellation-
  suppressing task in the awaited set.
- `wait_for(aw, timeout=T)`: "will wait until the future is actually
  cancelled, so the total wait time may exceed the timeout". Not a hard
  bound when the inner coroutine suppresses cancellation.
- `shield(aw)`: protects the inner awaitable from the caller's
  cancellation; the caller still receives `CancelledError` at its own await.
  Bounded shielding with a deadline is therefore implementable and real.
- Task bookkeeping: keep a strong reference to created tasks (the loop keeps
  only weak references); retrieve a finished task's exception through
  `result()`/`exception()`; `Task.cancel()` suppression requires `uncancel()`
  in the suppressor, which is out-of-scope user code this backend will not
  write: our fault-injection stubs emulate suppression with `shield` inside
  the stub, not with `uncancel`.

## 3. Design inputs (marked by source of truth)

- Parent-reported probes (actual runs against the current structure;
  NOT re-verified here): worker suppressing `CancelledError` wedges the
  unbounded gather ([app.py:263](../../apps/api/src/super_agent_voice/app.py)), so close
  ([app.py:264-267](../../apps/api/src/super_agent_voice/app.py)), release
  ([app.py:272-273](../../apps/api/src/super_agent_voice/app.py)), and the shield loop never reach
  quiescence; a blocked final wire `send` extends the handler boundlessly
  after the gate was already released.
- Parent-reported observation: during teardown, TestClient delivered
  repeated external cancels (five deliveries observed in one teardown).
- Design scenario (defined by this addendum for tests; NOT a recorded
  backend review observation): a scripted adapter whose `close()` blocks
  (event-driven) or settles with an exception, used to exercise the bounded
  close path deterministically.

## 4. Minimal correct design (Option A, revision 2)

Shared monotonic teardown deadline; each step is a presence wait; the
adapter close is independently bounded and *verified*, not assumed; the
session gate is released only after confirmed quiescence and confirmed
closure; final wire ops are bounded and stop-on-pending; anything still
unquiesced transfers atomically to one trusted residual supervisor.

### 4.1 Config field and validity

Add one field; test-injected values are expected; no env, no CLI:

```python
# config.py
teardown_seconds: float = 2.0
```

`create_app` validates explicitly and fails closed: the value must be
a real number, not `bool` (explicit `isinstance(v, bool)` rejection since
`bool` subclasses `int`), be finite (`math.isfinite(float(v))`,
rejecting NaN and infinities), and be strictly positive. There is no
arbitrary loop-budget waiver; every wait loop below derives its budget
from the one shared deadline:

```python
teardown_deadline = loop.time() + settings.teardown_seconds

def remaining() -> float:
    return max(0.0, teardown_deadline - loop.time())
```

No step resets or extends it: one blocked worker, one blocked close, and
one blocked wire op share a single `teardown_seconds` budget, not three.

### 4.2 Worker quiescence replaces the unbounded gather

Cancel the four workers, then one presence wait:

```python
for task in tasks:
    task.cancel()
done, pending = await asyncio.wait(tasks, timeout=remaining())
```

Exactly once, re-request cancellation on whatever remains in `pending`
(a nudge, not cleanup; no loop) and record `workers_quiesced = not pending`.

### 4.3 Close attempt: one task, two distinct verdicts

Start exactly one close attempt as a task. Two verdicts, never conflated:

- **`close_settled`**: the close task finished — including by raising or
  by cancellation. This proves only that *no close call is pending*; it
  does not prove that adapter or provider authority is released. A
  cancelled close task can still be waiting on suppression; a raised one
  may have failed mid-way.
- **`close_confirmed`**: the close attempt completed without an exception
  (`result()` returned normally). Only `close_confirmed` supports the
  claim that the adapter closed, within the fake-only scope.

```python
close_task = asyncio.create_task(adapter.close())
close_done, close_pending = await asyncio.wait([close_task], timeout=remaining())
```

If `close_pending`: issue one explicit `close_task.cancel()` (no wait for
its suppression) and leave the verdict "not settled". If the task settled
with an exception, retrieve and retain the exception through
`result()`/`exception()` — never leave it unretrieved — and record
`close_confirmed = False`. The old `wait_for(..., timeout=2)`
([app.py:266](../../apps/api/src/super_agent_voice/app.py)) is removed.

### 4.4 Gate release: quiescence plus confirmed closure only

Release is exactly-once per session, guarded by a per-session boolean so
no path can double-release, and it happens only when:

- `workers_quiesced` is true, AND
- `close_confirmed` is true.

A settled-but-exceptional close (or an unsettled one) retains the gate in
the quarantine branch (4.6). This is an explicit design amendment to
CT-03: the earlier behavior "raising close still releases the gate" is
superseded. Under fake-only scope this conservatively holds the slot for a
session whose cleanup could not be observed to succeed, pending at most
one idempotent retry (4.7). The category-preservation rule of CT-09
([app.py:268-271](../../apps/api/src/super_agent_voice/app.py)) is unchanged and
not weakened by this amendment.

### 4.5 Final wire ops: bounded, serialized, stop-on-pending

Invariants, replacing the earlier "no sub-tasks" wording:

- At most one pending wire operation exists at any stage, anywhere
  (handler pass or supervisor pass). A wire op may run in a task because a
  task is required for boundedness; the invariant is *no unbounded retry
  fan-out and no overlapping sends on one socket*, not "no tasks".
- Wire ops run only after the serialized sender has truly ended
  ([app.py:274-275](../../apps/api/src/super_agent_voice/app.py): quiescence already implies
  this) and never inside a half-sent audio pair.
- Each wire op is presence-bounded with `remaining()`. If a wire op does
  not finish in its remaining budget: cancel it once, record
  *undelivered* (never claimed sent), and **stop the whole wire sequence**:
  the next close/error op may not interleave with a pending
  cancel-resistant send on the same WebSocket. No further wire op is
  issued while that op task is pending anywhere.
- A timed-out wire task is owned by a strong reference; its exception is
  retrieved when it settles (supervisor duty, 4.7). If workers are
  quiesced and the close is confirmed, the gate may be released even while
  a wire op is still pending: the pending task owns only the one dead
  connection, not adapter/provider authority. That leftover connection
  lifetime is a disclosed residual (section 9), not a bound claim.
- The failure category never changes because of teardown outcomes.

### 4.6 Quarantine branch (fail closed, no invented claims)

Enter quarantine when, at or before the shared deadline: `pending` was
non-empty, or `close_confirmed` is false (unsettled close, or settled with
an exception or cancellation). Then:

- The gate is NOT released; with `max_active_sessions == 1`
  ([config.py:16](../../apps/api/src/super_agent_voice/config.py)), a second
  connection is refused with 1013 while old resources live.
- No further wire ops in this teardown block. Nothing about adapter,
  provider, or worker state is claimed to the client: never claim stopped
  or provider-session-ended when unknown. An already-set fixed category
  stays recorded in memory only and is delivered only at the point the
  supervisor can prove sender quiescence (4.7 step 3), if ever.
- The session handler returns promptly; ownership of the remainder
  transfers to the single residual supervisor (4.7).

### 4.7 One trusted residual supervisor (ownership transfer, no fan-out)

One supervisor task per session, created at most once, held by a strong
reference owned by the `create_app` scope. It absorbs ownership of, at
most: the four workers (only those still pending), the one close task
(never starting a second while the first is pending), any timed-out wire
task, and (4.8) an abandoned in-flight teardown task. Fixed sequence:

1. Wait unbounded-but-trusted for worker quiescence (one additional
   `cancel()` nudge after a fixed grace interval, no periodic loop, no
   exponential backoff; every wait iteration has an await point, so no
   busy loop).
2. **Never start a second `adapter.close()` while an earlier close task is
   still pending.** First wait — unbounded-but-trusted — for the original
   close attempt to actually settle and for workers to quiesce. Retry at
   most once, and only if the original attempt settled as cancelled or
   raised, and only because the adapter close contract is idempotent
   (fake adapter today; to be re-declared per adapter when R-01.7 builds
   real ones). A retry that also fails is terminal: the gate stays held;
   no automatic success is recorded anywhere.
3. Only after workers quiesced AND `close_confirmed`: release the gate
   exactly once (4.4 same guard), then run the deferred final wire ops
   under 4.5's rules (bounded, serialized, stop-on-pending), then one
   bounded socket close attempt.

Every task the supervisor owns is strong-referenced; every finished
task's exception is retrieved; nothing is left as an unhandled future.
Its unbounded waits are the honest exception to wait-side bounds
(Appendix A).

### 4.8 Protected bounded teardown (bounded shield waiter + ownership transfer)

Revision 1 told the developer to remove all shielding; that was wrong and
would reintroduce a just-fixed accepted TestClient bug: repeated external
cancels (five deliveries observed by the parent during teardown) must not
truncate cleanup, and the original `CancelledError` must still be raised
after cleanup. What was wrong in the current code is only that the shield
loop has no deadline and no ownership end-state. Required pattern;
equivalent implementations are acceptable if these invariants hold:

- The teardown coroutine runs in **one dedicated task** created inside the
  handler's `finally`, strong-referenced for as long as anyone waits on
  it. External cancels of the handler interrupt the *waiter*, never this
  task (documented `shield` semantics, section 2).
- The handler waits in a loop of presence waits:

  ```python
  while not cleanup_task.done():
      try:
          await asyncio.wait([cleanup_task], timeout=remaining())
      except asyncio.CancelledError:
          continue   # record the delivery; budget keeps shrinking
  ```

  The loop's total wall clock cannot exceed the shared deadline because
  every iteration budgets from `remaining()` — unbounded shielding is
  impossible here by construction: bounded shielding with an ownership
  end-state is required and achievable.
- Cancellation deliveries are recorded (counted in a test-visible
  counter); each delivery interrupts only the waiter; no iteration resets
  the deadline; no per-delivery task is spawned; no iteration lacks an
  await point (no busy loop).
- Exit branches:
  - Cleanup done within the deadline: the handler completes its bounded
    wait, then re-raises the **first** captured outer `CancelledError`
    (bare `raise` after the bounded wait; later duplicate deliveries do
    not replace the preserved signal). No fabricated error, no category
    override, no "always error" decision: cancellation after successful
    bounded cleanup stays the original signal, not a `session-failed`.
  - Shared deadline expired with cleanup still running: **atomic
    ownership transfer**: the handler deposits `cleanup_task` into the
    one supervisor (created here if no quarantine supervisor exists yet;
    never a per-delivery or per-retry task), which then owns its true
    completion and exception retrieval under 4.7's rules. The handler
    re-raises the captured original `CancelledError`. The gate is never
    released by the handler in this branch; only the supervisor may
    release, and only under 4.4's conditions.
- "Bounded" means the *waiter* and the handler bound. The in-flight
  teardown task's own lifetime is **owned, not bounded**; claiming it is
  bounded would be the false bound this addendum forbids.
- A second external cancel during cleanup does NOT "truncate teardown":
  the cleanup task keeps running under its new owner; only the waiter is
  interrupted. What remains honestly bounded is the handler; what remains
  honestly unbounded is the owned residual, disclosed in section 9.
- The existing `test_abrupt_disconnect_completes_cleanup_and_releases_gate`
  ([test_voice_api.py:304](../../apps/api/tests/test_voice_api.py)) must keep passing
  unchanged in intent.

## 5. Alternative considered and rejected

**Option B: rely only on a trusted adapter cancellation contract; treat
uncooperative adapters/workers as out of scope; leave `gather` and the
deadline-less shield loop as is.** Rejected as the primary mechanism: the
parent prefers code deadlines for actually blocked wire ops, and the
bounded waiter shows the deadline-less loop was never necessary. The
trusted cancellation contract stays only as a layered assumption to be
re-declared per real adapter under R-01.7, never the mechanism here.

## 6. Corrections to implement (ordered; the green suite must stay green)

1. `config.py`: add `teardown_seconds: float = 2.0`; validate finite,
   positive, non-bool at `create_app` construction, failing closed like
   token validation ([config.py:26-28](../../apps/api/src/super_agent_voice/config.py)); no env, no CLI.
2. `app.py`: extract one `_teardown(...)` helper implementing 4.2, 4.3,
   4.5, 4.6; the handler's `finally` runs the protected bounded waiter
   (4.8) around it, replacing `_finish` and its deadline-less loop
   ([app.py:255-296](../../apps/api/src/super_agent_voice/app.py)).
3. Replace the no-timeout gather ([app.py:263](../../apps/api/src/super_agent_voice/app.py))
   with the presence wait; remove `wait_for(adapter.close(), timeout=2)`
   ([app.py:266](../../apps/api/src/super_agent_voice/app.py)) in favor of 4.3 with the
   two-verdict recording.
4. Gate release moves to the quiescence + confirmed-closure branch (4.4,
   amended CT-03); release is guarded exactly-once.
5. Final wire ops: bounded, serialized, stop-on-pending, undelivered
   markers, strong ownership and exception retrieval (4.5).
6. The one supervisor: ownership transfer target for unsettled closes,
   timed-out wire ops, and abandoned teardown tasks (4.7); one close retry
   max, only after the original settles.
7. Cancellation semantics per 4.8: bounded presence-wait waiter,
   delivery counter, preserved first-cancel signal, deadline-based
   ownership transfer, no per-delivery tasks, no busy loop.

No correction adds a client-visible message type or field, and none
mutates auth-before-factory, mute handling, epoch tracking, or queue
bounds.

## 7. Test matrix (synthetic, stdlib asyncio only)

Deterministic stubs use `asyncio.Event`; injected short
`teardown_seconds` via test `VoiceConfig`; monotonic assertions
(`loop.time()` deltas with a documented epsilon); no sleeps where an
`Event` can drive determinism (a short sleep only when unavoidable, with
the reason in the test docstring). Mechanical cancellation suppression in
stubs is emulated with `shield` inside the stub, never by hand-written
catch-and-`uncancel` suppressor paths. Existing 46-test suite expectations
that this matrix supersedes are listed after the rows.

| # | Working test name | Focus |
| --- | --- | --- |
| T-1 | `test_empty_audio_chunk_fails_closed_and_releases_gate` | Review gap: scripted adapter yields `AudioChunk(data=b"", rate_hz=16000)`. The session fails closed with the fixed redacted `invalid-audio` category ([app.py:354-360](../../apps/api/src/super_agent_voice/app.py)), no fabricated `turn.complete`, teardown quiesces, gate released exactly once. The zero-yield events-end variant raising `provider-session-ended` ([app.py:373](../../apps/api/src/super_agent_voice/app.py)) is already covered by the existing invalid-output tests and is NOT re-tested here. |
| T-2 | `test_hanging_close_is_bounded_and_gate_released_only_at_confirmed_close` | `close()` awaits an `asyncio.Event` inside a shield (suppression scenario, section 3): handler returns within `teardown_seconds` without releasing the gate; second connection refused 1013; when the test releases the event, the close task settles normally, the supervisor observes `close_confirmed`, releases once, and the slot becomes available; original redacted category preserved throughout; no provider-end claim invented. |
| T-3 | `test_close_raises_once_idempotent_retry_succeeds_and_releases_gate` | `close()` raises on the first attempt and succeeds on a second (idempotent contract): the handler settles the attempt with an exception, enters quarantine, the supervisor waits for workers AND the settled attempt, retries exactly once, observes `close_confirmed`, releases the gate once, and delivers deferred bounded wire ops. The original fixed failure category is preserved (never invented or overwritten). Supersedes the old expectation that a raising close releases the gate on the first failed close. |
| T-4 | `test_permanent_close_failure_holds_gate` | `close()` raises every time (two attempts settle exceptionally, then the supervisor stops): the gate stays retained (fail closed; the session stays quarantined and refuses 1013); the supervisor's at-most-one-retry rule caps this at two exceptional settlements total; no claim of adapter closure is made; no automatic success path exists. |
| T-5 | `test_session_control_overflow_teardown_bounded_and_gate_released` | Controls beyond `max_controls` raise `_SessionFailure("session-failed")` ([app.py:92-93](../../apps/api/src/super_agent_voice/app.py)): teardown quiesces quickly, the gate is released exactly once on quiescence, and no final wire op runs before the sender has truly ended. |
| T-6 | `test_worker_suppressing_cancel_quarantines_and_holds_gate` | A worker shields its cancellation (stub: `shield` inside the stub; documented `uncancel` caveat not needed because no `TaskGroup`-like machinery is in teardown): handler returns bounded; gate retained; no worker/adapter state claimed over the wire; after the test event releases, the supervisor quiesces the close and releases. Pins "quarantine is fail-closed, not wedged-silent". |
| T-7 | `test_blocked_final_wire_op_is_bounded_and_stops_sequence` | Stub WebSocket whose `send_json` for the final error blocks forever: workers and close quiesce; the wire op is presence-bounded, marked undelivered, the wire sequence STOPS (no socket close attempt while a wire send is pending), gate releases because adapter/workers are done; residual wire task strong-referenced with its exception retrieved when the test ends it. |
| T-8 | `test_shutdown_cancel_propagates_original_after_bounded_cleanup` | One external `cancel()` mid-teardown with cooperative workers: the original `CancelledError` is re-raised after the bounded waiter completes (gate released, `close_confirmed` verified); no shield-loop swallow; no fabricated replacement error. |
| T-9 | `test_teardown_shared_deadline_bounds_total_not_per_await` | Worker suppression plus close suppression back to back (each a short simulated stall): total handler wait stays near `teardown_seconds`, not the sum of step budgets; each step budgets from `remaining()`. |
| T-10 | `test_no_final_status_inside_audio_pair_when_quarantined` | Sender stuck mid audio metadata/binary pair (stub send barrier) at teardown: quarantine branch fires; no final status or error interleaves into a half-written pair; pair invariant pinned by the existing `_send`-test assertion set. |
| T-11 | `test_supervisor_ownership_and_no_overlapping_close` | Instrumented task creation/count across a hanging-close and a raising-close case: exactly one supervisor; **no second `adapter.close()` is ever invoked while the first attempt is pending** (the old `wait_for` at [app.py:266](../../apps/api/src/super_agent_voice/app.py) is removed; the retry rule is 4.7's); at most one close retry after settled-raise or settled-cancel; every owned task strong-referenced with exceptions retrieved; no per-retry or per-delivery task spawning. |
| T-12 | `test_teardown_config_validity` | `teardown_seconds` of `0`, negative, `float("nan")`, `float("inf")`, `True`/`False`, and non-numeric all fail closed at `create_app` with the explicit config-error style; `2.0` and injected short values pass. |
| T-13 | `test_repeated_external_cancel_during_teardown_preserves_signal` | Deterministic: while cleanup is in flight (an `Event`-gated close with cooperative workers), deliver five external `cancel()`s to the handler (parent-observed shape; `Events`, not sleeps). Each delivery interrupts only the waiter; cleanup completes; `workers_quiesced and close_confirmed` hold; gate released exactly once; the handler re-raises the FIRST captured `CancelledError` after the bounded wait; an injected second-kind deliverable (error category override) never appears. |

Superseded expectations (explicit, not silently weakened):

- The old `test_close_failure_keeps_original_category_and_releases_gate`
  family released the gate even when the close settled with an exception;
  under the amended CT-03, T-3 and T-4 replace its gate expectations
  (release after a confirmed closure from the idempotent retry; hold on
  permanent failure). Its category-preservation assertion is retained
  verbatim in both new tests.
- The zero-yield events-end expectation remains `provider-session-ended`
  and stays in the existing suite; T-1 targets the empty-`AudioChunk`
  `invalid-audio` review gap instead.

## 8. Amendments required to the signed slice contract

Two alignment blocks, both already present in the rev-3 slice contract;
revision 4 of that contract tightens their wording (no other terms):

1. **CT-03 amendment (mandatory).** Updated wording: cleanup is always
   attempted, presence-bounded, and release is exactly-once, gated on
   worker quiescence AND `close_confirmed` (close finished without
   exception); a settled-with-exception close retains the slot pending at
   most one idempotent retry by the single supervisor; a permanently
   failing close holds the gate (4.3/4.4/4.7). The old raising-close
   gate-release expectation is superseded per T-3/T-4, with category
   preservation and the bounded cleanup attempt unchanged.
2. **CT-05 acceptance-table note.** *Superseded 2026-11-12 (R-01.6): authentication now precedes the slot.* Kept as-is at the time: pre-auth single-slot
   placement is accepted intent, bounded by the auth deadline inside the
   total budget ([app.py:171-180](../../apps/api/src/super_agent_voice/app.py)).

## 9. Limitations, stated without hedging

- **What is designed, not yet claimed passed.** All bounds here are
  designed and test-required. Nothing in this addendum asserts that the
  new tests run or pass; "proven" is claimed only for the documented
  primitive semantics in section 2.
- Handler time is bounded by presence waits. Resource lifetime is NOT
  bounded in-process: a worker or close attempt that never settles keeps
  the gate held (4.7). A process restart is the operator recovery.
- A timed-out-but-cancel-resistant wire op leaves one pending task on a
  dead connection: gate release is allowed (no adapter/provider authority
  pending, connection lifetime residual disclosed locally), and the next
  close attempt on that WebSocket may thereby be blocked. No auto error;
  fixed undelivered marker only.
- The supervisor's waits are trusted-residual and unbounded by design
  (ownership, not a correction of asyncio's limits); they do not loop
  retries with fresh deadlines and spawn nothing per attempt.
- The raising-close release expectation change is a **design amendment**,
  not a continuation of the old test: the slice contract's rev-4 block
  records this, and the 46-test expectations that disagree are superseded
  there, with category preservation carried over.
- Parent-reported backend numbers (46 PASS, review PASS, avg 8.2) are
  inputs, not re-verified by this agent.

## 10. Documentation impact on landing

- `app.py` teardown ordering notes (4.2-4.8); `config.py` comment for the
  new field and its validity rule.
- `voice-streaming-slice.md` rev 4 blocks as in section 8.
- No roadmap tick, no phase-gate move, no `roadmap-ids.txt` change is
  required or allowed by this addendum.

## Appendix A. Terms used precisely

- **Presence wait**: `asyncio.wait(fs, timeout=T)` returning `(done,
  pending)` at `T`; on-time regardless of suppression (section 2).
- **`workers_quiesced`**: after the bounded wait, `pending` was empty.
- **`close_settled` / `close_confirmed`**: settled = the close task
  finished, by return, raise, or cancel — no pending close call anywhere;
  confirmed = settled normally, which is the only gate-release-supporting
  verdict. Never merge these two.
- **Quarantine**: the gate retained after failed quiescence or
  unconfirmed closure; new sessions refused 1013; verdict never claimed
  over the wire.
- **Undelivered**: a wire op that missed its budget; cancelled once;
  sequence stops; never claimed as sent; exception retrieved when it
  settles.
- **Ownership transfer**: atomic, one-owner-at-a-time handover of an
  in-flight task from the handler's bounded waiter to the supervisor;
  exactly once per task; the previous owner never touches it afterward.
- **wait-side**: the handler-visible teardown wait chain, in total
  bounded by `teardown_seconds`; the supervisor's owned waits are the
  single documented exception, disclosed and unbounded by design.
