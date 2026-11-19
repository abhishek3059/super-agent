// The only way a sandboxed bot reaches the network. The sandbox profile lets bots dial a few
// loopback ports and nothing else, because an SBPL `localhost` filter missed ::ffff:0.0.0.0 and
// left every local service open. This proxy runs unsandboxed, resolves each target itself,
// refuses unless every address is public, and then dials that checked address (no re-resolve,
// so DNS rebinding cannot swap in a private one). HTTPS is a raw tunnel: TLS stays end to end.
import dns from 'node:dns/promises';
import http from 'node:http';
import net from 'node:net';

const CONNECT_MS = 15_000;
const IDLE_MS = 5 * 60_000;

const v4Blocked = new net.BlockList();
for (const [a, bits] of [['0.0.0.0', 8], ['10.0.0.0', 8], ['100.64.0.0', 10], ['127.0.0.0', 8], ['169.254.0.0', 16],
  ['172.16.0.0', 12], ['192.0.0.0', 24], ['192.0.2.0', 24], ['192.88.99.0', 24], ['192.168.0.0', 16], ['198.18.0.0', 15],
  ['198.51.100.0', 24], ['203.0.113.0', 24], ['224.0.0.0', 4], ['240.0.0.0', 4]] as const) v4Blocked.addSubnet(a, bits, 'ipv4');
// Only 2000::/3 is global unicast, which already refuses ::, ::1, 100::/64, fc00::/7, fe80::/10 and ff00::/8.
const v6Blocked = new net.BlockList();
v6Blocked.addSubnet('2001::', 23, 'ipv6');
v6Blocked.addSubnet('2001:db8::', 32, 'ipv6');

// Expands a valid IPv6 string to its eight 16-bit words.
function v6Words(ip: string): number[] {
  const dot = ip.lastIndexOf(':');
  if (ip.includes('.')) {
    const [a, b, c, d] = ip.slice(dot + 1).split('.').map(Number);
    ip = `${ip.slice(0, dot + 1)}${((a << 8) | b).toString(16)}:${((c << 8) | d).toString(16)}`;
  }
  const [l, r = null] = ip.split('::');
  const left = l ? l.split(':') : [];
  const right = r ? r.split(':') : [];
  const fill = r === null ? [] : Array(8 - left.length - right.length).fill('0');
  return [...left, ...fill, ...right].map((h) => parseInt(h, 16));
}

export function isPublicAddress(ip: string): boolean {
  if (net.isIPv4(ip)) return !v4Blocked.check(ip, 'ipv4');
  if (!net.isIPv6(ip) || ip.includes('%')) return false;
  const w = v6Words(ip);
  const v4 = (hi: number, lo: number) => isPublicAddress(`${hi >> 8}.${hi & 255}.${lo >> 8}.${lo & 255}`);
  const zero = (from: number, to: number) => w.slice(from, to).every((x) => x === 0);
  if (zero(0, 5) && (w[5] === 0 || w[5] === 0xffff)) return v4(w[6], w[7]); // IPv4-compatible (incl. ::, ::1) and mapped
  if (w[0] === 0x64 && w[1] === 0xff9b && zero(2, 6)) return v4(w[6], w[7]); // NAT64
  if (w[0] === 0x2002) return v4(w[1], w[2]); // 6to4
  return (w[0] & 0xe000) === 0x2000 && !v6Blocked.check(ip, 'ipv6');
}

const NAME = /^[a-z0-9_.-]{1,253}$/i;
const HOP = new Set(['connection', 'keep-alive', 'te', 'trailer', 'transfer-encoding', 'upgrade', 'host']);

class Refusal extends Error {
  constructor(readonly status: number, readonly reason: string) { super(reason); }
}

function target(host: string, port: string): { host: string; port: number } {
  const n = Number(port || 0);
  const bare = host.startsWith('[') && host.endsWith(']') ? host.slice(1, -1) : host;
  const ok = host === bare ? NAME.test(host) : net.isIPv6(bare);
  if (!ok || !Number.isInteger(n) || n < 1 || n > 65535) throw new Refusal(400, 'bad-target');
  return { host: bare, port: n };
}

// Resolves once and returns an address that has already passed the public check.
async function checkedAddress(host: string): Promise<string> {
  const addrs = net.isIP(host) ? [host] : (await dns.lookup(host, { all: true }).catch(() => [])).map((a) => a.address);
  if (!addrs.length) throw new Refusal(502, 'dns');
  if (!addrs.every(isPublicAddress)) throw new Refusal(403, 'not-public');
  return addrs[0];
}

function dial(host: string, port: number): net.Socket {
  const s = net.connect({ host, port });
  s.setTimeout(CONNECT_MS, () => s.destroy(new Error('timeout')));
  s.once('connect', () => s.setTimeout(IDLE_MS));
  return s;
}

function refused(e: unknown): Refusal {
  const r = e instanceof Refusal ? e : new Refusal(502, 'upstream');
  console.warn(`egress: refused (${r.reason})`);
  return r;
}

export function startEgressProxy(port: number, host = '127.0.0.1'): Promise<{ port: number; close(): Promise<void> }> {
  const tunnels = new Set<net.Socket>();
  const server = http.createServer(async (req, res) => {
    try {
      if (!req.url?.startsWith('http://')) throw new Refusal(400, 'not-absolute');
      let url: URL;
      try { url = new URL(req.url); } catch { throw new Refusal(400, 'bad-url'); }
      const t = target(url.hostname, url.port || '80');
      const addr = await checkedAddress(t.host);
      const named = new Set(String(req.headers.connection ?? '').toLowerCase().split(',').map((x) => x.trim()));
      const headers = Object.fromEntries(Object.entries(req.headers).filter(([k]) => !HOP.has(k) && !named.has(k) && !k.startsWith('proxy-')));
      const up = http.request({ method: req.method, path: url.pathname + url.search, headers: { ...headers, host: url.host },
        createConnection: () => dial(addr, t.port) });
      up.on('response', (r) => {
        res.writeHead(r.statusCode ?? 502, Object.fromEntries(Object.entries(r.headers).filter(([k]) => !HOP.has(k) && !k.startsWith('proxy-'))));
        r.pipe(res);
      });
      up.on('error', () => { refused(null); if (res.headersSent) res.destroy(); else res.writeHead(502).end(); });
      req.on('error', () => up.destroy());
      res.on('close', () => up.destroy());
      req.pipe(up);
    } catch (e) {
      res.writeHead(refused(e).status, { connection: 'close' }).end();
    }
  });
  server.on('connect', async (req: http.IncomingMessage, client: net.Socket, head: Buffer) => {
    tunnels.add(client);
    client.on('close', () => tunnels.delete(client));
    client.on('error', () => client.destroy());
    client.setTimeout(IDLE_MS, () => client.destroy());
    try {
      const m = /^(\[[^\]]+\]|[^:[\]]+):(\d{1,5})$/.exec(req.url ?? '');
      if (!m) throw new Refusal(400, 'bad-target');
      const t = target(m[1], m[2]);
      const upstream = dial(await checkedAddress(t.host), t.port);
      let open = false;
      const kill = () => { upstream.destroy(); client.destroy(); };
      upstream.on('error', () => { if (open) kill(); else client.end(`HTTP/1.1 ${refused(null).status} Refused\r\n\r\n`); });
      upstream.on('close', () => { if (open) kill(); });
      client.on('close', kill);
      upstream.once('connect', () => {
        open = true;
        client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
        upstream.write(head);
        upstream.pipe(client).pipe(upstream);
      });
    } catch (e) {
      client.end(`HTTP/1.1 ${refused(e).status} Refused\r\nConnection: close\r\n\r\n`);
    }
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, host, () => resolve({
      port: (server.address() as net.AddressInfo).port,
      close: () => new Promise<void>((done) => {
        for (const s of tunnels) s.destroy();
        server.closeAllConnections();
        server.close(() => done());
      }),
    }));
  });
}
