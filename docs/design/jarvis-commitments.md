# Jarvis commitments (design)

| Field | Value |
| --- | --- |
| Status | **Proposal. Not approved. Design only, no code.** |
| Date | 2026-11-21 |
| Requested by | Maintainer `jeevesh2515`, in chat with OpenCode (DeepSeek V4.1 Flash), 2026-11-21, from the Roamies blueprint |
| Roadmap | Proposed as R-H.14 (approval) and R-H.15 (build) in [parallel track H](../../roadmap.md#parallel-track-h-jarvis-hq-local-team-dec-23) |
| Related | [local memory and reminders](local-memory-reminders.md), R-M.13, [DEC-23](../../descisions.md#dec-23), [`proactive.ts`](../../apps/hq/server/src/proactive.ts) |

## 1. What was asked

The blueprint asks Jarvis to hear "nudge me in 3 hours to go to the gym" or
"remind me to check the build after dinner", store the commitment, and nudge
the operator when it is due. It proposes a new parser, a new SQLite table and
an amber overlay pulse.

## 2. What already exists

- R-M.13 covers explicit facts and reminders in the core app: `remember_fact`,
  `add_reminder`, `forget`, `undo_forget`, SQLite, opt-in, secrets refused.
  It is merged but unticked. Its design is
  [local memory and reminders](local-memory-reminders.md).
- HQ has fixed-time check-ins in `proactive.ts`. It has no commitment table
  and no natural-language due-date parser.
- The overlay relay carries only `status`, `level` and `skin`. An amber
  pulse needs a new bounded field, which is a separate decision.

## 3. Recommendation

Do not build a second reminder parser in HQ. Reuse the R-M.13 semantics.

- First choice: wire HQ to the approved reminder store and its code-side time
  parser once R-M.13 is ticked.
- If HQ needs it sooner, add a small `commitments` table in `hq.db` with the
  same fields and rules, and record why the shared store could not be used.
  Mark it temporary and migrate when R-M.13 lands.
- Parse relative times in code, not in a model. "In 3 hours", "tomorrow at
  09:00" and "weekdays at 9" are deterministic. "After dinner" is not, so ask
  one question instead of guessing.
- Deliver due reminders through the existing proactive turn, as one short
  chat message. Do not add a new overlay field in this item.

## 4. Scope for R-H.15

- Explicit requests only: the user's words contain "remind", "nudge" or
  "remember to".
- One local store, one row per commitment: id, user_id, bot_id, text,
  due_at, repeat, status, created_at, delivered_at.
- Caps: 200 open commitments, 240 characters each, control, bidi and
  zero-width characters stripped, secrets refused.
- A due commitment is delivered once. A repeating one moves to its next time.
- A missed commitment while HQ is closed is delivered at the next start, with
  the original due time stated.
- The user can list and cancel a commitment.
- No new provider, no model router, no background service.

## 5. Safety

- Commitment text is data, never an instruction to a worker.
- A commitment cannot start a job, send a message, move money or delete
  anything. It only produces a reminder message.
- No writes in a turn that read outside text, matching the reminder rule in
  the local memory design.
- Local only. Nothing leaves the machine to schedule or deliver.
- Fail closed: an unparsable time asks one question and stores nothing.

## 6. Tests

- Parser table: minutes, hours, days, "tomorrow at", "weekdays at", bad input.
- Timezone and clock-change behavior, including a time that does not exist.
- Delivery once, restart recovery, missed-while-closed delivery.
- Caps, secrets refusal, control-character stripping.
- Cancellation and listing.

## 7. Non-goals

- Mining implicit commitments from every sentence.
- A general cron editor beyond the existing repeat rules.
- An amber overlay pulse. That needs a bounded relay field and its own
  approval.
- A new model, provider or router.

## 8. Open questions

1. Per-user or per-bot commitments? A reminder to "check the build" belongs
   to the person, not one bot.
2. Does HQ share `memory.db` with the core app, or keep `hq.db`?
3. Who delivers a reminder when no bot is selected?
