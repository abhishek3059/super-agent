# Council meeting 2 — anonymized cross-review, means, rankings, disagreements, counterfactuals

| Field | Value |
| --- | --- |
| Date | 2026-11-07 (source council session) |
| Source | [docs/delivery/council.md](../docs/delivery/council.md) |
| Status | Archived deliberation record; not a new meeting |
| Revision 2 note | Corrections applied 2026-11-07 for independent review finding R-04 (see ../docs/reviews/super-agent.md): the recorded round-two provider-recommendation change was added with source citations. Exact scores and rankings above are unchanged. |

## Navigation

- [Council meetings index](README.md)
- [Council deliberation source](../docs/delivery/council.md)
- [Signed design](../docs/design/super-agent.md)
- [Delivery status](../docs/delivery/super-agent.md)
- [Discovery brief](../docs/delivery/super-agent-brief.md)
- [Requirements](../prd.md)
- [Decisions](../descisions.md)
- [Architecture](../architecture.md)
- [Phases](../phases.md)
- [Progress](../progress.md)
- [Build](../build.md)
- [Flow](../flow.md)
- [Tasks](../taks/README.md)
- [Implementation report](../docs/implementation/super-agent.md)

## Anonymized cross-review — aggregate received ratings

Each member scored the other three responses on relevance, feasibility, and insight, each from 1 to 5. The following are arithmetic means of the three received ratings, rounded to two decimals; discussion aids, not proof.

| Response | Relevance | Feasibility | Insight | Main contribution |
| --- | ---: | ---: | ---: | --- |
| A — Architect | 5.00 | 3.33 | 4.67 | State ownership, recovery, and authority separation |
| B — Skeptic | 5.00 | 4.00 | 5.00 | Concrete security and evidence boundaries |
| C — Pragmatist | 4.67 | 4.00 | 4.00 | A small, testable vertical slice |
| D — Researcher | 4.67 | 3.67 | 4.67 | Provider eligibility and capability gates |

## Reviewer rankings

- A: B > C > D.
- B: A > D > C.
- C: D > B > A.
- D: B > C > A.

Do not fabricate individual raw scorecards from aggregate means.

## Genuine disagreements and resolutions

1. Durable workers now or later? Resolution: small authoritative job ledger only when the chosen demo tests overlap/cancellation/restart.
2. Wake words immediately? Resolution: manual activation initially; defer system-wide wake detection and locked-screen/background listening.
3. In-process workers or isolation? Resolution: only bounded trusted functions initially; general agent execution requires separately tested OS containment and egress boundary.
4. Cloud-first versus private-first? Resolution: cloud may validate native conversation only after runtime consent, eligibility, and acceptable data terms.

## Provider recommendation change (round-two cross-review)

The cross-review changed the initially presumed provider recommendation. Recorded resolution (`docs/delivery/council.md`:113-117):

> All four converged on native audio, external authority enforcement, explicit cloud consent, no early unrestricted shell, and no unsupported local-hardware promise. The cross-review changed the initial provider recommendation: Gemini must not be the presumed personal runtime. An eligible direct OpenAI native-audio API is an alternative to investigate, not an established account connection.

Contributing Researcher rationale from round one (`docs/delivery/council.md`:85-87): current Gemini developer terms describe professional/business use rather than consumer use and warn against personal/sensitive content on unpaid services; paid services still process/log data, so eligibility must be checked rather than presumed for this personal assistant.

Scope of this change: Gemini remains an eligibility-gated alternative, not a categorically prohibited technology, and no provider, account, or native connection is approved or established by this record. The later GPT-Live/WebRTC/client-delegation research was a separately headed post-review Researcher follow-up in [council meeting 3](council-meeting-3.md) — not a new unanimous vote and not a tested runtime selection.

## Counterfactual pass

Because round one converged quickly, every cross-review also assumed the shared plan was wrong. Counterfactuals include: rejecting an ineligible/unconsented/unacceptable or failed cloud runtime; preferring genuinely compatible native local inference if measurements support it; removing unnecessary durable scheduling for disposable tasks; using an approved always-on host if sleep/off continuity is required; removing tools whose containment/egress tests fail.
