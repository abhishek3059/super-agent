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
 * made. For its own port it dials out: it holds a control line to the app's socket, and for each
 * byte the app sends there (one per caller on the app's side of that port) it opens a new line to
 * the same socket, says 'D', and joins it to the local port. The app never dials anything the bot
 * can write. It stays until nothing else runs in the namespace: Hermes starts its gateway
 * again from a new session and exits, and the gateway still needs its port.
 */
const BRIDGE_JS = `
const net = require('net'), fs = require('fs'), { spawn } = require('child_process');
const cfg = JSON.parse(process.argv[2]);
const link = (a, b) => { a.pipe(b); b.pipe(a); for (const s of [a, b]) s.on('error', () => { a.destroy(); b.destroy(); }); };
const serve = (to, ...on) => new Promise((up) => net.createServer((c) => link(c, to())).listen(...on, up));
(async () => {
  // Every port is open before the program starts, so its first connection already finds it.
  for (const p of cfg.fwd) await serve(() => net.connect('${BRIDGE_DIR}/f' + p + '.sock'), p, '127.0.0.1');
  if (cfg.rev) await new Promise((up, fail) => {
    const RV = '${BRIDGE_DIR}/rv.sock';
    const open = (tries) => {
      let connected = false;
      const ctl = net.connect(RV, () => { connected = true; ctl.write('C'); up(); });
      ctl.once('error', (e) => { if (!connected && tries > 0) setTimeout(() => open(tries - 1), 100); else fail(e); });
      ctl.on('data', (buf) => {
        for (let i = 0; i < buf.length; i++) {
          const d = net.connect(RV, () => { d.write('D'); link(d, net.connect(cfg.rev, '127.0.0.1')); });
          d.on('error', () => d.destroy());
        }
      });
      // Without the control line nobody can reach its port: stop rather than run half connected.
      ctl.once('close', () => { if (connected) process.exit(1); });
    };
    open(50);
  });
  const kid = spawn(process.argv[3], process.argv.slice(4), { stdio: 'inherit' });
  kid.once('error', (e) => { console.error(e.message); process.exit(127); });
  kid.once('exit', (code) => {
    setInterval(() => {
      if (!fs.readdirSync('/proc').some((d) => /^[0-9]+$/.test(d) && d !== '1' && +d !== process.pid)) process.exit(code ?? 1);
    }, 500);
  });
})();
`;

// ---------- seccomp: no vsock ----------
// --unshare-net does not cover AF_VSOCK, which WSL2 uses to talk to the Windows host. A classic BPF
// filter refuses socket(AF_VSOCK, ...) with EACCES (distinct from the kernel's own EAFNOSUPPORT, so a
// test can tell the filter worked), every syscall of a foreign ABI, and x32 calls on x86_64.
// Deny io_uring because its kernel operations can create sockets outside the socket syscall.
const IO_URING_SETUP = 425;
const IO_URING_REGISTER = 427;
const ARCH: Record<string, { audit: number; socket: number; x32: boolean }> = {
  x64: { audit: 0xc000003e, socket: 41, x32: true },
  arm64: { audit: 0xc00000b7, socket: 198, x32: false },
};
const AF_VSOCK = 40;
const ERRNO = (e: number) => 0x00050000 | e;
const ALLOW = 0x7fff0000;

/** The filter for this CPU as `struct sock_filter[]`, or null where none is written (then no bot starts). */
export function vsockFilter(arch = process.arch): Buffer | null {
  const a = ARCH[arch];
  if (!a) return null;
  const ins = (code: number, jt: number, jf: number, k: number) => {
    const b = Buffer.alloc(8);
    b.writeUInt16LE(code, 0); b.writeUInt8(jt, 2); b.writeUInt8(jf, 3); b.writeUInt32LE(k >>> 0, 4);
    return b;
  };
  const LD = 0x20, JEQ = 0x15, JGE = 0x35, RET = 0x06;
  return Buffer.concat([
    ins(LD, 0, 0, 4), //                    0 arch
    ins(JEQ, 0, 8, a.audit), //             1 foreign ABI -> 10
    ins(LD, 0, 0, 0), //                    2 syscall number
    ins(JGE, 6, 0, a.x32 ? 0x40000000 : 0xffffffff), // 3 x32 -> 10
    ins(JGE, 0, 1, IO_URING_SETUP), //     4 below io_uring range -> 6
    ins(JGE, 0, 4, IO_URING_REGISTER + 1), // 5 io_uring range -> 10
    ins(JEQ, 0, 4, a.socket), //            6 not socket() -> 11
    ins(LD, 0, 0, 16), //                   7 first argument (low half)
    ins(JEQ, 0, 2, AF_VSOCK), //            8 not vsock -> 11
    ins(RET, 0, 0, ERRNO(13)), //           9 EACCES
    ins(RET, 0, 0, ERRNO(1)), //           10 EPERM
    ins(RET, 0, 0, ALLOW), //              11
  ]);
}

/** bwrap reads the filter from an open file: a shell opens it as fd 3 and becomes bwrap. Nothing is interpolated. */
function withFilter(bwrap: string, args: string[]): { bin: string; args: string[] } {
  const filter = vsockFilter();
  if (!filter) throw new Error(`The Linux sandbox has no seccomp filter for this CPU (${process.arch}).`);
  const run = path.join(env.dataDir, 'run');
  fs.mkdirSync(run, { recursive: true, mode: 0o700 });
  const file = path.join(run, `seccomp-${process.arch}.bpf`);
  fs.writeFileSync(file, filter, { mode: 0o600 });
  return { bin: '/bin/sh', args: ['-c', 'exec 3<"$1" && shift && exec "$@"', 'sh', file, bwrap, '--seccomp', '3', ...args] };
}

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
  if (!ports.length && !c.listen) return withFilter(bwrap, [...mounts, ...lock, bin, ...args]);

  // The bridge's folder is the app's own and read-only inside: every socket in it is made by the app.
  const run = path.join(env.dataDir, 'run');
  fs.mkdirSync(run, { recursive: true, mode: 0o700 });
  const dir = fs.mkdtempSync(path.join(run, 'br-'));
  const rvSock = path.join(dir, 'rv.sock');
  if (Buffer.byteLength(rvSock) > 100) throw new Error(`The data folder path is too long for a unix socket: ${rvSock}`);
  fs.writeFileSync(path.join(dir, 'node'), '', { mode: 0o700 });
  fs.writeFileSync(path.join(dir, 'bridge.js'), BRIDGE_JS, { mode: 0o600 });

  return {
    ...withFilter(bwrap, [
      ...mounts,
      '--ro-bind', dir, BRIDGE_DIR, '--ro-bind', real(process.execPath), `${BRIDGE_DIR}/node`, ...lock,
      `${BRIDGE_DIR}/node`, `${BRIDGE_DIR}/bridge.js`, JSON.stringify({ fwd: ports, rev: c.listen ?? 0 }), bin, ...args,
    ]),
    attach(child: ChildProcess) {
      const conns = new Set<net.Socket>();
      const servers: net.Server[] = [];
      const link = (a: net.Socket, b: net.Socket | null) => {
        if (!b) { a.destroy(); return; }
        // pipe() ends the other side once its data is flushed; destroying on close would drop the
        // last bytes of a reply sent just before the peer hung up. Only an error tears both down.
        for (const s of [a, b]) { conns.add(s); s.on('error', () => { a.destroy(); b.destroy(); }); s.once('close', () => conns.delete(s)); }
        a.pipe(b); b.pipe(a);
      };
      const serve = (on: string | number, dial: () => net.Socket | null, take?: (c: net.Socket) => void) => {
        const s = net.createServer((c) => (take ? take(c) : link(c, dial())));
        // No bridge, no bot: a port already taken (by a stale process) must not leave it half connected.
        s.once('error', (e) => { console.warn(`[sandbox] bridge on ${on}: ${e.message}`); child.kill('SIGKILL'); });
        if (typeof on === 'number') s.listen(on, '127.0.0.1'); else s.listen(on);
        servers.push(s);
      };
      // Out: the process's own loopback port goes to the same port here.
      for (const p of ports) serve(path.join(dir, `f${p}.sock`), () => net.connect(p, '127.0.0.1'));
      // In: callers on its port wait in line; the bot's side answers each with a fresh 'D' line.
      if (c.listen) {
        const waiting: net.Socket[] = [];
        let control: net.Socket | null = null;
        serve(c.listen, () => null, (caller) => {
          if (!control) { caller.destroy(); return; }
          waiting.push(caller);
          caller.once('close', () => { const i = waiting.indexOf(caller); if (i >= 0) waiting.splice(i, 1); });
          control.write('N');
        });
        const rv = net.createServer((line) => {
          line.on('error', () => line.destroy());
          line.once('data', (chunk) => {
            const kind = chunk[0];
            if (chunk.length > 1) line.unshift(chunk.subarray(1));
            if (kind === 0x43 && !control) { // 'C': the first control line wins; the bridge makes it before the program starts
              control = line;
              line.once('close', () => { control = null; for (const w of waiting.splice(0)) w.destroy(); });
              return;
            }
            const caller = kind === 0x44 ? waiting.shift() : undefined; // 'D'
            if (caller) link(caller, line); else line.destroy();
          });
        });
        rv.once('error', (e) => { console.warn(`[sandbox] bridge socket: ${e.message}`); child.kill('SIGKILL'); });
        rv.listen(rvSock);
        servers.push(rv);
      }
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
