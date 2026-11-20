import type { IncomingMessage, Server } from 'node:http';
import { WebSocket, WebSocketServer } from 'ws';
import { db } from './db.js';
import { env } from './env.js';
import { allowedHost } from './lib/guard.js';
import { userFromToken } from './lib/auth.js';
import { activePage, readyScreen, SCREEN } from './computer.js';

/**
 * Live view of a bot's browser: browser <-> this server <-> the bot's Chrome (DevTools screencast).
 * The DevTools port never reaches the browser. Frames go down as binary JPEG. In "watch" mode
 * nothing the viewer sends is forwarded; in "control" mode only the input messages below are.
 */

const MOUSE = new Set(['mousePressed', 'mouseReleased', 'mouseMoved', 'mouseWheel']);
const KEY = new Set(['keyDown', 'keyUp', 'char']);
const BUTTON = new Set(['none', 'left', 'middle', 'right']);
const num = (v: unknown, max: number) => (typeof v === 'number' && Number.isFinite(v) ? Math.max(-max, Math.min(max, v)) : 0);
const str = (v: unknown, max: number) => (typeof v === 'string' ? v.slice(0, max) : undefined);

/** A viewer's input message as a DevTools command, or null if it is not one we forward. */
export function inputCommand(m: any): { method: string; params: object } | null {
  if (!m || typeof m !== 'object') return null;
  if (m.t === 'mouse' && MOUSE.has(m.type)) {
    return {
      method: 'Input.dispatchMouseEvent',
      params: {
        type: m.type, x: num(m.x, 10000), y: num(m.y, 10000), button: BUTTON.has(m.button) ? m.button : 'none',
        clickCount: num(m.clickCount, 3), deltaX: num(m.dx, 5000), deltaY: num(m.dy, 5000), modifiers: num(m.modifiers, 15),
      },
    };
  }
  if (m.t === 'key' && KEY.has(m.type)) {
    return {
      method: 'Input.dispatchKeyEvent',
      params: {
        type: m.type, key: str(m.key, 32), code: str(m.code, 32), text: str(m.text, 8), modifiers: num(m.modifiers, 15),
        windowsVirtualKeyCode: num(m.keyCode, 255),
      },
    };
  }
  return null;
}

/** Only this app's own page may open the socket (the browser checks here supplement the explicit session token). */
export function sameOrigin(req: IncomingMessage): boolean {
  const origin = req.headers.origin;
  if (!origin) return false;
  try {
    const o = new URL(origin);
    return (o.hostname === '127.0.0.1' || o.hostname === 'localhost') && (o.host === req.headers.host || o.origin === new URL(env.appUrl).origin);
  } catch { return false; }
}

export function attachScreenRelay(server: Server) {
  const protocol = 'hq-screen';
  const wss = new WebSocketServer({ noServer: true, maxPayload: 4096,
    handleProtocols: (offered) => offered.has(protocol) ? protocol : false });
  server.on('upgrade', (req: IncomingMessage, socket, head) => {
    let url: URL;
    try { url = new URL(req.url ?? '/', 'http://x'); } catch { socket.destroy(); return; }
    const m = url.pathname.match(/^\/api\/bots\/([^/]+)\/screen$/);
    // Nothing else on this server upgrades: an unanswered socket would stay open.
    if (!m) { socket.destroy(); return; }
    const offered = (req.headers['sec-websocket-protocol'] ?? '').split(',').map((p) => p.trim());
    const session = offered.length === 2 && offered[0] === protocol && offered[1].startsWith('hq-session.')
      ? offered[1].slice('hq-session.'.length) : undefined;
    const user = allowedHost(req.headers.host) && sameOrigin(req) ? userFromToken(session) : null;
    const bot = user ? (db.prepare('SELECT id FROM bots WHERE id=? AND user_id=?').get(m[1], user.id) as any) : null;
    if (!session || !user || !bot) {
      socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
      socket.destroy();
      return;
    }
    const mode = url.searchParams.get('mode') === 'control' ? 'control' : 'watch';
    wss.handleUpgrade(req, socket, head, (client) => {
      client.on('error', () => client.terminate());
      void relay(client, user.id, bot.id, mode, session);
    });
  });
}

async function relay(client: WebSocket, userId: string, botId: string, mode: 'watch' | 'control', session: string) {
  let upstream: WebSocket | null = null;
  let targetId = '';
  let seq = 0;
  let closed = false;
  const send = (method: string, params: object = {}) => {
    if (upstream?.readyState === WebSocket.OPEN) upstream.send(JSON.stringify({ id: ++seq, method, params }));
  };

  async function attach() {
    const page = await activePage(botId);
    if (closed || !page || page.id === targetId) return;
    try { upstream?.close(); } catch { /* */ }
    targetId = page.id;
    const up = (upstream = new WebSocket(page.webSocketDebuggerUrl));
    up.on('open', () => {
      send('Page.enable');
      // A headless tab counts as hidden: it paints nothing and input sent to it never returns. Bring it
      // to the front and have it behave as the visible, focused tab.
      send('Page.bringToFront');
      send('Emulation.setFocusEmulationEnabled', { enabled: true });
      send('Page.setWebLifecycleState', { state: 'active' });
      send('Page.startScreencast', { format: 'jpeg', quality: 70, maxWidth: SCREEN.width, maxHeight: SCREEN.height, everyNthFrame: 1 });
    });
    up.on('message', (d) => {
      let m: any;
      try { m = JSON.parse(String(d)); } catch { return; }
      if (m.method !== 'Page.screencastFrame') return;
      send('Page.screencastFrameAck', { sessionId: m.params.sessionId });
      if (client.readyState === WebSocket.OPEN && client.bufferedAmount < 4_000_000) client.send(Buffer.from(m.params.data, 'base64'));
    });
    // The tab closed or the bot moved on: the timer below picks the next one.
    up.on('close', () => { if (upstream === up) targetId = ''; });
    up.on('error', () => { /* close follows */ });
  }

  let timer: ReturnType<typeof setInterval> | undefined;
  client.on('message', (data) => {
    if (mode !== 'control') return;
    let cmd: ReturnType<typeof inputCommand> = null;
    try { cmd = inputCommand(JSON.parse(String(data))); } catch { /* not ours */ }
    if (cmd) send(cmd.method, cmd.params);
  });
  client.on('close', () => {
    closed = true;
    clearInterval(timer);
    try { upstream?.close(); } catch { /* */ }
  });

  try {
    await readyScreen(userId, botId);
    if (closed) return;
    client.send(JSON.stringify({ t: 'size', ...SCREEN }));
    await attach();
    // Follow the bot to a new tab, only once its own browser is known to be up.
    timer = setInterval(() => {
      if (userFromToken(session)?.id !== userId) { client.close(1008, 'session ended'); return; }
      void attach().catch(() => client.close(1011, 'screen unavailable'));
    }, 1500);
  } catch (e: any) {
    client.close(1011, String(e?.message ?? e).slice(0, 120));
  }
}
