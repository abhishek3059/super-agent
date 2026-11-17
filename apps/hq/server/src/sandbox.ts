import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { env } from './env.js';

/**
 * Containment for a bot's processes (its Hermes gateway and its Chrome), using the macOS sandbox.
 * A bot runs as the operator's user, so without this it could read the operator's files, another
 * bot's folder, and this app's session secret (and with that sign in as the operator). Inside the
 * profile a process and everything it starts can write only the folders it is given, read nothing
 * of the operator's or this app's beyond those, reach only the local ports and sockets it is given,
 * and cannot hand work to an unsandboxed app. It can still read system files and reach the internet.
 */

export interface Confinement {
  /** Folders (or files) it may read. Its own temporary folder is added (see tmpFor). */
  read: string[];
  /** Folders it may read and write. */
  write: string[];
  /** Loopback TCP ports it may connect to. The internet stays reachable. */
  localPorts: number[];
  /** The one loopback TCP port it may listen on (its own API or debugging port), if any. */
  listen?: number;
  /**
   * An app's bundle id, for a browser: Chromium ignores TMPDIR for its profile lock and makes it in
   * the system's per-user temp folder as `<bundle id>.XXXXXX`. Only folders of that name are opened.
   */
  tempPrefix?: string;
}

const q = (s: string) => `"${s.replace(/[\\"]/g, '\\$&')}"`;

/** Every folder above `p`, so a path can be walked down to without listing what else is there. */
function ancestors(p: string): string[] {
  const out: string[] = [];
  for (let d = path.dirname(p); d !== path.dirname(d); d = path.dirname(d)) out.push(d);
  return out;
}

/**
 * Closed to reads unless listed in the confinement: the operator's and other people's files, other
 * disks, the shared temporary folders, and every folder of this app and of the operator's Hermes,
 * wherever settings put them.
 */
const closed = () => [
  os.homedir(), '/Users', '/Volumes', '/Network', '/private/var/root', '/private/tmp', '/private/var/folders',
  env.dataDir, env.enginesDir, env.profilesDir, env.filesDir, path.dirname(env.dbPath), env.hermesHome,
];

/** Device files every program writes (null, the terminal, the debugger hooks). */
const DEVICES = '(subpath "/dev")';

/**
 * Ways into the operator's secrets that do not go through a file path. Launch Services itself stays
 * reachable (Chrome will not start without it); `lsopen` below is what stops apps being opened.
 */
const SERVICES = [
  'com.apple.SecurityServer', 'com.apple.securityd', 'com.apple.secd', 'com.apple.security.agent', // Keychain
  'com.apple.pasteboard.1', // clipboard
  'com.apple.coreservices.quarantine-resolver',
  'com.apple.tccd', 'com.apple.tccd.system',
];

export function sandboxProfile(c: Confinement): string {
  const real = (p: string) => { try { return fs.realpathSync(p); } catch { return path.resolve(p); } };
  const shut = [...new Set(closed().map(real))];
  const read = c.read.map(real);
  const write = c.write.map(real);
  const walk = [...new Set([...read, ...write].flatMap(ancestors))];
  return [
    '(version 1)',
    '(allow default)',
    // No way to ask an unsandboxed app to act for it.
    '(deny appleevent-send)', '(deny lsopen)', '(deny job-creation)',
    `(deny mach-lookup ${SERVICES.map((s) => `(global-name ${q(s)})`).join(' ')})`,
    // Other processes: not their environment (it can hold keys), not their signals.
    '(deny process-info* (target others))', '(deny signal (target others))',
    // Files. Writes: nowhere but its own folders, so it cannot replace a program the operator runs
    // later (Homebrew, /Applications, /usr/local). Reads: nothing under the closed folders.
    '(deny file-write* (subpath "/"))',
    `(allow file-write* ${DEVICES})`,
    `(deny file-read* ${shut.map((d) => `(subpath ${q(d)})`).join(' ')})`,
    walk.length ? `(allow file-read-metadata ${walk.map((d) => `(literal ${q(d)})`).join(' ')})` : '',
    read.length ? `(allow file-read* ${read.map((d) => `(subpath ${q(d)})`).join(' ')})` : '',
    write.length ? `(allow file-read* file-write* ${write.map((d) => `(subpath ${q(d)})`).join(' ')})` : '',
    // Listening: only on its own port and in its own folders. Otherwise a bot could take another
    // bot's port before that bot starts, and answer in its place.
    '(deny network-bind)',
    c.listen ? `(allow network-bind (local ip "localhost:${Math.trunc(c.listen)}"))` : '',
    write.length ? `(allow network-bind ${write.map((d) => `(local unix-socket (subpath ${q(d)}))`).join(' ')})` : '',
    // Local network: only its own ports. Another bot's browser and gateway listen on loopback too.
    '(deny network-outbound (remote ip "localhost:*"))',
    // Local sockets: only its own (the browser helper's, Chrome's lock) and the system's name lookup
    // and log, not the operator's ssh-agent or anyone else's.
    '(deny network-outbound (remote unix-socket))',
    '(allow network-outbound (remote unix-socket (path-literal "/private/var/run/mDNSResponder") (path-literal "/private/var/run/syslog")))',
    write.length ? `(allow network-outbound ${write.map((d) => `(remote unix-socket (subpath ${q(d)}))`).join(' ')})` : '',
    c.localPorts.length ? `(allow network-outbound ${c.localPorts.map((p) => `(remote ip "localhost:${Math.trunc(p)}")`).join(' ')})` : '',
    ...(c.tempPrefix && /^[A-Za-z0-9.-]{3,100}$/.test(c.tempPrefix) ? [
      '(allow file-read-metadata (regex #"^/private/var/folders"))',
      '(allow file-read* (regex #"^/private/var/folders/[^/]+/[^/]+/T/?$"))',
      `(allow file-read* file-write* (regex #"^/private/var/folders/[^/]+/[^/]+/T/${c.tempPrefix.replace(/\./g, '\\.')}\\."))`,
      `(allow network-bind (local unix-socket (regex #"^/private/var/folders/[^/]+/[^/]+/T/${c.tempPrefix.replace(/\./g, '\\.')}\\.")))`,
    ] : []),
  ].filter(Boolean).join('\n');
}

const SANDBOX_EXEC = '/usr/bin/sandbox-exec';

/**
 * The confined process's own temporary folder, in place of the shared one it cannot see. Kept short:
 * Chrome puts a socket under it, and macOS socket paths stop at 104 bytes.
 */
export const tmpFor = (name: string) => path.join(env.dataDir, 't', crypto.createHash('sha256').update(name).digest('hex').slice(0, 8));

/** The environment a confined process starts with: nothing of this server's (no keys), and its own temp folder. */
export function confinedEnv(name: string, extra: Record<string, string> = {}): NodeJS.ProcessEnv {
  const tmp = tmpFor(name);
  fs.mkdirSync(tmp, { recursive: true, mode: 0o700 });
  return {
    PATH: process.env.PATH ?? '/usr/local/bin:/usr/bin:/bin',
    HOME: process.env.HOME ?? '',
    USER: process.env.USER ?? '',
    LANG: process.env.LANG ?? 'C.UTF-8',
    TMPDIR: tmp + '/',
    ...extra,
  };
}

/** True when bots can be contained on this machine. */
export const canContain = () => process.platform === 'darwin' && fs.existsSync(SANDBOX_EXEC);

/**
 * The command that runs `bin args` inside the confinement. Fails closed: where there is no sandbox
 * (not macOS) it throws, unless the operator set HQ_UNCONTAINED=1 and accepts uncontained bots.
 */
export function contained(bin: string, args: string[], c: Confinement, name: string): { bin: string; args: string[] } {
  fs.mkdirSync(tmpFor(name), { recursive: true, mode: 0o700 });
  const confinement = { ...c, write: [...c.write, tmpFor(name)] };
  if (canContain()) return { bin: SANDBOX_EXEC, args: ['-p', sandboxProfile(confinement), bin, ...args] };
  if (process.env.HQ_UNCONTAINED === '1') return { bin, args };
  throw new Error('Bots can only be contained on macOS. Set HQ_UNCONTAINED=1 to run them uncontained at your own risk.');
}

/** Full path of a command on PATH (the sandbox needs to be told which file it may read). */
export function which(bin: string): string {
  if (bin.includes('/')) return path.resolve(bin);
  for (const dir of (process.env.PATH ?? '').split(':')) {
    const p = path.join(dir, bin);
    try { fs.accessSync(p, fs.constants.X_OK); return p; } catch { /* next */ }
  }
  return bin;
}
