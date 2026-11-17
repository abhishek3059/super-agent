import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { env } from '../env.js';

/**
 * The processes this server started for the bots (gateways, browsers), by name. Their pids are kept
 * in the server's own folder, never read from a folder a bot can write: a bot that could name a pid
 * could have the server signal any process of the operator's.
 */

const dir = path.join(env.dataDir, 'run');
const fileFor = (name: string) => path.join(dir, `${name}.pid`);

export function recordPid(name: string, pid: number | undefined) {
  if (!pid) return;
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  fs.writeFileSync(fileFor(name), String(pid), { mode: 0o600 });
}

/**
 * The pid we recorded under `name`, if that process is still alive and its command line contains
 * `marker` (a pid outlives its process and gets reused, so the number alone proves nothing).
 */
export function livePid(name: string, marker: string): number | null {
  let pid = NaN;
  try { pid = Number(fs.readFileSync(fileFor(name), 'utf8')); } catch { return null; }
  if (!Number.isInteger(pid) || pid <= 1) return null;
  try {
    return execFileSync('ps', ['-p', String(pid), '-o', 'command='], { encoding: 'utf8', timeout: 3000 }).includes(marker) ? pid : null;
  } catch { return null; }
}

/** Stop the process we recorded under `name` and everything in its group. */
export async function stopPid(name: string, marker: string): Promise<void> {
  const pid = livePid(name, marker);
  if (!pid) return;
  const signal = (sig: NodeJS.Signals) => {
    try { process.kill(-pid, sig); } catch { try { process.kill(pid, sig); } catch { /* gone */ } }
  };
  const gone = () => { try { process.kill(pid, 0); return false; } catch { return true; } };
  signal('SIGTERM');
  for (let i = 0; i < 40 && !gone(); i++) await new Promise((r) => setTimeout(r, 250));
  if (!gone()) { signal('SIGKILL'); await new Promise((r) => setTimeout(r, 300)); }
  fs.rmSync(fileFor(name), { force: true });
}
