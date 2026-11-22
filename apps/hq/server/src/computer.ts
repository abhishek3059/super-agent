import { execFileSync, spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { WebSocket } from 'ws';
import { db } from './db.js';
import { env } from './env.js';
import { confinedEnv, contained, tmpFor } from './sandbox.js';
import { deletingBots, livePid, recordPid, stopPid } from './lib/procs.js';
import { removeOwn, writeOwn } from './lib/own.js';
import { reserveCdpBase } from './lib/cdp-ports.js';
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
  '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/snap/bin/chromium',
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

// ---------- the bot's desktop ----------

const esc = (v: unknown) => String(v ?? '').replace(/[<>&"']/g, (c) => `&#${c.charCodeAt(0)};`);
const HOME_FILE = 'hq-home.html';
const homeUrl = (botId: string) => pathToFileURL(path.join(profileDir(botId), HOME_FILE)).href;

const APPS: [string, string, string][] = [
  ['Search', '🔎', 'https://www.google.com/'],
  ['Gmail', '✉️', 'https://mail.google.com/'],
  ['YouTube', '▶️', 'https://www.youtube.com/'],
  ['Maps', '🗺️', 'https://maps.google.com/'],
  ['GitHub', '🐙', 'https://github.com/'],
  ['Wikipedia', '📚', 'https://en.wikipedia.org/'],
  ['Hacker News', '📰', 'https://news.ycombinator.com/'],
];

/** The page a bot's browser opens on: a desktop with a clock, a search box and app tiles. */
export function desktopHtml(o: { owner: string; name: string; label: string; filesUrl: string }): string {
  const tile = (label: string, icon: string, href: string) =>
    `<a class="app" href="${esc(href)}"><span class="ic">${icon}</span><span>${esc(label)}</span></a>`;
  return `<!doctype html><meta charset="utf-8"><title>Home</title><style>
body{margin:0;height:100vh;display:grid;place-items:center;font:15px system-ui;color:#1d2330;
background:radial-gradient(circle at 20% 10%,#e8f1ff,transparent 50%),radial-gradient(circle at 85% 90%,#f3e9ff,transparent 50%),#f4f6fa}
main{text-align:center}#t{font-size:96px;font-weight:300;letter-spacing:-2px}#d{opacity:.6;margin-bottom:18px}
h1{margin:0;font-size:30px}.role{opacity:.6;margin:4px 0 22px}
form input{width:460px;padding:12px 18px;border-radius:24px;border:1px solid #d5dbe6;font:inherit;outline:none;background:#fff}
.apps{display:grid;grid-template-columns:repeat(4,96px);gap:18px;justify-content:center;margin-top:30px}
.app{display:flex;flex-direction:column;align-items:center;gap:8px;color:inherit;text-decoration:none;font-size:13px}
.ic{width:64px;height:64px;border-radius:18px;background:#fff;display:grid;place-items:center;font-size:30px;box-shadow:0 2px 10px #0001}
.app:hover .ic{box-shadow:0 4px 16px #0002}</style>
<main><div id="t"></div><div id="d"></div><h1>Welcome back, ${esc(o.owner)}</h1><div class="role">${esc(o.name)}${o.label ? ` · ${esc(o.label)}` : ''}</div>
<form action="https://www.google.com/search"><input name="q" placeholder="Search Google or type a URL" autofocus></form>
<div class="apps">${tile('Files', '📁', o.filesUrl)}${APPS.map((a) => tile(...a)).join('')}</div></main>
<script>function f(){const n=new Date();t.textContent=n.toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});
d.textContent=n.toLocaleDateString([], {weekday:'long',month:'long',day:'numeric'})}f();setInterval(f,1000)</script>`;
}

/** Written fresh on each start, so a rename shows and nothing the browser left there is kept. */
function writeHome(botId: string) {
  const b = db.prepare('SELECT b.name, b.label, u.name AS owner FROM bots b JOIN users u ON u.id=b.user_id WHERE b.id=?').get(botId) as any;
  writeOwn(profileDir(botId), HOME_FILE, desktopHtml({ owner: b?.owner ?? env.ownerName, name: b?.name, label: b?.label, filesUrl: `${pathToFileURL(path.join(env.filesDir, botId)).href}/` }), 0o644);
}

// ---------- tabs, for the viewer's browser bar ----------

export interface Tab { id: string; title: string; url: string }
const TAB_ID = /^[A-Za-z0-9_-]{1,64}$/;

/** What the address bar typed means: a web address, or else a search. Only http(s) is ever opened. */
export function addressToUrl(input: string): string {
  const s = input.trim().slice(0, 2000);
  const search = `https://www.google.com/search?q=${encodeURIComponent(s)}`;
  let u: URL;
  try { u = new URL(/^[a-z][a-z0-9+.-]*:(?!\d)/i.test(s) ? s : `https://${s}`); } catch { return search; }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') return search;
  // A bare word ("weather") is a search; something with a dot or a port is an address.
  return /^https?:/i.test(s) || (!/\s/.test(s) && (u.hostname.includes('.') || !!u.port)) ? u.href : search;
}

// Chrome's tab list sends titles HTML-escaped.
const ENTITY: Record<string, string> = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'" };
const unescapeTitle = (t: string) => t.replace(/&(amp|lt|gt|quot|#39);/g, (m) => ENTITY[m]);

/** Open tabs, the one on screen first. */
export async function listTabs(botId: string): Promise<Tab[]> {
  if (!chromePid(botId)) return [];
  try {
    const list = (await (await fetch(`${cdpUrlFor(botId)}/json/list`, { signal: AbortSignal.timeout(2000) })).json()) as any[];
    return list.filter((t) => t.type === 'page' && TAB_ID.test(t.id))
      .map((t) => ({ id: t.id, title: unescapeTitle(String(t.title ?? '')).slice(0, 200), url: String(t.url ?? '').slice(0, 2000) }));
  } catch { return []; }
}

export type TabAction = { action: 'new' } | { action: 'activate' | 'close'; id: string } | { action: 'navigate'; url: string }
  | { action: 'back' | 'forward' | 'reload' | 'home' };

export async function tabAction(botId: string, a: TabAction): Promise<void> {
  if (!chromePid(botId)) throw new Error('screen not running');
  const devtools = (p: string, method = 'GET') => fetch(`${cdpUrlFor(botId)}${p}`, { method, signal: AbortSignal.timeout(4000) })
    .then((r) => { if (!r.ok) throw new Error('the browser refused'); });
  switch (a.action) {
    case 'new': return devtools(`/json/new?${encodeURIComponent(homeUrl(botId))}`, 'PUT');
    case 'activate': case 'close':
      if (!TAB_ID.test(a.id)) throw new Error('bad tab');
      return devtools(`/json/${a.action}/${a.id}`);
    case 'navigate': await cdpOnce(botId, 'Page.navigate', { url: addressToUrl(a.url) }); return;
    case 'home': await cdpOnce(botId, 'Page.navigate', { url: homeUrl(botId) }); return;
    case 'reload': await cdpOnce(botId, 'Page.reload'); return;
    case 'back': case 'forward': {
      const h = await cdpOnce(botId, 'Page.getNavigationHistory');
      const entry = h?.entries?.[h.currentIndex + (a.action === 'back' ? -1 : 1)];
      if (entry) await cdpOnce(botId, 'Page.navigateToHistoryEntry', { entryId: entry.id });
      return;
    }
  }
}

const starting = new Map<string, Promise<void>>();

/** The profile path distinguishes workspaces and remains stable when the port block moves. */
const chromeMarker = (botId: string) => `--user-data-dir=${profileDir(botId)} `;
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
  fs.mkdirSync(profileDir(botId), { recursive: true, mode: 0o700 });
  fs.mkdirSync(path.join(env.filesDir, botId), { recursive: true });
  writeHome(botId);
  // Lock links from an earlier run point into the system temp folder; a new start makes its own.
  for (const f of ['SingletonLock', 'SingletonSocket', 'SingletonCookie']) fs.rmSync(path.join(profileDir(botId), f), { force: true });
  // The bot drives this browser freely (file:// pages, uploads, downloads), so the browser itself is
  // confined: its own profile and the bot's working folder, and the internet through the proxy.
  // Chrome cannot start its own inner sandbox inside ours, hence --no-sandbox; ours covers every
  // process it starts. The Keychain is closed to it, hence the mock one.
  // shortcut: pages lose Chrome's per-site process isolation from each other; upgrade when Chrome
  // can nest inside an outer sandbox.
  const run = contained(bin, [
    '--headless=new', '--no-sandbox', '--use-mock-keychain', `--remote-debugging-port=${cdpPortFor(botId)}`, '--remote-debugging-address=127.0.0.1',
    `--user-data-dir=${profileDir(botId)}`, `--window-size=${SCREEN.width},${SCREEN.height + CHROME_UI}`,
    '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--hide-scrollbars',
    // The internet only through the proxy, which refuses loopback and private addresses.
    `--proxy-server=http://127.0.0.1:${env.egressPort}`, '--proxy-bypass-list=<-loopback>', homeUrl(botId),
  ], { read: [], write: [profileDir(botId), path.join(env.filesDir, botId)], localPorts: [env.egressPort], listen: cdpPortFor(botId), tempPrefix: bundleId(bin) }, `${botId}.c`);
  // Nothing of this server's environment (the voice key lives there) reaches the browser.
  const child = spawn(run.bin, run.args, { detached: true, stdio: 'ignore', env: confinedEnv(`${botId}.c`) });
  let failed = '';
  child.once('error', (e) => { failed = e.message; });
  child.unref();
  run.attach?.(child);
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

/** Choose ports once, before any Hermes gateway binds its browser URL in the sandbox. */
export async function configureBrowserPorts(): Promise<void> {
  if (env.explicitCdpBase) return;
  const bots = db.prepare('SELECT engine_port FROM bots WHERE engine_port IS NOT NULL').all() as { engine_port: number }[];
  const offsets = bots.map((bot) => bot.engine_port - env.enginePortBase + 1);
  const services = [env.port, env.mcpPort, env.egressPort];
  const { base } = await reserveCdpBase(offsets.length ? offsets : [1], services);
  env.cdpPortBase = base;
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
