import { readOwn, writeOwn } from './lib/own.js';
import path from 'node:path';
import { sha256 } from './lib/ids.js';
import { engineHome } from './engine.js';
import type { Memory } from './types.js';

/**
 * What a bot remembers lives in its Hermes home, not in our database: `memories/MEMORY.md` (the
 * agent's own notes) and `memories/USER.md` (what it knows about the user). Each file is a list of
 * entries separated by a line holding only "§". The app shows them and lets the user remove one.
 */

const SEP = '\n§\n';
const FILES = [
  { key: 'm', file: 'MEMORY.md', source: 'learned' as const },
  { key: 'u', file: 'USER.md', source: 'chat' as const },
];

/** Entries of one memory file in the bot's home, read without following a link the bot planted there. */
function read(home: string, rel: string): { entries: string[]; mtime: number } {
  const f = readOwn(home, rel);
  return f ? { entries: f.text.split(SEP).map((e) => e.trim()).filter(Boolean), mtime: f.mtimeMs } : { entries: [], mtime: 0 };
}

// Bot ids never contain a dot, so it separates the parts of a memory id.
const idFor = (botId: string, key: string, text: string) => `mem.${botId}.${key}.${sha256(text).slice(0, 16)}`;

export function listMemories(botId: string): Memory[] {
  const home = engineHome(botId);
  if (!home) return [];
  const out: Memory[] = [];
  for (const f of FILES) {
    const { entries, mtime } = read(home, path.join('memories', f.file));
    for (const text of entries) out.push({ id: idFor(botId, f.key, text), botId, text, createdAt: Math.round(mtime), source: f.source });
  }
  return out;
}

/** The bot a memory id belongs to, so the caller can check who owns it. */
export function memoryBot(id: string): string | null {
  const parts = id.split('.');
  return parts.length === 4 && parts[0] === 'mem' ? parts[1] : null;
}

export function deleteMemory(id: string): boolean {
  const botId = memoryBot(id);
  const home = botId ? engineHome(botId) : null;
  if (!botId || !home) return false;
  const f = FILES.find((x) => x.key === id.split('.')[2]);
  if (!f) return false;
  const rel = path.join('memories', f.file);
  const { entries } = read(home, rel);
  const keep = entries.filter((text) => idFor(botId, f.key, text) !== id);
  if (keep.length === entries.length) return false;
  writeOwn(home, rel, keep.join(SEP) + (keep.length ? '\n' : ''), 0o644);
  return true;
}
