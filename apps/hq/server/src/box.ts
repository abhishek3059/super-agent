import { execFile } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';

/** The box: this machine. Library files and the sign-in terminal. */

/** A string safe to put inside single quotes in a shell command. */
const q = (s: string) => `'${s.replace(/'/g, `'\\''`)}'`;

export const box = {
  async writeFile(file: string, content: string | Buffer): Promise<void> {
    await fs.mkdir(path.dirname(file), { recursive: true });
    await fs.writeFile(file, content);
  },

  /** Open a terminal window running `command`, for sign-ins the operator finishes by hand. macOS only. */
  openTerminal(command: string): Promise<void> {
    if (process.platform !== 'darwin') return Promise.reject(new Error(`Run this in a terminal: ${command}`));
    const script = `tell application "Terminal"\nactivate\ndo script "${command.replace(/[\\"]/g, '\\$&')}"\nend tell`;
    return new Promise((resolve, reject) => execFile('osascript', ['-e', script], { timeout: 15_000 }, (err) => (err ? reject(err) : resolve())));
  },

  quote: q,
};
