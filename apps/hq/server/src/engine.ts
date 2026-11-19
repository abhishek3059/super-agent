import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import YAML from 'yaml';
import { cdpPortFor, cdpUrlFor } from './computer.js';
import { confinedEnv, contained, realFolder, which } from './sandbox.js';
import { removeOwn, writeOwn } from './lib/own.js';
import { deletingBots, livePid, recordPid, stopPid } from './lib/procs.js';
import { db } from './db.js';
import { env } from './env.js';
import type { EngineInfo, EngineProvider } from './types.js';

/**
 * Every bot is run by a Hermes agent of its own: a Hermes home under ENGINES_DIR/<botId> with its own
 * `hermes gateway run`, started here inside the bot's sandbox and left running when this server exits.
 * Its home sits outside ~/.hermes, so Hermes treats it as a separate tenant.
 */

export type EngineKind = 'managed';
export interface Engine { kind: EngineKind; url: string; key: string; home: string }

const botRow = (botId: string) => db.prepare('SELECT * FROM bots WHERE id=?').get(botId) as any;

// ---------- small file helpers ----------

/** KEY=value lines of a dotenv file (quotes stripped). Missing file = {}. */
function readDotenv(file: string): Record<string, string> {
  const out: Record<string, string> = {};
  let text = '';
  try { text = fs.readFileSync(file, 'utf8'); } catch { return out; }
  for (const line of text.split('\n')) {
    const m = /^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/.exec(line);
    if (!m) continue;
    let v = m[2].trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    out[m[1]] = v;
  }
  return out;
}

function readYaml(file: string): any {
  try { return YAML.parse(fs.readFileSync(file, 'utf8')) ?? {}; } catch { return {}; }
}

// ---------- identity ----------

/** Token a bot's Hermes agent presents to this server's MCP endpoint. */
export function mcpToken(botId: string): string {
  return crypto.createHmac('sha256', env.sessionSecret).update(`mcp:${botId}`).digest('hex');
}

export function engineKind(botId: string): EngineKind | null {
  const e = botRow(botId)?.engine;
  return e === 'managed' ? e : null;
}

const homeFor = (botId: string) => path.join(env.enginesDir, botId);

// ---------- assignment ----------

function freePort(): number {
  const used = new Set((db.prepare('SELECT engine_port FROM bots WHERE engine_port IS NOT NULL').all() as any[]).map((r) => r.engine_port as number));
  let p = env.enginePortBase;
  while (used.has(p)) p++;
  return p;
}

/** Give a new agent bot its engine: a gateway of its own, on a port of its own. */
export function assignEngine(botId: string): EngineKind {
  const b = botRow(botId);
  if (!b) throw new Error('bot not found');
  if (b.engine === 'managed') return b.engine;
  db.prepare("UPDATE bots SET engine='managed', engine_port=? WHERE id=?").run(freePort(), botId);
  return 'managed';
}

// ---------- a managed bot's Hermes home ----------

/** Model credentials a bot's agent may inherit from the operator's Hermes. Never messaging tokens. */
const SHARED_ENV = [
  'ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN',
  'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENROUTER_API_KEY', 'XAI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'NOUS_API_KEY',
  'FIRECRAWL_API_KEY', 'TAVILY_API_KEY', 'EXA_API_KEY', 'PARALLEL_API_KEY',
];

/** Parts of the operator's Hermes config a bot's agent starts from, so it reaches the same models. */
const SHARED_CONFIG = ['model', 'providers', 'custom_providers', 'auxiliary', 'fallback_model', 'fallback_providers'];

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

/** Rewrite the persona file after a rename or a new description. */
export function syncPersona(botId: string) {
  const b = botRow(botId);
  if (deletingBots.has(botId) || !b || b.engine !== 'managed' || !fs.existsSync(homeFor(botId))) return;
  writeOwn(homeFor(botId), 'SOUL.md', soul(b), 0o644);
}

function extraMcpServers(): Record<string, any> {
  if (!env.extraMcpServers) return {};
  try {
    const v = JSON.parse(env.extraMcpServers);
    return v && typeof v === 'object' && !Array.isArray(v) ? v : {};
  } catch {
    console.warn('[engine] EXTRA_MCP_SERVERS is not valid JSON; ignored');
    return {};
  }
}

/**
 * Write the bot's Hermes home. Everything in it is written new on each start, from the operator's
 * Hermes settings and our database, and nothing in it is read back: the bot can write its own home,
 * so whatever is there could be a link to one of the operator's files.
 */
function writeHome(botId: string): string {
  const b = botRow(botId);
  const home = homeFor(botId);
  fs.mkdirSync(home, { recursive: true, mode: 0o700 });
  realFolder(home); // a bot that replaced its home with a link does not get it back
  // The bot's working folder is its Library, so what it writes there shows up in the app.
  const cwd = path.join(env.filesDir, botId);
  fs.mkdirSync(cwd, { recursive: true });
  const cdp = cdpUrlFor(botId);

  const primary = readYaml(path.join(env.hermesHome, 'config.yaml'));
  const cfg: Record<string, unknown> = { agent: { reasoning_effort: 'medium' } };
  for (const k of SHARED_CONFIG) if (primary[k] !== undefined) cfg[k] = primary[k];
  // No computer_use: on this machine it would drive the operator's own desktop.
  cfg.platform_toolsets = { api_server: ['hermes-api-server'] };
  cfg.terminal = { cwd };
  cfg.browser = { cdp_url: cdp };
  cfg.mcp_servers = {
    ...extraMcpServers(),
    hq: { url: `${env.mcpBaseUrl}/mcp/${botId}`, headers: { Authorization: `Bearer ${mcpToken(botId)}` }, timeout: 1800, connect_timeout: 30 },
  };
  writeOwn(home, 'config.yaml', YAML.stringify(cfg));
  writeOwn(home, 'SOUL.md', soul(b), 0o644);

  // Subscription sign-ins live in auth.json, copied from the operator's Hermes each time the bot starts.
  try { writeOwn(home, 'auth.json', fs.readFileSync(path.join(env.hermesHome, 'auth.json'), 'utf8')); } catch { /* the operator has none */ }

  // Model keys from the operator's Hermes home only. This server's own keys (the voice key) are
  // never handed to a bot, and messaging tokens never match these names.
  const primaryEnv = readDotenv(path.join(env.hermesHome, '.env'));
  const vars: Record<string, string> = {};
  for (const [k, v] of Object.entries(primaryEnv)) if (v && (SHARED_ENV.includes(k) || /_API_KEY$|_BASE_URL$|^CLOUDFLARE_ACCOUNT_ID$/.test(k))) vars[k] = v;
  Object.assign(vars, { API_SERVER_ENABLED: 'true', API_SERVER_KEY: managedKey(botId), API_SERVER_PORT: String(b.engine_port), API_SERVER_HOST: '127.0.0.1', BROWSER_CDP_URL: cdp });
  writeOwn(home, '.env', Object.entries(vars).map(([k, v]) => `${k}=${v}`).join('\n') + '\n');
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

/** The gateway we started for this bot, if it is still running. Its command line carries these words. */
const GATEWAY = 'gateway run';
const gatewayPid = (botId: string) => livePid(`${botId}.gateway`, GATEWAY);

/**
 * Where Hermes' browser helper keeps its socket. Named from the bot id, so a bot that reuses a deleted
 * bot's port never inherits its folder, and kept short: socket paths stop at 104 bytes.
 */
const bhFor = (botId: string) => path.join(env.dataDir, 'bh', crypto.createHash('sha256').update(botId).digest('hex').slice(0, 8));

/**
 * A Hermes command for this bot, inside its sandbox. Anything that runs Hermes on a bot's home goes
 * through here, because the bot can write that home (config, hooks) and so steer what Hermes does.
 */
function hermesContained(botId: string, args: string[]) {
  const hermes = which(env.hermesBin);
  return contained(hermes, args, {
    read: [hermes, path.join(env.hermesHome, 'hermes-agent'), path.join(env.hermesHome, 'tools')],
    write: [homeFor(botId), path.join(env.filesDir, botId), bhFor(botId)],
    localPorts: [env.port, botRow(botId).engine_port, cdpPortFor(botId)],
    listen: botRow(botId).engine_port,
  }, `${botId}.g`);
}

const stopGateway = (botId: string) => stopPid(`${botId}.gateway`, GATEWAY);

const starting = new Map<string, Promise<void>>();
const failures = new Map<string, string>();

function managedUrl(botId: string): string {
  return `http://127.0.0.1:${botRow(botId).engine_port}`;
}

/** The key this bot's gateway accepts. Kept in our database: the bot's own .env is never read back. */
function managedKey(botId: string): string {
  const b = botRow(botId);
  if (b.engine_key) return b.engine_key;
  const key = crypto.randomBytes(24).toString('hex');
  db.prepare('UPDATE bots SET engine_key=? WHERE id=?').run(key, botId);
  return key;
}

async function startGateway(botId: string): Promise<void> {
  const b = botRow(botId);
  if (!b || b.engine !== 'managed') throw new Error('not a managed engine');
  if (!b.engine_port) db.prepare('UPDATE bots SET engine_port=? WHERE id=?').run(freePort(), botId);
  const url = managedUrl(botId);

  // A gateway this server started earlier (always inside the sandbox) is still good: use it as it is.
  if ((await healthy(url)) && gatewayPid(botId) && (await keyAccepted(url, managedKey(botId)))) return;
  await stopGateway(botId);
  if (await healthy(url)) throw new Error(`Port ${b.engine_port} is taken by a process this app did not start.`);

  if (deletingBots.has(botId)) throw new Error('bot unavailable');
  const home = writeHome(botId);

  // The log is ours, outside the bot's home: a file we open there could be a link to anywhere.
  const logFile = path.join(env.dataDir, 'logs', `${botId}.gateway.log`);
  fs.mkdirSync(path.dirname(logFile), { recursive: true, mode: 0o700 });
  const log = fs.openSync(logFile, 'a', 0o600);
  // The agent, and every command it runs, sees its own home, working folder and helper folder, the
  // Hermes program, and nothing else of the operator's. It reaches this server and its own browser only.
  const bh = bhFor(botId);
  fs.mkdirSync(bh, { recursive: true });
  const run = hermesContained(botId, ['gateway', 'run', '--no-supervise']);
  const child = spawn(run.bin, run.args, {
    cwd: home,
    detached: true,
    stdio: ['ignore', log, log],
    // Only what the agent needs: nothing from this server's environment, and no messaging tokens.
    env: confinedEnv(`${botId}.g`, {
      HERMES_HOME: home,
      HERMES_GATEWAY_LOCK_DIR: path.join(home, 'locks'),
      // Hermes' browser tool talks to a helper process it finds under this folder. With the default
      // (one folder per HOME) every agent on the computer would end up driving the same browser.
      BH_HOME: bh,
    }),
  });
  fs.closeSync(log);
  recordPid(`${botId}.gateway`, child.pid);
  let exited: string | null = null;
  child.once('error', (e) => { exited = `could not run ${env.hermesBin}: ${e.message}`; });
  child.once('exit', (code) => { exited = `the agent stopped while starting (exit ${code}). See ${logFile}`; });
  child.unref();

  for (let i = 0; i < 90; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    if (exited) throw new Error(exited);
    if (await healthy(url, 1500)) {
      console.log(`[engine] ${b.name}: gateway up on ${url}`);
      return;
    }
  }
  throw new Error('The agent did not come up within 90 seconds.');
}

/** Start (or adopt) the bot's gateway. Safe to call often; concurrent calls share one start. */
function ensureManaged(botId: string): Promise<void> {
  if (deletingBots.has(botId) || !botRow(botId)) return Promise.reject(new Error('bot unavailable'));
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
  if (deletingBots.has(botId)) throw new Error('bot unavailable');
  let kind = engineKind(botId);
  if (!kind) {
    const b = botRow(botId);
    if (!b) throw new Error('bot not found');
    if (b.kind === 'room') throw new Error('A group chat has no agent of its own.');
    kind = assignEngine(botId);
  }
  const url = managedUrl(botId);
  if (!(await healthy(url, 1500)) || !gatewayPid(botId)) await ensureManaged(botId);
  if (deletingBots.has(botId) || !botRow(botId)) throw new Error('bot unavailable');
  return { kind, url, key: managedKey(botId), home: homeFor(botId) };
}

/** The bot's Hermes home, without starting anything (memory files, sign-in commands). */
export function engineHome(botId: string): string | null {
  const kind = engineKind(botId);
  return kind ? homeFor(botId) : null;
}

/** Start the gateway in the background (after creating a bot, or on server start). */
export function provisionEngine(botId: string) {
  if (engineKind(botId) === 'managed') ensureManaged(botId).catch(() => {});
}

export async function restartEngine(botId: string): Promise<void> {
  if (engineKind(botId) !== 'managed' || deletingBots.has(botId)) return;
  await starting.get(botId)?.catch(() => {});
  if (deletingBots.has(botId) || !botRow(botId)) return;
  await stopGateway(botId);
  optionsCache.delete(botId);
  provisionEngine(botId);
}

export async function stopEngine(botId: string): Promise<void> {
  await starting.get(botId)?.catch(() => {});
  await stopGateway(botId);
}

export async function forgetEngineFiles(botId: string): Promise<void> {
  const home = homeFor(botId);
  failures.delete(botId);
  optionsCache.delete(botId);
  try {
    if (path.resolve(home).startsWith(path.resolve(env.enginesDir) + path.sep)) await removeOwn(home);
  } finally {
    await removeOwn(bhFor(botId)); // even when a bot locked its home against the delete
  }
}

/** Stop gateways from earlier runs before handling requests under the current rules. */
export async function stopAllGateways(): Promise<void> {
  const bots = db.prepare("SELECT id FROM bots WHERE engine='managed'").all() as { id: string }[];
  await Promise.all(bots.map((b) => stopGateway(b.id)));
}

/** On server start: give older bots an engine, then bring the managed gateways up. */
export function initEngines() {
  fs.mkdirSync(env.enginesDir, { recursive: true });
  const bots = db.prepare("SELECT id, is_primary FROM bots WHERE engine IS NULL AND COALESCE(kind,'agent') <> 'room' AND COALESCE(hidden,0)=0 ORDER BY is_primary DESC, created_at ASC").all() as any[];
  for (const b of bots) assignEngine(b.id);
  for (const b of db.prepare("SELECT id FROM bots WHERE engine='managed'").all() as any[]) provisionEngine(b.id);
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
  const base: EngineInfo = { botId, profile: botId, status: 'stopped', error: null, model: b.model ?? null, provider: b.provider ?? null, version: null, providers: [] };
  if (!kind) return { ...base, status: 'error', error: 'This bot has no agent.' };

  if (!b.engine_port) return { ...base, status: 'error', error: 'No port assigned.' };
  const e = { url: managedUrl(botId), key: managedKey(botId) };

  const health = await healthy(e.url);
  if (!health) {
    if (starting.has(botId)) return { ...base, status: 'starting' };
    const failed = failures.get(botId);
    if (failed) return { ...base, status: 'error', error: failed };
    provisionEngine(botId);
    return { ...base, status: 'starting' };
  }
  if (starting.has(botId)) return { ...base, status: 'starting' };

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
export function forgetEngineOptions(botId: string) { optionsCache.delete(botId); }
