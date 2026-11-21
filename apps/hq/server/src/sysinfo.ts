import { execFile } from 'node:child_process';
import fs from 'node:fs';

/**
 * Read-only facts about the operator's Mac for the system_info tool. Runs here, outside the bot
 * sandbox, so it takes no free-form input: a topic picks one fixed list of commands. Process
 * listings carry names only, never arguments or environment, which can hold keys.
 */

const COMMANDS: Record<string, [string, string[]][]> = {
  overview: [['sw_vers', []], ['sysctl', ['-n', 'machdep.cpu.brand_string', 'hw.ncpu', 'hw.memsize']], ['uptime', []]],
  disk: [['df', ['-h', '/', '/System/Volumes/Data']]],
  battery: [['pmset', ['-g', 'batt']]],
  processes: [['ps', ['-Arceo', 'pid,pcpu,pmem,comm']]],
};
export const SYSTEM_TOPICS = [...Object.keys(COMMANDS), 'apps'] as const;

const run = (bin: string, args: string[]) => new Promise<string>((resolve) =>
  execFile(bin, args, { timeout: 5000, maxBuffer: 1 << 20, env: { PATH: '/usr/bin:/bin:/usr/sbin:/sbin' } },
    (e, out) => resolve(e ? `${bin}: unavailable` : out.trim())));

export async function systemInfo(topic: string): Promise<string> {
  if (topic === 'apps') {
    try { return fs.readdirSync('/Applications').filter((n) => n.endsWith('.app')).map((n) => n.slice(0, -4)).join('\n'); }
    catch { return 'Applications: unavailable'; }
  }
  const cmds = COMMANDS[topic];
  if (!cmds) return `Unknown topic. Use one of: ${SYSTEM_TOPICS.join(', ')}.`;
  const out = (await Promise.all(cmds.map(([b, a]) => run(b, a)))).join('\n\n');
  return topic === 'processes' ? out.split('\n').slice(0, 26).join('\n') : out;
}
