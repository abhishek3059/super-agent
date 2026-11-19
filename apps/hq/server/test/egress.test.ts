// Self-checks for the bot egress proxy: only public addresses pass, and nothing local is reachable
// through it. Uses loopback targets only, so it needs no internet.
import assert from 'node:assert/strict';
import { createServer, type Server } from 'node:http';
import net from 'node:net';
import { after, before, test } from 'node:test';
import { isPublicAddress, startEgressProxy } from '../src/lib/egress.js';

test('non-public addresses are refused', () => {
  for (const ip of [
    '0.0.0.0', '0.1.2.3', '10.0.0.1', '100.64.0.1', '100.127.255.255', '127.0.0.1', '127.255.255.254', '169.254.169.254',
    '172.16.0.1', '172.31.255.255', '192.0.0.8', '192.0.2.1', '192.88.99.1', '192.168.1.1', '198.18.0.1', '198.19.255.255',
    '198.51.100.7', '203.0.113.9', '224.0.0.1', '239.255.255.250', '240.0.0.1', '255.255.255.255',
    '::', '::1', '::ffff:0.0.0.0', '::ffff:127.0.0.1', '::ffff:10.0.0.1', '::ffff:7f00:1', '::127.0.0.1', '::0.0.0.1',
    '64:ff9b::7f00:1', '64:ff9b::10.0.0.1', '100::1', '2001::1', '2001:1ff::1', '2001:db8::1', '2002:7f00:1::', '2002:a00:1::1',
    'fc00::1', 'fd12:3456::1', 'fe80::1', 'fe80::1%en0', 'febf::1', 'ff02::1',
    '', 'localhost', 'example.com', '1.2.3', '1.2.3.4.5', '256.1.1.1', '0177.0.0.1', '2130706433', '[::1]', ':::1', 'garbage',
  ]) assert.equal(isPublicAddress(ip), false, ip);
});

test('public addresses pass', () => {
  for (const ip of ['93.184.215.14', '1.1.1.1', '8.8.8.8', '2606:2800:21f:cb07:6820:80da:af6b:4b18',
    '::ffff:1.1.1.1', '64:ff9b::808:808', '2002:808:808::1', '2001:4860:4860::8888']) assert.equal(isPublicAddress(ip), true, ip);
});

let hits = 0;
let local: Server;
let localPort = 0;
let proxy: Awaited<ReturnType<typeof startEgressProxy>>;

before(async () => {
  local = createServer((_req, res) => { hits++; res.end('reached'); });
  await new Promise<void>((r) => local.listen(0, '127.0.0.1', r));
  localPort = (local.address() as net.AddressInfo).port;
  proxy = await startEgressProxy(0);
});

after(async () => {
  await proxy.close();
  await new Promise((r) => local.close(r));
});

// Sends one raw request to the proxy and returns the status code of its reply.
function status(request: string): Promise<number> {
  return new Promise((resolve, reject) => {
    const s = net.connect(proxy.port, '127.0.0.1', () => s.write(request));
    let buf = '';
    s.on('data', (d) => {
      buf += d;
      const m = /^HTTP\/1\.1 (\d{3})/.exec(buf);
      if (m) { s.destroy(); resolve(Number(m[1])); }
    });
    s.on('error', reject);
    s.on('close', () => reject(new Error(`no status: ${JSON.stringify(buf)}`)));
  });
}

const connect = (target: string) => status(`CONNECT ${target} HTTP/1.1\r\nHost: ${target}\r\n\r\n`);

test('CONNECT to loopback is refused', async () => {
  for (const t of [`127.0.0.1:${localPort}`, `localhost:${localPort}`, `[::ffff:0.0.0.0]:${localPort}`, `[::1]:${localPort}`,
    `[::ffff:127.0.0.1]:${localPort}`, `127.1:${localPort}`, `2130706433:${localPort}`]) assert.equal(await connect(t), 403, t);
});

test('plain HTTP to loopback is refused', async () => {
  for (const u of [`http://127.0.0.1:${localPort}/`, `http://localhost:${localPort}/`, `http://[::ffff:0.0.0.0]:${localPort}/`,
    `http://127.0.0.1:${proxy.port}/`]) assert.equal(await status(`GET ${u} HTTP/1.1\r\nHost: x\r\n\r\n`), 403, u);
});

test('malformed requests get 400', async () => {
  assert.equal(await connect('127.0.0.1:0'), 400);
  assert.equal(await connect('127.0.0.1'), 400);
  assert.equal(await connect('::1:443'), 400);
  assert.equal(await connect(`${'a'.repeat(254)}:443`), 400);
  assert.equal(await connect('bad host!:443'), 400);
  assert.equal(await status('GET / HTTP/1.1\r\nHost: x\r\n\r\n'), 400);
  assert.equal(await status(`GET https://127.0.0.1:${localPort}/ HTTP/1.1\r\nHost: x\r\n\r\n`), 400);
});

test('the local server was never reached through the proxy', () => {
  assert.equal(hits, 0);
});
