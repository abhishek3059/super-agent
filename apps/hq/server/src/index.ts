import { serve } from '@hono/node-server';
import { serveStatic } from '@hono/node-server/serve-static';
import { Hono } from 'hono';
import fs from 'node:fs';
import path from 'node:path';
import type { Server } from 'node:http';
import { env } from './env.js';
import { api } from './routes.js';
import { attachScreenRelay } from './screen.js';
import { initRoutines } from './routines.js';
import { initTriggers } from './triggers.js';
import { initProactive } from './proactive.js';
import { initSubagents } from './agent/subagents.js';
import { initRooms } from './agent/rooms.js';
import { checkinsApi } from './routes-proactive.js';
import { roomsApi } from './routes-rooms.js';
import { enqueue, expireStaleApprovals } from './agent/loop.js';
import { configApi } from './routes-config.js';
import { mcpApi } from './mcp.js';
import { initEngines, stopAllGateways } from './engine.js';
import { stopAllBrowsers } from './computer.js';
import { allowedHost, allowedOrigin } from './lib/guard.js';

initSubagents();
initRooms();
// Approvals wait in memory; whatever was still open when the last process stopped can no longer be answered.
expireStaleApprovals();

const app = new Hono();

app.use('*', async (c, next) => {
  if (!allowedHost(c.req.header('host'))) return c.text('forbidden host', 403);
  if (!allowedOrigin(c.req.header("origin"))) return c.text('forbidden origin', 403);
  await next();
});
app.get('/api/health', (c) => c.json({ ok: true, engine: 'hermes' }));
// The app's tools for the agent engines (MCP).
app.route('/mcp', mcpApi);
app.route('/api/checkins', checkinsApi);
app.route('/api/rooms', roomsApi);
app.route('/api', api);
app.route('/api', configApi);

// Serve the built web app in production.
const webDist = path.resolve(new URL('.', import.meta.url).pathname, '../../web/dist');
if (fs.existsSync(webDist)) {
  // The page itself is always revalidated, so a rebuild is picked up; its hashed assets can be cached.
  app.use('/*', async (c, next) => { await next(); if (!c.req.path.startsWith('/assets/') && !c.req.path.startsWith('/api/')) c.header('Cache-Control', 'no-cache'); });
  app.use('/*', serveStatic({ root: path.relative(process.cwd(), webDist) }));
  app.get('*', (c) => c.html(fs.readFileSync(path.join(webDist, 'index.html'), 'utf8')));
}

await Promise.all([stopAllBrowsers(), stopAllGateways()]);

const server = serve({ fetch: app.fetch, port: env.port, hostname: env.host }, (info) => console.log(`[hq] Jarvis HQ on http://127.0.0.1:${info.port} (run \`npm run open\` to sign in)`));
attachScreenRelay(server as unknown as Server);
// HQ_NO_SCHEDULER=1 for extra dev/test servers sharing a database copy, so routines and triggers don't fire twice.
if (process.env.HQ_NO_SCHEDULER !== '1') {
  initRoutines(enqueue);
  void initTriggers(enqueue);
  initProactive(enqueue);
} else console.log('[hq] scheduler disabled (HQ_NO_SCHEDULER=1)');
initEngines();
