// Self-checks for the Linux and WSL2 backend (bubblewrap): real contained processes, not strings.
// Skipped where it cannot run (macOS has its own checks in hq.test.ts).
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { setTimeout as sleep } from 'node:timers/promises';

process.env.HQ_DATA_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'hq-linux-'));
const { env } = await import('../src/env.js');
const { canContain, confinedEnv, contained } = await import('../src/sandbox.js');
const skip = process.platform !== 'linux' ? 'Linux only (bubblewrap)' : !canContain() && 'bubblewrap cannot make namespaces here';

type Conf = { read?: string[]; write?: string[]; localPorts?: number[]; listen?: number };

/** Run a command inside the confinement, the way the server does (spawn, then attach the bridge). */
function inBox(cmd: string[], c: Conf, name = 'bot_l.t') {
  const run = contained(cmd[0], cmd.slice(1), { read: [], write: [], localPorts: [], ...c }, name);
  const child = spawn(run.bin, run.args, { env: confinedEnv(name), stdio: ['ignore', 'pipe', 'pipe'], detached: true });
  run.attach?.(child);
  let out = '';
  child.stdout.on('data', (d) => { out += d; });
  child.stderr.on('data', (d) => { out += d; });
  const done = new Promise<{ ok: boolean; out: string }>((r) => child.once('close', (code) => r({ ok: code === 0, out })));
  return { child, done, run };
}
const sh = (script: string, c: Conf = {}) => inBox(['/bin/sh', '-c', script], c).done;
/** Connect from inside to 127.0.0.1:port and print the first line the other side sends. */
const dial = (port: number, host = '127.0.0.1') =>
  ['/bin/bash', '-c', `exec 3<>/dev/tcp/${host}/${port} && printf 'hi\\r\\n' >&3 && head -n1 <&3`];

const listenOnce = async (reply: string, onHit: () => void) => {
  const s = net.createServer((sock) => { onHit(); sock.on('error', () => {}); sock.end(`${reply}\n`); });
  await new Promise<void>((r) => s.listen(0, '127.0.0.1', r));
  return { s, port: (s.address() as net.AddressInfo).port };
};

const get = async (port: number) => { try { return await (await fetch(`http://127.0.0.1:${port}/`, { signal: AbortSignal.timeout(1500) })).text(); } catch { return null; } };
const freePort = async () => { const { s, port } = await listenOnce('', () => {}); await new Promise((r) => s.close(r)); return port; };
const waitFor = async (f: () => Promise<boolean>, ms = 8000) => { for (let t = 0; t < ms; t += 200) { if (await f()) return true; await sleep(200); } return false; };
/** A small HTTP server to run inside the box (the bridge mounts this node there at /run/hq/node). */
const insideServer = (port: number, word: string) =>
  `/run/hq/node -e "require('http').createServer((q,r)=>r.end('${word}')).listen(${port},'127.0.0.1')"`;

const own = path.join(env.dataDir, 'files', 'bot_a');
const other = path.join(env.dataDir, 'files', 'bot_b');
const shared = path.join(env.dataDir, 'shared-ro');

test('files: only what it is given, read-only or writable', { skip }, async (t) => {
  for (const d of [own, other, shared]) fs.mkdirSync(d, { recursive: true });
  fs.writeFileSync(path.join(other, 'private.txt'), 'neighbour');
  fs.writeFileSync(path.join(shared, 'hello.txt'), 'hello');
  const homeFile = path.join(os.homedir(), `.hq-selfcheck-${process.pid}`);
  fs.writeFileSync(homeFile, 'operator secret');
  t.after(() => fs.rmSync(homeFile, { force: true }));
  const c = { read: [shared], write: [own] };

  // Not visible at all: the operator's home, the app's data folder and a neighbour's folder.
  for (const target of [homeFile, os.homedir(), path.join(env.dataDir, 'session-secret'), path.join(other, 'private.txt')]) {
    assert.equal((await sh(`cat '${target}' || ls '${target}'`, c)).ok, false, target);
  }
  // The data folder is only a path to what it was given: its own contents are not there.
  const listing = await sh(`ls -A '${env.dataDir}' '${env.dataDir}/files'`, c);
  assert.ok(!/session-secret|bot_b|hq\.db|\.env/.test(listing.out), `no state of the app or a neighbour: ${listing.out}`);
  assert.deepEqual(await sh(`cat '${shared}/hello.txt'`, c), { ok: true, out: 'hello' }, 'a read folder is readable');
  assert.equal((await sh(`echo x > '${shared}/new.txt'`, c)).ok, false, 'and not writable');
  assert.deepEqual(await sh(`echo hi > '${own}/x' && cat '${own}/x'`, c), { ok: true, out: 'hi\n' }, 'its own folder is');
  assert.equal(fs.readFileSync(path.join(own, 'x'), 'utf8'), 'hi\n', 'and what it wrote is on the real disk');
  assert.equal((await sh(`test -w '${own}'`, c)).ok, true);

  // Nowhere else is writable: system folders, the root, the home, the neighbour.
  const outside = ['/usr/hq-selfcheck', '/etc/hq-selfcheck', '/hq-selfcheck', `${os.homedir()}/hq-selfcheck`, `${other}/hq-selfcheck`];
  for (const f of outside) assert.equal((await sh(`touch '${f}'`, c)).ok, false, f);
  for (const f of outside) assert.equal(fs.existsSync(f), false, `${f} was not created`);

  // The folder itself stays put: a mount point cannot be removed or renamed from inside.
  await sh(`rm -rf '${own}' || mv '${own}' '${own}.x'`, c);
  assert.ok(fs.lstatSync(own).isDirectory() && !fs.existsSync(`${own}.x`), 'the folder is still there (its contents are the bot\'s to delete)');
});

test('processes: no other process is visible or signalled', { skip }, async () => {
  const r = await sh(`for d in /proc/[0-9]*; do echo "\${d#/proc/}"; done; kill -0 ${process.pid} 2>&1 || echo CANNOT_SIGNAL`);
  const pids = r.out.split('\n').filter((l) => /^\d+$/.test(l));
  assert.ok(pids.length > 0 && pids.length < 6, `only its own few processes: ${pids}`);
  assert.ok(!pids.includes(String(process.pid)) && !pids.includes(String(process.ppid)), 'not this server or its parent');
  assert.match(r.out, /CANNOT_SIGNAL/);
});

test('network: an unlisted loopback port and the internet are out; a listed port goes through the bridge', { skip }, async (t) => {
  let blocked = 0;
  const canary = await listenOnce('CANARY', () => { blocked++; });
  t.after(() => canary.s.close());
  for (const host of ['127.0.0.1', 'localhost', '0.0.0.0']) {
    assert.equal((await inBox(dial(canary.port, host), {}).done).ok, false, `${host}:unlisted is refused`);
  }
  assert.equal((await inBox(dial(80, '1.1.1.1'), {}).done).ok, false, 'no route to the internet');
  assert.equal(blocked, 0, 'nothing reached the canary');

  // The same port, once listed: the connection reaches the host's 127.0.0.1:port.
  const run = inBox(dial(canary.port), { localPorts: [canary.port] });
  assert.deepEqual(await run.done, { ok: true, out: 'CANARY\n' });
  assert.equal(blocked, 1);
  // Listing one port opens only that one.
  const second = await listenOnce('OTHER', () => { blocked++; });
  t.after(() => second.s.close());
  assert.equal((await inBox(dial(second.port), { localPorts: [canary.port] }).done).ok, false);
  assert.equal(blocked, 1, 'the unlisted one was never reached');
});

test('network: the host reaches its listen port, a neighbour reaches it only through its own list, and it all goes with the child', { skip }, async (t) => {
  const port = await freePort();
  const run = inBox(['/bin/sh', '-c', `${insideServer(port, 'INSIDE')} & exit 0`], { listen: port });
  t.after(() => { try { process.kill(-run.child.pid!, 'SIGKILL'); } catch { /* gone */ } });
  assert.ok(await waitFor(async () => (await get(port)) === 'INSIDE'), 'the host reaches the process through the reverse bridge');
  // The launcher exited at once; the namespace and its bridge live while anything runs in it.
  await sleep(1500);
  assert.equal(await get(port), 'INSIDE', 'still served after the launcher exited');

  // A second box lists that port and reaches the first one (a bot's gateway reaching its browser).
  const via = await inBox(['/bin/bash', '-c', `exec 3<>/dev/tcp/127.0.0.1/${port} && printf 'GET / HTTP/1.0\\r\\n\\r\\n' >&3 && cat <&3`], { localPorts: [port] }).done;
  assert.match(via.out, /INSIDE$/, 'a second box that lists the port reaches the first');
  const bridges = () => fs.readdirSync(path.join(env.dataDir, 'run')).filter((d) => d.startsWith('br-'));
  assert.ok(bridges().length >= 1);

  process.kill(-run.child.pid!, 'SIGKILL');
  await run.done;
  assert.ok(await waitFor(async () => (await get(port)) === null), 'the host port closes when the child ends');
  assert.ok(await waitFor(async () => bridges().length === 0), 'and its bridge folder is removed');
});

test('network: a listen port that is already taken stops the bot from starting', { skip }, async (t) => {
  const taken = await listenOnce('NOT A BOT', () => {});
  t.after(() => taken.s.close());
  const run = inBox(['/bin/sh', '-c', 'sleep 30'], { listen: taken.port });
  const r = await Promise.race([run.done.then(() => 'ended'), sleep(5000).then(() => 'still running')]);
  if (r !== 'ended') try { process.kill(-run.child.pid!, 'SIGKILL'); } catch { /* gone */ }
  assert.equal(r, 'ended', 'the child was stopped');
});

test('a command with no ports starts no bridge and has no network at all', { skip }, async () => {
  const run = contained('/bin/true', [], { read: [], write: [], localPorts: [] }, 'bot_l.t');
  assert.equal(run.attach, undefined);
  assert.ok(run.args.includes('--unshare-net') || run.args.includes('--unshare-all'));
});
