# R-01.7: streaming seam and Gemini adapter

| Field | Value |
| --- | --- |
| Date | 2026-11-10 |
| Evidence | [R-01.7 record](../implementation/r01-7-streaming-seam.md) |

## What happened

The request-and-reply echo seam was replaced with the designed streaming seam,
and a Gemini Live adapter was added behind it with offline tests. A code review
returned REQUEST CHANGES with six required fixes before the work was accepted.

## What we learned

- Concurrency bugs hide in the paths tests rarely take: a hung provider connect, a stalled client, a cancelled handler. Each could hold the single session slot forever. Bound every await that can block on someone else, and cancel child tasks in `finally`.
- "Task exception was never retrieved" in test logs is a real signal. Here it came from child tasks orphaned when the handler was cancelled.
- An epoch shared by two tasks must be announced in the same step that changes it, or the browser can see newer audio before the interruption message.
- An interrupt watchdog must only run while the model is speaking; otherwise an ordinary Interrupt click kills a healthy session.
- Route every provider call through one task. Two tasks writing to one session reorder messages.
- Keeping the SDK out of the lock until its first real caller kept CI and installs unchanged, at the cost of not testing the real SDK yet.

## What to do differently

Ask for the concurrency review before writing tests, and list the "what if the other side stalls" cases as test cases up front.

## Still unknown

Real Gemini Live behavior: whether the SDK's `receive()` shape matches the mapping, how barge-in behaves, and real latency. That is R-01.8 and R-01.9.
