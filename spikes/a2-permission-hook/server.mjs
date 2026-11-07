// Spike A2: loopback approval server. Holds each pending agent permission
// request open until a human allows/denies it or it times out.
import { createServer } from "node:http";
import { randomBytes, randomUUID, timingSafeEqual } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { PORT, TOKEN_FILE, PENDING_TIMEOUT_MS } from "./config.mjs";

const MAX_BODY_BYTES = 64 * 1024;
const pending = new Map(); // id -> { request, createdAt, resolve }

export function startServer({ port = PORT, token = randomBytes(32).toString("hex"), timeoutMs = PENDING_TIMEOUT_MS } = {}) {
  const expected = Buffer.from(`Bearer ${token}`);
  let allowedHosts; // set after listen, from the actual bound port

  const authorized = (req) => {
    const got = Buffer.from(req.headers.authorization ?? "");
    return got.length === expected.length && timingSafeEqual(got, expected);
  };

  const send = (res, status, body) => {
    res.writeHead(status, { "content-type": "application/json" });
    res.end(JSON.stringify(body));
  };

  const readJson = (req) =>
    new Promise((resolve, reject) => {
      let size = 0;
      const chunks = [];
      req.on("data", (c) => {
        size += c.length;
        if (size > MAX_BODY_BYTES) {
          reject(new Error("body too large"));
          req.destroy();
        } else chunks.push(c);
      });
      req.on("end", () => {
        try {
          resolve(JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}"));
        } catch {
          reject(new Error("invalid json"));
        }
      });
    });

  const server = createServer(async (req, res) => {
    // Loopback-only API: reject DNS-rebinding Hosts and any browser Origin (REQ-11).
    if (!allowedHosts.has(req.headers.host) || req.headers.origin !== undefined) return send(res, 403, { error: "forbidden" });
    if (!authorized(req)) return send(res, 401, { error: "unauthorized" });

    const url = new URL(req.url, `http://${req.headers.host}`);
    try {
      if (req.method === "POST" && url.pathname === "/requests") {
        const body = await readJson(req);
        if (typeof body.tool_name !== "string") return send(res, 400, { error: "tool_name required" });
        const id = randomUUID();
        const decision = await new Promise((resolve) => {
          const timer = setTimeout(() => resolve({ decision: "ask", reason: "timed out; falling back to terminal prompt" }), timeoutMs);
          pending.set(id, {
            request: { tool_name: body.tool_name, tool_input: body.tool_input, session_id: body.session_id, cwd: body.cwd },
            createdAt: Date.now(),
            resolve: (d) => (clearTimeout(timer), resolve(d)),
          });
          req.on("close", () => !res.writableEnded && pending.get(id)?.resolve({ decision: "ask", reason: "client gone" }));
        });
        pending.delete(id);
        return send(res, 200, { id, ...decision });
      }

      if (req.method === "GET" && url.pathname === "/requests") {
        return send(res, 200, [...pending].map(([id, p]) => ({ id, ageMs: Date.now() - p.createdAt, ...p.request })));
      }

      const m = url.pathname.match(/^\/requests\/([0-9a-f-]{36})\/decision$/);
      if (req.method === "POST" && m) {
        const entry = pending.get(m[1]);
        if (!entry) return send(res, 404, { error: "no such pending request" });
        const { decision, reason = "" } = await readJson(req);
        if (decision !== "allow" && decision !== "deny") return send(res, 400, { error: "decision must be allow or deny" });
        entry.resolve({ decision, reason: String(reason).slice(0, 500) });
        return send(res, 200, { ok: true });
      }

      send(res, 404, { error: "not found" });
    } catch (err) {
      send(res, 400, { error: err.message });
    }
  });

  return new Promise((resolve) =>
    server.listen(port, "127.0.0.1", () => {
      const bound = server.address().port;
      allowedHosts = new Set([`127.0.0.1:${bound}`, `localhost:${bound}`]);
      resolve({ server, token, port: bound });
    }),
  );
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const { token, port } = await startServer();
  mkdirSync(dirname(TOKEN_FILE), { recursive: true, mode: 0o700 });
  writeFileSync(TOKEN_FILE, token, { mode: 0o600 });
  console.log(`approval server on http://127.0.0.1:${port} (token in ${TOKEN_FILE})`);
}
