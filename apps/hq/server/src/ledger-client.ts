import { z } from 'zod';
import { env } from './env.js';

export const roles = ['scout', 'forge', 'quill', 'atlas', 'ops'] as const;
export type Role = (typeof roles)[number];

const id = z.string().regex(/^[a-f0-9]{32}$/);
const claimSchema = z.object({
  job: z.object({ id, revision: z.int().positive(), instruction: z.string().min(1).max(1000) }).nullable(),
});
const acknowledgment = z.object({ id, state: z.string() });
export type Claim = NonNullable<z.infer<typeof claimSchema>['job']>;
export type Receipt = { state: 'succeeded' | 'failed' | 'unknown'; summary: string; artifacts: string[] };

export function ledgerClient(token: string, request: typeof fetch = fetch) {
  async function post<S extends z.ZodType>(role: Role, verb: string, body: object, schema: S): Promise<z.output<S>> {
    if (!/^[A-Za-z0-9_-]{43,128}$/.test(token)) throw new Error('ledger disabled');
    const response = await request(`http://127.0.0.1:8000/api/jobs/${role}/${verb}`, {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(2000),
      headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error('ledger request rejected');
    return schema.parse(await response.json());
  }

  return {
    submit: (role: Role, key: string, instruction: string) => post(role, 'submit', { key, instruction }, acknowledgment),
    claim: async (role: Role) => (await post(role, 'claim', {}, claimSchema)).job,
    finish: (role: Role, claim: Claim, receipt: Receipt) =>
      post(role, 'finish', { id: claim.id, revision: claim.revision, ...receipt }, acknowledgment),
  };
}

export const jobs = ledgerClient(env.ledgerToken);
