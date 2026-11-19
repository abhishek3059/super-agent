import assert from 'node:assert/strict';
import { spawn, type ChildProcess } from 'node:child_process';
import { once } from 'node:events';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';
import { setTimeout as sleep } from 'node:timers/promises';

const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hq-lifecycle-'));
process.env.HQ_DATA_DIR = dataDir;
process.env.DB_PATH = path.join(dataDir, 'hq.db');

const { deletingBots, livePid, recordPid, stopPid } = await import('../src/lib/procs.js');
const { db } = await import('../src/db.js');
const { initRooms } = await import('../src/agent/rooms.js');
initRooms();
db.prepare('INSERT INTO users(id,email,name,created_at) VALUES (?,?,?,?)').run('usr_test', 'owner@localhost', 'Test', Date.now());
const addBot = db.prepare(`
  INSERT INTO bots (id, user_id, name, engine, engine_port, created_at, updated_at)
  VALUES (?, 'usr_test', 'Test Bot', 'managed', ?, ?, ?)
`);
after(() => {
  db.close();
  fs.rmSync(dataDir, { recursive: true, force: true });
});

test('a failing ps leaves the pid record and the bot available for a later deletion retry', async () => {
  const { api } = await import('../src/routes.js');
  const { engineFor } = await import('../src/engine.js');
  const { readyScreen } = await import('../src/computer.js');
  const botId = 'bot_pid';
  addBot.run(botId, 8651, Date.now(), Date.now());
  const { createSession } = await import('../src/lib/auth.js');
  const authorization = `Bearer ${createSession('usr_test')}`;
  const name = `${botId}.gateway`;
  const record = path.join(dataDir, 'run', `${name}.pid`);
  const bin = path.join(dataDir, 'bin');
  const ps = path.join(bin, 'ps');
  fs.mkdirSync(bin);
  fs.writeFileSync(ps, '#!/bin/sh\nprintf "simulated ps failure\\n" >&2\nexit 1\n', { mode: 0o700 });
  const oldPath = process.env.PATH;
  process.env.PATH = bin;
  try {
    recordPid(name, process.pid);
    assert.equal(livePid(name, 'node'), null);
    await assert.rejects(stopPid(name, 'node'), /could not verify/i);
    assert.equal(fs.readFileSync(record, 'utf8'), String(process.pid));
    const request = () => api.request(`/bots/${botId}`, {
      method: 'DELETE', headers: { authorization },
    });
    const blocked = await request();
    assert.equal(blocked.status, 503);
    assert.ok(db.prepare('SELECT 1 FROM bots WHERE id=?').get(botId));
    assert.equal(fs.readFileSync(record, 'utf8'), String(process.pid));
    assert.equal(deletingBots.has(botId), false, 'deletion releases the guard on failure');

    // Neither lifecycle entry point can start a marked bot.
    deletingBots.add(botId);
    try {
      await assert.rejects(engineFor(botId), /bot unavailable/);
      await assert.rejects(readyScreen('usr_test', botId), /bot unavailable/);
      assert.equal((await request()).status, 409);
    } finally { deletingBots.delete(botId); }

    fs.writeFileSync(ps, '#!/bin/sh\nexit 1\n');
    assert.equal((await request()).status, 200);
    assert.equal(fs.existsSync(record), false, 'a confirmed absent process releases the stale record');
    assert.equal(db.prepare('SELECT 1 FROM bots WHERE id=?').get(botId), undefined);
  } finally {
    if (oldPath === undefined) delete process.env.PATH;
    else process.env.PATH = oldPath;
  }
});

async function waitFor(check: () => boolean | Promise<boolean>): Promise<void> {
  const deadline = performance.now() + 6000;
  while (performance.now() < deadline) {
    if (await check()) return;
    await sleep(25);
  }
  assert.fail('Timed out waiting for the process checkpoint');
}

test('HQ leaves the socket unbound until its old browser and gateway have exited', async (t) => {
  const botId = 'bot_startup';
  addBot.run(botId, 8650, Date.now(), Date.now());
  const children: ChildProcess[] = [];
  t.after(async () => {
    for (const child of children) {
      if (child.exitCode !== null || child.signalCode !== null) continue;
      const stopped = once(child, 'exit');
      child.kill('SIGKILL');
      await stopped;
    }
  });

  const staleScript = `
    const fs = require('node:fs');
    const [ready, stopping, release] = process.argv.slice(1);
    process.on('SIGTERM', () => fs.writeFileSync(stopping, ''));
    setInterval(() => { if (fs.existsSync(release)) process.exit(0); }, 20);
    fs.writeFileSync(ready, '');
  `;
  const oldProcesses = Object.entries({ chrome: '--remote-debugging-port=9301', gateway: 'gateway run' })
    .map(([role, marker]) => {
      const files = ['ready', 'stopping', 'release'].map((state) => path.join(dataDir, `${role}.${state}`));
      const child = spawn(process.execPath, ['-e', staleScript, '--', ...files, marker, 'fixture'], { detached: true, stdio: 'ignore' });
      children.push(child);
      recordPid(`${botId}.${role}`, child.pid);
      return files;
    });
  await waitFor(() => oldProcesses.every(([ready]) => fs.existsSync(ready)));

  const reservation = net.createServer().listen(0, '127.0.0.1');
  await once(reservation, 'listening');
  const { port } = reservation.address() as net.AddressInfo;
  const released = once(reservation, 'close');
  reservation.close();
  await released;

  const server = spawn(process.execPath, ['--import', 'tsx', 'src/index.ts'], {
    cwd: path.resolve(import.meta.dirname, '..'),
    env: {
      ...process.env, PORT: String(port), APP_URL: `http://127.0.0.1:${port}`,
      CDP_PORT_BASE: '9300', ENGINE_PORT_BASE: '8650', HQ_NO_SCHEDULER: '1',
      HERMES_BIN: '/dev/null', ENGINES_DIR: path.join(dataDir, 'engines'),
      HERMES_HOME_PRIMARY: path.join(dataDir, 'empty-hermes-home'),
    },
    stdio: 'ignore',
  });
  children.push(server);
  await waitFor(() => oldProcesses.every(([, stopping]) => fs.existsSync(stopping)));
  const socket = net.createConnection({ host: '127.0.0.1', port });
  try { await assert.rejects(once(socket, 'connect'), { code: 'ECONNREFUSED' }); }
  finally { socket.destroy(); }

  for (const [, , release] of oldProcesses) fs.writeFileSync(release, '');
  const health = `http://127.0.0.1:${port}/api/health`;
  await waitFor(() => fetch(health, { signal: AbortSignal.timeout(500) }).then((r) => r.ok, () => false));
  assert.equal(children[0].exitCode, 0);
  assert.equal(children[1].exitCode, 0);
});
