import type { Context } from 'hono';
import { HTTPException } from 'hono/http-exception';
import type { z } from 'zod';

export async function readJson<Schema extends z.ZodType>(c: Context, schema: Schema): Promise<z.output<Schema>> {
  const body: unknown = await c.req.json().catch(() => undefined);
  const parsed = schema.safeParse(body);
  if (!parsed.success) throw new HTTPException(400, {
    res: c.json({ error: 'invalid request body' }, 400),
  });
  return parsed.data;
}
