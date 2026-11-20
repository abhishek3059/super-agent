import { spawn, spawnSync } from 'node:child_process';
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
import { readDirs, sharedSkillsDir, skillDirs, skillReadDirs } from './access.js';
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

function readJson(file: string): any {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; }
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

/**
 * A port no bot has had before. Never reused: a process a deleted bot left behind keeps the sandbox
 * of its old ports, and would otherwise reach the next bot given them.
 */
function freePort(): number {
  db.exec('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)');
  const stored = Number((db.prepare("SELECT value FROM meta WHERE key='next_engine_port'").get() as any)?.value ?? 0);
  const highest = (db.prepare('SELECT MAX(engine_port) p FROM bots').get() as any)?.p ?? 0;
  // Never a port the app itself uses, nor one whose browser port would be: a bot allowed to reach its
  // own engine port would otherwise be allowed to reach the app API or another service.
  const taken = new Set([env.port, env.mcpPort, env.egressPort]);
  const cdpFor = (p: number) => env.cdpPortBase + (p - env.enginePortBase) + 1;
  let p = Math.max(stored, highest + 1, env.enginePortBase);
  while (taken.has(p) || taken.has(cdpFor(p))) p++;
  // Engine ports must stay below the browser ports, or one bot's engine port could be another's browser port.
  if (p >= env.cdpPortBase || cdpFor(p) > 65535) throw new Error('No free bot ports left.');
  db.prepare("INSERT OR REPLACE INTO meta(key, value) VALUES ('next_engine_port', ?)").run(String(p + 1));
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

// HQ voice has its own OpenAI key. These are the supported Hermes worker routes.
const HOSTED_PROVIDERS = new Map([
  ['openai-codex', { name: 'OpenAI Codex', key: null }],
  ['nvidia', { name: 'NVIDIA NIM', key: 'NVIDIA_API_KEY' }],
  ['anthropic', { name: 'Anthropic', key: 'ANTHROPIC_API_KEY' }],
]);

function configuredProviders(cfg: any): Set<string> {
  const names = [cfg?.model?.provider, ...(Array.isArray(cfg?.fallback_providers) ? cfg.fallback_providers.map((f: any) => f?.provider) : []),
    ...Object.keys(cfg?.providers ?? {})];
  return new Set(names.filter((name) => HOSTED_PROVIDERS.has(name)));
}

/** In a dedicated seed, a provider signed in to (or with a key saved) from HQ counts as configured. */
export function withCredentials(configured: Set<string>, auth: any, dotenv: Record<string, string>): Set<string> {
  const out = new Set(configured);
  if (auth?.providers?.['openai-codex'] || auth?.credential_pool?.['openai-codex']?.length) out.add('openai-codex');
  for (const [id, p] of HOSTED_PROVIDERS) if (p.key && dotenv[p.key]) out.add(id);
  return out;
}

function defaultWorkerModel(primary: any): { provider: string; default: string } {
  const { provider, default: model } = primary?.model ?? {};
  if (!HOSTED_PROVIDERS.has(provider) || typeof model !== 'string' || !model.trim()) {
    throw new Error('Set a supported hosted default model in the HQ Hermes profile and restart the agent.');
  }
  // Use Hermes' official provider endpoint. Arbitrary URLs and automatic fallbacks are omitted.
  return { provider, default: model };
}

/** What the bot can reach on the operator's Mac, so it neither guesses nor promises more. */
function access(): string {
  const dirs = readDirs();
  return [
    `\nYou can read (never change) these folders on the operator's Mac: ${dirs.length ? dirs.join(', ') : 'none'}. Your own working folder is the only place you write files.`,
    `For facts about the Mac (system, disk, battery, running apps, installed apps) call the hq system_info tool.`,
    `Your skills include the operator's own. To share a skill you made with the other bots, save it as ${sharedSkillsDir()}/<skill-name>/SKILL.md.`,
  ].join('\n');
}

function soul(b: any): string {
  const owner = (db.prepare('SELECT name FROM users WHERE id=?').get(b.user_id) as any)?.name ?? 'the user';
  const role = b.label ? `, ${b.label}` : '';
  return [
    `You are ${b.name}${role}. You work for ${owner} as one of a small team of AI agents, each with its own browser and workspace.`,
    b.description ? `\n${b.description}` : '',
    access(),
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
  cfg.model = defaultWorkerModel(primary);
  // No computer_use: on this machine it would drive the operator's own desktop.
  cfg.platform_toolsets = { api_server: ['hermes-api-server'] };
  cfg.terminal = { cwd };
  cfg.browser = { cdp_url: cdp };
  // The operator's skills, read-only, and the folder bots share the skills they make.
  fs.mkdirSync(sharedSkillsDir(), { recursive: true, mode: 0o700 });
  cfg.skills = { external_dirs: [sharedSkillsDir(), ...skillDirs()] };
  cfg.mcp_servers = {
    ...extraMcpServers(),
    hq: { url: `${env.mcpBaseUrl}/mcp/${botId}`, headers: { Authorization: `Bearer ${mcpToken(botId)}` }, timeout: 1800, connect_timeout: 30 },
  };
  writeOwn(home, 'config.yaml', YAML.stringify(cfg));
  writeOwn(home, 'SOUL.md', soul(b), 0o644);

  // Sign-ins (auth.json) and keys (.env) from the operator's Hermes, for the configured providers
  // only, copied fresh on each start. This server's own keys (the voice key) never reach a bot.
  const auth = readJson(path.join(env.hermesHome, 'auth.json'));
  const primaryEnv = readDotenv(path.join(env.hermesHome, '.env'));
  // Only a dedicated seed may hand over credentials it holds but does not name: the operator's own
  // ~/.hermes can hold keys meant for other work.
  const providers = env.dedicatedSeed ? withCredentials(configuredProviders(primary), auth, primaryEnv) : configuredProviders(primary);
  const codex = providers.has('openai-codex');
  writeOwn(home, 'auth.json', JSON.stringify({
    version: auth?.version ?? 1,
    providers: codex && auth?.providers?.['openai-codex'] ? { 'openai-codex': auth.providers['openai-codex'] } : {},
    credential_pool: codex && auth?.credential_pool?.['openai-codex'] ? { 'openai-codex': auth.credential_pool['openai-codex'] } : {},
    active_provider: codex && auth?.active_provider === 'openai-codex' ? 'openai-codex' : null,
  }));
  const vars: Record<string, string> = {};
  for (const provider of providers) {
    const key = HOSTED_PROVIDERS.get(provider)?.key;
    if (key && primaryEnv[key]) vars[key] = primaryEnv[key];
  }
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

/**
 * The bot's running gateway: the process listening on its engine port whose command or working folder
 * is in its own Hermes home. Hermes relaunches itself in a new session after it starts, so the process this
 * server spawned is gone by then; the listener is what identifies the gateway. Only this bot's
 * sandbox may listen on that port, so nothing else can pose as it.
 */
function gatewayPid(botId: string): number | null {
  const port = botRow(botId)?.engine_port;
  if (!port) return null;
  const listeners = spawnSync('lsof', ['-nP', `-iTCP:${port}`, '-sTCP:LISTEN', '-t'], { encoding: 'utf8', timeout: 3000 });
  for (const line of (listeners.stdout ?? '').split('\n').filter(Boolean)) {
    const pid = Number(line);
    if (!Number.isInteger(pid) || pid <= 1) continue;
    const cmd = spawnSync('ps', ['-p', String(pid), '-o', 'command='], { encoding: 'utf8', timeout: 3000 }).stdout ?? '';
    // Hermes' relaunch runs as `python3 -I -c <script>` with no path in its arguments; its working folder is the home.
    const cwd = (spawnSync('lsof', ['-a', '-p', String(pid), '-d', 'cwd', '-Fn'], { encoding: 'utf8', timeout: 3000 }).stdout ?? '')
      .split('\n').find((l) => l.startsWith('n'))?.slice(1) ?? '';
    const home = homeFor(botId);
    const real = fs.existsSync(home) ? fs.realpathSync(home) : home; // lsof prints resolved paths
    if (cmd.includes(`${home}/`) || cwd === real || cwd.startsWith(`${real}/`)) return pid;
  }
  return null;
}

/** The internet, for a confined process: only through the proxy. Loopback stays direct (its own listed ports). */
export const proxyEnv = (): Record<string, string> => {
  const proxy = `http://127.0.0.1:${env.egressPort}`;
  return { HTTPS_PROXY: proxy, HTTP_PROXY: proxy, ALL_PROXY: proxy, https_proxy: proxy, http_proxy: proxy, all_proxy: proxy,
    NO_PROXY: '127.0.0.1,localhost', no_proxy: '127.0.0.1,localhost', NODE_USE_ENV_PROXY: '1' };
};

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
    read: [hermes, path.join(env.hermesHome, 'hermes-agent'), path.join(env.hermesHome, 'tools'), ...readDirs(), ...skillReadDirs(skillDirs())],
    write: [homeFor(botId), path.join(env.filesDir, botId), bhFor(botId), sharedSkillsDir()],
    localPorts: [env.mcpPort, env.egressPort, botRow(botId).engine_port, cdpPortFor(botId)],
    listen: botRow(botId).engine_port,
  }, `${botId}.g`);
}

/** When each bot's gateway was last confirmed as ours (see engineFor). */
const confirmed = new Map<string, number>();

async function stopGateway(botId: string): Promise<void> {
  confirmed.delete(botId);
  await stopPid(`${botId}.gateway`, GATEWAY); // the launcher, while it still runs
  const pid = gatewayPid(botId); // and the relaunched gateway itself
  if (!pid) return;
  const signal = (sig: NodeJS.Signals) => { try { process.kill(-pid, sig); } catch { try { process.kill(pid, sig); } catch { /* gone */ } } };
  signal('SIGTERM');
  for (let i = 0; i < 40 && gatewayPid(botId) === pid; i++) await new Promise((r) => setTimeout(r, 250));
  if (gatewayPid(botId) === pid) { signal('SIGKILL'); await new Promise((r) => setTimeout(r, 300)); }
  if (gatewayPid(botId)) throw new Error(`Could not stop the gateway of ${botId}`);
}

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
      ...proxyEnv(),
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
  // The process check (lsof, ps) blocks briefly, so a gateway confirmed in the last minute is trusted.
  const recent = Date.now() - (confirmed.get(botId) ?? 0) < 60_000;
  if (!(await healthy(url, 1500)) || (!recent && !gatewayPid(botId))) { confirmed.delete(botId); await ensureManaged(botId); }
  confirmed.set(botId, Date.now());
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
  // The first explicit refresh can change an inherited model before we have seen its old route.
  db.prepare(`UPDATE bots SET engine_revision=1 WHERE id=? AND engine_revision=0
    AND engine_active_route IS NULL AND provider IS NULL AND model IS NULL`).run(botId);
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

function isChatModel(provider: string, model: unknown): model is string {
  if (typeof model !== 'string' || !model || model.length > 160) return false;
  if (provider !== 'nvidia') return true;
  // NVIDIA lists embeddings and classifiers alongside chat models.
  return !/(?:embed|nemoguard|safety-guard|content-safety|gliner2-pii|\/nvclip$|\/riva-translate|\/ising-calibration)/i.test(model)
    // A retired seed default that no longer answers chat requests on this route.
    && model !== 'nvidia/nemotron-3-super-120b-a12b';
}

export function toProviders(data: any): EngineProvider[] {
  const list: any[] = Array.isArray(data?.providers) ? data.providers : [];
  return list.flatMap((p): EngineProvider[] => {
    const supported = HOSTED_PROVIDERS.get(p?.slug);
    if (!supported) return [];
    const models: unknown[] = [...(Array.isArray(p.featured_models) ? p.featured_models : []),
      ...(Array.isArray(p.models) ? p.models : [])];
    const chatModels = models.filter((m): m is string => isChatModel(p.slug, m));
    return [{
      id: p.slug,
      name: supported.name,
      kind: supported.key ? 'api_key' : 'subscription',
      connected: p.authenticated === true,
      models: [...new Set(chatModels)],
    }];
  });
}

export function validWorkerRoute(providers: EngineProvider[], provider: string, model: string): boolean {
  return providers.some((candidate) => candidate.id === provider && candidate.connected && candidate.models.includes(model));
}

export async function workerRoute(botId: string, e: Engine, provider: string | null, model: string | null) {
  const inventory = await modelOptions(botId, e);
  const selectedProvider = provider ?? inventory?.provider;
  const selectedModel = model ?? inventory?.model;
  const providers = toProviders(inventory);
  const selected = providers.find((route) => route.id === selectedProvider && route.connected);
  // A configured default might be omitted by an incomplete remote model listing.
  const isDefault = !provider && !model;
  if (!selected || typeof selectedProvider !== 'string' || !isChatModel(selectedProvider, selectedModel) ||
      (!isDefault && !validWorkerRoute(providers, selectedProvider, selectedModel))) {
    throw new Error('This bot’s model is unavailable. Choose a connected provider and model in Engine settings.');
  }
  return { provider: selectedProvider, model: selectedModel };
}

export function workerConversation(bot: { id: string; generation: number; engine_revision: number }, route: { provider: string; model: string }): string {
  // Remember the actual route so changing the seed default also releases a pinned Hermes thread.
  const active = JSON.stringify(route);
  const row = db.prepare(`UPDATE bots SET engine_active_route=?,
      engine_revision=engine_revision+CASE WHEN engine_active_route IS NOT NULL AND engine_active_route IS NOT ? THEN 1 ELSE 0 END
    WHERE id=? AND generation=? AND engine_revision=? RETURNING engine_revision`)
    .get(active, active, bot.id, bot.generation, bot.engine_revision) as { engine_revision: number } | undefined;
  if (!row) throw new Error('The bot settings changed before this turn started. Send the request again.');
  return `hq-${bot.id}-g${bot.generation}${row.engine_revision ? `-e${row.engine_revision}` : ''}`;
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
  if (!data) return { ...base, status: 'error', error: 'The Hermes model catalog is unavailable. Restart the agent and try again.' };
  const provider = b.provider ?? data.provider ?? null;
  const model = b.model ?? data.model ?? null;
  const providers = toProviders(data);
  const usable = provider && isChatModel(provider, model)
    && (b.provider || b.model ? validWorkerRoute(providers, provider, model) : providers.some((p) => p.id === provider && p.connected));
  return {
    ...base,
    status: usable ? 'ready' : 'error',
    error: usable ? null : 'Choose an available model from a connected provider.',
    version: typeof health.version === 'string' && health.version !== 'unknown' ? health.version : null,
    model,
    provider,
    providers,
  };
}

/** After a sign-in the provider list changes; drop what we remembered. */
export function forgetEngineOptions(botId: string) { optionsCache.delete(botId); }
