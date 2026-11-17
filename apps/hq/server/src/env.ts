import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const port = Number(process.env.PORT ?? 8787);
/** Everything the app keeps (database, bot homes, browser profiles, files) lives outside the repo. */
const dataDir = process.env.HQ_DATA_DIR ?? path.join(os.homedir(), '.super-agent', 'hq');
fs.mkdirSync(dataDir, { recursive: true });
fs.chmodSync(dataDir, 0o700);
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

export const env = {
  port,
  /** Loopback only. The app has no multi-user sign-in, so it must never listen on a public address. */
  host: '127.0.0.1',
  appUrl: process.env.APP_URL ?? `http://127.0.0.1:${port}`,
  dataDir,
  sessionSecret: sessionSecret(),
  dbPath: process.env.DB_PATH ?? path.join(dataDir, 'hq.db'),
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
  hermesUrl: (process.env.HERMES_URL ?? '').replace(/\/+$/, ''),
  hermesKey: process.env.HERMES_KEY ?? '',
  /** Where each bot's own Hermes home lives. Outside ~/.hermes so it is a separate tenant. */
  enginesDir: process.env.ENGINES_DIR ?? path.join(dataDir, 'engines'),
  enginePortBase: Number(process.env.ENGINE_PORT_BASE ?? 8650),
  /** URL the Hermes gateways use to reach this server's MCP endpoint. */
  mcpBaseUrl: (process.env.MCP_BASE_URL ?? `http://127.0.0.1:${port}`).replace(/\/+$/, ''),
  /** Extra MCP servers every bot gets, as a JSON object of Hermes `mcp_servers` entries. */
  extraMcpServers: process.env.EXTRA_MCP_SERVERS ?? '',

  // ---- each bot's own screen: a Chrome with its own profile ----
  chromeBin: process.env.CHROME_BIN ?? '',
  cdpPortBase: Number(process.env.CDP_PORT_BASE ?? 9300),
  profilesDir: path.join(dataDir, 'profiles'),
  filesDir: path.join(dataDir, 'files'),
  maxBots: Number(process.env.MAX_BOTS ?? 8),
};
