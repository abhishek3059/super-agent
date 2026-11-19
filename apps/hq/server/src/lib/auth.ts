import type { MiddlewareHandler } from 'hono';
import crypto from 'node:crypto';
import { env } from '../env.js';
import { db, now } from '../db.js';
import { sha256, token } from './ids.js';
import type { User } from '../types.js';

const TTL_MS = 30 * 24 * 3600 * 1000;

export type AuthVars = { Variables: { user: User } };

export function createSession(userId: string): string {
  const t = token();
  db.prepare('INSERT INTO auth_sessions(token,user_id,created_at,expires_at) VALUES (?,?,?,?)').run(sha256(t), userId, now(), now() + TTL_MS);
  return t;
}

const bearer = (authorization: string | undefined) => /^Bearer ([A-Za-z0-9_-]{43})$/i.exec(authorization ?? '')?.[1];

export function destroySession(authorization: string | undefined) {
  const t = bearer(authorization);
  if (t) db.prepare('DELETE FROM auth_sessions WHERE token=?').run(sha256(t));
}

export function userFromToken(t: string | undefined): User | null {
  if (!t || !/^[A-Za-z0-9_-]{43}$/.test(t)) return null;
  const r = db
    .prepare('SELECT u.* FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>?')
    .get(sha256(t), now()) as any;
  return r ? { id: r.id, email: r.email, name: r.name, avatarUrl: r.avatar_url } : null;
}

export const userFromAuthorization = (authorization: string | undefined) => userFromToken(bearer(authorization));

export const requireUser: MiddlewareHandler<AuthVars> = async (c, next) => {
  const u = userFromAuthorization(c.req.header('authorization'));
  if (!u) return c.json({ error: 'unauthenticated' }, 401);
  c.set('user', u);
  await next();
};

export function ownerProof(side: 'server' | 'client', client: string, server: string): string {
  return crypto.createHmac('sha256', env.sessionSecret).update(`hq-owner:${side}:${client}:${server}`).digest('hex');
}
