import { spawnSync, type ChildProcess } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { env } from './env.js';
import type { Confinement, Contained } from './sandbox.js';

/**
 * Containment on Linux and WSL2, with bubblewrap. It gives a bot what the macOS profile does:
 * an empty root with only the system folders read-only, the folders it is given, no other process
 * (own pid namespace and /proc), and no network of its own. The macOS profile lets a process reach
 * only listed loopback ports. Here the process has an empty loopback, and a small bridge carries
 * those ports in and out over unix sockets, so the rules stay the same: it reaches the app's tool
 * endpoint, the internet proxy and its own browser, and listens on its own port, nothing else.
 */

/** Empty string when bubblewrap can make the namespaces it needs, else why not (Ubuntu 24.04 can refuse). */
export function probeBwrap(bwrap: string): string {
  const r = spawnSync(bwrap, ['--ro-bind', '/', '/', '--unshare-all', '--die-with-parent', 'true'], { encoding: 'utf8', timeout: 10_000 });
  if (r.error) return (r.error as NodeJS.ErrnoException).code === 'ENOENT' ? 'bwrap is not installed' : r.error.message;
  return r.status === 0 ? '' : (r.stderr.trim().split('\n')[0] || `bwrap exited ${r.status}`);
}

const real = (p: string) => { try { return fs.realpathSync(p); } catch { return path.resolve(p); } };

/** Mount `p` at its own real path, and a link at the path it was given by when that differs. */
const bind = (flag: '--ro-bind-try' | '--bind', p: string) => {
  const r = real(p);
  return [flag, r, r, ...(r === p ? [] : ['--symlink', r, p])];
};

/** Merged-/usr systems link these into /usr (a link is recreated, a real folder is mounted). */
const SYSTEM_LINKS = ['/bin', '/sbin', '/lib', '/lib32', '/lib64', '/libx32'];

const BRIDGE_DIR = '/run/hq';

/**
 * Runs inside the namespace as its first process, then starts the real program. For each port it may
 * reach, it listens on that loopback port here and hands each connection to a unix socket the app
 * made; for its own port, it serves a unix socket that the app's listener on the same port hands
 * connections to. It stays until nothing else runs in the namespace: Hermes starts its gateway
 * again from a new session and exits, and the gateway still needs its port.
 */
const BRIDGE_JS = `
const net = require('net'), fs = require('fs'), { spawn } = require('child_process');
const cfg = JSON.parse(process.argv[2]);
const link = (a, b) => { a.pipe(b); b.pipe(a); for (const s of [a, b]) { s.on('error', () => {}); s.once('close', () => { a.destroy(); b.destroy(); }); } };
const serve = (to, ...on) => new Promise((up) => net.createServer((c) => link(c, to())).listen(...on, up));
(async () => {
  // Every port is open before the program starts, so its first connection already finds it.
  for (const p of cfg.fwd) await serve(() => net.connect('${BRIDGE_DIR}/f' + p + '.sock'), p, '127.0.0.1');
  if (cfg.rev) await serve(() => net.connect(cfg.rev, '127.0.0.1'), '${BRIDGE_DIR}/rev/l.sock');
  const kid = spawn(process.argv[3], process.argv.slice(4), { stdio: 'inherit' });
  kid.once('error', (e) => { console.error(e.message); process.exit(127); });
  kid.once('exit', (code) => {
    setInterval(() => {
      if (!fs.readdirSync('/proc').some((d) => /^[0-9]+$/.test(d) && d !== '1' && +d !== process.pid)) process.exit(code ?? 1);
    }, 500);
  });
})();
`;

const validPort = (p: number) => Number.isInteger(p) && p > 0 && p < 65536;

/**
 * The bwrap command for `bin args`. `c.write` already holds the process's own temporary folder.
 * With ports to carry, the command starts the bridge first and the caller must call `attach` with
 * the spawned child, which starts the app's side of the bridge and removes it when the child exits.
 */
export function bwrapRun(bwrap: string, bin: string, args: string[], c: Confinement): Contained {
  const ports = [...new Set(c.localPorts)].filter((p) => p !== c.listen);
  for (const p of [...ports, ...(c.listen ? [c.listen] : [])]) if (!validPort(p)) throw new Error(`Bad port ${p}`);
  const mounts = [
    '--unshare-all', '--die-with-parent', '--new-session', // new session: no terminal injection
    '--ro-bind', '/usr', '/usr', '--ro-bind', '/etc', '/etc', '--ro-bind-try', '/opt', '/opt',
    ...SYSTEM_LINKS.flatMap((d) => {
      try { return fs.lstatSync(d).isSymbolicLink() ? ['--symlink', fs.readlinkSync(d), d] : ['--ro-bind', d, d]; } catch { return []; }
    }),
    '--ro-bind-try', '/sys/devices/system', '/sys/devices/system', // CPU and memory counts, nothing else of /sys
    '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
    // The real home is never mounted. A path to it does not exist here and cannot be written.
    ...c.read.flatMap((p) => bind('--ro-bind-try', p)),
    // Mount points cannot be removed or renamed from inside, as in the macOS profile.
    ...c.write.flatMap((p) => { fs.mkdirSync(p, { recursive: true, mode: 0o700 }); return bind('--bind', p); }),
  ];
  // Last, so that nothing is writable but the mounts above (the empty root is writable otherwise).
  const lock = ['--remount-ro', '/'];
  if (!ports.length && !c.listen) return { bin: bwrap, args: [...mounts, ...lock, bin, ...args] };

  // The bridge's folder is the app's own, never one a bot can write, except `rev` (the one socket the
  // bot's side creates). Its mount points exist beforehand because the mount above them is read-only.
  const run = path.join(env.dataDir, 'run');
  fs.mkdirSync(run, { recursive: true, mode: 0o700 });
  const dir = fs.mkdtempSync(path.join(run, 'br-'));
  const rev = path.join(dir, 'rev');
  const revSock = path.join(rev, 'l.sock');
  if (Buffer.byteLength(revSock) > 100) throw new Error(`The data folder path is too long for a unix socket: ${revSock}`);
  fs.mkdirSync(rev, { mode: 0o700 });
  fs.writeFileSync(path.join(dir, 'node'), '', { mode: 0o700 });
  fs.writeFileSync(path.join(dir, 'bridge.js'), BRIDGE_JS, { mode: 0o600 });

  return {
    bin: bwrap,
    args: [
      ...mounts,
      '--ro-bind', dir, BRIDGE_DIR, '--bind', rev, `${BRIDGE_DIR}/rev`, '--ro-bind', real(process.execPath), `${BRIDGE_DIR}/node`, ...lock,
      `${BRIDGE_DIR}/node`, `${BRIDGE_DIR}/bridge.js`, JSON.stringify({ fwd: ports, rev: c.listen ?? 0 }), bin, ...args,
    ],
    attach(child: ChildProcess) {
      const conns = new Set<net.Socket>();
      const servers: net.Server[] = [];
      const link = (a: net.Socket, b: net.Socket | null) => {
        if (!b) { a.destroy(); return; }
        for (const s of [a, b]) { conns.add(s); s.on('error', () => {}); s.once('close', () => { conns.delete(s); a.destroy(); b.destroy(); }); }
        a.pipe(b); b.pipe(a);
      };
      const serve = (on: string | number, dial: () => net.Socket | null) => {
        const s = net.createServer((c) => link(c, dial()));
        // No bridge, no bot: a port already taken (by a stale process) must not leave it half connected.
        s.once('error', (e) => { console.warn(`[sandbox] bridge on ${on}: ${e.message}`); child.kill('SIGKILL'); });
        if (typeof on === 'number') s.listen(on, '127.0.0.1'); else s.listen(on);
        servers.push(s);
      };
      // Out: the process's own loopback port goes to the same port here.
      for (const p of ports) serve(path.join(dir, `f${p}.sock`), () => net.connect(p, '127.0.0.1'));
      // In: our listener on its port goes to its socket, only if that is still a socket (the bot can write that folder).
      if (c.listen) serve(c.listen, () => (fs.lstatSync(revSock, { throwIfNoEntry: false })?.isSocket() ? net.connect(revSock) : null));
      // Nothing of the bot runs once bwrap has exited, so its folder cannot change while it goes.
      const done = () => {
        for (const s of servers) s.close();
        for (const s of conns) s.destroy();
        fs.rmSync(dir, { recursive: true, force: true });
      };
      child.once('exit', done);
      child.once('error', done);
    },
  };
}
