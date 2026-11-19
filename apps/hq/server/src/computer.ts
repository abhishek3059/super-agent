import { execFileSync, spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { WebSocket } from 'ws';
import { db } from './db.js';
import { env } from './env.js';
import { confinedEnv, contained, tmpFor } from './sandbox.js';
import { deletingBots, livePid, recordPid, stopPid } from './lib/procs.js';
import { removeOwn } from './lib/own.js';
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
  '/Applications/ego lite.app/Contents/MacOS/ego lite',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
];
const chromeBin = () => env.chromeBin || CHROMES.find((p) => fs.existsSync(p)) || '';

/** The browser app's bundle id (see Confinement.tempPrefix), read from the app around the binary. */
function bundleId(bin: string): string | undefined {
  const plist = bin.match(/^(.*\.app)\/Contents\/MacOS\//)?.[1];
  if (!plist) return undefined;
  try { return execFileSync('plutil', ['-extract', 'CFBundleIdentifier', 'raw', `${plist}/Contents/Info.plist`], { encoding: 'utf8', timeout: 3000 }).trim(); } catch { return undefined; }
}

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

/** The browser we started for this bot: its command line names its own debugging port. */
const chromeMarker = (botId: string) => `--remote-debugging-port=${cdpPortFor(botId)} `;
const chromePid = (botId: string) => livePid(`${botId}.chrome`, chromeMarker(botId));

async function startChrome(botId: string): Promise<void> {
  // Only a browser this server started (always inside the sandbox) is used. Anything else on the port is refused.
  if (await alive(botId)) {
    if (chromePid(botId)) return;
    throw new Error(`Port ${cdpPortFor(botId)} is taken by a browser this app did not start. Close it and try again.`);
  }
  if (deletingBots.has(botId)) throw new Error('bot unavailable');
  const bin = chromeBin();
  if (!bin) throw new Error('No Chrome found. Install Google Chrome or set CHROME_BIN.');
  if (!validId(botId)) throw new Error('bad bot id');
  const bot = db.prepare('SELECT name, label FROM bots WHERE id=?').get(botId) as any;
  const esc = (s: string) => String(s ?? '').replace(/[<>&"']/g, '');
  const home = `data:text/html,${encodeURIComponent(
    `<title>${esc(bot?.name)}</title><body style="margin:0;height:100vh;display:grid;place-items:center;background:#0b0f14;color:#cfe8ff;font:500 28px system-ui"><div style="text-align:center">${esc(bot?.name)}<div style="font-size:14px;opacity:.6;margin-top:8px">${esc(bot?.label)}</div></div>`,
  )}`;
  fs.mkdirSync(profileDir(botId), { recursive: true, mode: 0o700 });
  fs.mkdirSync(path.join(env.filesDir, botId), { recursive: true });
  // Lock links from an earlier run point into the system temp folder; a new start makes its own.
  for (const f of ['SingletonLock', 'SingletonSocket', 'SingletonCookie']) fs.rmSync(path.join(profileDir(botId), f), { force: true });
  // The bot drives this browser freely (file:// pages, uploads, downloads), so the browser itself is
  // confined: its own profile and the bot's working folder, the internet, and no local ports.
  // Chrome cannot start its own inner sandbox inside ours, hence --no-sandbox; ours covers every
  // process it starts. The Keychain is closed to it, hence the mock one.
  // shortcut: pages lose Chrome's per-site process isolation from each other; upgrade when Chrome
  // can nest inside an outer sandbox.
  const run = contained(bin, [
    '--headless=new', '--no-sandbox', '--use-mock-keychain', `--remote-debugging-port=${cdpPortFor(botId)}`, '--remote-debugging-address=127.0.0.1',
    `--user-data-dir=${profileDir(botId)}`, `--window-size=${SCREEN.width},${SCREEN.height + CHROME_UI}`,
    '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--hide-scrollbars', home,
  ], { read: [], write: [profileDir(botId), path.join(env.filesDir, botId)], localPorts: [], listen: cdpPortFor(botId), tempPrefix: bundleId(bin) }, `${botId}.c`);
  // Nothing of this server's environment (the voice key lives there) reaches the browser.
  const child = spawn(run.bin, run.args, { detached: true, stdio: 'ignore', env: confinedEnv(`${botId}.c`) });
  let failed = '';
  child.once('error', (e) => { failed = e.message; });
  child.unref();
  recordPid(`${botId}.chrome`, child.pid);
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 250));
    if (failed) throw new Error(`could not start Chrome: ${failed}`);
    if (await alive(botId)) return;
  }
  // Do not leave a half-started browser holding the profile's lock.
  if (child.pid) try { process.kill(-child.pid, 'SIGKILL'); } catch { /* gone */ }
  throw new Error('Chrome did not come up within 10 seconds.');
}

/** The bot's Chrome is up. Safe to call often; concurrent calls share one start. */
export function readyScreen(_userId: string, botId: string): Promise<void> {
  if (deletingBots.has(botId) || !db.prepare('SELECT 1 FROM bots WHERE id=?').get(botId)) {
    return Promise.reject(new Error('bot unavailable'));
  }
  let p = starting.get(botId);
  if (!p) {
    p = startChrome(botId).finally(() => starting.delete(botId));
    starting.set(botId, p);
  }
  return p;
}

/** Called before a bot starts working, so its first turn finds its own browser and starts no other. */
export const screenForWork = readyScreen;

const stopChrome = (botId: string) => stopPid(`${botId}.chrome`, chromeMarker(botId));

/** Close everything in the bot's browser and bring it back to its start page. Logins stay. */
export async function resetBotScreen(userId: string, botId: string): Promise<void> {
  if (deletingBots.has(botId)) throw new Error('bot unavailable');
  await stopChrome(botId);
  await readyScreen(userId, botId);
}

export async function releaseScreen(botId: string): Promise<void> {
  await starting.get(botId)?.catch(() => {});
  await stopChrome(botId);
}

/** A deleted bot leaves nothing behind: its browser profile and its Library folder go. */
export async function forgetBotFiles(botId: string): Promise<void> {
  if (!validId(botId)) return;
  for (const root of [env.profilesDir, env.filesDir]) {
    const dir = path.join(root, botId);
    if (path.dirname(dir) === root) await removeOwn(dir);
  }
  // Its temporary folders too, so a later bot never inherits one (they are named from the bot id).
  for (const name of [`${botId}.g`, `${botId}.c`]) await removeOwn(tmpFor(name));
}

/** On server start: stop every browser an earlier run left, so each starts again under current rules. */
export async function stopAllBrowsers(): Promise<void> {
  const bots = db.prepare("SELECT id FROM bots WHERE COALESCE(kind,'agent') <> 'room'").all() as { id: string }[];
  await Promise.all(bots.map((b) => stopChrome(b.id)));
}

// ---------- DevTools helpers ----------

export interface PageTarget { id: string; webSocketDebuggerUrl: string; url: string; title: string }

/** The tab the bot is on: Chrome lists the most recently used page first. */
export async function activePage(botId: string): Promise<PageTarget | null> {
  // Only the browser this server started for the bot, and only a page address on that same port:
  // a bot that closed its browser and answered on the port itself could otherwise send the server
  // (which is not sandboxed) to any address it likes.
  if (!chromePid(botId)) return null;
  const prefix = `ws://127.0.0.1:${cdpPortFor(botId)}/devtools/page/`;
  try {
    const list = (await (await fetch(`${cdpUrlFor(botId)}/json/list`, { signal: AbortSignal.timeout(2000) })).json()) as any[];
    return list.find((t) => t.type === 'page' && typeof t.webSocketDebuggerUrl === 'string' && t.webSocketDebuggerUrl.startsWith(prefix)
      && /^[A-Za-z0-9_-]+$/.test(t.webSocketDebuggerUrl.slice(prefix.length))) ?? null;
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
