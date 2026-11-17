import fs, { constants as C } from 'node:fs';
import path from 'node:path';

/**
 * Reading and writing files in a folder a bot can write (its Hermes home, its working folder).
 * The server is not sandboxed, so it must never be led out of that folder: a bot can plant a link
 * there, and a plain read or write would follow it to the operator's files.
 *
 * `root` is the bot's folder itself, which the bot cannot replace (it cannot write the parent).
 */

/** The file's path, after checking that the folder it sits in really is inside `root`. */
function inside(root: string, rel: string): string {
  const base = fs.realpathSync(root);
  const file = path.join(base, rel);
  const dir = fs.realpathSync(path.dirname(file));
  if (dir !== base && !dir.startsWith(base + path.sep)) throw new Error('outside the bot folder');
  // shortcut: a bot could swap a sub-folder for a link between this check and the open below (Node
  // has no openat). The open still refuses a link at the last step and never replaces an existing
  // file, so the most it gains is a new file of this name elsewhere. Upgrade if that ever matters.
  return path.join(dir, path.basename(file));
}

/** Replace the file with `content`. Whatever was there (a link, a folder) is removed, never written through. */
export function writeOwn(root: string, rel: string, content: string | Buffer, mode = 0o600): void {
  fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
  const file = inside(root, rel);
  fs.rmSync(file, { force: true, recursive: true });
  const fd = fs.openSync(file, C.O_WRONLY | C.O_CREAT | C.O_EXCL | C.O_NOFOLLOW, mode);
  try { fs.writeFileSync(fd, content); } finally { fs.closeSync(fd); }
}

/** The file's text and time, or null if it is missing, is a link, or is not a plain file. */
export function readOwn(root: string, rel: string, maxBytes = 1 << 20): { text: string; mtimeMs: number } | null {
  let fd: number | null = null;
  try {
    fd = fs.openSync(inside(root, rel), C.O_RDONLY | C.O_NOFOLLOW);
    const st = fs.fstatSync(fd);
    if (!st.isFile() || st.size > maxBytes) return null;
    return { text: fs.readFileSync(fd, 'utf8'), mtimeMs: st.mtimeMs };
  } catch { return null; } finally { if (fd !== null) fs.closeSync(fd); }
}
