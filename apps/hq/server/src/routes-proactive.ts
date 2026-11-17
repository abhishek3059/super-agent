import { Hono } from 'hono';
import { z } from 'zod';
import { readJson } from './lib/request.js';
import { requireUser, type AuthVars } from './lib/auth.js';
import { fireCheckin, getCheckins, setCheckins } from './proactive.js';

/** /api/checkins: proactive check-in settings for the primary bot. */
export const checkinsApi = new Hono<AuthVars>();
checkinsApi.use('*', requireUser);

checkinsApi.get('/', (c) => c.json(getCheckins(c.get('user').id)));

checkinsApi.put('/', async (c) => {
  const body = await readJson(c, z.strictObject({
    enabled: z.boolean().optional(), times: z.array(z.string()).optional(), timezone: z.string().optional(),
  }));
  try {
    return c.json(setCheckins(c.get('user').id, body));
  } catch (e: any) {
    return c.json({ error: e?.message ?? String(e) }, 400);
  }
});

/** Trigger a check-in now (for testing / "check in with me" button). */
checkinsApi.post('/now', (c) => {
  fireCheckin(c.get('user').id, 0, true);
  return c.json({ ok: true });
});
