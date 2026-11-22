// Jarvis desktop overlay: a passive, click-through companion over every app. It never takes focus,
// never captures the screen and never clicks. It hears HQ's companion state over the same loopback
// sign-in the `npm run jarvis` launcher uses, and only the main process ever holds the session.
import { app, BrowserWindow, Menu, Tray, nativeImage, screen, session } from 'electron';
import os from 'node:os';
import path from 'node:path';
import { ownerLogin } from '../scripts/owner-login.mjs';

const here = import.meta.dirname;
const base = `http://127.0.0.1:${Number(process.env.PORT ?? 8787)}`;
// On Windows with HQ in WSL2, point this at the WSL data folder (see apps/hq/README.md).
const dataDir = process.env.HQ_DATA_DIR ?? path.join(os.homedir(), '.super-agent', 'hq');

let win = null;
let tray = null;
let mode = 'follow';
let token = '';
let quitting = false;
let signing = null;
let area = null;

function send(channel, value) { if (win && !win.isDestroyed()) win.webContents.send(channel, value); }

function createOverlay() {
  win = new BrowserWindow({
    show: false, frame: false, transparent: true, backgroundColor: '#00000000', hasShadow: false,
    focusable: false, resizable: false, movable: false, fullscreenable: false, skipTaskbar: true, alwaysOnTop: true,
    webPreferences: { preload: path.join(here, 'preload.cjs'), contextIsolation: true, sandbox: true, nodeIntegration: false, spellcheck: false },
  });
  win.setIgnoreMouseEvents(true);
  win.setAlwaysOnTop(true, 'screen-saver');
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  // Request exclusion where the capture API honors it.
  win.setContentProtection(true);
  win.webContents.on('will-navigate', (e) => e.preventDefault());
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.once('did-finish-load', () => {
    send('mode', mode);
    pumpCursor();
    void listen();
  });
  win.once('ready-to-show', () => win.showInactive());
  win.loadFile(path.join(here, 'overlay.html'));
}

/** Follows the cursor from display to display; the work area keeps it off the menu bar, Dock and taskbar. */
function pumpCursor() {
  let last = '';
  setInterval(() => {
    if (!win || win.isDestroyed()) return;
    const p = screen.getCursorScreenPoint();
    const wa = screen.getDisplayNearestPoint(p).workArea;
    if (!area || wa.x !== area.x || wa.y !== area.y || wa.width !== area.width || wa.height !== area.height) {
      area = wa;
      win.setBounds(wa);
      send('area', { width: wa.width, height: wa.height });
    }
    const key = `${p.x},${p.y}`;
    if (key !== last) { last = key; send('cursor', { x: p.x - wa.x, y: p.y - wa.y }); }
  }, 16);
}

async function signIn() {
  const link = await ownerLogin(base, dataDir);
  const res = await fetch(link, { headers: { accept: 'application/json' }, redirect: 'error', signal: AbortSignal.timeout(5000) });
  if (!res.ok) throw new Error(`sign-in refused (HTTP ${res.status})`);
  const { token: t } = await res.json();
  if (typeof t !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(t)) throw new Error('sign-in returned no session');
  // If sign-in finishes during quit, attempt to revoke it without retaining the token.
  if (quitting) { await fetch(`${base}/api/auth/logout`, { method: 'POST', headers: { authorization: `Bearer ${t}` }, signal: AbortSignal.timeout(2000) }).catch(() => {}); return; }
  token = t;
}

/** Reads HQ's event stream and forwards only companion state; reconnects, and signs in again on 401. */
async function listen() {
  for (let wait = 1000; ; wait = Math.min(wait * 2, 15_000)) {
    if (quitting) return;
    try {
      if (!token) { signing = signIn(); try { await signing; } finally { signing = null; } }
      // HQ pings every 20 s; silence for 45 s means a half-open stream (WSL2 after sleep), so start over.
      const idle = new AbortController();
      let timer = setTimeout(() => idle.abort(), 45_000);
      const res = await fetch(`${base}/api/events`, { headers: { authorization: `Bearer ${token}` }, redirect: 'error', signal: idle.signal });
      if (res.status === 401) { token = ''; throw new Error('session expired'); }
      if (!res.ok || !res.body) throw new Error(`events refused (HTTP ${res.status})`);
      send('connection', 'connected');
      wait = 1000;
      let buffer = '';
      for await (const chunk of res.body.pipeThrough(new TextDecoderStream())) {
        clearTimeout(timer);
        timer = setTimeout(() => idle.abort(), 45_000);
        buffer += chunk;
        let end;
        while ((end = buffer.indexOf('\n\n')) >= 0) {
          const frame = buffer.slice(0, end);
          buffer = buffer.slice(end + 2);
          const data = frame.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim()).join('');
          try { const ev = JSON.parse(data); if (ev.type === 'companion') send('companion', ev.state); } catch { /* not JSON */ }
        }
        if (buffer.length > 1_000_000) throw new Error('event stream frame too large');
      }
    } catch (e) {
      console.error(`[overlay] ${e.message}`);
    }
    send('connection', 'offline');
    await new Promise((r) => setTimeout(r, wait));
  }
}

function setMode(next) {
  mode = next;
  send('mode', mode);
  tray.setContextMenu(trayMenu());
}

const trayMenu = () => Menu.buildFromTemplate([
  { label: 'Follow cursor', type: 'radio', checked: mode === 'follow', click: () => setMode('follow') },
  { label: 'Park in corner', type: 'radio', checked: mode === 'park', click: () => setMode('park') },
  { label: 'Hide', type: 'radio', checked: mode === 'hidden', click: () => setMode('hidden') },
  { type: 'separator' },
  { label: 'Quit Jarvis overlay', click: () => app.quit() },
]);

if (!app.requestSingleInstanceLock()) app.exit(0);
else app.whenReady().then(() => {
  // The overlay page needs no camera, microphone, screen or notifications.
  session.defaultSession.setPermissionRequestHandler((_wc, _perm, done) => done(false));
  session.defaultSession.setPermissionCheckHandler(() => false);
  app.dock?.hide();
  tray = new Tray(nativeImage.createFromPath(path.join(here, 'tray.png')));
  tray.setToolTip('Jarvis overlay');
  tray.setContextMenu(trayMenu());
  createOverlay();
});
// Attempt bounded server-side revocation before exiting.
app.on('before-quit', (e) => {
  quitting = true;
  if (!token && !signing) return;
  e.preventDefault();
  // A sign-in still in flight ends its own session once it sees `quitting`; wait for it first.
  void (async () => {
    await signing?.catch(() => {});
    if (token) {
      await fetch(`${base}/api/auth/logout`, { method: 'POST', headers: { authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(2000) }).catch(() => {});
    }
    app.exit(0);
  })();
});
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => app.quit());
