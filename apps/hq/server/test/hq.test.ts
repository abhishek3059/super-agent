// Self-checks for the parts that guard a boundary: who may call the server, what a viewer may send
// to a bot's browser, and that a handoff between bots always comes back.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { spawnSync } from 'node:child_process';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';

const home = fs.mkdtempSync(path.join(os.tmpdir(), 'hq-test-'));
process.env.HOME = process.env.USERPROFILE = home;
process.env.HQ_DATA_DIR = process.env.ENGINES_DIR = process.env.DB_PATH = path.join(home, 'ignored');
delete process.env.SESSION_SECRET;
after(() => fs.rmSync(home, { recursive: true, force: true }));
process.env.PORT = '8787';
// Set before anything loads env.ts: these must not switch the unapproved services on.
process.env.XAI_API_KEY = 'x';
process.env.COMPOSIO_API_KEY = 'y';
const { allowedHost, allowedOrigin } = await import('../src/lib/guard.js');
const { attachScreenRelay, inputCommand, sameOrigin } = await import('../src/screen.js');
const { autoReply } = await import('../src/agent/loop.js');
const { isOwnerKey } = await import('../src/lib/auth.js');
const { env } = await import('../src/env.js');

test('only loopback hosts are served', () => {
  assert.ok(allowedHost('127.0.0.1:8787'));
  assert.ok(allowedHost('localhost:8787'));
  for (const h of [undefined, '', 'evil.example', 'evil.example:8787', '127.0.0.1:9999', '127.0.0.1.evil.example:8787']) assert.equal(allowedHost(h), false, String(h));
});

test('cross-site browser requests are refused', () => {
  assert.ok(allowedOrigin(undefined));
  assert.ok(allowedOrigin('http://127.0.0.1:8787'));
  for (const o of ['https://evil.example', 'http://127.0.0.1:9999', 'null', 'not a url']) assert.equal(allowedOrigin(o), false, o);
});

test('the screen socket needs this app as its origin', () => {
  const req = (origin?: string, host = '127.0.0.1:8787') => ({ headers: { origin, host } }) as any;
  assert.ok(sameOrigin(req('http://127.0.0.1:8787')));
  assert.equal(sameOrigin(req(undefined)), false);
  assert.equal(sameOrigin(req('https://evil.example')), false);
  assert.equal(sameOrigin(req('http://evil.example:8787', 'evil.example:8787')), false);
});

test('viewer input is limited to mouse and key events with bounded fields', () => {
  assert.equal(inputCommand({ t: 'eval', expression: 'alert(1)' }), null);
  assert.equal(inputCommand({ t: 'mouse', type: 'Runtime.evaluate' }), null);
  assert.equal(inputCommand(null), null);
  assert.equal(inputCommand('mouse'), null);
  const m = inputCommand({ t: 'mouse', type: 'mousePressed', x: 1e9, y: 'x', button: 'evil', clickCount: 99 })!;
  assert.equal(m.method, 'Input.dispatchMouseEvent');
  assert.deepEqual({ x: (m.params as any).x, y: (m.params as any).y, button: (m.params as any).button, clickCount: (m.params as any).clickCount }, { x: 10000, y: 0, button: 'none', clickCount: 3 });
  const k = inputCommand({ t: 'key', type: 'keyDown', key: 'a'.repeat(500), text: 'b'.repeat(500) })!;
  assert.equal((k.params as any).key.length, 32);
  assert.equal((k.params as any).text.length, 8);
});

test('a handoff always returns a result or a failure, and a reply never bounces', () => {
  const ask = { type: 'bot', fromBotId: 'bot_a', fromName: 'Jarvis', text: 'do it', depth: 1 } as const;
  const turn = (over: object = {}) => ({ messaged: new Set<string>(), lastText: 'done: 42', depth: 1, ...over });
  assert.equal(autoReply(ask, turn(), null), 'done: 42');
  assert.match(autoReply(ask, turn({ lastText: '  ' }), null)!, /anything to report/);
  assert.match(autoReply(ask, turn(), 'the run failed')!, /could not finish.*the run failed/);
  assert.equal(autoReply(ask, turn({ messaged: new Set(['bot_a']) }), null), null, 'it already answered itself');
  assert.equal(autoReply({ ...ask, reply: true }, turn(), null), null, 'a reply is not answered');
  assert.equal(autoReply({ type: 'user', text: 'hi' } as any, turn(), null), null);
});

test('the owner key is derived from the session secret and nothing else passes', async () => {
  const crypto = await import('node:crypto');
  assert.ok(isOwnerKey(crypto.createHmac('sha256', env.sessionSecret).update('owner-login').digest('hex')));
  for (const k of ['', 'abc', '00'.repeat(32), crypto.createHmac('sha256', 'other').update('owner-login').digest('hex')]) assert.equal(isOwnerKey(k), false);
  assert.equal(fs.statSync(path.join(env.dataDir, 'session-secret')).mode & 0o777, 0o600);
  assert.equal(fs.statSync(env.dataDir).mode & 0o777, 0o700);
  assert.equal(env.dataDir, path.join(fs.realpathSync(home), '.super-agent', 'hq'));
  for (const name of ['dbPath', 'enginesDir', 'filesDir', 'profilesDir'] as const) {
    assert.equal(path.dirname(env[name]), env.dataDir);
  }
});

test('an approval card accepts only its three answers', async () => {
  const { isDecision } = await import('../src/agent/loop.js');
  for (const d of ['allow', 'always', 'deny']) assert.ok(isDecision(d));
  for (const d of [undefined, null, '', 'x', 'ALLOW', {}, true]) assert.equal(isDecision(d), false);
});

test('services DEC-23 does not approve stay off whatever the environment says', async () => {
  const { TOOLS } = await import('../src/agent/tools.js');
  assert.equal(env.xaiKey, '');
  assert.equal(env.composioKey, '');
  for (const name of ['x_search', 'list_event_triggers', 'create_event_routine', 'request_app_connection']) assert.ok(!TOOLS.some((t) => t.name === name), name);
  assert.ok(TOOLS.some((t) => t.name === 'send_to_bot'));
});

test('the approval route refuses anything but a real answer', async () => {
  const { api } = await import('../src/routes.js');
  const { db } = await import('../src/db.js');
  db.prepare('INSERT INTO users(id,email,name,created_at) VALUES (?,?,?,?)').run('usr_t', 't@localhost', 'T', Date.now());
  db.prepare('INSERT INTO auth_sessions(token,user_id,created_at,expires_at) VALUES (?,?,?,?)').run('tok_t', 'usr_t', Date.now(), Date.now() + 60_000);
  const post = (body: string) => api.request('/approvals/ap_none', { method: 'POST', headers: { cookie: 'hq_session=tok_t', 'content-type': 'application/json' }, body });
  for (const body of ['{}', '{"decision":null}', '{"decision":"x"}', 'not json']) {
    assert.equal((await post(body)).status, 400, body);
  }
  assert.equal((await post('{"decision":"allow"}')).status, 404, 'a real answer for an unknown card is not found');
  assert.equal((await api.request('/approvals/ap_none', { method: 'POST', body: '{"decision":"allow"}' })).status, 403, 'no session');
});

test('bot creation rejects malformed JSON and invalid fields before creating a bot', async () => {
  const { api } = await import('../src/routes.js');
  const { db } = await import('../src/db.js');
  const { initSubagents } = await import('../src/agent/subagents.js');
  const { initRooms } = await import('../src/agent/rooms.js');
  initSubagents();
  initRooms();
  db.prepare('INSERT INTO users(id,email,name,created_at) VALUES (?,?,?,?)').run('usr_b', 'b@localhost', 'B', Date.now());
  db.prepare('INSERT INTO auth_sessions(token,user_id,created_at,expires_at) VALUES (?,?,?,?)').run('tok_b', 'usr_b', Date.now(), Date.now() + 60_000);
  const post = (body: string) => api.request('/bots', { method: 'POST', headers: {
    cookie: 'hq_session=tok_b', 'content-type': 'application/json',
  }, body });
  for (const body of ['not json', 'null', '[]', '{}', '{"name":42}', '{"name":"Agent","delegate":true}']) {
    assert.equal((await post(body)).status, 400, body);
  }
  assert.deepEqual(db.prepare('SELECT id FROM bots WHERE user_id=?').all('usr_b'), []);
  assert.equal((await post('{"name":"Agent","mode":"teammate"}')).status, 200);
});

test('HQ refuses remote Hermes origins and symlinked data roots', () => {
  const script = ['--import', 'tsx', '--input-type=module', '-e', "await import('./src/env.ts')"];
  const probe = (settings: NodeJS.ProcessEnv) => spawnSync(process.execPath, script, {
    cwd: new URL('../', import.meta.url), env: { ...process.env, ...settings }, encoding: 'utf8',
  });
  const remote = probe({ HERMES_URL: 'http://192.0.2.10:8650' });
  assert.notEqual(remote.status, 0);
  assert.match(remote.stderr, /requires a loopback HTTP origin/);
  const linkedHome = fs.mkdtempSync(path.join(home, 'link-'));
  fs.symlinkSync(path.dirname(env.dataDir), path.join(linkedHome, '.super-agent'), 'junction');
  const linked = probe({ HOME: linkedHome, USERPROFILE: linkedHome, HERMES_URL: '' });
  assert.notEqual(linked.status, 0);
  assert.match(linked.stderr, /requires real data directories/);
});

test('a malformed screen cookie is refused without throwing from the upgrade event', () => {
  const server = createServer();
  attachScreenRelay(server);
  const writes: string[] = [];
  let closed = false;
  server.emit('upgrade', {
    url: '/api/bots/bot_missing/screen',
    headers: { host: '127.0.0.1:8787', origin: 'http://127.0.0.1:8787', cookie: 'hq_session=%ZZ' },
  }, { write: (data: string) => writes.push(data), destroy: () => { closed = true; } }, Buffer.alloc(0));
  assert.deepEqual(writes, ['HTTP/1.1 403 Forbidden\r\n\r\n']);
  assert.equal(closed, true);
});
