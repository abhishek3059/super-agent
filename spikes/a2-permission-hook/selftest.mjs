// node spikes/a2-permission-hook/selftest.mjs : end-to-end check, no Claude Code needed.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const dir = mkdtempSync(join(tmpdir(), "sa-spike-"));
process.env.SUPER_AGENT_TOKEN_FILE = join(dir, "token");
const { startServer } = await import("./server.mjs");
const { toHookOutput } = await import("./hook.mjs");

const { server, token, port } = await startServer({ port: 0, timeoutMs: 1500 });
writeFileSync(process.env.SUPER_AGENT_TOKEN_FILE, token);
const base = `http://127.0.0.1:${port}`;
const auth = { authorization: `Bearer ${token}`, "content-type": "application/json" };
const env = { ...process.env, SUPER_AGENT_PORT: String(port) };

function runHook(payload) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [new URL("./hook.mjs", import.meta.url).pathname], { env });
    let out = "";
    child.stdout.on("data", (d) => (out += d));
    child.on("close", (code) => resolve({ code, out }));
    child.stdin.end(JSON.stringify(payload));
  });
}

async function waitPending() {
  for (let i = 0; i < 50; i++) {
    const list = await (await fetch(`${base}/requests`, { headers: auth })).json();
    if (list.length) return list[0];
    await new Promise((r) => setTimeout(r, 20));
  }
  throw new Error("request never became pending");
}

const decide = (id, decision, reason) => fetch(`${base}/requests/${id}/decision`, { method: "POST", headers: auth, body: JSON.stringify({ decision, reason }) });
const payload = { hook_event_name: "PermissionRequest", tool_name: "Bash", tool_input: { command: "npm test" }, session_id: "s1", cwd: "/tmp" };

// allow
let hook = runHook(payload);
let p = await waitPending();
assert.equal(p.tool_name, "Bash");
await decide(p.id, "allow");
let r = await hook;
assert.equal(r.code, 0);
assert.deepEqual(JSON.parse(r.out), toHookOutput({ decision: "allow" }));

// deny with reason
hook = runHook(payload);
p = await waitPending();
await decide(p.id, "deny", "not now");
r = await hook;
assert.equal(JSON.parse(r.out).hookSpecificOutput.decision.message, "not now");

// timeout -> no output (normal prompt, never auto-allow)
r = await runHook(payload);
assert.equal(r.code, 0);
assert.equal(r.out, "");

// security: no token, wrong Host, browser Origin, bad decision
assert.equal((await fetch(`${base}/requests`)).status, 401);
assert.equal((await fetch(`${base}/requests`, { headers: { ...auth, origin: "https://evil.example" } })).status, 403);
const { request } = await import("node:http");
const hostStatus = await new Promise((res) => request({ port, path: "/requests", headers: { ...auth, host: "evil.example" } }, (x) => res(x.statusCode)).end());
assert.equal(hostStatus, 403);
hook = runHook(payload);
p = await waitPending();
assert.equal((await decide(p.id, "yes")).status, 400);
await decide(p.id, "deny");
await hook;

// server down -> hook prints nothing, exits 0
server.close();
r = await runHook(payload);
assert.equal(r.code, 0);
assert.equal(r.out, "");

console.log("selftest: all checks passed");
