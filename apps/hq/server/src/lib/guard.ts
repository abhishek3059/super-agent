import { env } from '../env.js';

// Loopback only, and only when addressed as loopback: a page on another site that points a DNS name
// at 127.0.0.1 is refused by the Host check, and its cross-site writes by the Origin check.
const LOOPBACK = new Set([`127.0.0.1:${env.port}`, `localhost:${env.port}`]);
export const allowedHost = (host: string | undefined) => !!host && LOOPBACK.has(host);
const ORIGINS = new Set([...LOOPBACK].map((host) => `http://${host}`).concat(env.appUrl));
export function allowedOrigin(origin: string | undefined): boolean {
  return origin === undefined || ORIGINS.has(origin);
}
