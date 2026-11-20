// Self-checks for the parts that guard a boundary: who may call the server, what a viewer may send
// to a bot's browser, and that a handoff between bots always comes back.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';

process.env.HQ_DATA_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'hq-test-'));
process.env.PORT = '8787';
// Set before anything loads env.ts: these must not switch the unapproved services on.
process.env.XAI_API_KEY = 'x';
process.env.COMPOSIO_API_KEY = 'y';
const { allowedHost, allowedOrigin } = await import('../src/lib/guard.js');
const { inputCommand, sameOrigin } = await import('../src/screen.js');
const { autoReply } = await import('../src/agent/loop.js');
const { env } = await import('../src/env.js');
const { createSession } = await import('../src/lib/auth.js');

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

test('owner sign-in consumes a distinct, single-use client proof', async () => {
  const { api } = await import('../src/routes.js');
  const client = crypto.randomBytes(32).toString('hex');
  const challenge = await api.request(`/auth/owner?client=${client}`);
  assert.equal(challenge.status, 200);
  const { proof: serverProof, server } = await challenge.json();
  const hmac = (side: string) => crypto.createHmac('sha256', env.sessionSecret)
    .update(`hq-owner:${new URL(env.appUrl).origin}:${side}:${client}:${server}`).digest('hex');
  assert.equal(serverProof, hmac('server'));
  const post = (proof: string) => api.request('/auth/owner', {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ server, proof }),
  });
  assert.equal((await post(serverProof)).status, 403);
  const granted = await post(hmac('client'));
  assert.equal(granted.status, 200);
  assert.equal((await post(hmac('client'))).status, 403);
  const { initRooms } = await import('../src/agent/rooms.js');
  const { initSubagents } = await import('../src/agent/subagents.js');
  initSubagents();
  initRooms();
  const { url } = await granted.json();
  const linkPath = new URL(url).pathname.slice('/api'.length);
  const signedIn = await api.request(linkPath, { headers: { accept: 'application/json' } });
  assert.equal(signedIn.status, 200);
  assert.equal(signedIn.headers.has('set-cookie'), false);
  assert.equal(signedIn.headers.get('cache-control'), 'no-store');
  assert.equal((await api.request(linkPath)).status, 410);
  const { token } = await signedIn.json();
  const headers = { authorization: `Bearer ${token}` };
  assert.equal((await api.request('/bots', { headers })).status, 200);
  assert.equal((await api.request('/bots', { headers: { cookie: `hq_session=${token}` } })).status, 401);
  assert.equal((await api.request('/auth/logout', { method: 'POST', headers })).status, 200);
  assert.equal((await api.request('/bots', { headers })).status, 401);
  assert.equal(fs.statSync(path.join(env.dataDir, 'session-secret')).mode & 0o777, 0o600);
  assert.equal(fs.statSync(env.dataDir).mode & 0o777, 0o700);
});

test('the owner launcher sends no credential to an impostor listener', async () => {
  const { ownerLogin } = await import('../../scripts/owner-login.mjs');
  const received: { method?: string; authorization?: string }[] = [];
  const impostor = createServer((req, res) => {
    received.push({ method: req.method, authorization: req.headers.authorization });
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ server: 'ab'.repeat(32), proof: 'cd'.repeat(32) }));
  });
  await new Promise<void>((resolve) => { impostor.listen(0, '127.0.0.1', resolve); });
  try {
    const addr = impostor.address();
    assert.ok(addr && typeof addr !== 'string');
    await assert.rejects(ownerLogin(`http://127.0.0.1:${addr.port}`, env.dataDir), /authenticate/);
    assert.deepEqual(received, [{ method: 'GET', authorization: undefined }]);
  } finally {
    await new Promise<void>((resolve) => { impostor.close(() => resolve()); });
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
  const authorization = `Bearer ${createSession('usr_t')}`;
  const post = (body: string) => api.request('/approvals/ap_none', { method: 'POST', headers: { authorization, 'content-type': 'application/json' }, body });
  for (const body of ['{}', '{"decision":null}', '{"decision":"x"}', 'not json']) {
    assert.equal((await post(body)).status, 400, body);
  }
  assert.equal((await post('{"decision":"allow"}')).status, 404, 'a real answer for an unknown card is not found');
  assert.equal((await api.request('/approvals/ap_none', { method: 'POST', body: '{"decision":"allow"}' })).status, 401, 'no session');
});

test('voice tools require an active call for the signed-in bot', async (t) => {
  const { api } = await import('../src/routes.js');
  const { initRooms } = await import('../src/agent/rooms.js');
  const { initSubagents } = await import('../src/agent/subagents.js');
  initSubagents();
  initRooms();
  const authorization = `Bearer ${createSession('usr_t')}`;
  const post = (route: string, body: object) => api.request(route, { method: 'POST',
    headers: { authorization, 'content-type': 'application/json' }, body: JSON.stringify(body) });
  const create = async (name: string) => {
    const res = await post('/bots', { name });
    assert.equal(res.status, 200);
    return (await res.json()).bot.id;
  };
  const [botId, otherBot] = [await create('Voice Test'), await create('Other Test')];
  const originalKey = env.openaiKey;
  env.openaiKey = 'stub-for-local-test';
  t.mock.method(globalThis, 'fetch', async () => Response.json({ value: 'stub-client-secret' }));
  try {
    const minted = await post('/voice/session', { botId });
    assert.equal(minted.status, 200);
    const { callId } = await minted.json();
    const tool = (id: string, call?: string) => post('/voice/tool', { botId: id, callId: call, name: 'recall_text_messages' });
    assert.equal((await tool(botId)).status, 400);
    assert.equal((await tool(botId, 'unknown')).status, 409);
    assert.equal((await tool(otherBot, callId)).status, 409);
    assert.equal((await tool(botId, callId)).status, 200);
    assert.equal((await post('/voice/end', { botId, callId })).status, 200);
    assert.equal((await tool(botId, callId)).status, 409);
  } finally {
    env.openaiKey = originalKey;
  }
});

test('a bot sandbox closes reads, writes and local sockets outside what it is given', async () => {
  const { sandboxProfile, contained, canContain } = await import('../src/sandbox.js');
  const own = path.join(env.dataDir, 'files', 'bot_a');
  fs.mkdirSync(own, { recursive: true });
  const real = fs.realpathSync(env.dataDir);
  const p = sandboxProfile({ read: [], write: [own], localPorts: [8787] });
  const at = (rule: string) => { const i = p.indexOf(rule); assert.ok(i >= 0, rule); return i; };
  // Later rules win, so every allow must come after the deny it narrows.
  assert.ok(at('(deny file-write* (subpath "/"))') < at(`(allow file-read* file-write* (subpath "${real}/files/bot_a"))`));
  const reads = p.split('\n').find((l) => l.startsWith('(deny file-read*'))!;
  for (const d of [os.homedir(), real, '/private/tmp', '/private/var/folders', '/Volumes']) assert.ok(reads.includes(`(subpath "${fs.realpathSync(d)}")`), d);
  assert.ok(at('(deny network-outbound (remote unix-socket))') < at(`(remote unix-socket (subpath "${real}/files/bot_a"))`));
  assert.ok(at('(deny network-outbound (remote ip "*:*"))') < at('(allow network-outbound (remote ip "localhost:8787"))'), 'all network denied first, then its own ports');
  at('(deny user-preference-read user-preference-write)');
  at('com.apple.lsd.modifydb');
  assert.ok(reads.includes('(subpath "/private/var/tmp")'), 'the shared /var/tmp is closed');
  for (const rule of ['(deny lsopen)', '(deny appleevent-send)', '(deny job-creation)', '(deny process-info* (target others))', 'com.apple.SecurityServer']) at(rule);
  assert.ok(!sandboxProfile({ read: [], write: ['/tmp/a"b'], localPorts: [] }).includes('a"b'), 'quotes in a path cannot end the string');
  const bad = sandboxProfile({ read: [], write: [], localPorts: [], tempPrefix: 'x")) (allow default' });
  assert.ok(!bad.includes('/private/var/folders"))') && !bad.includes('x"))'), 'a bad bundle id adds no rule');
  const good = sandboxProfile({ read: [], write: [], localPorts: [], tempPrefix: 'com.google.Chrome' });
  assert.ok(good.includes('T/com\\.google\\.Chrome\\.'), 'a good one opens only folders of that name');
  // Listening: nowhere but its own port.
  const listen = sandboxProfile({ read: [], write: [own], localPorts: [], listen: 9301 });
  assert.ok(listen.indexOf('(deny network-bind)') < listen.indexOf('(allow network-bind (local ip "localhost:9301"))'));
  assert.ok(!listen.includes('localhost:9302'));
  if (!canContain()) assert.throws(() => contained('/bin/echo', [], { read: [], write: [], localPorts: [] }, 't'), /contained on macOS/, 'no sandbox, no bot');
});

test('inside the sandbox a process cannot read the session secret or a neighbour, and can use its own folder', { skip: process.platform !== 'darwin' }, async () => {
  const { contained } = await import('../src/sandbox.js');
  const { execFileSync } = await import('node:child_process');
  const own = path.join(env.dataDir, 'files', 'bot_a');
  const other = path.join(env.dataDir, 'files', 'bot_b');
  for (const d of [own, other]) fs.mkdirSync(d, { recursive: true });
  fs.writeFileSync(path.join(other, 'private.txt'), 'neighbour');
  const sh = (cmd: string) => {
    const run = contained('/bin/sh', ['-c', cmd], { read: [], write: [own], localPorts: [] }, 'bot_a.t');
    try { return { ok: true, out: execFileSync(run.bin, run.args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }) }; } catch (e: any) { return { ok: false, out: String(e.stderr ?? '') }; }
  };
  assert.equal(sh(`test -w '${own}'`).ok, true, 'Hermes can check its SQLite directory');
  assert.deepEqual(sh(`echo hi > '${own}/x' && cat '${own}/x'`), { ok: true, out: 'hi\n' });
  for (const target of [path.join(env.dataDir, 'session-secret'), path.join(other, 'private.txt'), path.join(os.homedir(), '.ssh')]) {
    const r = sh(`cat '${target}' || ls '${target}'`);
    assert.equal(r.ok, false, target);
    assert.match(r.out, /Operation not permitted/, target);
  }
  assert.equal(sh(`touch '${os.homedir()}/hq-sandbox-selfcheck'`).ok, false);
  assert.equal(fs.existsSync(path.join(os.homedir(), 'hq-sandbox-selfcheck')), false);
  // Nowhere outside its folders is writable, including the shared temp folder.
  assert.equal(sh('touch /private/tmp/hq-sandbox-selfcheck').ok, false);
  assert.equal(fs.existsSync('/private/tmp/hq-sandbox-selfcheck'), false);
  // It cannot hand a command to launchd, which would run it outside the sandbox.
  const job = sh(`launchctl submit -l hq.selfcheck -- /usr/bin/touch '${own}/via-launchd'; echo $?`);
  assert.match(job.out, /\b1\s*$/);
  await new Promise((r) => setTimeout(r, 500));
  assert.equal(fs.existsSync(path.join(own, 'via-launchd')), false);
});

test('the server never writes or reads through a link a bot planted in its own folder', async () => {
  const { writeOwn, readOwn, listOwn, streamOwn } = await import('../src/lib/own.js');
  const root = fs.mkdtempSync(path.join(env.dataDir, 'own-'));
  const outside = path.join(env.dataDir, 'operator-file');
  fs.writeFileSync(outside, 'original');
  fs.symlinkSync(outside, path.join(root, 'planted.txt'));
  writeOwn(root, 'planted.txt', 'PWNED');
  assert.equal(fs.readFileSync(outside, 'utf8'), 'original', 'the target is untouched');
  assert.equal(fs.lstatSync(path.join(root, 'planted.txt')).isSymbolicLink(), false, 'the link was replaced by a file');
  fs.symlinkSync(outside, path.join(root, 'read.txt'));
  assert.equal(readOwn(root, 'read.txt'), null, 'a link is not read');
  fs.symlinkSync(env.dataDir, path.join(root, 'dir'));
  const secret = fs.readFileSync(path.join(env.dataDir, 'session-secret'), 'utf8');
  assert.throws(() => writeOwn(root, 'dir/session-secret', 'x'), 'a linked sub-folder leads outside, so the sandboxed write fails');
  assert.equal(fs.readFileSync(path.join(env.dataDir, 'session-secret'), 'utf8'), secret);
  assert.equal(readOwn(root, 'dir/session-secret'), null, 'nor can it be read through the link');
  assert.throws(() => writeOwn(root, '../escape.txt', 'x'), /outside the bot folder/);
  assert.equal(fs.existsSync(path.join(env.dataDir, 'escape.txt')), false);
  const listed = listOwn(root, '')!.map((f) => f.name).sort();
  assert.ok(listed.includes('planted.txt') && !listed.includes('read.txt'), 'links are not listed');
  assert.equal(listOwn(root, 'dir'), null, 'a linked folder is not listed');
  let got = ''; for await (const chunk of streamOwn(root, 'planted.txt')!) got += chunk;
  assert.equal(got, 'PWNED');
  assert.equal(streamOwn(root, 'read.txt'), null, 'a link is not sent');
  writeOwn(root, '-n', 'dash');
  assert.equal(readOwn(root, '-n')?.text, 'dash', 'a name starting with - is a file, not an option');
  writeOwn(root, 'sub/ok.txt', 'fine');
  assert.equal(readOwn(root, 'sub/ok.txt')?.text, 'fine');
});

test('a process id is only ever taken from the server\'s own folder and must match its command', async () => {
  const { recordPid, livePid, stopPid } = await import('../src/lib/procs.js');
  recordPid('bot_a.test', process.pid);
  assert.equal(livePid('bot_a.test', 'no such marker in this command'), null, 'a live pid that is not ours is refused');
  assert.equal(livePid('bot_unknown.test', 'node'), null);
  await stopPid('bot_a.test', 'no such marker in this command');
  assert.ok(process.pid > 0, 'this process was not signalled');
});

test('a bot that swaps its whole folder for a link gets nothing from the server', { skip: process.platform !== 'darwin' }, async () => {
  const { writeOwn } = await import('../src/lib/own.js');
  const { contained, confinedEnv } = await import('../src/sandbox.js');
  const { execFileSync } = await import('node:child_process');
  const root = path.join(env.dataDir, 'files', 'bot_swap');
  fs.mkdirSync(root, { recursive: true });
  // Inside its sandbox the bot cannot remove or rename its own folder.
  const run = contained('/bin/sh', ['-c', `rm -rf '${root}' || mv '${root}' '${root}.x'; echo $?`], { read: [], write: [root], localPorts: [] }, 'bot_swap.t');
  execFileSync(run.bin, run.args, { env: confinedEnv('bot_swap.t'), stdio: 'ignore' });
  assert.ok(fs.lstatSync(root).isDirectory(), 'the folder is still there and still a folder');
  // And if it were a link anyway (say, made before this rule), the server refuses it.
  const outside = path.join(env.dataDir, 'operator-home');
  fs.mkdirSync(outside, { recursive: true });
  fs.rmSync(root, { recursive: true, force: true });
  fs.symlinkSync(outside, root);
  assert.throws(() => writeOwn(root, '.zshrc', 'evil'), /not a plain folder/);
  assert.equal(fs.existsSync(path.join(outside, '.zshrc')), false);
  assert.throws(() => contained('/bin/true', [], { read: [], write: [root], localPorts: [] }, 'bot_swap.g'), /not a plain folder/, 'nor will it start a process there');
});

// shortcut: this checks planted links, which the old recursive delete also left alone; the race it
// guards (a folder swapped mid-delete) is not reproduced here. Covered by review, not by this test.
test('deleting a bot folder removes what is inside it and never what a link inside it points to', { skip: process.platform !== 'darwin' }, async () => {
  const { removeOwn } = await import('../src/lib/own.js');
  const root = path.join(env.dataDir, 'files', 'bot_gone');
  fs.mkdirSync(path.join(root, 'sub'), { recursive: true });
  fs.writeFileSync(path.join(root, 'sub', 'a.txt'), 'bot file');
  const outside = path.join(env.dataDir, 'operator-keep');
  fs.mkdirSync(outside, { recursive: true });
  fs.writeFileSync(path.join(outside, 'precious.txt'), 'keep me');
  fs.symlinkSync(outside, path.join(root, 'link-to-operator'));
  fs.symlinkSync(path.join(outside, 'precious.txt'), path.join(root, 'sub', 'file-link'));
  const removal = removeOwn(root);
  assert.equal(fs.existsSync(root), true, 'delete yields while the confined command runs');
  await removal;
  assert.equal(fs.existsSync(root), false, 'the bot folder is gone');
  assert.equal(fs.readFileSync(path.join(outside, 'precious.txt'), 'utf8'), 'keep me', 'what the links pointed to is untouched');
  // A link left in a folder's place: only the link goes.
  fs.symlinkSync(outside, root);
  await removeOwn(root);
  assert.equal(fs.existsSync(path.join(outside, 'precious.txt')), true);
});

test('inside the sandbox no loopback address form reaches an unlisted port, and preferences are closed', { skip: process.platform !== 'darwin' }, async (t) => {
  const net = await import('node:net');
  const { contained, confinedEnv } = await import('../src/sandbox.js');
  const { execFileSync } = await import('node:child_process');
  let hits = 0;
  const canary = net.createServer((sock) => { hits++; sock.end('CANARY'); });
  await new Promise<void>((r) => canary.listen(0, '127.0.0.1', r));
  t.after(() => canary.close()); // a failed assertion must not leave the test process waiting on this server
  const port = (canary.address() as any).port;
  const own = path.join(env.dataDir, 'files', 'bot_net');
  fs.mkdirSync(own, { recursive: true });
  // The system curl runs inside the sandbox (a python shim does not). Exit 7 is "could not connect",
  // returned at once when the sandbox denies it; the old localhost-only rule let ::ffff:0.0.0.0 through
  // to a connection attempt instead (exit 28 here, a full connection in the security review).
  for (const host of ['127.0.0.1', '0.0.0.0', '[::1]', '[::]', '[::ffff:127.0.0.1]', '[::ffff:0.0.0.0]']) {
    const run = contained('/usr/bin/curl', ['-s', '-m', '3', '-o', '/dev/null', `http://${host}:${port}/`], { read: [], write: [own], localPorts: [] }, 'bot_net.t');
    let code = 0;
    try { execFileSync(run.bin, run.args, { cwd: own, env: confinedEnv('bot_net.t'), stdio: 'ignore', timeout: 15000 }); } catch (e: any) { code = e.status; }
    assert.equal(code, 7, `${host} must be refused outright`);
  }
  assert.equal(hits, 0, 'nothing reached the canary');
  // Preferences live outside the sandbox and are written by cfprefsd: closed.
  const domain = `com.hqselfcheck.${process.pid}`;
  const run = contained('/usr/bin/defaults', ['write', domain, 'k', 'v'], { read: [], write: [own], localPorts: [] }, 'bot_net.t');
  try { execFileSync(run.bin, run.args, { env: confinedEnv('bot_net.t'), stdio: 'ignore' }); } catch { /* refused */ }
  let written = true;
  try { execFileSync('/usr/bin/defaults', ['read', domain, 'k'], { stdio: 'ignore' }); } catch { written = false; }
  if (written) execFileSync('/usr/bin/defaults', ['delete', domain]);
  assert.equal(written, false, 'the preference was not written');
});

test('a process recorded by an earlier version (bare pid) is still found and stopped', async () => {
  const { stopPid, livePid } = await import('../src/lib/procs.js');
  const { spawn } = await import('node:child_process');
  const child = spawn('/bin/bash', ['-c', 'exec -a "hermes gateway run legacy-selfcheck" sleep 30'], { detached: true, stdio: 'ignore' });
  await new Promise((r) => setTimeout(r, 300));
  fs.mkdirSync(path.join(env.dataDir, 'run'), { recursive: true });
  fs.writeFileSync(path.join(env.dataDir, 'run', 'bot_legacy.gateway.pid'), String(child.pid));
  assert.equal(livePid('bot_legacy.gateway', 'gateway run'), child.pid, 'the old record is recognised');
  await stopPid('bot_legacy.gateway', 'gateway run');
  let alive = true;
  try { process.kill(child.pid!, 0); } catch { alive = false; }
  assert.equal(alive, false, 'and its process is stopped, not left running under old rules');
});

test('a web page cannot ask for an owner sign-in challenge', async () => {
  const { api } = await import('../src/routes.js');
  const client = crypto.randomBytes(32).toString('hex');
  for (const headers of [{ 'sec-fetch-site': 'cross-site' }, { 'sec-fetch-site': 'same-origin' }, { origin: 'https://evil.example' }]) {
    assert.equal((await api.request(`/auth/owner?client=${client}`, { headers })).status, 403, JSON.stringify(headers));
  }
  assert.equal((await api.request(`/auth/owner?client=${client}`)).status, 200, 'the launcher (no browser headers) still can');
});

test('worker routes require a connected supported provider and keep its full model inventory', async () => {
  const { toProviders, validWorkerRoute } = await import('../src/engine.js');
  const models = Array.from({ length: 20 }, (_, i) => `nvidia/model-${i}`);
  const providers = toProviders({ providers: [
    { slug: 'nvidia', authenticated: true, featured_models: [models[0]], models: [...models, 'nvidia/embed-qa-4', 'nvidia/nemotron-3-super-120b-a12b'] },
    { slug: 'openai-codex', authenticated: false, models: ['codex-model'] },
    { slug: 'gemini', authenticated: true, models: ['gemini-model'] },
    { slug: 'ollama', authenticated: true, models: ['local-model'] },
  ] });
  assert.deepEqual(providers.map((p) => p.id), ['nvidia', 'openai-codex']);
  assert.deepEqual(providers[0].models, models);
  assert.equal(validWorkerRoute(providers, 'nvidia', models[19]), true);
  assert.equal(validWorkerRoute(providers, 'nvidia', 'codex-model'), false);
  assert.equal(validWorkerRoute(providers, 'openai-codex', 'codex-model'), false);
  assert.equal(validWorkerRoute(providers, 'gemini', 'gemini-model'), false);
});

async function seedEngineBot(id: string) {
  const { db } = await import('../src/db.js');
  db.prepare('INSERT OR IGNORE INTO users(id,email,name,created_at) VALUES (?,?,?,?)')
    .run('usr_picker', 'picker@localhost', 'Picker Test', Date.now());
  db.prepare('INSERT INTO bots(id,user_id,name,created_at,updated_at,engine,engine_port) VALUES (?,?,?,?,?,?,?)')
    .run(id, 'usr_picker', 'Picker Test', Date.now(), Date.now(), 'managed', 8560);
  return db;
}

test('engine settings refuse a missing catalog and advance the conversation revision on changed routes', async (t) => {
  const { engineInfo, forgetEngineOptions, workerConversation } = await import('../src/engine.js');
  const { configApi } = await import('../src/routes-config.js');
  const botId = 'bot_picker_test';
  const db = await seedEngineBot(botId);
  let catalog = false;
  t.mock.method(globalThis, 'fetch', async (url: string) => {
    if (url.endsWith('/health')) return Response.json({ status: 'ok' });
    if (!catalog) return new Response(null, { status: 503 });
    return Response.json({ provider: 'nvidia', model: 'nvidia/nemotron-3-super-120b-a12b',
      providers: [{ slug: 'nvidia', authenticated: true, models: ['chat-a','chat-b'] }] });
  });
  const save = (model: string) => configApi.request(`/bots/${botId}/engine`, {
    method: 'PATCH', headers: { authorization: `Bearer ${createSession('usr_picker')}`, 'content-type': 'application/json' },
    body: JSON.stringify({ provider: 'nvidia', model }),
  });
  assert.match((await engineInfo(botId)).error ?? '', /catalog is unavailable/);
  assert.equal((await save('chat-a')).status, 409);
  catalog = true;
  forgetEngineOptions(botId);
  assert.equal((await engineInfo(botId)).status, 'error', 'retired seed default cannot start a turn');
  const bot = { id: botId, generation: 1, engine_revision: 0 };
  assert.equal(workerConversation(bot, { provider: 'nvidia', model: 'chat-a' }), `hq-${botId}-g1`);
  assert.equal(workerConversation(bot, { provider: 'nvidia', model: 'chat-b' }), `hq-${botId}-g1-e1`);
  assert.throws(() => workerConversation(bot, { provider: 'nvidia', model: 'chat-a' }), /settings changed/);
  for (const [model, revision] of [['chat-a', 2], ['chat-a', 2], ['chat-b', 3], ['chat-a', 4]] as const) {
    assert.equal((await save(model)).status, 200);
    assert.equal(db.prepare('SELECT engine_revision FROM bots WHERE id=?').get(botId).engine_revision, revision);
  }
});


test('worker restarts share the turn queue and refuse an already busy bot', async () => {
  const { isBotBusy, runInBotQueue } = await import('../src/agent/loop.js');
  const { configApi } = await import('../src/routes-config.js');
  const botId = 'bot_restart_test';
  await seedEngineBot(botId);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const first = runInBotQueue(botId, () => gate);
  let laterRan = false;
  const later = runInBotQueue(botId, async () => { laterRan = true; });
  try {
    assert.equal(isBotBusy(botId), true);
    const result = await configApi.request(`/bots/${botId}/engine/restart`, {
      method: 'POST', headers: { authorization: `Bearer ${createSession('usr_picker')}` },
    });
    assert.equal(result.status, 409);
    assert.equal(laterRan, false);
  } finally {
    release();
    await Promise.all([first, later]);
  }
  assert.equal(laterRan, true);
});
