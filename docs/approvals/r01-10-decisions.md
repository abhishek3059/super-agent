# R-01.10: maintainer decisions for closing PH-01

| Field | Value |
| --- | --- |
| Roadmap item | R-01.10, RT-002 and RT-003 records complete and RT-G01 evidenced |
| Date | 2026-11-19 |
| Decided by | `abhishek3059`, in chat with Claude Code (`claude-opus-5-5`), which recorded it at his instruction. One maintainer's decision is enough ([DEC-21](../../descisions.md#dec-21)). |
| Inputs | [R-01.10 boundary review](../reviews/r01-10-boundary-review.md), [R-01.10 acceptance record](../implementation/r01-10-acceptance.md#blockers) |

## 1. Which run counts for RT-G01

Blocker 2 of the acceptance record asked a maintainer to say which path counts
for the native-media part of RT-G01. **Decision:** a real-microphone run
through the existing console in Gemini mode, done by a maintainer under the
[Gemini testing exception](gemini-live-testing-exception.md), counts. The
operator does every click and all speech; an agent may only observe and write
the record. Synthetic small talk only. The question offered two other paths:
the unbuilt synthetic-only console, and a local-only run, which would need a
gate change. Neither was chosen.

This decision lets the run count as PH-01 evidence. It does not widen the
exception: real voice to Gemini for anyone beyond the maintainers is still
R-A.2.

## 2. Finding F5 (boundary review B1)

**Decision:** fix it in PH-01 instead of accepting it. The fix is R-01.F9,
a mutual HMAC handshake in which the server proves it holds the token before
the console sends any credential. See
[the R-01.F9 record](../implementation/r01-f9-handshake-proof.md).

## 3. Finding F2 (boundary review B2)

**Decision:** accepted for maintainer-only testing. The
[F2 acceptance](r01-6-f2-risk-acceptance.md) set the condition "before ...
a Gemini or job-control capability that matters enough to deny". This
decision records that Gemini in the console, used only by maintainers under
the testing exception, does not yet meet that condition. F2 must be fixed
before any of these:

- R-A.2 allows real voice to a cloud provider beyond maintainer testing;
- a multi-user machine, or an always-on or remote host;
- job control reachable from a voice session.

## Not decided here

The other open findings of the boundary review (B3 to B8) are not accepted by
this record. They stay open for later roadmap items.
