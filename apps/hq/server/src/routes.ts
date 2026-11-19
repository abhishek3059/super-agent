import crypto from 'node:crypto';
import { Hono } from 'hono';
import { streamSSE } from 'hono/streaming';
import { db, now } from './db.js';
import { env } from './env.js';
import { newId } from './lib/ids.js';
import { hub } from './lib/hub.js';
import { deletingBots } from './lib/procs.js';
import { createSession, destroySession, ownerProof, requireUser, userFromAuthorization, type AuthVars } from './lib/auth.js';
import { allLive, appendRow, clearConversation, emitBot, getBot, getBotRow, getRow, listBots, listRoutines, listRows, listTasks, toRoutine, updateRow } from './store.js';
import { enqueue, interrupt, isDecision, resolveApproval } from './agent/loop.js';
import { computerState, forgetBotFiles, readyScreen, releaseScreen, screenshot } from './computer.js';
import { assignEngine, forgetEngineFiles, provisionEngine, stopEngine, syncPersona } from './engine.js';
import { deleteMemory, listMemories, memoryBot } from './engine-memory.js';
import { catalog, connectedToolkits, disconnect, startConnect, toolkitInfo } from './composio.js';
import { runRoutine, scheduleRoutine, unscheduleRoutine } from './routines.js';
import { deleteEventTrigger } from './triggers.js';
import { dispatchRoomMessage } from './agent/rooms.js';
import { voiceApi } from './voice.js';
import type { AvatarColor, AvatarShape, Toolkit } from './types.js';

export const api = new Hono<AuthVars>();

const SHAPES: AvatarShape[] = ['blob', 'pebble', 'bean', 'egg', 'squircle', 'tablet', 'capsule', 'cylinder', 'hex', 'gem', 'crystal', 'wedge', 'shield', 'dome', 'arch', 'cloud', 'teardrop', 'leaf', 'square', 'sparkle', 'clover', 'flower', 'heart', 'house', 'star'];
const COLORS: AvatarColor[] = ['black', 'brown', 'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'violet', 'magenta', 'gray'];

function hashPick<T>(id: string, list: T[]): T {
  let h = 0x811c9dc5;
  for (const ch of id) { h ^= ch.charCodeAt(0); h = Math.imul(h, 0x01000193) >>> 0; }
  return list[h % list.length];
}

/** Thrown for things the user can fix; the message is shown to them. */
class UserError extends Error {}

const agentCount = () => (db.prepare("SELECT COUNT(*) n FROM bots WHERE COALESCE(kind,'agent')<>'room' AND COALESCE(hidden,0)=0").get() as any).n as number;

function createBot(userId: string, b: { name: string; label?: string; description?: string; instructions?: string; avatarShape?: string; avatarColor?: string; mode?: string; isPrimary?: boolean }) {
  // Every bot runs its own agent and browser on this machine.
  if (agentCount() >= env.maxBots) throw new UserError(`The team is full (${env.maxBots} bots). Remove one to add another, or raise MAX_BOTS.`);
  const id = newId('bot');
  const shape = SHAPES.includes(b.avatarShape as AvatarShape) ? b.avatarShape : hashPick(id, SHAPES.slice(0, 13));
  const color = COLORS.includes(b.avatarColor as AvatarColor) ? b.avatarColor : hashPick(id, COLORS.filter((c) => c !== 'black'));
  db.prepare(
    'INSERT INTO bots(id,user_id,name,label,description,instructions,avatar_shape,avatar_color,mode,is_primary,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
  ).run(id, userId, b.name.trim().slice(0, 60) || 'New Bot', b.label ?? '', b.description ?? '', b.instructions ?? '', shape, color, b.mode === 'teammate' ? 'teammate' : 'personal', b.isPrimary ? 1 : 0, now(), now());
  // Gateways start on the bot's first turn, so an idle team costs no memory.
  assignEngine(id);
  hub.emit(userId, { type: 'roster' });
  return getBot(id)!;
}

/** The team a new install starts with: Jarvis in front, four specialists behind. */
const TEAM = [
  { name: 'Jarvis', label: 'Chief of Staff', avatarShape: 'blob', avatarColor: 'cyan', isPrimary: true, description: 'Your main point of contact. You take requests by voice or chat, do quick things yourself, and hand real work to the specialist on the team who fits it (send_to_bot), then report back what they found.' },
  { name: 'Scout', label: 'Research', avatarShape: 'hex', avatarColor: 'blue', description: 'You research on the web with your own browser and return findings with sources.' },
  { name: 'Forge', label: 'Engineering', avatarShape: 'square', avatarColor: 'orange', description: 'You write, run and fix code in your workspace and report exactly what you changed and tested.' },
  { name: 'Quill', label: 'Writing', avatarShape: 'teardrop', avatarColor: 'violet', description: 'You draft and edit documents, emails and posts, and save finished pieces to your Library.' },
  { name: 'Atlas', label: 'Operations', avatarShape: 'house', avatarColor: 'green', description: 'You plan, track tasks and routines, and keep recurring work on schedule.' },
];

/** The one person this install belongs to. Created, with the team, the first time they sign in. */
function ownerId(): string {
  const existing = db.prepare('SELECT id FROM users ORDER BY created_at LIMIT 1').get() as any;
  if (existing) return existing.id;
  const id = newId('usr');
  db.prepare('INSERT INTO users(id,email,name,created_at) VALUES (?,?,?,?)').run(id, 'owner@localhost', env.ownerName, now());
  for (const b of TEAM) createBot(id, b);
  return id;
}

// ---------- auth ----------

api.get('/auth/me', (c) => c.json({ user: userFromAuthorization(c.req.header('authorization')) }));

/** One-time sign-in links made by the owner endpoint. Kept in memory: a restart drops them. */
const signInLinks = new Map<string, { token: string; expires: number }>();

// The launcher verifies a fresh server proof before returning a separate, single-use client proof.
const ownerChallenges = new Map<string, { client: string; expires: number }>();
const nonce = /^[0-9a-f]{64}$/;
api.get('/auth/owner', (c) => {
  const client = c.req.query('client') ?? '';
  if (!nonce.test(client)) return c.json({ error: 'invalid challenge' }, 400);
  if (ownerChallenges.size >= 32) ownerChallenges.delete(ownerChallenges.keys().next().value!);
  const server = crypto.randomBytes(32).toString('hex');
  ownerChallenges.set(server, { client, expires: now() + 10_000 });
  c.header('Cache-Control', 'no-store');
  return c.json({ server, proof: ownerProof('server', client, server) });
});

api.post('/auth/owner', async (c) => {
  const body = await c.req.json().catch(() => null);
  const { server, proof } = body ?? {};
  if (typeof server !== 'string' || !nonce.test(server) || typeof proof !== 'string' || !nonce.test(proof)) {
    return c.json({ error: 'forbidden' }, 403);
  }
  const challenge = ownerChallenges.get(server);
  if (!challenge || challenge.expires <= now() ||
      !crypto.timingSafeEqual(Buffer.from(proof, 'hex'), Buffer.from(ownerProof('client', challenge.client, server), 'hex'))) {
    return c.json({ error: 'forbidden' }, 403);
  }
  ownerChallenges.delete(server);
  c.header('Cache-Control', 'no-store');
  const token = crypto.randomBytes(24).toString('base64url');
  // A few may be open at once (two browsers); the oldest goes first.
  if (signInLinks.size >= 4) signInLinks.delete(signInLinks.keys().next().value!);
  signInLinks.set(token, { token, expires: Date.now() + 5 * 60_000 });
  return c.json({ ok: true, url: `${env.appUrl}/api/auth/link/${token}` });
});

api.get('/auth/link/:token', (c) => {
  const l = signInLinks.get(c.req.param('token'));
  signInLinks.delete(c.req.param('token'));
  if (!l || l.expires < Date.now()) return c.text('This sign-in link was already used or has expired. Run `npm run open` again.', 410);
  const session = createSession(ownerId());
  c.header('Cache-Control', 'no-store');
  c.header('Referrer-Policy', 'no-referrer');
  if (c.req.header('accept') === 'application/json') return c.json({ token: session });
  // Only the HQ origin receives the session. HTTP cookies would be visible to other loopback ports.
  const scriptNonce = crypto.randomBytes(24).toString('base64url');
  c.header('Content-Security-Policy', `default-src 'none'; script-src 'nonce-${scriptNonce}'; frame-ancestors 'none'; base-uri 'none'`);
  return c.html(`<!doctype html><meta charset="utf-8"><title>Signing in to Jarvis HQ</title><script nonce="${scriptNonce}">sessionStorage.setItem('hq_session',${JSON.stringify(session)});location.replace('/');</script><noscript>Enable JavaScript to sign in to Jarvis HQ.</noscript>`);
});

api.post('/auth/logout', (c) => { destroySession(c.req.header('authorization')); return c.json({ ok: true }); });

// everything below requires a session
api.use('/*', async (c, next) => {
  if (c.req.path.startsWith('/api/auth/') || c.req.path.startsWith('/api/apps/callback') || c.req.path === '/api/health') return next();
  return requireUser(c, next);
});

// ---------- events (SSE) ----------

api.get('/events', (c) => {
  const user = c.get('user');
  return streamSSE(c, async (stream) => {
    const queue: string[] = [];
    let wake: (() => void) | null = null;
    const unsub = hub.subscribe(user.id, (ev) => { queue.push(JSON.stringify(ev)); wake?.(); });
    stream.onAbort(() => { unsub(); wake?.(); });
    await stream.writeSSE({ data: JSON.stringify({ type: 'hello', serverTime: now() }) });
    while (!stream.aborted) {
      if (!queue.length) {
        await Promise.race([new Promise<void>((r) => (wake = r)), new Promise((r) => setTimeout(r, 20_000))]);
        wake = null;
        if (!queue.length) { await stream.writeSSE({ data: JSON.stringify({ type: 'ping' }) }); continue; }
      }
      while (queue.length) await stream.writeSSE({ data: queue.shift()! });
    }
    unsub();
  });
});

// ---------- bots ----------

const ownBot = (userId: string, id: string) => {
  const b = getBotRow(id);
  return b && b.user_id === userId && !deletingBots.has(id) ? b : null;
};

api.get('/bots', (c) => c.json({ bots: listBots(c.get('user').id), live: allLive(c.get('user').id) }));

api.post('/bots', async (c) => {
  const body = await c.req.json();
  try {
    return c.json({ bot: createBot(c.get('user').id, body) });
  } catch (e: any) {
    if (e instanceof UserError) return c.json({ error: e.message }, 409);
    throw e;
  }
});

api.patch('/bots/:id', async (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  const p = await c.req.json();
  const cols: Record<string, string> = { name: 'name', label: 'label', description: 'description', instructions: 'instructions', avatarShape: 'avatar_shape', avatarColor: 'avatar_color', mode: 'mode', effort: 'effort', pinned: 'pinned', voice: 'voice', voiceSpeed: 'voice_speed', voiceLanguage: 'voice_language' };
  for (const [k, col] of Object.entries(cols)) {
    if (p[k] !== undefined) db.prepare(`UPDATE bots SET ${col}=?, updated_at=? WHERE id=?`).run(typeof p[k] === 'boolean' ? (p[k] ? 1 : 0) : p[k], now(), b.id);
  }
  if (b.kind !== 'room') {
    if (['name', 'label', 'description'].some((k) => p[k] !== undefined)) syncPersona(b.id);
  }
  emitBot(b.id);
  return c.json({ bot: getBot(b.id) });
});

api.delete('/bots/:id', async (c) => {
  const user = c.get('user');
  const b = getBotRow(c.req.param('id'));
  if (!b || b.user_id !== user.id) return c.json({ error: 'not found' }, 404);
  if (deletingBots.has(b.id)) return c.json({ error: 'bot deletion already in progress' }, 409);

  deletingBots.add(b.id);
  try {
    interrupt(b.id);
    if (b.kind !== 'room') {
      const stops = await Promise.allSettled([stopEngine(b.id), releaseScreen(b.id)]);
      if (stops.some((r) => r.status === 'rejected')) {
        return c.json({ error: 'Could not stop the bot safely. Try deleting it again.' }, 503);
      }
    }
    for (const r of listRoutines(b.id)) {
      unscheduleRoutine(r.id);
      await deleteEventTrigger(r.id).catch(() => {});
    }
    if (b.kind !== 'room') {
      await forgetEngineFiles(b.id).catch((e) => console.warn('[engine] cleanup failed', e?.code ?? 'unknown'));
      await forgetBotFiles(b.id).catch((e) => console.warn('[computer] cleanup failed', e?.code ?? 'unknown'));
    }
    db.prepare('DELETE FROM screens WHERE bot_id=?').run(b.id);
    db.prepare('DELETE FROM bots WHERE id=?').run(b.id);
    hub.emit(user.id, { type: 'roster' });
    return c.json({ ok: true });
  } finally {
    deletingBots.delete(b.id);
  }
});

api.post('/bots/:id/primary', (c) => {
  const user = c.get('user');
  const b = ownBot(user.id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  db.prepare('UPDATE bots SET is_primary = (id = ?) WHERE user_id=?').run(b.id, user.id);
  hub.emit(user.id, { type: 'roster' });
  return c.json({ ok: true });
});

api.post('/bots/:id/read', (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  db.prepare('UPDATE bots SET unread=0 WHERE id=?').run(b.id);
  emitBot(b.id);
  return c.json({ ok: true });
});

// ---------- conversation ----------

api.get('/bots/:id/rows', (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  const beforeSeq = c.req.query('beforeSeq') ? Number(c.req.query('beforeSeq')) : undefined;
  return c.json({ generation: b.generation, rows: listRows(b.id, { beforeSeq, limit: Number(c.req.query('limit') ?? 200) }) });
});

api.post('/bots/:id/messages', async (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  const { text } = await c.req.json<{ text: string }>();
  if (!text?.trim()) return c.json({ error: 'empty' }, 400);
  const row = appendRow(b.id, 'message', { type: 'message', role: 'user', text: text.trim() });
  // Group chats dispatch to their member Bots instead of running their own loop.
  if (b.kind === 'room') dispatchRoomMessage(b.id, text.trim(), enqueue);
  // Any pending question card is answered by a free-text message.
  else enqueue(b.id, { type: 'user', text: text.trim() });
  return c.json({ row });
});

api.post('/bots/:id/interrupt', (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  interrupt(b.id);
  return c.json({ ok: true });
});

api.post('/bots/:id/fresh', (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  interrupt(b.id);
  clearConversation(b.id);
  emitBot(b.id);
  return c.json({ ok: true });
});

api.post('/approvals/:id', async (c) => {
  const { decision } = await c.req.json<{ decision: 'allow' | 'always' | 'deny' }>().catch(() => ({ decision: undefined }));
  if (!isDecision(decision)) return c.json({ error: 'decision must be allow, always or deny' }, 400);
  try { resolveApproval(c.get('user').id, c.req.param('id'), decision); } catch { return c.json({ error: 'not found' }, 404); }
  return c.json({ ok: true });
});

api.post('/bots/:id/cards/:seq/answer', async (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  const row = getRow(b.id, Number(c.req.param('seq')));
  const { answer } = await c.req.json<{ answer: string }>();
  if (!row || row.body.type !== 'card' || row.body.card !== 'question') return c.json({ error: 'not a question' }, 400);
  updateRow(b.id, row.seq, { ...row.body, status: 'answered', answer });
  appendRow(b.id, 'message', { type: 'message', role: 'user', text: answer });
  enqueue(b.id, { type: 'user', text: `[Answer to "${row.body.question}"] ${answer}` });
  return c.json({ ok: true });
});

api.post('/bots/:id/cards/:seq/dismiss', (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  const row = getRow(b.id, Number(c.req.param('seq')));
  if (!row || row.body.type !== 'card') return c.json({ error: 'not a card' }, 400);
  const body: any = { ...row.body, status: row.body.card === 'connect' ? 'skipped' : 'dismissed' };
  updateRow(b.id, row.seq, body);
  if (row.body.card === 'connect') enqueue(b.id, { type: 'system', text: `The user skipped connecting ${row.body.toolkitName}. Continue without it.` });
  return c.json({ ok: true });
});

// ---------- routines / tasks / memories ----------

api.get('/bots/:id/routines', (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  return b ? c.json({ routines: listRoutines(b.id) }) : c.json({ error: 'not found' }, 404);
});

api.patch('/routines/:id', async (c) => {
  const r = db.prepare('SELECT r.* FROM routines r JOIN bots b ON b.id=r.bot_id WHERE r.id=? AND b.user_id=?').get(c.req.param('id'), c.get('user').id) as any;
  if (!r) return c.json({ error: 'not found' }, 404);
  const { enabled } = await c.req.json<{ enabled: boolean }>();
  db.prepare('UPDATE routines SET enabled=? WHERE id=?').run(enabled ? 1 : 0, r.id);
  const next = toRoutine(db.prepare('SELECT * FROM routines WHERE id=?').get(r.id));
  enabled ? scheduleRoutine(next) : unscheduleRoutine(r.id);
  hub.emit(c.get('user').id, { type: 'routines', botId: r.bot_id });
  return c.json({ routine: next });
});

api.post('/routines/:id/run', (c) => {
  const r = db.prepare('SELECT r.* FROM routines r JOIN bots b ON b.id=r.bot_id WHERE r.id=? AND b.user_id=?').get(c.req.param('id'), c.get('user').id) as any;
  if (!r) return c.json({ error: 'not found' }, 404);
  runRoutine(r.id);
  return c.json({ ok: true });
});

api.delete('/routines/:id', async (c) => {
  const r = db.prepare('SELECT r.* FROM routines r JOIN bots b ON b.id=r.bot_id WHERE r.id=? AND b.user_id=?').get(c.req.param('id'), c.get('user').id) as any;
  if (!r) return c.json({ error: 'not found' }, 404);
  unscheduleRoutine(r.id);
  await deleteEventTrigger(r.id);
  db.prepare('DELETE FROM routines WHERE id=?').run(r.id);
  hub.emit(c.get('user').id, { type: 'routines', botId: r.bot_id });
  return c.json({ ok: true });
});

api.get('/bots/:id/tasks', (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  return b ? c.json({ tasks: listTasks(b.id) }) : c.json({ error: 'not found' }, 404);
});

api.get('/tasks', (c) => {
  const rows = db.prepare('SELECT t.* FROM tasks t JOIN bots b ON b.id=t.bot_id WHERE b.user_id=? ORDER BY t.updated_at DESC LIMIT 200').all(c.get('user').id) as any[];
  return c.json({ tasks: rows.map((r) => ({ id: r.id, botId: r.bot_id, title: r.title, state: r.state, note: r.note, updatedAt: r.updated_at })) });
});

api.get('/bots/:id/memories', (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  return c.json({ memories: listMemories(b.id) });
});

api.delete('/memories/:id', (c) => {
  const botId = memoryBot(c.req.param('id'));
  if (!botId || !ownBot(c.get('user').id, botId)) return c.json({ error: 'not found' }, 404);
  deleteMemory(c.req.param('id'));
  return c.json({ ok: true });
});

// ---------- computer ----------

api.get('/computer', (c) => c.json({ computer: computerState(c.get('user').id) }));

api.post('/computer/ensure', (c) => c.json({ computer: computerState(c.get('user').id) }));

api.get('/bots/:id/screenshot', async (c) => {
  const b = ownBot(c.get('user').id, c.req.param('id'));
  if (!b) return c.json({ error: 'not found' }, 404);
  const shot = await screenshot(b.id);
  return shot ? c.body(shot, 200, { 'Content-Type': 'image/jpeg', 'Cache-Control': 'no-store' }) : c.body(null, 204);
});

// ---------- apps (Composio marketplace) ----------

api.get('/apps', async (c) => {
  const user = c.get('user');
  const search = (c.req.query('search') ?? '').toLowerCase();
  const category = c.req.query('category') ?? '';
  const [all, connected] = await Promise.all([catalog(), connectedToolkits(user.id).catch(() => new Set<string>())]);
  let items: Toolkit[] = all.map((t) => ({ ...t, connected: connected.has(t.slug) }));
  if (search) items = items.filter((t) => t.name.toLowerCase().includes(search) || t.slug.includes(search) || t.description?.toLowerCase().includes(search));
  if (category) items = items.filter((t) => t.categories.some((x) => x.toLowerCase() === category.toLowerCase()));
  const categories = [...new Set(all.flatMap((t) => t.categories))].sort();
  const connectedApps = all.filter((t) => connected.has(t.slug)).map((t) => ({ ...t, connected: true }));
  return c.json({ apps: items.slice(0, Number(c.req.query('limit') ?? 120)), connected: [...connected], connectedApps, categories, total: items.length });
});

api.post('/apps/:slug/connect', async (c) => {
  const user = c.get('user');
  const slug = c.req.param('slug');
  const { botId, seq } = await c.req.json<{ botId?: string; seq?: number }>().catch(() => ({} as any));
  const cb = new URL(`${env.appUrl}/api/apps/callback`);
  cb.searchParams.set('slug', slug);
  if (botId) cb.searchParams.set('bot', botId);
  if (seq) cb.searchParams.set('seq', String(seq));
  const r = await startConnect(user.id, slug, cb.toString());
  return c.json(r);
});

api.get('/apps/callback', async (c) => {
  const userId = userFromAuthorization(c.req.header('authorization'))?.id ?? '';
  // This page needs no session and its query string comes from outside: only a plain slug gets through.
  const slug = /^[a-z0-9_-]{1,64}$/.test(c.req.query('slug') ?? '') ? c.req.query('slug')! : '';
  const botId = c.req.query('bot');
  const seq = Number(c.req.query('seq') ?? 0);
  const ok = c.req.query('status') !== 'failed';
  const userExists = db.prepare('SELECT 1 FROM users WHERE id=?').get(userId);
  if (userExists && ok) {
    const connected = await connectedToolkits(userId).catch(() => new Set<string>());
    if (connected.has(slug)) {
      hub.emit(userId, { type: 'connections' });
      if (botId && ownBot(userId, botId)) {
        const info = await toolkitInfo(slug);
        if (seq) {
          const row = getRow(botId, seq);
          if (row?.body.type === 'card' && row.body.card === 'connect') updateRow(botId, seq, { ...row.body, status: 'connected' });
        }
        enqueue(botId, { type: 'system', text: `The user connected ${info?.name ?? slug}. Continue with what you were doing.` });
      }
    }
  }
  return c.html(`<!doctype html><meta charset="utf-8"><title>Connected</title><body style="font-family:system-ui;padding:40px;text-align:center">${ok ? 'Connected. You can close this window.' : 'Connection failed.'}<script>try{window.opener&&window.opener.postMessage({type:'hq-connected',slug:${JSON.stringify(slug).replace(/</g, '\\u003c')},ok:${ok}},'*')}catch(e){};setTimeout(()=>window.close(),800)</script></body>`);
});

api.delete('/apps/:slug', async (c) => {
  await disconnect(c.get('user').id, c.req.param('slug'));
  hub.emit(c.get('user').id, { type: 'connections' });
  return c.json({ ok: true });
});

api.get('/policies', (c) => c.json({ policies: db.prepare('SELECT tool, mode FROM policies WHERE user_id=?').all(c.get('user').id) }));
api.delete('/policies/:tool', (c) => {
  db.prepare('DELETE FROM policies WHERE user_id=? AND tool=?').run(c.get('user').id, c.req.param('tool'));
  return c.json({ ok: true });
});

api.route('/voice', voiceApi);
