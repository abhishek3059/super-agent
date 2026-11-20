#!/usr/bin/env node
// `npm run jarvis`: start Jarvis HQ if it is not running, then open it in the browser, signed in.
// `npm run open` only opens it. The launcher and server authenticate each other before sign-in.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { ownerLogin } from './owner-login.mjs';

const root = path.resolve(import.meta.dirname, '..');
const port = Number(process.env.PORT ?? 8787);
const base = `http://127.0.0.1:${port}`;
const dataDir = process.env.HQ_DATA_DIR ?? path.join(os.homedir(), '.super-agent', 'hq');

const up = () => fetch(`${base}/api/health`, { signal: AbortSignal.timeout(1500) }).then((r) => r.ok, () => false);

if (!(await up())) {
  if (process.argv.includes('--open-only')) { console.error(`Jarvis HQ is not running on ${base}. Start it with: npm run jarvis`); process.exit(1); }
  if (!fs.existsSync(path.join(root, 'server/dist/index.js')) || !fs.existsSync(path.join(root, 'web/dist/index.html'))) {
    console.error('Not built yet. Run: npm ci && npm run build'); process.exit(1);
  }
  fs.mkdirSync(dataDir, { recursive: true });
  const log = fs.openSync(path.join(dataDir, 'server.log'), 'a', 0o600);
  const child = spawn(process.execPath, ['dist/index.js'], { cwd: path.join(root, 'server'), detached: true, stdio: ['ignore', log, log] });
  fs.closeSync(log);
  let exited = false;
  child.once('exit', () => { exited = true; });
  child.once('error', () => { exited = true; });
  child.unref();
  const deadline = Date.now() + 20_000;
  let ready = false;
  while (!exited && Date.now() < deadline) {
    if (await up()) { ready = true; break; }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  if (!ready) { console.error(`The server did not start. See ${path.join(dataDir, 'server.log')}`); process.exit(1); }
  console.log(`Jarvis HQ started on ${base} (log: ${path.join(dataDir, 'server.log')})`);
}

let url;
try { url = await ownerLogin(base, dataDir); }
catch {
  console.error('Could not sign in to the local Jarvis HQ server. Check its port and HQ_DATA_DIR.');
  process.exit(1);
}
const opener = process.platform === 'darwin' ? 'open' : process.platform === 'win32' ? 'explorer' : 'xdg-open';
spawn(opener, [url], { detached: true, stdio: 'ignore' }).unref();
console.log('Opened Jarvis HQ in your browser.');
