# Brain design: data layer

| Field | Value |
| --- | --- |
| Date | 2026-11-13 |
| Author | Claude Fable 5.2 (`claude-fable-5-2`), operator `abhishek3059` |
| Status | **Proposal.** No schema exists. Nothing here is installed. Every dependency named is an option for the maintainers, not a choice. |
| Companion documents | [overview](overview.md), [memory](memory.md), [recommendations](recommendations.md), [threat model](threat-model.md), [evaluation](evaluation.md) |

This document gives the storage for the persistent memory layers: files,
schemas, migrations, indexes, retrieval, encryption options, and purge jobs.
External facts were researched on 2026-11-13; section 9 lists each source and
marks what was not verified.

## 1. Files and ownership

| Store | File | Owner | Status |
| --- | --- | --- | --- |
| Job ledger | Decided by the PH-02 ledger work | Ledger session | Not designed here |
| Memory | `~/.super-agent/memory.db` | Memory service | Proposed (OD-10) |
| Session memory | None. Process memory only. | Conversation coordinator | Proposed |

The directory `~/.super-agent/` is already used for the local token
([config.py](../../../apps/api/src/super_agent_voice/config.py)). The memory
file follows the token file's rules: mode 0600 and owned by the user on
POSIX, refused if it is a symlink. The Windows ACL check is the same open
review item the token file has.

**Tables that extend the ledger: none are created by this design.** The
brain needs these fields from the ledger, requested as IR-1, IR-3, IR-4, and
IR-8 in the [overview](overview.md#11-interface-requests-for-the-ledger):

| Ledger record | Requested field |
| --- | --- |
| Task proposal and task record | `origin`, `data_class` |
| Action or attempt record | `provider`, `model` |
| Task snapshot | `short_name`, `speakable_summary`, `evidence_ref` |
| Notification record | `kind = suggestion`, `class` |
| Capability registry | The five `memory.*` operations |

**Tables that are separate** live in `memory.db` and are listed in section 3.
The two files reference each other by plain ID values only. There is no
cross-file foreign key, because the ledger purges jobs after 24 hours and a
day-book entry must survive that.

The memory service is the only writer. Connection settings:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA secure_delete = ON;
PRAGMA busy_timeout = 2000;
```

**Startup check, fail closed.** The memory service refuses to open the store
unless SQLite is version 3.42.0 or later and a probe
`CREATE VIRTUAL TABLE temp.probe USING fts5(x, content = '', contentless_delete = 1)`
succeeds. Version 3.42.0 is the first with the FTS5 `secure-delete` option
that forgetting relies on. The probe uses `contentless_delete` because the
library index needs it and its minimum version was not verified.

## 2. Migrations

No migration library. The schema version is `PRAGMA user_version`, an
integer SQLite reserves for the application.

- Migrations are numbered SQL files, `0001_init.sql`, `0002_...sql`, applied
  in order.
- On open: read `user_version`; for each higher-numbered file, run it and
  set `user_version` in one transaction.
- Forward only. A store whose version is higher than the code knows is
  refused, not downgraded.
- A migration that rewrites a table copies it, so the migration ends with a
  WAL checkpoint and the cleanup in section 7. Otherwise old values could
  survive in free pages.
- Each migration ships with a test that applies it to a fixture of the
  previous version.

## 3. Schemas

Timestamps are integer Unix seconds in UTC. IDs are random 128-bit values as
hex text. `subject_id` is the authenticated subject from the grant.

```sql
-- L2 profile: standing orders (slots).
CREATE TABLE memory_item (
  id                   TEXT PRIMARY KEY,
  subject_id           TEXT NOT NULL,
  key                  TEXT NOT NULL,     -- a key from the registry in code
  value_json           TEXT NOT NULL,     -- typed value; text is at most 200 characters
  speakability         TEXT NOT NULL CHECK (speakability IN ('aloud', 'screen', 'sealed')),
  sensitivity          TEXT NOT NULL CHECK (sensitivity IN ('low', 'sensitive')),
  state                TEXT NOT NULL CHECK (state IN ('active', 'superseded')),
  source               TEXT NOT NULL CHECK (source IN ('user_statement', 'clarification_answer', 'import')),
  author               TEXT NOT NULL CHECK (author IN ('user', 'system')),
  confirmation         TEXT NOT NULL CHECK (confirmation IN ('screen', 'voice')),
  confidence           TEXT NOT NULL CHECK (confidence IN ('confirmed', 'stated')),
  origin_job_id        TEXT NOT NULL,
  created_at           INTEGER NOT NULL,
  confirmed_at         INTEGER NOT NULL,
  last_used_at         INTEGER,
  review_after         INTEGER,
  expires_at           INTEGER,           -- set when superseded; NULL while active
  supersedes_id        TEXT REFERENCES memory_item(id) ON DELETE SET NULL,
  contradiction_count  INTEGER NOT NULL DEFAULT 0,
  first_contradicted_at INTEGER,          -- start of the current 90-day window
  last_contradicted_at INTEGER
);

-- One active slot per key.
CREATE UNIQUE INDEX memory_item_active_key
  ON memory_item (subject_id, key) WHERE state = 'active';
CREATE INDEX memory_item_expiry ON memory_item (expires_at) WHERE expires_at IS NOT NULL;

-- Forgotten records. Holds no value.
CREATE TABLE memory_tombstone (
  id            TEXT PRIMARY KEY,         -- the forgotten record's id
  subject_id    TEXT NOT NULL,
  key           TEXT NOT NULL,            -- shows that the key once had a value
  forget_job_id TEXT NOT NULL,
  forgotten_at  INTEGER NOT NULL,
  expires_at    INTEGER NOT NULL
);

-- L3 day book: one row per terminal job revision, from the job_terminal event.
CREATE TABLE daybook_entry (
  seq             INTEGER PRIMARY KEY,    -- stable rowid for the full-text index
  id              TEXT NOT NULL UNIQUE,
  subject_id      TEXT NOT NULL,
  job_id          TEXT NOT NULL,          -- plain value, not a foreign key
  revision        INTEGER NOT NULL,
  operation       TEXT NOT NULL,
  short_name      TEXT NOT NULL,
  outcome_state   TEXT NOT NULL CHECK (outcome_state IN ('succeeded', 'failed', 'cancelled')),
  summary         TEXT NOT NULL,          -- verifier's summary, at most 200 characters
  evidence_digest TEXT NOT NULL,
  data_class      TEXT NOT NULL CHECK (data_class IN ('synthetic', 'personal')),
  speakability    TEXT NOT NULL CHECK (speakability IN ('aloud', 'screen')),  -- from the operation's registry entry
  occurred_at     INTEGER NOT NULL,
  expires_at      INTEGER NOT NULL,
  UNIQUE (job_id, revision)               -- a repeated event writes nothing
);
CREATE INDEX daybook_entry_time ON daybook_entry (subject_id, occurred_at);
CREATE INDEX daybook_entry_expiry ON daybook_entry (expires_at);

-- Full-text index over the day book. Rows follow daybook_entry through triggers.
CREATE VIRTUAL TABLE daybook_fts USING fts5 (
  short_name, summary, content = 'daybook_entry', content_rowid = 'seq'
);

-- L4 library: approved roots, documents, and chunk positions. No chunk text.
CREATE TABLE library_root (
  id         TEXT PRIMARY KEY,
  subject_id TEXT NOT NULL,
  path       TEXT NOT NULL,
  grant_ref  TEXT NOT NULL,               -- the grant that approved this root
  added_at   INTEGER NOT NULL,
  UNIQUE (subject_id, path)
);
CREATE TABLE library_doc (
  id           TEXT PRIMARY KEY,
  root_id      TEXT NOT NULL REFERENCES library_root(id) ON DELETE CASCADE,
  rel_path     TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  size_bytes   INTEGER NOT NULL,
  indexed_at   INTEGER NOT NULL,
  UNIQUE (root_id, rel_path)
);
CREATE TABLE library_chunk (
  id         INTEGER PRIMARY KEY,         -- also the FTS rowid
  doc_id     TEXT NOT NULL REFERENCES library_doc(id) ON DELETE CASCADE,
  ordinal    INTEGER NOT NULL,
  byte_start INTEGER NOT NULL,
  byte_end   INTEGER NOT NULL,
  chunk_hash TEXT NOT NULL
);
-- Terms only; the text is re-read from the file at retrieval.
CREATE VIRTUAL TABLE library_fts USING fts5 (body, content = '', contentless_delete = 1);

-- Suggestion bookkeeping: which rule fired about what, and the cooldown. No text.
CREATE TABLE suggestion_state (
  rule_id        TEXT NOT NULL,
  subject_id     TEXT NOT NULL,
  subject_key    TEXT NOT NULL,           -- what the suggestion is about, e.g. a profile key
  last_outcome   TEXT NOT NULL CHECK (last_outcome IN ('offered', 'accepted', 'declined', 'ignored')),
  ignored_streak INTEGER NOT NULL DEFAULT 0,  -- two in a row count as declined
  offered_at     INTEGER NOT NULL,
  cooldown_until INTEGER NOT NULL,
  PRIMARY KEY (rule_id, subject_id, subject_key)
);

-- Store-wide counters.
CREATE TABLE memory_meta (
  name  TEXT PRIMARY KEY,
  value INTEGER NOT NULL                  -- 'memory_epoch'
);
```

Notes on the schema:

- The key registry (allowed keys, types, default speakability, sensitivity,
  review period) is code, not a table. Changing it is a reviewed code change.
- `daybook_fts` needs three triggers on `daybook_entry` (insert, delete,
  update) in the standard external-content pattern. After creation, run
  `INSERT INTO daybook_fts(daybook_fts, rank) VALUES ('secure-delete', 1)`
  and the same for `library_fts`.
- `contentless_delete` needs a recent SQLite. The minimum version for it was
  **not verified** in this research; the startup check must probe for it and
  the implementer must confirm the version against the SQLite documentation.
- `library_fts` holds an inverted index of terms. It is not the document
  text, but terms do reveal content, so its rows are purged with the
  document. Deleting a row is not enough here: in the reviewer's local test
  (SQLite 3.50.4) a deleted term stayed in the file bytes after the delete,
  both secure-delete settings, and a truncating checkpoint. It was gone
  only after `INSERT INTO library_fts(library_fts) VALUES ('optimize')`.
  The library sweep in section 7 therefore runs `optimize`.
- `daybook_entry` has no `unknown` outcome. An `unknown` job is not
  terminal and gets its row when it reconciles
  ([memory](memory.md#l3-day-book)).
- Free-text notes have no table. They are left out of this design
  ([memory](memory.md#l2-profile-standing-orders)).
- There is no table for session memory, for recommendation text, or for
  assembled contexts. Those are never stored.
- The optional embedding table is in section 5 and is created only if the
  maintainers choose that option.

### 3.1 Proposed revision: learning from conversation

**Proposed. Not built.** Needs the DEC described in
[memory, section 9](memory.md#9-proposed-revision-2026-11-13-learning-from-conversation).
Nothing in section 3 above changes unless it is approved.

```sql
-- Profile: allow inferred records and decay.
ALTER TABLE memory_item ADD COLUMN status TEXT NOT NULL DEFAULT 'confirmed'
  CHECK (status IN ('inferred', 'confirmed'));
ALTER TABLE memory_item ADD COLUMN decay_after INTEGER;       -- inferred only; NULL when confirmed
ALTER TABLE memory_item ADD COLUMN reinforced_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE memory_item ADD COLUMN session_epoch TEXT;        -- the session it was distilled from
-- The source and confidence CHECKs would also gain 'distilled' and 'inferred'.

-- One distilled summary per session.
CREATE TABLE episode (
  id             TEXT PRIMARY KEY,
  subject_id     TEXT NOT NULL,
  session_epoch  TEXT NOT NULL,
  occurred_at    INTEGER NOT NULL,
  summary        TEXT NOT NULL,           -- at most 400 characters
  status         TEXT NOT NULL CHECK (status IN ('inferred', 'confirmed')),
  distill_job_id TEXT NOT NULL,
  expires_at     INTEGER NOT NULL
);

-- Decisions and commitments.
CREATE TABLE decision (
  id             TEXT PRIMARY KEY,
  subject_id     TEXT NOT NULL,
  session_epoch  TEXT NOT NULL,
  kind           TEXT NOT NULL CHECK (kind IN ('decision', 'commitment')),
  text           TEXT NOT NULL,           -- at most 200 characters
  state          TEXT NOT NULL CHECK (state IN ('open', 'done', 'dropped')),
  status         TEXT NOT NULL CHECK (status IN ('inferred', 'confirmed')),
  decided_at     INTEGER NOT NULL,
  expires_at     INTEGER,                 -- NULL while open (OD-17)
  distill_job_id TEXT NOT NULL
);
```

- Episodes and decisions get a full-text table like `daybook_fts` and, if
  embeddings are approved, a row in the embedding table of section 5. The
  embedding is deleted with its source row, and the forget job counts it.
- A tombstone for an inferred record blocks re-inference for 30 days.
- The sweeper treats `episode` and `decision` like `daybook_entry`, with
  the same row-count receipt.
- The distiller's schema has no column for credentials, so none can be
  stored here.

## 4. Indexing and access paths

| Read | Query shape | Index used |
| --- | --- | --- |
| Standing order by key | `subject_id`, `key`, active | `memory_item_active_key` |
| All records for the memory screen | `subject_id`, active | Table scan; at most a few hundred rows |
| Day book for a `query_ledger` call with filter `history` | FTS match on the search terms the model passed, newest first, limit 3, `aloud` entries only for a voice context | `daybook_fts`, then `daybook_entry_time` |
| Day book for the opening brief | `subject_id`, `occurred_at` after the last brief | `daybook_entry_time` |
| Library chunks inside a job | FTS match, limited to the roots in the job's grant, limit set by the action | `library_fts`, joined to `library_chunk` and `library_doc` |
| Expiry sweeps | `expires_at` before now | The expiry indexes |

No model writes SQL or an FTS query string. Code builds the match
expression from the search terms a tool call passed or from the task
specification, after
removing FTS operators and quoting each term.

## 5. Retrieval

The design needs retrieval in two places with very different sizes: the day
book (hundreds of short rows at 30-day retention) and the library (possibly
many documents). Three options, in order of cost:

| Option | What it adds | Dependency and licence | Limits |
| --- | --- | --- | --- |
| (a) FTS5 keyword search with BM25 ranking | Nothing | SQLite is public domain. FTS5 must be compiled in: confirmed on the python.org Windows build tested (Python 3.14.4, SQLite 3.50.4); **not verified** for the python.org macOS build. | Misses paraphrases ("flight search" against "plane tickets"). |
| (b) Embeddings stored as BLOBs, brute-force cosine in Python | A local embedding model through Ollama's `/api/embed`. Optionally `numpy`. | A new model download and, if used, a new package. Candidate models and licences below. | Pure standard-library search is fine for hundreds of vectors and too slow for tens of thousands (estimate: seconds per query at 50,000 vectors of 768 dimensions). |
| (c) A vector extension, `sqlite-vec` | Indexed vector search in SQL | Dual MIT and Apache-2.0. Version 0.1.9, pre-1.0. Needs `enable_load_extension`, which the macOS system Python lacks; python.org macOS build **not verified**. | Stable release documents no approximate search; that exists only in alpha releases. A loaded native extension is new code in the trust boundary. |

Candidate embedding models, if option (b) is chosen. Licences are from
Hugging Face model metadata, sizes from the Ollama library pages; dimensions
were **not verified**.

| Model | Licence | Size | Note |
| --- | --- | --- | --- |
| `all-minilm` | Apache-2.0 | 46 MB | Smallest; 512-token context |
| `nomic-embed-text` | Apache-2.0 | 274 MB | 2K context |
| `mxbai-embed-large` | Apache-2.0 | 670 MB | 512-token context |
| `bge-m3` | MIT | about 1.2 GB | 8K context; multilingual |
| `embeddinggemma` | **Custom Gemma licence** | 622 MB | Needs a licence review before any use |

**Recommendation for OD-4:** start with (a). It adds no dependency and is
enough for exact-key profile reads, which need no search at all, and for a
small day book. Add (b) with the standard library only if the paraphrase
scenarios in [evaluation](evaluation.md) fail on the day book. Consider (c)
only for the library, as part of the T1 design in R-A.4.

If (b) is chosen, this table is added by a migration:

```sql
CREATE TABLE embedding (
  owner_kind TEXT NOT NULL CHECK (owner_kind IN ('daybook', 'chunk')),
  owner_id   TEXT NOT NULL,
  model      TEXT NOT NULL,              -- vectors from different models are never compared
  dim        INTEGER NOT NULL,
  vector     BLOB NOT NULL,              -- float32, little-endian
  created_at INTEGER NOT NULL,
  PRIMARY KEY (owner_kind, owner_id, model)
);
```

An embedding is a derived copy of its source. It is deleted in the same
transaction as its owner, and it is listed in the forget receipt. Embedding
calls on `personal` text go to local Ollama only.

## 6. Encryption at rest

The threat is another user or process on the machine, or someone with the
disk, reading `memory.db`. Options:

| Option | Cost | Protects against | Does not protect against |
| --- | --- | --- | --- |
| (a) OS disk encryption plus file permissions | No dependency. FileVault on macOS. On Windows, BitLocker management is for Pro, Enterprise, and Education; Home editions have "device encryption", which depends on the machine and account setup. | A lost or stolen powered-off machine | Any process running as the user; a machine where disk encryption is off |
| (b) SQLCipher through the `sqlcipher3` package | New dependency. SQLCipher Community Edition is BSD-3-Clause. `sqlcipher3` publishes Windows and macOS wheels; its own licence metadata is blank and **must be read** before use. `sqlcipher3-binary` is Linux only. | Reading the file without the key, including from backups | A process that can read the key |
| (c) SQLite3 Multiple Ciphers through `apsw-sqlite3mc` | New dependency. The library is MIT; the Python package's exact licence and current Windows and macOS wheels were **not verified**. Replaces the standard `sqlite3` module with APSW. | Same as (b) | Same as (b) |
| (d) Field-level encryption of `value_json` | Needs a cipher library (the Python standard library has no symmetric cipher) and a key in the OS store: the `keyring` package (MIT) or Windows DPAPI through `ctypes`. | Reading values from the file or a backup | Keys, timestamps, and the day book stay readable; full-text search over encrypted fields is lost |

SQLite's own encryption extension (SEE) costs US $2,000 and is outside the
$0 cap.

For (b), (c), and (d) the key must live in the OS credential store, never in
the repository, a project file, or an environment file
([REQ-12](../../../prd.md#req-12)). Note that on macOS, any script run by
the same Python executable can read a `keyring` secret without a prompt, so
the key store does not stop malware running as the user.

**Recommendation for OD-5:** (a) for the first build, with the memory screen
stating plainly that the file is protected by the operating system's disk
encryption and nothing else. Decide (b) before T1 (R-A.4), when library
content could make the store far more sensitive. Both steps are maintainer
decisions.

## 7. Retention and purge

Every purge of the persistent store is a `memory.purge` job or a step of a
`memory.forget` job, so each has a receipt with row counts per store.

| Purge | Trigger | Removes |
| --- | --- | --- |
| Session clear | Session end for any reason | The in-process session structure. No disk work. |
| Expiry sweep | Backend start, then hourly while running | `memory_item` rows past `expires_at`; `daybook_entry` rows past `expires_at` with their FTS rows; expired tombstones; `suggestion_state` rows whose cooldown ended more than 90 days ago |
| Forget | A confirmed `memory.forget` job | The record, its superseded ancestors, derived rows, and `suggestion_state` rows for its key; writes a tombstone; bumps `memory_epoch` |
| Library orphan sweep | After a root is removed or a file hash changes | `library_doc`, `library_chunk`, `library_fts` rows, followed by the FTS `optimize` command so deleted terms leave the file |
| Ledger-driven purge | The ledger's reconcile and purge operation (IR-6) | Nothing of its own; it calls the expiry sweep and records the counts |

The sweep runs at start because the host may have been asleep or off
([REQ-18](../../../prd.md#req-18)); a missed hourly run is caught up then.
An expired row is never returned by a read even before the sweep deletes it:
every read filters on `expires_at`.

**Storage-level cleanup.** Deleting a row is not enough to remove its bytes:

1. `PRAGMA secure_delete = ON` makes SQLite overwrite deleted content with
   zeros.
2. The FTS5 `secure-delete` option does the same inside the full-text index.
3. After a forget or an expiry sweep that deleted rows, run
   `PRAGMA wal_checkpoint(TRUNCATE)`. Deleted content may otherwise remain
   in the write-ahead log file until the next checkpoint. This interaction
   is reasoned, **not verified** against SQLite documentation. In the
   reviewer's local test these three steps left no residue for
   `memory_item`, `daybook_entry`, and `daybook_fts`. The residue tests in
   [evaluation](evaluation.md) are what must prove it on each host.
4. For the contentless library index, also run the FTS `optimize` command
   (see the schema notes).

What this cannot do: SQLite's documentation is clear that these options do
not reach backups, file-system journals, or flash wear-levelling. Those
limits are stated to the user ([memory](memory.md#7-forgetting)).

## 8. Constraint check

| Constraint | How this design meets it |
| --- | --- |
| $0 | Standard-library `sqlite3` only in the recommended options. Every other option is listed with its licence and left open. |
| No audio or transcripts stored | No table can hold one. Values are capped; the day book stores a 200-character verifier summary. |
| Content is data | No stored text is executed or used as a query. Match expressions are built by code. |
| Voice is not identity | `confirmation` and `sensitivity` are stored on each record so code can require the screen. |
| Ledger owns truth | No ledger table is defined here. Every write happens inside a job. |
| Retention | Every persistent row has an expiry or a review date, and a purge that removes it. |

## 9. Research record

Researched on 2026-11-13 by a research subagent, then reviewed. "Verified"
means read on the cited primary source that day.

| Claim | Status | Source |
| --- | --- | --- |
| FTS5 needs `SQLITE_ENABLE_FTS5` at build time; the `secure-delete` option arrived in 3.42.0 | Verified | <https://sqlite.org/fts5.html> |
| FTS5 works in the python.org Windows build of Python 3.14.4 (SQLite 3.50.4) | Verified by a local test only | Local run |
| FTS5 and `enable_load_extension` in the python.org macOS build | **Not verified** | none |
| `PRAGMA secure_delete` overwrites deleted content with zeros; `user_version` is application-owned | Verified | <https://sqlite.org/pragma.html> |
| `secure_delete` and the write-ahead log | **Not verified** against documentation. One local test on SQLite 3.50.4 found no residue after delete, checkpoint, and byte search for the profile and day-book tables. | Reviewer's local run, 2026-11-13 |
| A contentless-delete FTS5 table keeps deleted terms in the file until `optimize` | Observed in one local test on SQLite 3.50.4; **not verified** against documentation | Reviewer's local run, 2026-11-13 |
| The three schema blocks execute on SQLite 3.50.4 | Verified by a local run; the partial unique index was created but its rejection of a second active row was not exercised | Reviewer's local run, 2026-11-13 |
| Minimum SQLite version for `contentless_delete` | **Not verified** | none |
| `sqlite-vec` is dual MIT and Apache-2.0, latest stable 0.1.9, approximate search only in alpha releases | Verified | <https://pypi.org/pypi/sqlite-vec/json>, <https://github.com/asg017/sqlite-vec/releases> |
| `sqlite-vec` loads through `enable_load_extension`; the macOS system Python lacks it | Verified | <https://alexgarcia.xyz/sqlite-vec/python.html> |
| Ollama embedding endpoint is `POST /api/embed` | Verified | <https://docs.ollama.com/api/embed> |
| Embedding model licences (Hugging Face metadata) and sizes (Ollama library pages) | Verified as listed; dimensions **not verified** | <https://ollama.com/library> |
| Brute-force search timing | **Estimate**, no published figure found | none |
| SQLCipher Community Edition is BSD-3-Clause | Verified | <https://github.com/sqlcipher/sqlcipher> |
| `sqlcipher3` wheels cover Windows and macOS; licence metadata blank | Verified | <https://pypi.org/pypi/sqlcipher3/json> |
| SQLite SEE costs US $2,000 | Verified | <https://sqlite.org/com/see.html> |
| SQLite3 Multiple Ciphers is MIT | Verified | <https://utelle.github.io/SQLite3MultipleCiphers/> |
| `apsw-sqlite3mc` licence and current wheels | **Not verified** | none |
| BitLocker management is not offered on Windows Home; device encryption is | Verified | <https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/> |
| FileVault on Apple silicon | Verified | <https://support.apple.com/guide/mac-help/protect-data-on-your-mac-with-filevault-mh11785/mac> |
| `keyring` is MIT, with Windows and macOS backends | Verified | <https://pypi.org/pypi/keyring/json> |
| The Python standard library has no symmetric cipher | From the author's knowledge, **not verified** this session | none |
