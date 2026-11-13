# Brain design: memory layers

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Author | Claude Fable 5.2 (`claude-fable-5-2`), operator `abhishek3059` |
| Status | **Proposal.** Design only. No memory store exists. Persistent memory needs its own approval under [RT-G05](../../../prd.md#rt-g05) (see OD-2 in the [overview](overview.md#10-open-maintainer-decisions)). |
| Companion documents | [overview](overview.md), [data layer](data-layer.md), [recommendations](recommendations.md), [threat model](threat-model.md), [evaluation](evaluation.md) |

A butler remembers how the household likes things, keeps a day book of what
was done, and knows what not to repeat in company. This document defines the
five memory layers, how a memory is proposed, confirmed, corrected, and
forgotten, and what every record must carry.

All windows and limits are provisional ([REQ-17](../../../prd.md#req-17)).

## 1. Principles

1. **Nothing verbatim persists.** No audio and no transcript is stored
   ([REQ-14](../../../prd.md#req-14)). Persistent memory holds short,
   distilled values that the user confirmed, and entries derived from
   verified receipts.
2. **Profile content changes only inside a job.** A stored value is
   created, replaced, or forgotten only while an admitted `memory.*` job
   executes. The job has a receipt. Model narration changes nothing.
3. **Only a user turn can ask for that.** The broker refuses
   `memory.remember`, `memory.correct`, `memory.forget`, and `memory.export`
   unless the proposal's origin is `user_turn`. The origin is set by code
   from the call path (interface request IR-1 in the
   [overview](overview.md#11-interface-requests-for-the-ledger)). A planner
   step, a worker, a schedule, and any content a job read cannot ask.

   Code, never a model, also writes this bookkeeping. None of it is profile
   content, and none of it can be requested by a model:

   | Write | When | By |
   | --- | --- | --- |
   | A day-book row | The ledger's `job_terminal` event | Memory service |
   | `last_used_at` on a slot | The slot fills a locked draft | Memory service |
   | Contradiction counters on a slot | A drafted value differs from the active order (section 6) | Memory service |
   | A `suggestion_state` row | A suggestion is offered or answered | Memory service |
   | Deletion of expired rows | A `memory.purge` job with origin `system` | Memory service |
4. **Memory is data.** A stored value is untrusted input to a model, like a
   web page. It can fill a blank in a task. It cannot grant a scope, name a
   new recipient, or change a limit.
5. **One reader.** Only the context assembler reads memory for a model, and
   it reads through the memory service with a stated purpose.
6. **Every record says where it came from and when it ends.**

## 2. The five layers

| | L0 Working context | L1 Session memory | L2 Profile (standing orders) | L3 Day book | L4 Library |
| --- | --- | --- | --- | --- | --- |
| Butler analogy | What he holds in mind this moment | What was said this evening | How the household likes things | The record of what was done | The shelves he may consult |
| Lifetime | One model call | One voice session | Until corrected, forgotten, or expired | A fixed window after the job (OD-3) | While the folder stays approved |
| Owner | Context assembler | Conversation coordinator | The user; kept by the memory service | Memory service, from ledger events | The user's files; index kept by the memory service |
| Storage | Process memory | Process memory, keyed by session epoch | `memory.db`, table `memory_item` | `memory.db`, table `daybook_entry` | The files stay where they are; `memory.db` holds an index |
| Read path | Is the prompt | Assembler, same session epoch only | Assembler, by exact key named in a task schema | Assembler, by a full-text query that code builds | Worker step, by a query inside an admitted job |
| Write path | Assembler builds it | Coordinator appends turns, drafts, exceptions | `memory.remember` and `memory.correct` jobs | Code, on the ledger's `job_terminal` event | Indexer job over an approved root |
| Deletion | Discarded after the call | Cleared when the session ends for any reason | `memory.forget` job; expiry sweep | Expiry sweep; forget everything | Root removed or file gone: index rows purged |
| Tier | n/a | T0 | Own gate (OD-2) | Inherits the tier of the job it records | T1; input to R-A.4, not enabled |

### L0 Working context

The assembled prompt for one call, described in the
[overview, section 5](overview.md#5-context-assembly). It is never stored
and never logged.

### L1 Session memory

Held in the backend process for the life of one voice session:

- recent turns as text, bounded (PR 36's adapter already keeps 12 messages
  in memory and never logs them);
- the open task draft and its pending question;
- **session exceptions**: statements that override a standing order for now
  ("steak tonight");
- slot answers given this session, so nothing is asked twice;
- pending memory proposals waiting for a yes.

Everything is keyed by the session epoch. When the session ends, by stop,
timeout, error, or emergency stop, the whole structure is dropped. This
design writes nothing in L1 to disk. A backend restart therefore loses L1,
which is the intended behaviour.

Two limits. Recent turns exist as text only on the local cascade; a native
audio adapter gives code no transcript, so L1 there holds drafts,
exceptions, and slot answers taken from tool arguments. And PR 36's adapter
itself writes each utterance to a temporary file for transcription. That
file is outside this design; its deletion must be confirmed in PR 36's
review before the claim "no audio is stored" is made for the whole system.

### L2 Profile: standing orders

One kind of record, the **slot**: a typed value under a key from the **key
registry**, for example `travel.home_city`, `summary.length`,
`identity.preferred_address`. The registry lives in code. Each key defines
its type, its default speakability, its sensitivity (`low` or `sensitive`),
and a review period. An unknown key is rejected, so a model cannot invent a
place to store things. A text value is at most 200 characters.

At most one slot is `active` per key. The user can list, edit, and delete
every record on the authenticated screen.

**Free-text notes are deliberately left out.** "Remember that the spare key
is under the pot" is the kind of thing people will ask for. It is also the
widest surface in a memory system: free text can hold a secret
([REQ-12](../../../prd.md#req-12)), can carry instructions into a later
context, and needs its own retrieval path. A fact worth keeping gets a
registry key. Notes can be added later with their own design and review.

**Export.** `memory.export` writes every active record, with provenance, as
one JSON file under `~/.super-agent/exports/`, mode 0600. It is started
from the screen only, is never spoken, and never enters a model context. It
includes `screen` and `sealed` values, because the user asked for their own
data on their own authenticated screen. The file is a copy: the user
deletes it, and "forget everything" removes the exports directory too.

### L3 Day book

One entry per terminal job revision, written by code when the ledger emits
`job_terminal` (IR-2). Every field is copied from typed ledger fields:

- when it ended, the operation, the task's short name;
- the terminal state: `succeeded`, `failed`, or `cancelled`. `unknown` is
  not terminal in [architecture.md](../../../architecture.md#canonical-job-states),
  so an `unknown` job gets no entry until it reconciles to one of the three.
  Until then the ledger snapshot is the only record, and the ledger keeps
  it because the 24-hour purge starts at a terminal state;
- the verifier's bounded summary (at most 200 characters);
- an evidence digest, the job ID, and the revision;
- the job's data class and the entry's expiry;
- a speakability class, `aloud` or `screen`, taken from the operation's
  entry in the capability registry. An operation whose results may be
  private (anything over personal sources) is registered as `screen`.

No model writes a day-book field. The entry keeps the job ID as a plain
value, not a foreign key, because the ledger deletes job metadata after 24
hours ([PH-00 setup decisions](../../approvals/ph-00-setup-decisions.md)).
After that purge the entry is all that remains, which is why its retention
is a maintainer decision (OD-3).

`memory.*` jobs produce no day-book entry. A record that something was
forgotten would itself be a trace.

### L4 Library

Approved folders that a worker may search during an admitted job. Nothing is
loaded whole. The index stores chunk positions and hashes, not chunk text:
at retrieval the worker re-reads the file, checks the hash, and uses the
text only if it still matches. A stale chunk triggers a re-index.

Which folders are approved, by whom, and with what injection handling is the
T1 design in R-A.4. This document only fixes the shape: on-demand retrieval,
bounded chunk counts, no content copies in the index. The first use is the
approved task pair over repository Markdown documents, which is `synthetic`
data.

## 3. Provenance on every record

Every L2 record stores the fields below. An L3 day-book entry has the same
provenance, but most of it is constant and is not stored: its source is
always `receipt`, its author `system`, its confirmation `none`, and its
creation time is `occurred_at`. It stores `job_id`, `evidence_digest`, and
`expires_at`.

| Field | Values | Notes |
| --- | --- | --- |
| `source` | `user_statement`, `clarification_answer`, `receipt`, `import` | How the value arrived |
| `author` | `user`, `system` | Who produced the stored text. A model is never the author of a stored value; it may only relay what the user confirmed. |
| `confirmation` | `screen`, `voice`, `none` | `none` only for L3, which rests on a receipt |
| `confidence` | `confirmed`, `stated` | `confirmed` after an explicit yes to a readback. `stated` for a voice-only yes on a low-sensitivity key. There is no numeric score, because nothing would calibrate it. |
| `origin_job_id` | job ID | The `memory.*` job or the recorded job |
| `created_at`, `confirmed_at`, `last_used_at` | timestamps | |
| `review_after` | timestamp | When the butler should ask if this is still right |
| `expires_at` | timestamp | When the sweeper deletes it |
| `supersedes_id` | record ID | The record this one replaced |

There is no `inferred` confidence level. A guess is never stored as a
memory. A pattern the system notices becomes a suggestion
([recommendations](recommendations.md)), and only the user's yes turns it
into a record.

## 4. Speakability

Voice reaches everyone in the room, and voice is not identity
([REQ-09](../../../prd.md#req-09)). So each record has one class:

| Class | The voice model sees | Spoken aloud | Example |
| --- | --- | --- | --- |
| `aloud` | The value | Yes, when relevant | `summary.length`, `travel.home_city` |
| `screen` | A reference only | Never. Shown on the authenticated screen. | `contact.home_address` |
| `sealed` | Nothing | Never. Never enters any model context. | A value a future approved operation needs verbatim |

The class defaults from the key registry. The user may make a record more
private at any time. Making one less private needs the screen.

A `screen` value still works hands-free. The voice model sees
`{slot: contact.home_address}`, places the reference in a task draft, and
code substitutes the real value when the draft locks. The butler says "to
your home address", not the address.

## 5. Lifecycle

```text
            (session memory only)            (memory.db)
user turn -> candidate -> readback -> yes -> active -> superseded
                 |            |                 |
                 +--- no -----+                 +-> forgotten (tombstone)
                 (dropped, never stored)        +-> expired (deleted)
```

**Proposed.** A candidate comes from one of three places:

1. The user says "remember that...". The voice model calls `propose_task`
   with operation `memory.remember`, a registry key, and a value.
2. The user answers a clarifying question for a slot that has a profile key.
   Code already holds the key and the value; no model is involved. At the
   next pause the butler offers once: "Shall I remember short summaries as
   your usual?"
3. The user accepts a suggestion to make something a standing order.

A candidate lives only in session memory. If the session ends first, it is
gone.

**Confirmed.** The butler reads back the key's meaning and the value (a
`screen` value is shown, not spoken). A yes confirms. Code observes the yes
itself, from a screen press or from the transcribed turn that follows the
readback; the model never reports it
([overview, section 7](overview.md#7-from-a-vague-request-to-a-typed-task)).
For a `sensitive` key the yes must come from the screen (OD-6).
On confirmation the draft locks, the broker admits a `memory.remember` job,
and the memory service writes the record as `active`. The butler says "I'll
remember that" only after the job is `succeeded`.

**Used.** Each use updates `last_used_at`. A slot filled into a task is
disclosed in a few words (BR-1). A record confirmed by voice only also
forces a readback of the task before it locks.

**Corrected.** "Actually my home city is Northport" is `memory.correct`:
readback, yes, then the old record becomes `superseded` and a new `active`
record points to it. Superseded records are kept for 30 days so a mistaken
correction can be undone, then deleted.

**Reviewed.** After `review_after` (one year by default) the butler asks at
a quiet moment whether the standing order still holds. A yes moves the date.
Silence changes nothing; the record does not expire because a question went
unanswered.

**Forgotten.** See section 7.

## 6. Conflicts

Precedence, highest first:

1. What the user says in the current turn, for the current task.
2. A session exception.
3. An active standing order.
4. The task schema's default.

The worked case from the brief: `diet.preference = vegetarian` was confirmed
last month. Today the user says "book a table, I want steak."

- The current statement wins for this task. The butler does not argue.
- A session exception `diet.preference -> steak` is recorded in L1. For the
  rest of the session the butler does not ask about it again.
- The profile is not changed. Code detects the contradiction when a draft
  carries a value for a slot whose profile key has a different active
  order. It counts at most once per session per key: `contradiction_count`
  goes up by one and `last_contradicted_at` is set. If the previous window
  began more than 90 days ago (`first_contradicted_at`), the count restarts
  at one and the window starts now. No contradicting value is stored.
- Next session, the standing order applies again as before.
- When the count reaches three inside one 90-day window, the butler asks
  once: "You've gone against your vegetarian preference a few
  times. Should I change it, or keep it?" The answer is a normal
  `memory.correct`, or a reset of the counter.

Other cases:

| Case | Resolution |
| --- | --- |
| Two statements in one turn conflict | The butler asks one question. Nothing is stored. |
| A document or tool output states a different value | Ignored for memory. Content cannot propose a write (principle 3). |
| A correction arrives while a job using the old value is running | The job keeps its admitted revision and arguments. Nothing records which job used which record, so the butler says only that work already started keeps the old value. The user can steer a job by name; that is a `steer_task` and a new revision. |
| Voice-confirmed record against a screen-confirmed one for the same key | Cannot occur: one active record per key. A voice correction of a screen-confirmed sensitive record needs the screen. |

## 7. Forgetting

"Forget my home city" is a `memory.forget` job. The butler reads back what
will be forgotten, by key meaning and not by value when the class is
`screen`. A spoken yes is enough for one `low` record, which the user can
simply state again. A `sensitive` record needs the screen. After the yes,
the job does the following in one transaction where the store allows it:

1. Deletes the record's content and every superseded ancestor.
2. Deletes its rows from every derived store: the embedding table if one
   exists, and the `suggestion_state` rows about that key.
3. Writes a tombstone: record ID, the key, the time, and the job ID. A
   tombstone has no value in it. It does show, for 30 days, that the key
   once had a value.
4. Increments the **memory epoch**.
5. Verifies: queries each store for the record ID and expects zero rows.
6. Writes a receipt with the row count removed from each store.

Then, outside the transaction, it drops the value from session memory and
runs the storage-level cleanup in the [data layer](data-layer.md#7-retention-and-purge).

The butler says "It's forgotten" only when the job is `succeeded`. If the
verification finds a row, the job is `failed` and the butler says it could
not confirm the deletion.

The memory epoch is how in-flight work lets go. Every assembled context
records the epoch it was built from. A planner or worker step built from an
older epoch is rebuilt before it runs, so a forgotten value is not carried
into a later step. A job that already used the value in its admitted
arguments keeps it. The butler says so in general terms and the user can
ask for the list of running jobs.

The tombstone exists so a forgotten slot is not offered again the next time
the user answers the same question. It expires after 30 days.

"Forget everything" deletes `memory.db` and the exports directory and
creates a new empty store. It always needs the screen: a voice in the room
must not be able to wipe the profile. That is one reason the overview
recommends a separate file (OD-10).

Forgetting is the user deleting the assistant's memory of them. Whether
that sits outside the T4 "permanent deletion" tier of
[DEC-18](../../../descisions.md#dec-18) is for the maintainers to record
(OD-14).

**What forgetting cannot reach.** These are stated limits, shown to the user
on the memory screen:

- Operating-system backups and file-history snapshots of `memory.db`.
- Blocks the disk has not yet reused (see the [data layer](data-layer.md#7-retention-and-purge)).
- Effects that already happened in jobs that used the value.
- Day-book summaries and ledger snapshots written before the forget.
  A verifier summary may repeat a value a job used. Nothing records
  which job used which record, so a single forget cannot find them.
  They go when the entry expires, or at once with forget everything.
  A day-book entry cannot be forgotten on its own.
- Export files the user moved or copied elsewhere.
- Temporary files a voice adapter writes for transcription (see L1).
- Whatever the local model server keeps on its own. Whether Ollama persists
  prompt content is **unverified** and must be checked before R-M.7.

No cloud provider holds a copy, because `personal` data never leaves the
machine under the recommended OD-1.

## 8. Retention summary

| Record | Default | Decision |
| --- | --- | --- |
| Session memory | End of session | Fixed by PH-00 |
| Profile slot | No expiry; review after 1 year | Provisional |
| Superseded record | 30 days | Provisional |
| Tombstone | 30 days | Provisional |
| Day-book entry | 30 days | OD-3 |
| Library index rows | Until the file or root goes | Set in R-A.4 |
| Session transcript (distiller input) | Discarded after distilling, in RAM only | OD-16 (proposed, section 9) |
| `inferred` profile record | Expires unless reinforced | OD-17 (proposed, section 9) |
| Episode | 90 days, adjustable | OD-17 (proposed, section 9) |
| Decision or commitment | Until done or forgotten | OD-17 (proposed, section 9) |
| Job spec, verified checkpoints, stop reason | 30 days | OD-18 (proposed); PH-00 says 24 hours today |

## 9. Proposed revision (2026-11-13): learning from conversation

**Proposal only. Nothing in this section is built or approved.** It changes
principles 2 and 3 above and the "no `inferred` level" rule in section 3. It
needs a DEC approved by both maintainers, recorded through OD-15 to OD-17 in
the [overview](overview.md#10-open-maintainer-decisions). Until then,
sections 1 to 8 stand as written.

### 9.1 Motive

On 2026-11-13 the operator said, in chat with Claude Code, that the
companion must learn from his conversations locally (preferences,
decisions, important points) and personalize itself over time, otherwise
"this app is the same as others". The design above learns only when the user
says "remember that...". Most useful facts are never said that way. A butler
who has to be told everything twice is not a butler.

### 9.2 Source text

The source is the session transcript, held in L1 RAM only.

- On the native Gemini route the adapter receives input and output
  transcription (PR 41 enables it). Gemini's internal session state is not
  accessible and is not needed.
- On a local cascade or a local native model, the text is local.

The transcript is never written to disk. It exists in L1 until the session
ends, and the distiller reads it once.

### 9.3 The distiller

A `memory.distill` job, with a new origin `session_end` set by code when a
session closes. It is not a user turn, so principle 3 changes: `session_end`
may run `memory.distill` and nothing else.

| Property | Rule |
| --- | --- |
| Model | The local model only. No cloud call, whatever the route of the session. |
| Tools and network | None. |
| Input | Only the user's own speech turns from this session epoch. Never tool output, documents, web content, job content, or the butler's own replies. |
| Output | Schema-constrained candidates. Kinds: `preference`, `decision`, `fact`, `commitment`, `habit`. Each has a source session epoch, a time, and a confidence of `inferred`. |
| Validation | Code checks each candidate against the key registry (profile kinds) or the episode and decision schemas (section 9.4). Anything else is dropped. |
| Timing | Background, after the session. Speed does not matter, so a small model on the 4 GB laptop is enough. |
| Receipt | A job receipt with counts per store. The butler says "I noted a few things" only when the job is `succeeded`. |

The emergency-stop latch (IR-7) stops the distiller. A session that ends in
an emergency stop is not distilled.

### 9.4 Three stores

| Store | Holds | Relation to the five layers |
| --- | --- | --- |
| Profile | Typed slots for preferences and habits, from the key registry | Extends L2. Adds status `inferred` beside `confirmed`. |
| Episodes | One distilled summary per session: what was discussed, in at most 400 characters, with the session time | Extends L3. The day book records jobs; episodes record conversation. Same sweeper and same purge path. |
| Decisions and commitments | What the user decided or promised ("use Postgres", "call the bank Friday"), with a state `open`, `done`, or `dropped` | Extends L3, as a second table in `memory.db`. |

No new layer is added. Free-text notes stay out (section 2): an episode
summary and a decision are short, schema-bound, and typed, not open notes.
The proposed tables are in the [data layer](data-layer.md#31-proposed-revision-learning-from-conversation).

### 9.5 Safety rules

1. **Only the user's own speech is read.** Injected content cannot plant a
   memory, because content never reaches the distiller.
2. **Inferred means weak.** An `inferred` record may shape tone, defaults,
   and suggestions. It never authorizes a task, names a recipient, changes a
   limit, widens a scope, or fills a `sensitive` slot without a confirmation.
3. **Sensitive categories always need the screen.** Health, money,
   credentials, and personal data about third parties are held as a
   candidate until the user confirms on screen. Unconfirmed, they expire
   with the session's candidate list and are never stored. Credentials are
   never stored at all ([REQ-12](../../../prd.md#req-12)); the distiller's
   schema has no field for them.
4. **A "What I learned" screen** lists every inferred and confirmed record
   with its source session, its time, and a delete button. It is the
   screen-only counterpart to the voice command "what do you know about me".
5. **Decay.** An `inferred` record that is not reinforced by a later
   session expires (OD-17). Reinforcement means a later session yields the
   same record. A reinforced record can be promoted by the user to
   `confirmed`.
6. **The transcript is discarded after distilling.** [REQ-14](../../../prd.md#req-14)
   holds. Keeping it encrypted for a few days is a different decision (OD-16).
7. **Distilled memory never leaves the device.** On the cloud route the
   egress gate treats every distilled record as `personal` data
   ([REQ-13](../../../prd.md#req-13), OD-1). Only the context assembler
   reads it, and only for a local model or as a `screen` reference.
8. **Forget works the same way.** A forgotten record follows section 7,
   including the tombstone, so the distiller does not relearn it the next
   day. Forgetting a record also blocks its re-inference for 30 days.

### 9.6 Retrieval

- **Profile** stays keyword and exact key. Keys are few and typed.
- **Episodes and decisions** use a local embedding model, because paraphrase
  recall is the point: "the trip thing" must find "plan a holiday". This
  relates to OD-4. The recommendation there ("full-text first") stays right
  for the day book and the profile. For episodes it is reversed, and the
  maintainers should record that as part of OD-15.
- The context assembler loads the top standing preferences and the most
  recent open decisions at session start. During a session it searches
  episodes per turn through the memory service, with a stated purpose and a
  bounded result count, like any other read.
- Embeddings are derived data. They are deleted with their source row, and
  the forget job's verification counts them (section 7).

### 9.7 What stays true

Nothing here lets a model write profile content directly. The distiller
proposes; code validates; the memory service writes through a job with a
receipt. The user remains the only author of a `confirmed` record. The
acceptance scenarios that depend on this revision are in
[evaluation, section 12](evaluation.md#12-acceptance-scenario-the-interrupted-trip).

## 10. Constraint check

| Constraint | How this design meets it |
| --- | --- |
| $0, local | Process memory and one local SQLite file. |
| No audio or transcripts stored | This design writes nothing in L1 to disk. L2 holds confirmed distilled values. L3 holds receipt fields. PR 36's temporary transcription file is the open exception noted under L1. |
| Content is data | Principles 3 and 4. Text slot values and day-book summaries are labelled `untrusted` in a context. |
| Voice is not identity | Speakability classes; screen confirmation for sensitive keys; standing orders cannot widen a grant. |
| Ledger owns truth | Every write is a job with a receipt; the day book is written only from a ledger event. |
| Tiers | L4 is T1 and not enabled. L2 needs its own approval. |
| Learning from conversation | Section 9 is a proposal. Local model only, user speech only, `inferred` records never authorize, transcript discarded. |
