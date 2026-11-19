import { spawnSync } from 'node:child_process';
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

// Reserve a bot's ports while its process and file cleanup is in progress.
export const deletingBots = new Set<string>();

export function recordPid(name: string, pid: number | undefined) {
  if (!pid) return;
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  fs.writeFileSync(fileFor(name), String(pid), { mode: 0o600 });
}

// A null result is stale or missing; undefined means we couldn't establish the process identity.
function inspectPid(name: string, marker: string): number | null | undefined {
  let pid: number;
  try { pid = Number(fs.readFileSync(fileFor(name), 'utf8')); } catch (e) {
    return (e as NodeJS.ErrnoException).code === 'ENOENT' ? null : undefined;
  }
  if (!Number.isInteger(pid) || pid <= 1) return null;
  const result = spawnSync('ps', ['-p', String(pid), '-o', 'command='], { encoding: 'utf8', timeout: 3000 });
  if (result.error || result.signal) return undefined;
  if (result.status === 0) return result.stdout.includes(marker) ? pid : null;
  // With a valid selector and no matching processes, ps exits 1 without output.
  if (result.status === 1 && !result.stdout && !result.stderr) return null;
  return undefined;
}

export function livePid(name: string, marker: string): number | null {
  return inspectPid(name, marker) ?? null;
}

/** Stop the process we recorded under `name` and everything in its group. */
export async function stopPid(name: string, marker: string): Promise<void> {
  const pid = inspectPid(name, marker);
  if (pid === undefined) throw new Error(`Could not verify the recorded process for ${name}`);
  if (pid === null) { fs.rmSync(fileFor(name), { force: true }); return; }
  const signal = (sig: NodeJS.Signals) => {
    try { process.kill(-pid, sig); } catch { try { process.kill(pid, sig); } catch { /* gone */ } }
  };
  const gone = () => {
    try { process.kill(pid, 0); return false; } catch (e) { return (e as NodeJS.ErrnoException).code === 'ESRCH'; }
  };
  signal('SIGTERM');
  for (let i = 0; i < 40 && !gone(); i++) await new Promise((r) => setTimeout(r, 250));
  if (!gone()) { signal('SIGKILL'); await new Promise((r) => setTimeout(r, 300)); }
  if (!gone()) throw new Error(`Could not stop the recorded process for ${name}`);
  fs.rmSync(fileFor(name), { force: true });
}
