import pg from 'pg';
import { env } from './env.js';
import { sha256 } from './lib/ids.js';

/**
 * Per-bot semantic memory: PostgreSQL + pgvector for storage, a local Ollama for embeddings. Both
 * must be on this machine (env.ts refuses anything else). Every query is parameterized and every
 * read and delete is scoped to one bot and its user, so a bot never sees another bot's memory.
 */

export const NO_MATCH = 'No matching memory. Tell the user you do not have this in memory; do not guess.';
/**
 * Lowest cosine similarity that counts as a match. nomic-embed-text scores are compressed: on real
 * text, paraphrased questions about a stored fact scored 0.55 to 0.80 and unrelated ones 0.48 to 0.62
 * (see docs/implementation/jarvis-hq-local-run.md, "Semantic memory"). 0.6 favours recall: a few
 * general questions can return a weak entry, which the persona tells the bot to ignore. Re-tune when
 * HQ_EMBED_MODEL changes.
 */
export const MIN_SIMILARITY = 0.6;
export const MAX_TEXT = 4000;
const EMBED_TIMEOUT_MS = 10_000;
const DIMS = 768; // nomic-embed-text; the column below is fixed to it

export type Embedder = (text: string, kind: 'document' | 'query') => Promise<number[]>;

/** nomic-embed-text wants a task prefix on every input. */
export async function ollamaEmbed(text: string, kind: 'document' | 'query'): Promise<number[]> {
  const res = await fetch(`${env.embedUrl.replace(/\/$/, '')}/api/embed`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ model: env.embedModel, input: `search_${kind}: ${text}` }),
    signal: AbortSignal.timeout(EMBED_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(`The embedding service answered ${res.status}. Is the model pulled (ollama pull ${env.embedModel})?`);
  const v = ((await res.json()) as { embeddings?: number[][] }).embeddings?.[0];
  if (!Array.isArray(v) || v.length !== DIMS) throw new Error(`The embedding model must return ${DIMS} numbers per text.`);
  return v;
}

let embedder: Embedder = ollamaEmbed;
/** Test seam: swap the embedder. */
export const setEmbedder = (fn: Embedder) => { embedder = fn; };

let pool: pg.Pool | null = null;
let ready: Promise<void> | null = null;

function db(): pg.Pool {
  if (!env.memoryDbUrl) throw new Error('Semantic memory is off.');
  return (pool ??= new pg.Pool({ connectionString: env.memoryDbUrl, max: 4, connectionTimeoutMillis: 5000 }));
}

/** Creates the table on first use; a failure is retried on the next call. */
function schema(): Promise<void> {
  return (ready ??= (async () => {
    const p = db();
    await p.query('create extension if not exists vector');
    await p.query(`create table if not exists hq_memories (
      id uuid primary key default gen_random_uuid(),
      user_id text not null,
      bot_id text not null,
      text text not null,
      source text not null check (source in ('saved','hermes')),
      content_hash text not null,
      created_at timestamptz not null default now(),
      embedding vector(${DIMS}) not null,
      unique (bot_id, content_hash)
    )`);
    await p.query('create index if not exists hq_memories_embedding_idx on hq_memories using hnsw (embedding vector_cosine_ops)');
    await p.query('create index if not exists hq_memories_bot_idx on hq_memories (bot_id)');
  })().catch((e) => { ready = null; throw e; }));
}

/** Closes the pool (tests and shutdown). */
export async function closeMemory() {
  const p = pool;
  pool = null; ready = null;
  await p?.end();
}

const normalize = (s: string) => s.trim().replace(/\s+/g, ' ');
const hashOf = (text: string) => sha256(normalize(text).toLowerCase());
const literal = (v: number[]) => `[${v.join(',')}]`;

function checked(text: string): string {
  const t = normalize(text);
  if (!t) throw new Error('Nothing to remember: the text is empty.');
  if (t.length > MAX_TEXT) throw new Error(`That is too long to remember (${t.length} characters; the limit is ${MAX_TEXT}). Save a shorter summary.`);
  return t;
}

/** Stores one fact for this bot. The same text twice stores once. Returns the row id. */
export async function saveMemory(userId: string, botId: string, raw: string, source: 'saved' | 'hermes' = 'saved'): Promise<string> {
  const text = checked(raw);
  await schema();
  const hash = hashOf(text);
  const known = await db().query('select id from hq_memories where bot_id=$1 and content_hash=$2', [botId, hash]);
  if (known.rows[0]) return known.rows[0].id;
  const v = await embedder(text, 'document');
  const r = await db().query(
    `insert into hq_memories (user_id, bot_id, text, source, content_hash, embedding) values ($1,$2,$3,$4,$5,$6::vector)
     on conflict (bot_id, content_hash) do nothing returning id`,
    [userId, botId, text, source, hash, literal(v)],
  );
  return r.rows[0]?.id ?? (await db().query('select id from hq_memories where bot_id=$1 and content_hash=$2', [botId, hash])).rows[0].id;
}

/** Makes the 'hermes' rows match the bot's Hermes memory entries: new ones are added, gone ones removed. */
async function syncHermes(userId: string, botId: string, entries: string[]) {
  // Entries over the limit are embedded from their first MAX_TEXT characters rather than refused: they are not the model's to resize.
  const wanted = new Map(entries.map((e) => normalize(e).slice(0, MAX_TEXT)).filter(Boolean).map((t) => [hashOf(t), t]));
  await db().query(`delete from hq_memories where bot_id=$1 and source='hermes' and not (content_hash = any($2::text[]))`, [botId, [...wanted.keys()]]);
  for (const t of wanted.values()) await saveMemory(userId, botId, t, 'hermes');
}

/** Lines `[mem:xxxxxxxx] (date, source) text` for the bot's closest memories, or NO_MATCH. */
export async function searchMemory(userId: string, botId: string, query: string, limit = 5, hermesEntries: string[] = []): Promise<string> {
  const q = checked(query);
  const n = Math.min(Math.max(Math.trunc(Number(limit)) || 5, 1), 10);
  await schema();
  await syncHermes(userId, botId, hermesEntries);
  const v = await embedder(q, 'query');
  const client = await db().connect();
  try {
    // Without iterative scans the hnsw index filters after it ranks and can return too few of one bot's rows.
    await client.query('begin');
    await client.query("set local hnsw.iterative_scan = 'strict_order'");
    const r = await client.query(
      `select id, text, source, created_at, 1 - (embedding <=> $1::vector) as score
         from hq_memories where bot_id=$2 and user_id=$3
        order by embedding <=> $1::vector limit $4`,
      [literal(v), botId, userId, n],
    );
    await client.query('commit');
    const hits = r.rows.filter((row) => row.score >= MIN_SIMILARITY);
    if (!hits.length) return NO_MATCH;
    return hits.map((row) => `[mem:${String(row.id).slice(0, 8)}] (${new Date(row.created_at).toISOString().slice(0, 10)}, ${row.source}) ${row.text}`).join('\n');
  } catch (e) {
    await client.query('rollback').catch(() => {});
    throw e;
  } finally {
    client.release();
  }
}

/** A deleted bot leaves no memory rows behind. */
export async function forgetBotMemory(botId: string): Promise<void> {
  if (!env.memoryOn) return;
  await schema();
  await db().query('delete from hq_memories where bot_id=$1', [botId]);
}
