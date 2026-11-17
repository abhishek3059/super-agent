import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { WebSocket } from 'ws';
import { db } from './db.js';
import { env, workspaceFor } from './env.js';
import { contained, workspaceDirectory } from './sandbox.js';
import type { ComputerState } from './types.js';

/**
 * Each bot's own screen: a headless Chrome with its own profile folder and DevTools port, on this
 * machine and reachable on loopback only. The bot's Hermes browser tool drives that Chrome
 * (config `browser.cdp_url`), and the viewer shows it live (screen.ts). Nothing here touches the
 * operator's own browser or desktop.
 */

export const SCREEN = { width: 1280, height: 800 };
/** Headless Chrome still reserves this much of the window height for its (unseen) toolbar. */
const CHROME_UI = 87;

const CHROMES = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
];
const chromeBin = () => env.chromeBin || CHROMES.find((p) => fs.existsSync(p)) || '';

const validId = (botId: string) => /^bot_[\w-]+$/.test(botId);
const profileDir = (botId: string) => path.join(env.profilesDir, botId);

/** One port per bot, derived from its engine port so the two never collide across bots. */
export function cdpPortFor(botId: string): number {
  const p = (db.prepare('SELECT engine_port FROM bots WHERE id=?').get(botId) as any)?.engine_port as number | undefined;
  return p ? env.cdpPortBase + (p - env.enginePortBase) + 1 : env.cdpPortBase;
}

/** DevTools address of this bot's Chrome (for Hermes' browser tools). */
export const cdpUrlFor = (botId: string) => `http://127.0.0.1:${cdpPortFor(botId)}`;

const alive = (botId: string) =>
  fetch(`${cdpUrlFor(botId)}/json/version`, { signal: AbortSignal.timeout(1500) }).then((r) => r.ok, () => false);

export function computerState(userId: string): ComputerState {
  const bots = db.prepare("SELECT id FROM bots WHERE user_id=? AND COALESCE(kind,'agent') <> 'room'").all(userId) as any[];
  const bin = chromeBin();
  return {
    status: bin ? 'running' : 'error',
    error: bin ? null : 'No Chrome found. Install Google Chrome or set CHROME_BIN.',
    screens: bots.map((b) => ({ botId: b.id, screenId: b.id, ...SCREEN })),
    maxScreens: env.maxBots,
  };
}

const starting = new Map<string, Promise<void>>();
const children = new Map<string, ReturnType<typeof spawn>>();

async function startChrome(botId: string): Promise<void> {
  if (await alive(botId)) {
    if (children.has(botId)) return;
    throw new Error('Browser port already occupied');
  }
  const bin = chromeBin();
  if (!bin) throw new Error('No Chrome found. Install Google Chrome or set CHROME_BIN.');
  if (!validId(botId)) throw new Error('bad bot id');
  const bot = db.prepare('SELECT name, label FROM bots WHERE id=?').get(botId) as any;
  const esc = (s: string) => String(s ?? '').replace(/[<>&"']/g, '');
  const home = `data:text/html,${encodeURIComponent(
    `<title>${esc(bot?.name)}</title><body style="margin:0;height:100vh;display:grid;place-items:center;background:#0b0f14;color:#cfe8ff;font:500 28px system-ui"><div style="text-align:center">${esc(bot?.name)}<div style="font-size:14px;opacity:.6;margin-top:8px">${esc(bot?.label)}</div></div>`,
  )}`;
  const profile = profileDir(botId);
  const workspace = workspaceFor(botId);
  for (const dir of [profile, workspace, path.join(profile, 'tmp')]) workspaceDirectory(dir);
  // Chrome's nested sandbox cannot start under this profile. The outer sandbox blocks Internet access.
  const run = contained(bin, [
    '--headless=new', '--no-sandbox', '--use-mock-keychain', `--remote-debugging-port=${cdpPortFor(botId)}`, '--remote-debugging-address=127.0.0.1',
    `--user-data-dir=${profileDir(botId)}`, `--window-size=${SCREEN.width},${SCREEN.height + CHROME_UI}`,
    '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--hide-scrollbars', home,
  ], [bin.slice(0, bin.indexOf('.app/') + 4)].filter((p) => p.endsWith('.app')), [profile, workspace], [], cdpPortFor(botId));
  const child = spawn(run.bin, run.args, {
    cwd: workspace, detached: true, stdio: 'ignore',
    env: { HOME: profile, TMPDIR: path.join(profile, 'tmp'), MAC_CHROMIUM_TMPDIR: path.join(profile, 'tmp'), PATH: '/usr/bin:/bin' },
  });
  children.set(botId, child);
  const clear = () => { if (children.get(botId) === child) children.delete(botId); };
  child.once('exit', clear);
  child.once('error', clear);
  let failed = '';
  child.once('error', (e) => { failed = e.message; });
  child.once('exit', (code, signal) => { failed = `contained Chrome exited (${code ?? signal})`; });
  child.unref();
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 250));
    if (failed) throw new Error(`could not start Chrome: ${failed}`);
    if (children.get(botId) === child && await alive(botId)) return;
  }
  await stopChrome(botId);
  throw new Error('Chrome did not come up within 10 seconds.');
}

/** The bot's Chrome is up. Safe to call often; concurrent calls share one start. */
export function readyScreen(_userId: string, botId: string): Promise<void> {
  let p = starting.get(botId);
  if (!p) {
    p = startChrome(botId).finally(() => starting.delete(botId));
    starting.set(botId, p);
  }
  return p;
}

/** Called before a bot starts working, so its first turn finds its own browser and starts no other. */
export const screenForWork = readyScreen;

async function stopChrome(botId: string) {
  const pid = children.get(botId)?.pid;
  if (!pid) return;
  try { process.kill(-pid, 'SIGTERM'); } catch { return; }
  for (let i = 0; i < 20 && children.has(botId); i++) await new Promise((r) => setTimeout(r, 250));
  if (children.has(botId)) {
    try { process.kill(-pid, 'SIGKILL'); } catch { /* already stopped */ }
  }
}

/** Close everything in the bot's browser and bring it back to its start page. Logins stay. */
export async function resetBotScreen(userId: string, botId: string): Promise<void> {
  await stopChrome(botId);
  await readyScreen(userId, botId);
}

export const releaseScreen = stopChrome;

/** A deleted bot leaves nothing behind: its browser profile and its Library folder go. */
export async function forgetBotFiles(botId: string): Promise<void> {
  if (!validId(botId)) return;
  for (const root of [env.profilesDir, env.filesDir]) {
    const dir = path.join(root, botId);
    if (path.dirname(dir) === root) fs.rmSync(dir, { recursive: true, force: true });
  }
}

// ---------- DevTools helpers ----------

export interface PageTarget { id: string; webSocketDebuggerUrl: string; url: string; title: string }

/** The tab the bot is on: Chrome lists the most recently used page first. */
export async function activePage(botId: string): Promise<PageTarget | null> {
  try {
    const list = (await (await fetch(`${cdpUrlFor(botId)}/json/list`, { signal: AbortSignal.timeout(2000) })).json()) as any[];
    return list.find((t) => t.type === 'page' && t.webSocketDebuggerUrl) ?? null;
  } catch { return null; }
}

/** One DevTools command on the bot's current tab. */
export async function cdpOnce(botId: string, method: string, params: object = {}, timeoutMs = 8000): Promise<any> {
  const page = await activePage(botId);
  if (!page) throw new Error('no page');
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    const t = setTimeout(() => { ws.terminate(); reject(new Error('timeout')); }, timeoutMs);
    ws.on('open', () => ws.send(JSON.stringify({ id: 1, method, params })));
    ws.on('message', (d) => {
      const m = JSON.parse(String(d));
      if (m.id !== 1) return;
      clearTimeout(t);
      ws.close();
      m.error ? reject(new Error(m.error.message)) : resolve(m.result);
    });
    ws.on('error', (e) => { clearTimeout(t); reject(e); });
  });
}

export async function screenshot(botId: string): Promise<Buffer | null> {
  if (!(await alive(botId))) return null;
  try {
    const r = await cdpOnce(botId, 'Page.captureScreenshot', { format: 'jpeg', quality: 60 });
    return Buffer.from(r.data, 'base64');
  } catch { return null; }
}
