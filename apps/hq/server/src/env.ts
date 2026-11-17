import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const port = Number(process.env.PORT ?? 8787);
/** Everything the app keeps (database, bot homes, browser profiles, files) lives outside the repo. */
const home = fs.realpathSync(os.homedir());
const parent = path.join(home, '.super-agent');
const dataDir = path.join(parent, 'hq');
const workspace = fs.realpathSync(path.resolve(import.meta.dirname, '../../../..'));
const relative = path.relative(workspace, dataDir);
if (!relative || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
  throw new Error('Jarvis HQ data directory must be outside the checkout');
}
for (const dir of [parent, dataDir]) {
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  const info = fs.lstatSync(dir);
  if (!info.isDirectory() || info.isSymbolicLink()) throw new Error('Jarvis HQ requires real data directories');
}
fs.chmodSync(dataDir, 0o700);

for (const name of ['.env', 'session-secret', 'hq.db', 'engines', 'profiles', 'files']) {
  if (fs.lstatSync(path.join(dataDir, name), { throwIfNoEntry: false })?.isSymbolicLink()) {
    throw new Error('Jarvis HQ data entries cannot be symbolic links');
  }
}
// Keys (OPENAI_API_KEY and friends) can live in <data folder>/.env: outside the repo, owner-only.
const envFile = path.join(dataDir, '.env');
if (fs.existsSync(envFile)) { fs.chmodSync(envFile, 0o600); process.loadEnvFile(envFile); }

/** SESSION_SECRET, or one generated on first run and kept in the data folder (mode 0600). */
function sessionSecret(): string {
  if (process.env.SESSION_SECRET) return process.env.SESSION_SECRET;
  const file = path.join(dataDir, 'session-secret');
  try { return fs.readFileSync(file, 'utf8').trim(); } catch { /* first run */ }
  const s = crypto.randomBytes(32).toString('hex');
  fs.writeFileSync(file, s, { mode: 0o600 });
  return s;
}

const hermesHome = process.env.HERMES_HOME_PRIMARY ?? path.join(os.homedir(), '.hermes');

function loopbackUrl(value: string, allowLocalhost = false): string {
  const url = new URL(value);
  if (url.protocol !== 'http:' || url.username || url.password || url.search || url.hash || url.pathname !== '/'
      || (url.hostname !== '127.0.0.1' && !(allowLocalhost && url.hostname === 'localhost'))) {
    throw new Error('Jarvis HQ requires a loopback HTTP origin');
  }
  return url.origin;
}

const hermesUrl = process.env.HERMES_URL;

export const env = {
  port,
  /** Loopback only. The app has no multi-user sign-in, so it must never listen on a public address. */
  host: '127.0.0.1',
  appUrl: loopbackUrl(process.env.APP_URL ?? `http://127.0.0.1:${port}`, true),
  dataDir,
  sessionSecret: sessionSecret(),
  dbPath: path.join(dataDir, 'hq.db'),
  ownerName: process.env.HQ_OWNER_NAME ?? os.userInfo().username,

  // ---- optional services: a missing key switches the feature off ----
  /** Live voice (OpenAI Realtime), dictation and voice previews. Paid, approved by the maintainer. */
  openaiKey: process.env.OPENAI_API_KEY ?? '',
  voiceModel: process.env.OPENAI_VOICE_MODEL ?? 'gpt-realtime-2.1',
  /**
   * Research on X (paid) and connected apps (real accounts) are upstream features DEC-23 does not
   * approve. They stay off, whatever the environment says, until a maintainer approves them.
   */
  xaiKey: '',
  xaiModel: process.env.XAI_MODEL ?? 'grok-4.7',
  composioKey: '',

  // ---- Hermes engine ----
  /** The `hermes` CLI used to start a gateway for each bot. */
  hermesBin: process.env.HERMES_BIN ?? 'hermes',
  /** The operator's own Hermes home: bots start from its model settings and sign-ins. Never written to. */
  hermesHome,
  /**
   * Set HERMES_URL to hand the first bot to a Hermes gateway that already runs. Unset (the default),
   * every bot gets a gateway of its own and the operator's gateway is left alone.
   */
  hermesUrl: hermesUrl ? loopbackUrl(hermesUrl) : '',
  hermesKey: process.env.HERMES_KEY ?? '',
  /** Where each bot's own Hermes home lives. Outside ~/.hermes so it is a separate tenant. */
  enginesDir: path.join(dataDir, 'engines'),
  enginePortBase: Number(process.env.ENGINE_PORT_BASE ?? 8650),
  /** URL the Hermes gateways use to reach this server's MCP endpoint. */
  mcpBaseUrl: `http://127.0.0.1:${port}`,

  // ---- each bot's own screen: a Chrome with its own profile ----
  chromeBin: process.env.CHROME_BIN ?? '',
  cdpPortBase: Number(process.env.CDP_PORT_BASE ?? 9300),
  profilesDir: path.join(dataDir, 'profiles'),
  filesDir: path.join(dataDir, 'files'),
  maxBots: Number(process.env.MAX_BOTS ?? 8),
};
