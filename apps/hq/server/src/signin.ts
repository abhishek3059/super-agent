import { spawn, type ChildProcess } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { env } from './env.js';
import { readOwn, writeOwn } from './lib/own.js';

/**
 * Provider sign-in for the HQ Hermes profile (env.hermesHome), which every bot's home copies from
 * on start. ChatGPT uses Hermes' own Codex OAuth: the person signs in on OpenAI's page in their own
 * browser, and the tokens land in that profile's auth.json. Claude takes an API key, kept owner-only
 * in that profile's .env. No credential passes through the web page except the key the person pastes.
 * Hermes runs here as the operator, as `hermes auth add` in a terminal would, so this is offered only
 * for a seed HQ alone uses (HERMES_HOME_PRIMARY), never the operator's own ~/.hermes.
 */

const NEEDS_SEED = 'Sign-in from HQ needs a Hermes seed only HQ uses. Set HERMES_HOME_PRIMARY and restart HQ.';
export const signInAvailable = () => env.dedicatedSeed;

export interface SignIn { status: 'idle' | 'pending' | 'done' | 'error'; url: string | null; code: string | null; error: string | null }

let state: SignIn = { status: 'idle', url: null, code: null, error: null };
let child: ChildProcess | null = null;

/** The sign-in link and (device flow only) the code, from Hermes' printed instructions. */
export function parseLoginOutput(out: string): { url: string | null; code: string | null } {
  const text = out.replace(/\x1b\[[0-9;]*m/g, '');
  const url = text.match(/https:\/\/[^\s"'<>]+/)?.[0] ?? null;
  const code = text.match(/Enter this code:\s*([A-Z0-9]{4,}(?:-[A-Z0-9]{4,})*)/)?.[1] ?? null;
  return { url: url && /^https:\/\/(auth\.openai\.com|chatgpt\.com)\//.test(url) ? url : null, code };
}

export const signInState = (): SignIn => state;

/** Which accounts the seed holds, from its files (never their values). */
export function accounts(): { chatgpt: boolean; claude: boolean } {
  let auth: any = null;
  try { auth = JSON.parse(readOwn(env.hermesHome, 'auth.json')?.text ?? 'null'); } catch { /* unreadable: not connected */ }
  const dotenv = readOwn(env.hermesHome, '.env')?.text ?? '';
  return {
    chatgpt: !!(auth?.providers?.['openai-codex'] || auth?.credential_pool?.['openai-codex']?.length),
    claude: /^\s*(export\s+)?ANTHROPIC_API_KEY\s*=\s*\S/m.test(dotenv),
  };
}

export function startCodexSignIn(): SignIn {
  if (!env.dedicatedSeed) throw new Error(NEEDS_SEED);
  if (state.status === 'pending') return state;
  state = { status: 'pending', url: null, code: null, error: null };
  // Only what Hermes needs: this server's own keys (voice) stay here.
  const p = spawn(env.hermesBin, ['auth', 'add', 'openai-codex', '--type', 'oauth', '--browser', '--no-browser', '--timeout', '600'], {
    env: { PATH: process.env.PATH ?? '', HOME: process.env.HOME ?? '', HERMES_HOME: env.hermesHome },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child = p;
  let out = '';
  const read = (d: Buffer) => {
    if (child !== p) return; // a cancelled sign-in's late output
    out = (out + d.toString()).slice(-20_000);
    const found = parseLoginOutput(out);
    state = { ...state, url: state.url ?? found.url, code: state.code ?? found.code };
  };
  p.stdout!.on('data', read);
  p.stderr!.on('data', read);
  const kill = setTimeout(() => p.kill('SIGTERM'), 11 * 60_000);
  p.on('error', (e) => { if (child === p) state = { ...state, status: 'error', error: `Could not run Hermes: ${e.message}` }; });
  p.on('close', (code) => {
    clearTimeout(kill);
    if (child !== p) return;
    child = null;
    if (state.status !== 'pending') return;
    const last = out.replace(/\x1b\[[0-9;]*m/g, '').trim().split('\n').pop()?.slice(0, 200) ?? '';
    state = code === 0 ? { status: 'done', url: null, code: null, error: null } : { ...state, status: 'error', error: last || 'Sign-in did not finish.' };
  });
  return state;
}

export function cancelSignIn() {
  const p = child;
  child = null;
  p?.kill('SIGTERM');
  state = { status: 'idle', url: null, code: null, error: null };
}

const ANTHROPIC_KEY = /^sk-ant-[A-Za-z0-9_-]{20,300}$/;

/** Store or replace the Anthropic key in the HQ Hermes seed's .env, keeping every other line. */
export function saveAnthropicKey(key: unknown): void {
  if (!env.dedicatedSeed) throw new Error(NEEDS_SEED);
  if (typeof key !== 'string' || !ANTHROPIC_KEY.test(key.trim())) throw new Error('That does not look like an Anthropic API key (sk-ant-…).');
  // Rewriting a file we could not read would lose the keys in it: refuse instead.
  const exists = fs.existsSync(path.join(env.hermesHome, '.env')) || isLink(path.join(env.hermesHome, '.env'));
  const old = exists ? readOwn(env.hermesHome, '.env') : { text: '' };
  if (!old) throw new Error('The Hermes seed .env is not a plain readable file. Fix it by hand; nothing was changed.');
  const lines = old.text ? old.text.replace(/\n$/, '').split('\n').filter((l) => !/^\s*(export\s+)?ANTHROPIC_API_KEY\s*=/.test(l)) : [];
  writeOwn(env.hermesHome, '.env', [...lines, `ANTHROPIC_API_KEY=${key.trim()}`].join('\n') + '\n');
}

const isLink = (f: string) => { try { return fs.lstatSync(f).isSymbolicLink(); } catch { return false; } };
