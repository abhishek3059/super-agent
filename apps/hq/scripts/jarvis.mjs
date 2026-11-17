#!/usr/bin/env node
// `npm run jarvis`: start Jarvis HQ if it is not running, then open it in the browser, signed in.
// `npm run open` only opens it. Sign-in is a one-time link; the key that mints it is derived from
// the session secret in the data folder, so only someone who can read that folder can sign in.
import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

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
  spawn(process.execPath, ['dist/index.js'], { cwd: path.join(root, 'server'), detached: true, stdio: ['ignore', log, log] }).unref();
  for (let i = 0; i < 40 && !(await up()); i++) await new Promise((r) => setTimeout(r, 250));
  if (!(await up())) { console.error(`The server did not start. See ${path.join(dataDir, 'server.log')}`); process.exit(1); }
  console.log(`Jarvis HQ started on ${base} (log: ${path.join(dataDir, 'server.log')})`);
}

const secret = process.env.SESSION_SECRET ?? fs.readFileSync(path.join(dataDir, 'session-secret'), 'utf8').trim();
const key = crypto.createHmac('sha256', secret).update('owner-login').digest('hex');
const r = await fetch(`${base}/api/auth/owner`, { method: 'POST', headers: { Authorization: `Bearer ${key}` } });
if (!r.ok) { console.error(`Sign-in was refused (${r.status}). Is HQ_DATA_DIR the folder the server uses?`); process.exit(1); }
const { url } = await r.json();
const opener = process.platform === 'darwin' ? 'open' : process.platform === 'win32' ? 'explorer' : 'xdg-open';
spawn(opener, [url], { detached: true, stdio: 'ignore' }).unref();
console.log('Opened Jarvis HQ in your browser.');
