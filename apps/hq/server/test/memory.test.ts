// Self-checks for per-bot semantic memory. The SQL tests need a pgvector Postgres: set
// HQ_MEMORY_TEST_DB_URL (a loopback URL) to run them; they skip otherwise so CI without Postgres passes.
// Rows are written under bot ids starting with bot_test_ and removed afterwards.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';

const testDb = process.env.HQ_MEMORY_TEST_DB_URL ?? '';
process.env.HQ_DATA_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'hq-memory-'));
if (testDb) process.env.HQ_MEMORY_DB_URL = testDb; else delete process.env.HQ_MEMORY_DB_URL;
const { isLoopbackUrl, env } = await import('../src/env.js');
const mem = await import('../src/memory.js');
const skipDb = testDb ? false : 'HQ_MEMORY_TEST_DB_URL is not set (needs a local pgvector Postgres)';

const run = crypto.randomBytes(4).toString('hex');
const botA = `bot_test_${run}_a`;
const botB = `bot_test_${run}_b`;
const botC = `bot_test_${run}_c`;
const user = 'usr_test';
after(async () => {
  if (testDb) for (const b of [botA, botB, botC]) await mem.forgetBotMemory(b);
  await mem.closeMemory();
});

/** One-hot vectors keyed by a word: texts with the same word are identical, others orthogonal. */
const WORDS = ['alpha', 'beta', 'gamma', 'delta'];
const fake: import('../src/memory.js').Embedder = async (text) => {
  const v = new Array(768).fill(0);
  v[Math.max(0, WORDS.findIndex((w) => text.toLowerCase().includes(w)))] = 1;
  return v;
};

test('only loopback URLs are accepted', () => {
  for (const ok of ['postgres://hq:pw@127.0.0.1:5433/hq_memory', 'http://localhost:11434', 'http://[::1]:11434']) assert.equal(isLoopbackUrl(ok), true, ok);
  for (const bad of ['postgres://hq:pw@db.example.com:5432/x', 'http://192.168.1.5:11434', 'http://127.0.0.1.evil.com', 'postgres://hq@127.0.0.1/x?host=evil.example', 'not a url', '']) assert.equal(isLoopbackUrl(bad), false, bad);
});

test('a non-local database URL keeps memory off and the password out of the log', () => {
  const code = "const {env}=await import('./src/env.ts');console.log('ON='+env.memoryOn)";
  const r = spawnSync(process.execPath, ['--import', 'tsx', '--input-type=module', '-e', code], {
    cwd: path.resolve(import.meta.dirname, '..'),
    env: { ...process.env, HQ_MEMORY_DB_URL: 'postgres://hq:s3cret-pw@db.example.com:5432/x' },
    encoding: 'utf8',
  });
  assert.match(r.stdout, /ON=false/);
  assert.match(r.stderr, /HQ_MEMORY_DB_URL must point at 127\.0\.0\.1/);
  assert.doesNotMatch(r.stdout + r.stderr, /s3cret-pw/);
});

test('with no database URL the memory tools are not offered', async () => {
  if (testDb) return; // the tools exist when a test database is configured
  assert.equal(env.memoryOn, false);
  const { TOOLS } = await import('../src/agent/tools.js');
  assert.equal(TOOLS.some((t) => t.name.startsWith('memory_')), false);
});

test('text over the limit is refused before anything is embedded or stored', async () => {
  mem.setEmbedder(async () => { throw new Error('must not be called'); });
  await assert.rejects(mem.saveMemory(user, botA, 'x'.repeat(mem.MAX_TEXT + 1)), /too long/);
  await assert.rejects(mem.searchMemory(user, botA, 'y'.repeat(mem.MAX_TEXT + 1)), /too long/);
  await assert.rejects(mem.saveMemory(user, botA, '   '), /empty/);
});

test('save dedupes, search is cited, below-threshold gives the no-match message', { skip: skipDb }, async () => {
  mem.setEmbedder(fake);
  const id = await mem.saveMemory(user, botA, 'alpha: the user prefers green tea');
  assert.equal(await mem.saveMemory(user, botA, '  ALPHA:  the user prefers   green tea '), id);
  const hit = await mem.searchMemory(user, botA, 'alpha');
  assert.match(hit, new RegExp(`^\\[mem:${id.slice(0, 8)}\\] \\(\\d{4}-\\d{2}-\\d{2}, saved\\) alpha: the user prefers green tea$`));
  assert.equal(await mem.searchMemory(user, botA, 'beta'), mem.NO_MATCH);
});

test('a bot never reads another bot or user memory', { skip: skipDb }, async () => {
  mem.setEmbedder(fake);
  await mem.saveMemory(user, botA, 'gamma: belongs to A');
  await mem.saveMemory(user, botB, 'gamma: belongs to B');
  const a = await mem.searchMemory(user, botA, 'gamma');
  assert.match(a, /belongs to A/);
  assert.doesNotMatch(a, /belongs to B/);
  assert.equal(await mem.searchMemory('usr_other', botA, 'gamma'), mem.NO_MATCH);
  assert.equal(await mem.searchMemory(user, `${botA}_none`, 'gamma'), mem.NO_MATCH);
});

test('Hermes entries are synced in and out, and limit is capped at 10', { skip: skipDb }, async () => {
  mem.setEmbedder(fake);
  assert.match(await mem.searchMemory(user, botB, 'delta', 5, ['delta: hermes note']), /, hermes\) delta: hermes note/);
  assert.equal(await mem.searchMemory(user, botB, 'delta', 5, []), mem.NO_MATCH); // the entry was removed from Hermes
  for (let i = 0; i < 12; i++) await mem.saveMemory(user, botB, `delta: item ${i}`);
  assert.equal((await mem.searchMemory(user, botB, 'delta', 99)).split('\n').length, 10);
});

test('deleting a bot removes its rows and only its rows', { skip: skipDb }, async () => {
  mem.setEmbedder(fake);
  await mem.forgetBotMemory(botB);
  assert.equal(await mem.searchMemory(user, botB, 'delta'), mem.NO_MATCH);
  assert.match(await mem.searchMemory(user, botA, 'gamma'), /belongs to A/);
});

// Tunes MIN_SIMILARITY with the real model. Needs Ollama with the model at HQ_EMBED_URL.
const ollamaUp = testDb ? await fetch(`${env.embedUrl}/api/tags`, { signal: AbortSignal.timeout(2000) }).then((r) => r.ok, () => false) : false;
test('real embeddings: related queries match, unrelated ones do not', { skip: skipDb || (ollamaUp ? false : 'Ollama is not reachable at HQ_EMBED_URL') }, async () => {
  const cos = (a: number[], b: number[]) => a.reduce((s, x, i) => s + x * b[i], 0) / Math.hypot(...a) / Math.hypot(...b);
  const facts = [
    'The user prefers green tea over coffee in the morning.',
    'The user decided to host the website on Vercel instead of Netlify.',
    "The user's sister Priya lives in Toronto and works as a nurse.",
  ];
  const related = ['What does the user like to drink in the morning?', 'Where did we decide to deploy the website?', 'Who is the user\'s sister?'];
  const unrelated = ['What is the boiling point of nitrogen?', 'Who won the 2018 World Cup?', 'Explain how photosynthesis works.', 'What year did the Berlin Wall fall?'];
  const doc = await Promise.all(facts.map((f) => mem.ollamaEmbed(f, 'document')));
  const best = async (q: string) => { const v = await mem.ollamaEmbed(q, 'query'); return Math.max(...doc.map((d) => cos(v, d))); };
  const rel = await Promise.all(related.map(best));
  const unrel = await Promise.all(unrelated.map(best));
  console.log('related similarities  :', rel.map((x) => x.toFixed(3)).join(' '));
  console.log('unrelated similarities:', unrel.map((x) => x.toFixed(3)).join(' '));

  mem.setEmbedder(mem.ollamaEmbed);
  for (const f of facts) await mem.saveMemory(user, botC, f);
  for (const q of related) assert.match(await mem.searchMemory(user, botC, q), /\[mem:/, q);
  for (const q of unrelated) assert.equal(await mem.searchMemory(user, botC, q), mem.NO_MATCH, q);
});
