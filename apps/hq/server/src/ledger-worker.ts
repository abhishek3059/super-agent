import fs from 'node:fs/promises';
import { appendRow, emitBot } from './store.js';
import { db } from './db.js';
import { env, workspaceFor } from './env.js';
import { canContain } from './sandbox.js';
import { isBotBusy, runInBotQueue, runLedgerTurn } from './agent/loop.js';
import { jobs, roles, type Role } from './ledger-client.js';

function worker(role: Role) {
  return db.prepare(`SELECT id, user_id FROM bots WHERE kind = 'agent' AND engine = 'managed'
    AND lower(name) = ? AND user_id = (SELECT id FROM users ORDER BY created_at, id LIMIT 1)
    ORDER BY created_at, id LIMIT 1`).get(role) as { id: string; user_id: string } | undefined;
}

// Receipts name only top-level regular files created or changed by this turn.
async function artifacts(botId: string) {
  const root = workspaceFor(botId);
  const files = new Map<string, string>();
  if (await fs.realpath(root).catch(() => null) !== root) return files;
  for (const entry of await fs.readdir(root, { withFileTypes: true }).catch(() => [])) {
    if (!entry.isFile() || !/^[A-Za-z0-9_.-]{1,64}$/.test(entry.name)) continue;
    const stat = await fs.lstat(`${root}/${entry.name}`).catch(() => null);
    if (stat?.isFile()) files.set(entry.name, `${stat.ino}:${stat.mtimeMs}:${stat.size}`);
  }
  return files;
}

export function startLedgerWorkers(): () => Promise<void> {
  const running = new Map<Role, Promise<void>>();
  const timers: NodeJS.Timeout[] = [];
  if (env.ledgerToken && env.localModel && canContain()) {
    for (const role of roles) {
      timers.push(setInterval(() => {
        if (running.has(role)) return;
        const tick = (async () => {
          const bot = worker(role);
          if (!bot || isBotBusy(bot.id)) return;
          await runInBotQueue(bot.id, async () => {
            const claim = await jobs.claim(role);
            if (!claim) return;
            const before = await artifacts(bot.id);
            const result = await runLedgerTurn(bot.id, claim.id, claim.instruction);
            const after = await artifacts(bot.id);
            const paths = [...after].filter(([name, stamp]) => before.get(name) !== stamp)
              .map(([name]) => name).slice(0, 8);
            const receipt = { ...result, artifacts: paths };
            // A repeat can recover a lost confirmation without rerunning the job.
            try { await jobs.finish(role, claim, receipt); } catch { await jobs.finish(role, claim, receipt); }
            appendRow(bot.id, 'notice', { type: 'notice', text: `Ledger job ${claim.id} ${receipt.state}`, tone: 'info' });
            emitBot(bot.id);
          });
        })().catch(() => {
          // A lost claim or completion is reconciled by expiry in the ledger.
          console.warn('[hq] ledger worker request failed', role);
        }).finally(() => { running.delete(role); });
        running.set(role, tick);
      }, 1500).unref());
    }
  }
  return async () => {
    for (const timer of timers) clearInterval(timer);
    await Promise.allSettled(running.values());
  };
}
