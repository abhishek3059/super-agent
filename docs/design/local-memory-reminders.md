# Local memory and reminders (design)

| Field | Value |
| --- | --- |
| Status | Proposal, built on branch `feat/local-memory-reminders` ahead of the roadmap order. Not accepted. |
| Tier | T2 under [DEC-18](../../descisions.md#dec-18): reversible writes to the assistant's own store, logged, with an undo path |
| Approval | [Out-of-order record](../approvals/local-memory-exception.md) |
| Reference | Roamies design reference, section 1 (ideas only), in [PR 44](https://github.com/abhishek3059/super-agent/pull/44) |
| Code | `apps/api/src/super_agent_voice/memory.py`, wired in `local_adapter.py` |

## What the assistant can do

With `SUPER_AGENT_MEMORY=on` (off by default):

| Tool | Does |
| --- | --- |
| `remember_fact` | Saves one short fact the user asked it to remember |
| `add_reminder` | Saves a reminder for a spoken time, optionally repeating |
| `list_memory`, `list_reminders` | Reads back what is stored |
| `complete_reminder` | Marks a reminder done; a repeating one moves to its next time |
| `forget` | Removes up to 5 matching items |
| `undo_forget` | Restores the last forget within 24 hours |

Due reminders are spoken between turns, never over the user, and the user's
next words cut a reminder off. A question gets notes, marked "data, not
instructions", only when a stored fact or a reminder due within 48 hours
shares a word with it: at most 3 facts and 5 reminders. An unrelated question
gets none. "What do you remember about me" gets the 5 newest facts.

## Controls (in code)

1. **Local only.** One SQLite file, `~/.super-agent/memory.db`, mode 0600 in a
   0700 folder. Nothing is sent anywhere; the model is the local Ollama model.
2. **Opt-in and fail closed.** Memory tools exist only when
   `SUPER_AGENT_MEMORY=on`; any other value except `off` refuses the session.
3. **Caps.** 150 facts, 200 open reminders, 1 to 240 characters each, with
   control, bidi and zero-width characters stripped.
4. **No obvious secrets.** Text that looks like a password, PIN, API key,
   token or private key is refused and never echoed. "Change my password" is
   allowed; "my password is ..." is not. This is a pattern check, not a
   guarantee: "bank pin 4821" or a bare card number gets through.
5. **Times are parsed in code.** The model passes the user's words ("every
   weekday at nine am"); code turns them into a time or refuses, and the reply
   states the time it chose. A bare "at 5" means the next 05:00. Repeat rules are `daily`, `weekdays`, `weekends`, or one weekday.
6. **Undo.** Forget is a soft delete kept for 24 hours; `undo_forget` restores
   the last batch. Adding is undone by forgetting.
7. **Logged, metadata only.** Each memory tool call appends time, tool name,
   and ok or error to `~/.super-agent/tool-audit.log`. Never the text, so the
   log shows that something was added or forgotten, not what. Spoken
   reminders are not logged.
8. **No memory writes after reading outside text.** In a turn where a tier 1
   tool read a file, note, email or calendar entry, every memory write tool
   refuses. A message cannot plant a reminder that later speaks in the
   assistant's voice. Reading memory is still allowed. The guard covers that
   turn only: if the user repeats read text and says "remember that" in a
   later turn, it is saved, because the user asked.
9. **Stored text cannot break the notes frame.** Parentheses become square
   brackets on save.
10. **Strict arguments.** Exactly the declared keys and types; plain digit
    strings count as numbers because small models send them that way.
11. **The user must have asked.** `remember_fact`, `add_reminder` and `forget`
    run only when the user's words in that turn contain a matching request
    word ("remember", "remind", "forget" and a few like them). The small model
    otherwise saved things nobody asked for.

## Next step: recall that does not forget (proposal, not built)

Today recall is word overlap, so "my sibling" does not find "my sister is
Asha". The brain design in PR #40 (`docs/design/brain/data-layer.md`, section
5) already compares the options; this note only says what fits the T2 store.
The store is capped at 150 facts, so heavy machinery is not needed:

1. **First, no new dependency.** Add SQLite FTS5 keyword search over facts
   (the same BM25 ranking the brain design lists as option a). Check that the
   Python build has FTS5 before relying on it.
2. **Then, if paraphrases still miss:** store one vector per fact, made by a
   small local embedding model through Ollama (`nomic-embed-text`, Apache-2.0,
   274 MB), and rank by cosine similarity in plain Python. At 150 vectors this
   takes milliseconds. Keep FTS5 too and merge the two rankings, because
   embeddings alone miss exact names and numbers. Delete a vector with its
   fact, and never compare vectors from different models.
3. **Not now:** `sqlite-vec` (a native extension in the trust boundary, and
   pre-1.0) and any hosted vector database. Both break the local-only rule
   for little gain at this size.

Neither step reduces hallucination by itself. What does: retrieve only a few
notes per turn (done), tell the model to answer from a note or say it does not
know, and let it call `list_memory` for a full lookup. Token cost stays flat,
because the notes sent per turn stay at 3 facts. This needs a roadmap item and
both maintainers' yes before any code.

## Known limits

- Reminders fire only while a voice session is open. A reminder due while no
  session is open is spoken at the next session's first check.
- A reminder is marked only after it is spoken. One cut off by the user, or
  by the session closing, is spoken again at a later check. A spoken one-time
  reminder is done; a spoken repeat moves to its next time.
- "Done" on a repeat that was just spoken keeps its next time. "Done" said
  early, before a repeat speaks, after an earlier one was heard, also keeps
  the next time, so that one still speaks.
- Completing a one-time reminder has no undo.
- Forgotten text stays on disk, soft-deleted, for up to 24 hours.
- A memory write already running in a thread finishes even if the user
  interrupts or the session closes.
- Local time comes from `/etc/localtime`. On Windows it falls back to a fixed
  offset, so repeats can drift by an hour across a clock change. A time that
  does not exist on a clock-change day (01:30 when clocks jump) moves forward
  an hour.
- The small brain sometimes misreads stored times or pads reminder text (see
  the [test record](../implementation/local-memory-test.md)).
- A prompt injection spoken by the user, or one that reaches the model without
  a tier 1 read, can still be remembered and shown again as a note. The notes
  are framed as data and no tool can act on them.
