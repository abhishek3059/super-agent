import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const noncePattern = /^[0-9a-f]{64}$/;

export async function ownerLogin(base, dataDir, signal = AbortSignal.timeout(5000)) {
  const url = new URL(base);
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || url.origin !== base) {
    throw new Error('Owner sign-in requires the local HQ origin');
  }
  const secret = process.env.SESSION_SECRET ?? fs.readFileSync(path.join(dataDir, 'session-secret'), 'utf8').trim();
  if (!secret) throw new Error('Owner sign-in secret is missing');
  const client = crypto.randomBytes(32).toString('hex');
  const hmac = (side, server) => crypto.createHmac('sha256', secret).update(`hq-owner:${side}:${client}:${server}`).digest('hex');
  const endpoint = `${base}/api/auth/owner`;
  const options = { redirect: 'error', signal };
  const challenge = await fetch(`${endpoint}?client=${client}`, options);
  if (!challenge.ok) throw new Error(`Owner challenge refused (HTTP ${challenge.status})`);
  const { server, proof } = await challenge.json();
  if (!noncePattern.test(String(server)) || !noncePattern.test(String(proof)) ||
      !crypto.timingSafeEqual(Buffer.from(proof, 'hex'), Buffer.from(hmac('server', server), 'hex'))) {
    throw new Error('Could not authenticate the local HQ server');
  }
  const result = await fetch(endpoint, {
    ...options, method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ server, proof: hmac('client', server) }),
  });
  if (!result.ok) throw new Error(`Owner sign-in refused (HTTP ${result.status})`);
  const { url: link } = await result.json();
  if (typeof link !== 'string' || !link.startsWith(`${base}/api/auth/link/`) ||
      !/^[\w-]{32}$/.test(link.slice(`${base}/api/auth/link/`.length))) {
    throw new Error('Owner sign-in returned an invalid link');
  }
  return link;
}
