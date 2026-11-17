import { execFileSync, spawn } from 'node:child_process';
import crypto from 'node:crypto';
import type { Readable } from 'node:stream';
import path from 'node:path';
import { confinedEnv, contained } from '../sandbox.js';

/**
 * Reading and writing files in a folder a bot can write (its Hermes home, its working folder).
 * The server is not sandboxed, and a bot can plant links or swap sub-folders there at any moment,
 * so the server never touches those files itself. A short shell command does it, inside a sandbox
 * that can write only that folder: whatever the bot swaps in, the command cannot reach past it.
 */

/** A path inside the folder: relative, with no `..`, nothing hidden from the check above. */
function relative(rel: string): string {
  const parts = rel.split('/');
  if (path.isAbsolute(rel) || !rel || parts.some((p) => !p || p === '.' || p === '..') || /[\0\n\r]/.test(rel)) {
    throw new Error('outside the bot folder');
  }
  return rel;
}

/** Each folder's commands get a temporary folder of their own, so one bot's never meets another's. */
const tmpName = (root: string) => `own-${crypto.createHash('sha256').update(root).digest('hex').slice(0, 12)}`;

function inSandbox(root: string, script: string, args: string[], input?: string | Buffer, maxBuffer = 1 << 20): string {
  const run = contained('/bin/sh', ['-c', script, 'sh', ...args], { read: [], write: [root], localPorts: [] }, tmpName(root));
  return execFileSync(run.bin, run.args, { cwd: root, input, env: confinedEnv(tmpName(root)), timeout: 10_000, maxBuffer, encoding: 'utf8' });
}

/** Replace the file with `content`. Whatever was there (a link, a folder) is removed, never written through. */
export function writeOwn(root: string, rel: string, content: string | Buffer, mode = 0o600): void {
  // `./` keeps a name that starts with `-` from being read as an option.
  inSandbox(root, 'mkdir -p "$(dirname "./$1")" && rm -rf "./$1" && (umask 077; cat > "./$1") && chmod "$2" "./$1"',
    [relative(rel), (mode & 0o777).toString(8)], content);
}

/** The file's text and time, or null if it is missing, is a link, is not a plain file, or is too big. */
export function readOwn(root: string, rel: string, maxBytes = 1 << 20): { text: string; mtimeMs: number } | null {
  try {
    const out = inSandbox(root, '[ -f "./$1" ] && [ ! -L "./$1" ] && stat -f %m "./$1" && head -c "$2" "./$1"',
      [relative(rel), String(maxBytes + 1)], undefined, maxBytes + 64);
    const nl = out.indexOf('\n');
    const text = out.slice(nl + 1);
    if (nl < 0 || Buffer.byteLength(text) > maxBytes) return null;
    return { text, mtimeMs: Number(out.slice(0, nl)) * 1000 };
  } catch { return null; }
}

/**
 * A file to send to the operator, read inside the sandbox too. Null if it is not a plain file. The
 * check and the read are two commands, so no length is promised; the read stops after a minute.
 */
export function streamOwn(root: string, rel: string): Readable | null {
  const check = '[ -f "./$1" ] && [ ! -L "./$1" ]';
  try { inSandbox(root, check, [relative(rel)]); } catch { return null; }
  const run = contained('/bin/sh', ['-c', `${check} && exec cat "./$1"`, 'sh', relative(rel)], { read: [], write: [root], localPorts: [] }, tmpName(root));
  const child = spawn(run.bin, run.args, { cwd: root, env: confinedEnv(tmpName(root)), stdio: ['ignore', 'pipe', 'ignore'], timeout: 60_000 });
  child.stdout.once('close', () => child.kill());
  return child.stdout;
}

/** The plain files and folders directly in `rel` ('' for the folder itself), listed inside the sandbox. */
export function listOwn(root: string, rel: string): { name: string; size: number; modifiedAt: number; isDir: boolean }[] | null {
  const dir = rel ? relative(rel) : '.';
  try {
    const out = inSandbox(root, '[ -d "./$1" ] && [ ! -L "./$1" ] && find "./$1" -mindepth 1 -maxdepth 1 \\( -type f -o -type d \\) -exec stat -f "%HT\t%z\t%m\t%N" {} +',
      [dir], undefined, 4 << 20);
    return out.split('\n').filter(Boolean).map((line) => {
      const [type, size, mtime, ...name] = line.split('\t');
      return { name: path.basename(name.join('\t')), size: Number(size), modifiedAt: Number(mtime) * 1000, isDir: type === 'Directory' };
    });
  } catch { return null; }
}
