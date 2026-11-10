# Bounded teardown and focused review

| Field | Value |
| --- | --- |
| Date | 2026-11-11 |
| Evidence | [Backend output](../implementation/voice-streaming-backend-output.md), [66-test run](../implementation/evidence/voice-streaming-backend-2026-11-11.txt), [uncertainty log](../reviews/voice-streaming-uncertain-findings.md) |

## What happened

Cancellation-safe cleanup still had unbounded waits. The signed correction
uses a shared deadline and transfers unresolved cleanup to one owned
supervisor. A control-overflow test was also timing-dependent: sending many
client controls did not guarantee the sender queue would fill. An event-gated
synchronous producer burst exercises the actual overflow deterministically.
The combined backend suite now passes all 66 cases. Final code review and
phase acceptance remain separate.

## What we learned

Bounded handler waits do not imply bounded resource lifetime. Preserve
ownership until worker quiescence and successful closure are confirmed.
Terminal assertions belong after the owning supervisor settles, not before
an asynchronous cleanup resumption is allowed to finish.

Repeated full reviews and treating speculative findings as new requirements
delayed implementation. The operator requested a focused review of concrete
failure paths and a separate file for uncertain observations.

## What to do differently

Complete the agreed tests, review once, batch concrete blockers, and recheck
only affected findings. Log uncertainty with evidence and a revisit condition.
Do not add scheduling workarounds solely to make intermediate flags appear
final. Keep the quality and independent security gates intact.

## Still unknown

Real-server shutdown, device behavior, and native-provider termination are
not established by these offline tests. They remain acceptance obligations,
not claims made by the fake adapter.
