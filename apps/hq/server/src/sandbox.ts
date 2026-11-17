import fs from 'node:fs';
import path from 'node:path';

const launcher = '/usr/bin/sandbox-exec';
const quote = JSON.stringify;
const readable = ['/System', '/usr/lib', '/usr/bin', '/bin', '/sbin', '/dev/null', '/dev/urandom',
  '/private/etc', '/private/var/select/sh', '/Library/Apple/System/Library', '/Library/Frameworks', '/opt/homebrew/Cellar'];

export function canContain() {
  return process.platform === 'darwin' && fs.existsSync(launcher);
}

export function workspaceDirectory(dir: string) {
  fs.mkdirSync(dir, { mode: 0o700, recursive: true });
  if (fs.realpathSync(dir) !== dir || !fs.lstatSync(dir).isDirectory()) throw new Error('unsafe worker directory');
}

export function contained(bin: string, args: string[], read: string[], write: string[], ports: number[], listen: number) {
  if (!canContain()) throw new Error('Worker containment requires macOS');
  const executable = bin.includes('/') ? bin : (process.env.PATH ?? '').split(path.delimiter)
    .map((dir) => path.resolve(dir, bin)).find((file) => fs.existsSync(file));
  if (!executable) throw new Error('Worker executable unavailable');
  const paths = (items: string[]) => [...new Set(items)].map((p) => `(subpath ${quote(p)})`).join(' ');
  const ancestors = [...new Set([...read, ...write, executable].flatMap((file) => {
    const dirs: string[] = [];
    for (let dir = path.dirname(file); dir !== path.dirname(dir); dir = path.dirname(dir)) dirs.push(dir);
    return dirs;
  }))];
  const endpoint = (port: number) => {
    if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid worker port');
    return quote(`localhost:${port}`);
  };
  const profile = [
    '(version 1)', '(allow default)',
    '(deny file-read* file-write* network* appleevent-send lsopen job-creation)',
    '(deny process-info* (target others))', '(deny signal (target others))',
    '(deny mach-lookup (global-name "com.apple.SecurityServer") (global-name "com.apple.securityd") (global-name "com.apple.secd") (global-name "com.apple.pasteboard.1") (global-name "com.apple.tccd"))',
    `(allow file-read* (literal "/") ${paths([...readable, ...read, executable, fs.realpathSync(executable), ...write])})`,
    `(allow file-read-metadata (literal "/etc") (literal "/etc/hermes") ${ancestors.map((p) => `(literal ${quote(p)})`).join(' ')})`,
    `(allow file-write* ${paths([...write, '/dev/null'])})`,
    `(allow network-bind network-inbound (local ip ${endpoint(listen)}))`,
    ...write.map((dir) => `(allow network-bind network-inbound (local unix-socket (subpath ${quote(dir)})))`),
    ...write.map((dir) => `(allow network-outbound (remote unix-socket (subpath ${quote(dir)})))`),
    ...(ports.length ? [`(allow network-outbound ${ports.map((p) => `(remote ip ${endpoint(p)})`).join(' ')})`] : []),
  ].join('\n');
  return { bin: launcher, args: ['-p', profile, executable, ...args] };
}
