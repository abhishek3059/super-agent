import fs from 'node:fs';
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

function read(file: string): { entries: string[]; mtime: number } {
  try {
    if (fs.realpathSync(path.dirname(file)) !== path.dirname(file)) return { entries: [], mtime: 0 };
    const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
    try {
      const status = fs.fstatSync(fd);
      if (!status.isFile() || status.size > 256 * 1024 || status.nlink !== 1) return { entries: [], mtime: 0 };
      const raw = fs.readFileSync(fd, 'utf8');
      return { entries: raw.split(SEP).map((e) => e.trim()).filter(Boolean), mtime: status.mtimeMs };
    } finally { fs.closeSync(fd); }
  } catch {
    return { entries: [], mtime: 0 };
  }
}

// Bot ids never contain a dot, so it separates the parts of a memory id.
const idFor = (botId: string, key: string, text: string) => `mem.${botId}.${key}.${sha256(text).slice(0, 16)}`;

export function listMemories(botId: string): Memory[] {
  const home = engineHome(botId);
  if (!home) return [];
  const out: Memory[] = [];
  for (const f of FILES) {
    const { entries, mtime } = read(path.join(home, 'memories', f.file));
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
  const file = path.join(home, 'memories', f.file);
  const { entries } = read(file);
  const keep = entries.filter((text) => idFor(botId, f.key, text) !== id);
  if (keep.length === entries.length) return false;
  const fd = fs.openSync(file, fs.constants.O_WRONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const status = fs.fstatSync(fd);
    if (!status.isFile() || status.nlink !== 1 || fs.realpathSync(path.dirname(file)) !== path.dirname(file)) return false;
    fs.ftruncateSync(fd, 0);
    fs.writeFileSync(fd, keep.join(SEP) + (keep.length ? '\n' : ''));
  } finally { fs.closeSync(fd); }
  return true;
}
