# Brain design: recommendations

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Author | Claude Fable 5.2 (`claude-fable-5-2`), operator `abhishek3059` |
| Status | **Proposal.** Design only. Nothing is built. Suggestions draw on persistent memory, so they wait for the same approval (OD-2 in the [overview](overview.md#10-open-maintainer-decisions)). |
| Companion documents | [overview](overview.md), [memory](memory.md), [data layer](data-layer.md), [threat model](threat-model.md), [evaluation](evaluation.md) |

A good butler anticipates. He notices that the same request comes every
Monday and offers to make it a habit. He does not act on the idea, does not
repeat an offer that was declined, and can always say what made him think of
it. This document designs that behaviour as advice only.

Limits and thresholds are provisional ([REQ-17](../../../prd.md#req-17)).

## 1. What a suggestion is

A suggestion is one short sentence offered to the user, with:

- the **evidence** it rests on: one or more profile records or day-book
  entries, by ID;
- a **kind** (section 3);
- optionally a **draft task** the user can accept.

A suggestion is never an action. Accepting one starts the normal flow in the
[overview, section 7](overview.md#7-from-a-vague-request-to-a-typed-task):
draft, readback, lock, broker admission. Declining one does nothing except
start a cooldown.

## 2. Pipeline

```text
rules (code) -> candidates -> filters (code) -> phrasing (model) -> validation (code) -> offer
```

1. **Rules find candidates.** A fixed set of rules in code scans the profile
   and the day book. A model never decides what to suggest. Each candidate
   names its rule, its subject, and its evidence record IDs.
2. **Filters drop candidates** that are in cooldown, that rest on expired or
   forgotten records, or whose evidence the destination may not see. A voice
   suggestion may cite only `aloud` records
   ([memory](memory.md#4-speakability)).
3. **A model phrases the sentence.** The context is the rule's template, the
   evidence fields, and the butler persona. It is a `personal` call, so it
   runs on the local model only
   ([overview, section 4](overview.md#4-model-routing-at-0)). The model
   returns `{text, evidence_ids}`.
4. **Code validates.** The returned `evidence_ids` must be a non-empty
   subset of the IDs supplied. The text must be within 200 characters. If
   validation fails, the rule's fixed template sentence is used instead. If
   no local model is available, the template is used directly.
5. **The offer is recorded** as a notification of kind `suggestion` (IR-8)
   and delivered at a pause or in the opening brief.

Because rules choose and code validates, a model that misbehaves can at
worst phrase a true suggestion badly.

## 3. Rules

The first rule set is small on purpose. Each rule reads typed fields only.

| Rule | Fires when | Suggests | Evidence |
| --- | --- | --- | --- |
| `remember-offer` | The user just answered a clarifying question for a slot that has a profile key, and no standing order or tombstone exists for that key | Make the answer a standing order | The answer itself, held in session memory. Nothing is stored unless the user says yes. |
| `repeat-task` | The day book shows the same operation with the same short name `succeeded` 3 times within 30 days | Offer to run it again now | The 3 day-book entries |
| `stale-order` | A standing order is past `review_after` | Ask whether it still holds | The profile record |
| `contradicted-order` | A standing order's `contradiction_count` reached 3 within 90 days | Ask whether to change it ([memory](memory.md#6-conflicts)) | The profile record |
| `failed-retry` | A day-book entry is `failed` with a retryable reason and no later entry for that short name succeeded | Offer to try again | The failed entry |
| `follow-up` | A job `succeeded` and its operation's task schema lists a follow-up operation | Offer the follow-up | The succeeded entry |

Notes:

- `repeat-task` offers to run the task again. It does not offer a schedule.
  Scheduling is a separate capability ([REQ-18](../../../prd.md#req-18))
  that this pack does not design.
- With the approved task pair, `follow-up` has one real case: after
  "summarize this document" succeeds, offer "extract the open questions and
  action items" from the same document
  ([PH-00 setup decisions](../../approvals/ph-00-setup-decisions.md)).
- A new rule is a reviewed code change. There is no rule that calls a model
  to "look for anything interesting".

## 4. How a suggestion cites its evidence

Spoken, the butler gives the reason in the same breath, in plain words:

> "You've asked for a short summary three times this month. Shall I make
> that your usual?"

On screen, the suggestion card lists each evidence record: for a profile
record its key, value, and when it was confirmed; for a day-book entry its
short name, outcome, and date. Each line links to the record on the memory
screen, where the user can correct or forget it.

If the user asks "why did you suggest that?", the butler answers from the
recorded evidence IDs. If any cited record has since been forgotten or has
expired, the butler says the reason is no longer on record. It does not
reconstruct one.

## 5. When suggestions are offered

| Moment | Limit |
| --- | --- |
| Opening brief | At most 3 suggestions, after the job facts |
| A natural pause in a session | At most 1 unprompted suggestion per session |
| The user asks "any suggestions?" | Up to 3, highest-priority first |
| During an open task draft, or while a `now` notification is pending | None |

Priority is fixed: `contradicted-order`, `failed-retry`, `follow-up`,
`stale-order`, `repeat-task`. `remember-offer` is not ranked: it is offered
once, at the first pause after the task it belongs to is proposed, and it
counts as that session's one unprompted suggestion.

Outcomes and cooldowns, stored in `suggestion_state`
([data layer](data-layer.md#3-schemas)):

| Outcome | Meaning | Cooldown for the same rule and subject |
| --- | --- | --- |
| `accepted` | The user said yes; a draft was opened | 90 days |
| `declined` | The user said no | 90 days |
| `ignored` | Offered, no answer before the session ended | 14 days; after two `ignored` in a row, treated as `declined` |

The user can turn suggestions off entirely with a standing order,
`assistant.suggestions = off`. The rules then do not run.

## 6. Why this stays advice

| Property | Mechanism outside the model |
| --- | --- |
| A suggestion cannot act | The phrasing call has no tools. Its output is text and IDs. |
| Accepting needs the user | Acceptance is a user turn that opens a draft; the broker admits the proposal with origin `user_turn` like any other. |
| A suggestion cannot write memory | Profile-changing `memory.*` operations are refused unless the origin is a user turn (IR-1). "Shall I make that your usual?" followed by yes is a normal `memory.remember` with readback. |
| Content cannot plant a suggestion | Rules read typed profile and day-book fields. Document text and tool output are in neither. |
| A suggestion cannot widen scope | The draft it opens is validated against the existing grant. |
| It is on the record | Each offer is a notification record with its evidence IDs and outcome. |

Under [DEC-18](../../../descisions.md#dec-18), advice is T0. T0 also says
"no personal data access", and a suggestion reads the profile and the day
book. That is why suggestions wait for the persistent-memory approval
(OD-2) and for the T0 persona item R-A.3, and are not claimed as plain T0
here.

## 7. Out of scope

- Proactive suggestions from calendar, email, or files. Those need T1.
- Suggestions pushed when no session is open. That needs notifications to a
  device and an always-on host (PH-06).
- Scheduling and automatic repetition.
- Advice in regulated domains. The butler suggests things about the user's
  own tasks and preferences. It does not volunteer medical, legal, or
  financial advice.

## 8. Constraint check

| Constraint | How this design meets it |
| --- | --- |
| $0, local | Rules are code. Phrasing uses the local model or a template. |
| No audio or transcripts stored | `suggestion_state` holds rule, subject key, outcome, and dates. No suggestion text is stored. |
| Content is data | Evidence comes from typed fields; phrasing output is validated. |
| Voice is not identity | A spoken yes to a suggestion opens a draft that still needs readback, and the screen for sensitive keys. |
| Ledger owns truth | Offers and outcomes are notification records. |
| Tiers | Advice only. No tool, no write, no new authority. |
