import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import YAML from 'yaml';
import { cdpPortFor, cdpUrlFor } from './computer.js';
import { db } from './db.js';
import { env, workspaceFor } from './env.js';
import { contained, workspaceDirectory } from './sandbox.js';
import type { EngineInfo, EngineProvider } from './types.js';

/**
 * Every bot is run by a Hermes agent.
 *
 * - The 'primary' engine is a Hermes gateway that already runs on the computer (HERMES_URL, home
 *   HERMES_HOME_PRIMARY). It has its own life: messaging, memory, model. We only talk to its API
 *   server; we never write its config, restart it or stop it.
 * - A 'managed' engine is a Hermes home of our own under ~/.super-agent/hq/engines/<botId> with its own
 *   `hermes gateway run`, started here and left running when this server exits. Its home sits
 *   outside ~/.hermes, so Hermes treats it as a separate tenant beside the primary gateway.
 */

export type EngineKind = 'primary' | 'managed';
export interface Engine { kind: EngineKind; url: string; key: string; home: string }

const botRow = (botId: string) => db.prepare('SELECT * FROM bots WHERE id=?').get(botId) as any;

// ---------- small file helpers ----------

function writePrivate(file: string, content: string) {
  const temporary = `${file}.${crypto.randomUUID()}`;
  fs.writeFileSync(temporary, content, { mode: 0o600, flag: 'wx' });
  try { fs.renameSync(temporary, file); } finally { fs.rmSync(temporary, { force: true }); }
}

// ---------- identity ----------

export function engineKind(botId: string): EngineKind | null {
  const e = botRow(botId)?.engine;
  return e === 'primary' || e === 'managed' ? e : null;
}

const homeFor = (botId: string) => path.join(env.enginesDir, botId, 'runtime');

// ---------- assignment ----------

function freePort(): number {
  const used = new Set((db.prepare('SELECT engine_port FROM bots WHERE engine_port IS NOT NULL').all() as any[]).map((r) => r.engine_port as number));
  let p = env.enginePortBase;
  while (used.has(p)) p++;
  return p;
}

/** Give a new agent bot its engine: the existing agent if nobody has it yet, otherwise one of our own. */
export function assignEngine(botId: string): EngineKind {
  const b = botRow(botId);
  if (!b) throw new Error('bot not found');
  if (b.engine === 'managed' && b.engine_port) return 'managed';
  db.prepare("UPDATE bots SET engine='managed', engine_port=? WHERE id=?").run(freePort(), botId);
  return 'managed';
}

// ---------- a managed bot's Hermes home ----------

function soul(b: any): string {
  const owner = (db.prepare('SELECT name FROM users WHERE id=?').get(b.user_id) as any)?.name ?? 'the user';
  const role = b.label ? `, ${b.label}` : '';
  return [
    `You are ${b.name}${role}. You work for ${owner} as one of a small team of AI agents, each with its own browser and workspace.`,
    b.description ? `\n${b.description}` : '',
    '\nYou are direct, warm and brief. You do the work rather than describe it, and you say plainly what you did and what you could not do.',
    '',
  ].join('\n');
}

/** Rewrite the persona file after a rename or a new description. The primary agent keeps its own. */
export function syncPersona(botId: string) {
  const b = botRow(botId);
  if (!b || b.engine !== 'managed') return;
  const home = homeFor(botId);
  if (!fs.existsSync(home)) return;
  workspaceDirectory(home);
  writePrivate(path.join(home, 'SOUL.md'), soul(b));
}

/** Build a worker config without importing the operator's Hermes configuration or keys. */
function writeHome(botId: string, key: string): string {
  const home = homeFor(botId);
  const cwd = workspaceFor(botId);
  for (const dir of [path.dirname(home), home, cwd, path.join(home, 'tmp'), path.join(home, 'locks')]) workspaceDirectory(dir);
  if (!env.localModel || !Number.isInteger(env.modelPort) || env.modelPort < 1024 || env.modelPort > 65535
      || env.modelPort === env.port || env.modelPort === 8000) throw new Error('Local worker model is not configured');
  const cdp = cdpUrlFor(botId);
  writePrivate(path.join(home, 'config.yaml'), YAML.stringify({
    model: { default: env.localModel, provider: 'custom', base_url: `http://127.0.0.1:${env.modelPort}/v1` },
    gateway: { standalone: true },
    platform_toolsets: { api_server: ['file', 'terminal', 'browser'] },
    terminal: { cwd }, browser: { cdp_url: cdp },
  }));
  writePrivate(path.join(home, 'SOUL.md'), soul(botRow(botId)));
  writePrivate(path.join(home, '.env'), [
    'API_SERVER_ENABLED=true', `API_SERVER_KEY=${key}`,
    `API_SERVER_PORT=${botRow(botId).engine_port}`, 'API_SERVER_HOST=127.0.0.1',
  ].join('\n') + '\n');
  return home;
}

// ---------- a managed bot's gateway ----------

async function healthy(url: string, timeoutMs = 2500): Promise<any | null> {
  try {
    const r = await fetch(`${url}/health`, { signal: AbortSignal.timeout(timeoutMs) });
    return r.ok ? await r.json() : null;
  } catch { return null; }
}

async function keyAccepted(url: string, key: string): Promise<boolean> {
  try {
    const r = await fetch(`${url}/v1/models`, { headers: key ? { Authorization: `Bearer ${key}` } : {}, signal: AbortSignal.timeout(4000) });
    return r.ok;
  } catch { return false; }
}

/** The gateway's pid, but only if the pid file belongs to this home and the process is alive. */
const children = new Map<string, ReturnType<typeof spawn>>();
export async function stopGateway(botId: string): Promise<boolean> {
  const child = children.get(botId);
  if (child?.pid) {
    const stopped = new Promise<void>((resolve) => child.once('exit', () => resolve()));
    try { process.kill(-child.pid, 'SIGTERM'); } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ESRCH') return false;
    }
    await Promise.race([stopped, new Promise<void>((resolve) => setTimeout(resolve, 5000))]);
    if (children.get(botId) === child) {
      try { process.kill(-child.pid, 'SIGKILL'); } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== 'ESRCH') return false;
      }
      await Promise.race([stopped, new Promise<void>((resolve) => setTimeout(resolve, 2000))]);
    }
    if (children.get(botId) === child) return false;
  }
  return !(await healthy(managedUrl(botId), 500));
}

process.once('exit', () => {
  for (const child of children.values()) {
    if (child.pid) try { process.kill(-child.pid, 'SIGKILL'); } catch { /* already gone */ }
  }
});

const agentEnv = (): NodeJS.ProcessEnv => ({
  PATH: process.env.PATH ?? '/usr/local/bin:/usr/bin:/bin',
  HOME: process.env.HOME ?? '',
  USER: process.env.USER ?? '',
  LANG: process.env.LANG ?? 'C.UTF-8',
});

const starting = new Map<string, Promise<void>>();
const failures = new Map<string, string>();
const keys = new Map<string, string>();

function managedUrl(botId: string): string {
  return `http://127.0.0.1:${botRow(botId).engine_port}`;
}

function managedKey(botId: string): string {
  let k = keys.get(botId);
  if (!k) {
    k = crypto.randomBytes(32).toString('hex');
    keys.set(botId, k);
  }
  return k;
}

async function startGateway(botId: string): Promise<void> {
  const b = botRow(botId);
  if (!b || b.engine !== 'managed') throw new Error('not a managed engine');
  if (!b.engine_port) b.engine_port = freePort();
  db.prepare('UPDATE bots SET engine_port=? WHERE id=?').run(b.engine_port, botId);
  const url = managedUrl(botId);

  if (children.has(botId) && await healthy(url) && await keyAccepted(url, managedKey(botId))) return;
  if (await healthy(url)) throw new Error('Worker port already occupied');
  const home = writeHome(botId, managedKey(botId));
  const cwd = workspaceFor(botId);
  const runtime = path.join(env.hermesHome, 'hermes-agent');
  const run = contained(env.hermesBin, ['gateway', 'run', '--no-supervise'], [runtime, path.join(env.hermesHome, 'tools')], [home, cwd],
    [env.modelPort, cdpPortFor(botId)], b.engine_port);
  const child = spawn(run.bin, run.args, {
    cwd, detached: true, stdio: 'ignore',
    env: { ...agentEnv(), HOME: home, TMPDIR: path.join(home, 'tmp'), HERMES_HOME: home, HERMES_GATEWAY_LOCK_DIR: path.join(home, 'locks') },
  });
  children.set(botId, child);
  const clear = () => { if (children.get(botId) === child) children.delete(botId); };
  child.once('exit', clear);
  child.once('error', clear);
  let exited: string | null = null;
  child.once('error', (e) => { exited = `could not run ${env.hermesBin}: ${e.message}`; });
  child.once('exit', (code) => { exited = `the agent stopped while starting (exit ${code}). The worker did not open its loopback gateway.`; });
  child.unref();

  const startupDeadline = Date.now() + 90_000;
  while (Date.now() < startupDeadline) {
    await new Promise((r) => setTimeout(r, 1000));
    if (exited) throw new Error(exited);
    if (children.get(botId) === child && await healthy(url, 1500) && await keyAccepted(url, managedKey(botId))) {
      console.log(`[engine] ${b.name}: gateway up on ${url}`);
      return;
    }
  }
  await stopGateway(botId);
  throw new Error('The agent did not come up within 90 seconds.');
}

/** Start (or adopt) the bot's gateway. Safe to call often; concurrent calls share one start. */
function ensureManaged(botId: string): Promise<void> {
  let p = starting.get(botId);
  if (!p) {
    p = startGateway(botId)
      .then(() => { failures.delete(botId); })
      .catch((e: any) => {
        const msg = String(e?.message ?? e);
        failures.set(botId, msg);
        console.warn(`[engine] ${botId}: ${msg}`);
        throw e;
      })
      .finally(() => starting.delete(botId));
    starting.set(botId, p);
  }
  return p;
}

/** Where to send this bot's turns. Starts its gateway if it is not running. */
export async function engineFor(botId: string): Promise<Engine> {
  let kind = engineKind(botId);
  if (!kind) {
    const b = botRow(botId);
    if (!b) throw new Error('bot not found');
    if (b.kind === 'room') throw new Error('A group chat has no agent of its own.');
    kind = assignEngine(botId);
  }
  if (kind === 'primary') throw new Error('External Hermes workers are disabled');
  const url = managedUrl(botId);
  if (!children.has(botId) || !(await healthy(url, 1500))) await ensureManaged(botId);
  return { kind, url, key: managedKey(botId), home: homeFor(botId) };
}

/** The bot's Hermes home, without starting anything (memory files, sign-in commands). */
export function engineHome(botId: string): string | null {
  const kind = engineKind(botId);
  return kind === 'managed' ? homeFor(botId) : null;
}

export function provisionEngine(botId: string) {
  if (env.localModel && engineKind(botId) === 'managed') void ensureManaged(botId).catch(() => {});
}

export async function restartEngine(botId: string): Promise<void> {
  if (engineKind(botId) !== 'managed') return;
  await starting.get(botId)?.catch(() => {});
  if (!await stopGateway(botId)) throw new Error('Previous worker could not be stopped');
  optionsCache.delete(botId);
  provisionEngine(botId);
}

/** The bot is gone: stop its gateway and delete its home. The primary agent is left alone. */
export async function removeEngine(botId: string): Promise<void> {
  const home = homeFor(botId);
  if (!fs.existsSync(home)) return;
  await starting.get(botId)?.catch(() => {});
  await stopGateway(botId);
  keys.delete(botId);
  failures.delete(botId);
  optionsCache.delete(botId);
  if (path.resolve(home).startsWith(path.resolve(env.enginesDir) + path.sep)) fs.rmSync(home, { recursive: true, force: true });
}

/** On server start: give older bots an engine, then bring the managed gateways up. */
export function initEngines() {
  fs.mkdirSync(env.enginesDir, { recursive: true });
  const bots = db.prepare("SELECT id, is_primary FROM bots WHERE (engine IS NULL OR engine = 'primary') AND COALESCE(kind,'agent') <> 'room' AND COALESCE(hidden,0)=0 ORDER BY is_primary DESC, created_at ASC").all() as any[];
  for (const b of bots) assignEngine(b.id);
}

// ---------- what the settings panel shows ----------

/** Providers worth showing even when not signed in. */
const WELL_KNOWN = ['anthropic', 'openai-codex', 'xai-oauth', 'xai', 'openrouter', 'nous', 'gemini', 'openai-api'];

const optionsCache = new Map<string, { at: number; data: any }>();

async function modelOptions(botId: string, e: { url: string; key: string }): Promise<any | null> {
  const hit = optionsCache.get(botId);
  if (hit && Date.now() - hit.at < 15_000) return hit.data;
  try {
    const r = await fetch(`${e.url}/api/model/options`, { headers: e.key ? { Authorization: `Bearer ${e.key}` } : {}, signal: AbortSignal.timeout(8000) });
    if (!r.ok) return null;
    const data = await r.json();
    optionsCache.set(botId, { at: Date.now(), data });
    return data;
  } catch { return null; }
}

function toProviders(data: any): EngineProvider[] {
  const list: any[] = Array.isArray(data?.providers) ? data.providers : [];
  const out = list
    .filter((p) => p?.slug && (p.authenticated || WELL_KNOWN.includes(p.slug)))
    .map((p): EngineProvider => {
      const featured = Array.isArray(p.featured_models) && p.featured_models.length ? p.featured_models : Array.isArray(p.models) ? p.models : [];
      return {
        id: String(p.slug),
        name: p.slug === 'anthropic' ? 'Claude (Anthropic)' : String(p.name ?? p.slug),
        // Hermes lists Anthropic as an API-key provider, yet it can also sign in to a Claude subscription. Offer that until a key is in place.
        kind: String(p.auth_type ?? '').includes('oauth') || (p.slug === 'anthropic' && !p.authenticated) ? 'subscription' : 'api_key',
        connected: !!p.authenticated,
        models: featured.filter((m: unknown) => typeof m === 'string').slice(0, 12),
      };
    });
  const rank = (p: EngineProvider) => (p.connected ? 0 : 1) * 100 + (WELL_KNOWN.indexOf(p.id) < 0 ? 50 : WELL_KNOWN.indexOf(p.id));
  return out.sort((a, b) => rank(a) - rank(b));
}

export async function engineInfo(botId: string): Promise<EngineInfo> {
  const b = botRow(botId);
  if (!b) throw new Error('bot not found');
  const kind = engineKind(botId);
  const base: EngineInfo = { botId, profile: kind === 'primary' ? 'default' : botId, status: 'stopped', error: null, model: b.model ?? null, provider: b.provider ?? null, version: null, providers: [], ownScreen: false };
  if (!kind) return { ...base, status: 'error', error: 'This bot has no agent.' };

  let e: { url: string; key: string };
  if (kind === 'primary') return { ...base, status: 'error', error: 'External workers are disabled' };
  else {
    if (!b.engine_port) return { ...base, status: 'error', error: 'No port assigned.' };
    e = { url: managedUrl(botId), key: managedKey(botId) };
  }

  const health = await healthy(e.url);
  if (!health) {
    if (starting.has(botId)) return { ...base, status: 'starting' };
    const failed = failures.get(botId);
    if (failed) return { ...base, status: 'error', error: failed };
    provisionEngine(botId);
    return { ...base, status: 'starting' };
  }
  if (kind === 'managed' && starting.has(botId)) return { ...base, status: 'starting' };

  const data = await modelOptions(botId, e);
  return {
    ...base,
    status: 'ready',
    version: typeof health.version === 'string' && health.version !== 'unknown' ? health.version : null,
    model: b.model ?? data?.model ?? null,
    provider: b.provider ?? data?.provider ?? null,
    providers: toProviders(data),
  };
}

/** After a sign-in the provider list changes; drop what we remembered. */
