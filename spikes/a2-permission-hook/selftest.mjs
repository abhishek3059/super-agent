// node spikes/a2-permission-hook/selftest.mjs : end-to-end check, no Claude Code needed.
// Offline and loopback-only. Test storage lives only under SUPER_AGENT_TEST_TMP
// (mandatory on Windows, e.g. C:\Users\user\AppData\Local\Temp\opencode);
// without the override POSIX keeps the system-temp default. Nothing touches
// the real token/key homes, the repo, or external services.
// Importing this module has no side effects; running it on Windows without
// the approved test root fails closed before any storage (design).
import assert from "node:assert/strict";
import { spawn, execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync, openSync, closeSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join, relative } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { request } from "node:http";
import { randomBytes } from "node:crypto";
import { isDirectRun } from "../entrypoint.mjs";

const children = new Set();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const cap = (s, d, size) => { const n = s + d; return n.length > size ? n.slice(-size) : n; };

// provider credentials never reach child processes
const childEnvBase = { ...process.env };
for (const k of Object.keys(childEnvBase)) if (/GEMINI|GOOGLE_API|ANTHROPIC_API|OPENAI_API|CLAUDE_API/i.test(k)) delete childEnvBase[k];

/** Spawn a tracked child bounded by a deadline; killed unconditionally in cleanup. */
function spawnChild(argv, { input = "", env = childEnvBase, timeoutMs = 10_000, cwd } = {}) {
  const acc = { out: "", err2: "" };
  const child = spawn(argv[0], argv.slice(1), { env, cwd, windowsHide: true });
  children.add(child);
  const result = new Promise((res) => {
    let code = null, signal = null, timedOut = false, spawnError = null, settled = false;
    const settle = () => {
      if (settled) return;
      settled = true;
      children.delete(child);
      clearTimeout(timer);
      res({ code, signal, out: acc.out, err2: acc.err2, timedOut, spawnError });
    };
    const timer = setTimeout(() => { timedOut = true; try { child.kill(); } catch {} }, timeoutMs);
    child.stdout.on("data", (d) => { acc.out = cap(acc.out, d.toString(), 64 * 1024); }); // bounded capture
    child.stderr.on("data", (d) => { acc.err2 = cap(acc.err2, d.toString(), 64 * 1024); });
    child.stdin.on("error", () => {}); // a dead server turns stdin writes into EPIPE: not a crash
    child.on("error", (e) => { spawnError = e; settle(); });
    child.on("close", (c, s) => { clearTimeout(timer); code = c; signal = s; settle(); });
    child.stdin.end(input);
  });
  return { child, acc, result };
}

const killChild = (child) => new Promise((res) => {
  if (child.exitCode !== null || child.signalCode !== null) return res(); // already exited
  let done = false;
  const finish = () => { if (!done) { done = true; clearTimeout(timer); res(); } };
  const timer = setTimeout(finish, 3_000); // never hang cleanup on a wedged child
  child.once("close", finish);
  try { child.kill(); } catch { finish(); }
});

const payload = { hook_event_name: "PermissionRequest", tool_name: "Bash", tool_input: { command: "npm test" }, session_id: "s1", cwd: "/tmp" };
let token, port, base, auth;
const hookPath = fileURLToPath(new URL("./hook.mjs", import.meta.url));
const serverCliPath = fileURLToPath(new URL("./server.mjs", import.meta.url));
const selfPath = fileURLToPath(import.meta.url);

const runHook = (payloadStringOrObject, { tokenFile, port: hookPort } = {}) =>
  spawnChild([process.execPath, hookPath], {
    input: typeof payloadStringOrObject === "string" ? payloadStringOrObject : JSON.stringify(payloadStringOrObject),
    env: { ...childEnvBase, SUPER_AGENT_PORT: String(hookPort ?? port), SUPER_AGENT_TOKEN_FILE: String(tokenFile) },
  });

const waitPending = async (b, headers, { spawned } = {}) => {
  for (let i = 0; i < 50; i++) {
    if (spawned && (spawned.child.exitCode !== null || spawned.child.signalCode !== null)) {
      const { err2 } = await spawned.result;
      throw new Error(`hook exited before posting: ${err2.trim()}`);
    }
    const list = await (await fetch(`${b}/requests`, { headers, signal: AbortSignal.timeout(2000) })).json();
    if (list.length) return list[0];
    await sleep(20);
  }
  throw new Error(`request never became pending (${b}${headers === auth ? " main" : " alt"})`);
};

const decide = (id, decision, reason, b = base) =>
  fetch(`${b}/requests/${id}/decision`, { method: "POST", headers: auth, body: JSON.stringify({ decision, reason }), signal: AbortSignal.timeout(2000) });

async function main() {
  // --- test root (checked before loading any feature module) ----------------
  const TEST_ROOT = process.env.SUPER_AGENT_TEST_TMP;
  if (TEST_ROOT === undefined && process.platform === "win32") {
    console.error("selftest: requires SUPER_AGENT_TEST_TMP set to an approved private directory on Windows");
    process.exit(1);
  }
  let root = tmpdir();
  if (TEST_ROOT !== undefined) {
    const st = statSync(TEST_ROOT); // throws on absence
    assert.ok(st.isDirectory(), "SUPER_AGENT_TEST_TMP must be a directory");
    root = TEST_ROOT;
  }
  const suite = mkdtempSync(join(root, "Süper Agent spike ")); // unique; spaces and non-ASCII
  const isWin = process.platform === "win32";
  const assertReaddirClean = () => assert.deepEqual(readdirSync(suite).filter((n) => n.startsWith("spike-token-")), [], "no staging directory leftovers");
  let server = null;

  try {
    // --- entrypoint guard (pure, no exec) -----------------------------------
    const { startServer, createReadyGate } = await import("./server.mjs");
    const { toHookOutput, describeHookError } = await import("./hook.mjs");
    const { writeTokenFile, parseDaclDump, windowsCurrentSid } = await import("./token-file.mjs");

    /** `icacls /save` via fixed System32 tool, bounded; returns decoded dump text. */
    const dumpDacl = (target) => {
      const dump = join(suite, `acl-check-${randomBytes(4).toString("hex")}.tmp`);
      try {
        execFileSync(join(process.env.SystemRoot ?? "C:\\Windows", "System32", "icacls.exe"), [target, "/save", dump], { timeout: 5000, maxBuffer: 64 * 1024, windowsHide: true });
        const buf = readFileSync(dump);
        return buf.length > 1 && buf[0] === 0xff && buf[1] === 0xfe
          ? buf.subarray(2).toString("utf16le")
          : buf.length > 1 && buf[1] === 0
            ? buf.toString("utf16le")
            : buf.toString("utf8");
      } finally {
        rmSync(dump, { force: true });
      }
    };

    /** Structural + owner-only assertions on a private token file's dump. */
    const assertOwnerOnlyDacl = (target, sid, { requireOICI = false } = {}) => {
      const parsed = parseDaclDump(dumpDacl(target));
      assert.ok(/^P(AI)?$/.test(parsed.flags), `DACL protected from inheritance (flags: ${parsed.flags})`);
      assert.equal(parsed.aces.length, 1, "exactly one ACE");
      const { type, flags, rights, obj, objInherit, trustee } = parsed.aces[0];
      assert.equal(type, "A");
      assert.equal(flags, requireOICI ? "OICI" : "");
      assert.equal(rights, "FA");
      assert.equal(obj, "", "no object guid in ACE");
      assert.equal(objInherit, "", "no inherited-object guid in ACE");
      assert.equal(trustee.toUpperCase(), sid.toUpperCase());
    };

    assert.equal(isDirectRun(import.meta.url), true, "running directly now");
    assert.equal(isDirectRun(import.meta.url, ""), false, "empty argv means imported");
    const savedEntry = process.argv[1];
    try {
      delete process.argv[1];
      assert.equal(isDirectRun(import.meta.url), false, "missing argv means imported");
    } finally {
      process.argv[1] = savedEntry;
    }
    assert.equal(isDirectRun(import.meta.url, relative(process.cwd(), selfPath)), true, "relative-to-cwd argv entry");
    const weird = join(suite, "eo #10 %2F öko.mjs");
    assert.equal(isDirectRun(pathToFileURL(weird).href, weird), true, "spaces, hash, percent, non-ASCII entry");
    assert.equal(isDirectRun(pathToFileURL(weird).href, weird + "x"), false, "different path is not direct");
    const gate = createReadyGate();
    assert.equal(gate.ready, false);
    gate.open();
    assert.equal(gate.ready, true);
    gate.close();
    assert.equal(gate.ready, false);
    assert.equal(describeHookError(Object.assign(new Error(), { name: "TimeoutError" })), "server-decision-window-expired");
    assert.equal(describeHookError(Object.assign(new Error(), { code: "ECONNREFUSED" })), "server-unreachable");
    assert.equal(describeHookError(new SyntaxError()), "invalid-hook-input");
    assert.deepEqual(toHookOutput({ decision: "allow" }).hookSpecificOutput.decision, { behavior: "allow" });
    assert.equal(toHookOutput({ decision: "ask" }), null);

    // --- importing the selftest is side-effect-free ---------------------------
    {
      const probe = await spawnChild(
        [process.execPath, "-e", "const u = await import('node:url'); await import(u.pathToFileURL(process.env.A2_SELF).href);"],
        { env: { ...childEnvBase, A2_SELF: selfPath, SUPER_AGENT_TEST_TMP: process.env.SUPER_AGENT_TEST_TMP }, timeoutMs: 10_000 },
      ).result;
      assert.equal(probe.code, 0, `selftest import probe exited cleanly (${probe.err2.slice(0, 200)})`);
      if (isWin) {
        // Windows: direct run without the approved test root fails closed
        // before storage; importing remains side-effect-free.
        const rootless = { ...childEnvBase };
        delete rootless.SUPER_AGENT_TEST_TMP;
        const guarded = await spawnChild([process.execPath, selfPath], { env: rootless, timeoutMs: 10_000 }).result;
        assert.equal(guarded.code, 1, `guarded direct run exits 1 (${guarded.code})`);
        assert.ok(guarded.err2.includes("SUPER_AGENT_TEST_TMP"), guarded.err2.slice(0, 200));
      }
    }
    // --- importing server/hook modules does nothing ----------------------------
    {
      const probe = await spawnChild(
        [process.execPath, "-e", "const u = await import('node:url'); await import(u.pathToFileURL(process.env.A2_SERVER).href); await import(u.pathToFileURL(process.env.A2_HOOK).href);"],
        { env: { ...childEnvBase, A2_SERVER: serverCliPath, A2_HOOK: hookPath }, timeoutMs: 10_000 },
      ).result;
      assert.equal(probe.code, 0, `module import probe exited cleanly (${probe.err2.slice(0, 200)})`);
    }

    // --- main feature tests ------------------------------------------------------
    const started = await startServer({ port: 0, timeoutMs: 1500 });
    server = started.server;
    token = started.token; port = started.port;
    base = `http://127.0.0.1:${port}`;
    auth = { authorization: `Bearer ${token}`, "content-type": "application/json" };
    const baseTokenFile = join(suite, "spike token #1 öko");
    writeFileSync(baseTokenFile, token);

    // allow
    let hook = runHook(payload, { tokenFile: baseTokenFile });
    let p = await waitPending(base, auth, { spawned: hook });
    assert.equal(p.tool_name, "Bash");
    await decide(p.id, "allow");
    let r = await hook.result;
    assert.equal(r.code, 0);
    assert.deepEqual(JSON.parse(r.out), toHookOutput({ decision: "allow" }));

    // deny with reason
    hook = runHook(payload, { tokenFile: baseTokenFile });
    p = await waitPending(base, auth, { spawned: hook });
    await decide(p.id, "deny", "not now");
    r = await hook.result;
    assert.equal(r.code, 0);
    assert.equal(JSON.parse(r.out).hookSpecificOutput.decision.message, "not now");

    // timeout -> no output (normal prompt, never auto-allow)
    {
      const th = runHook(payload, { tokenFile: baseTokenFile });
      await waitPending(base, auth, { spawned: th });
      r = await th.result;
      assert.equal(r.code, 0);
      assert.equal(r.out, "");
    }

    // spawn failure is reported, not hung, and leaves no tracked child
    const badSpawn = await spawnChild(["sa-nonexistent-cmd-x"]).result;
    assert.ok(badSpawn.spawnError, "spawn error surfaced immediately");

    // malformed stdin -> safe category, no decision, exit 0
    r = await runHook("not json", { tokenFile: baseTokenFile }).result;
    assert.equal(r.code, 0);
    assert.equal(r.out, "");
    assert.ok(r.err2.includes("invalid-hook-input"), r.err2);

    // missing token (server still up) -> safe category, no decision, exit 0
    r = await runHook(payload, { tokenFile: join(suite, "absent öko token") }).result;
    assert.equal(r.code, 0);
    assert.equal(r.out, "");
    assert.ok(r.err2.includes("token-or-server-unavailable"), r.err2);

    // security: no token, browser Origin, explicit-IPv4 bad Host, bad decision
    assert.equal((await fetch(`${base}/requests`, { signal: AbortSignal.timeout(2000) })).status, 401);
    assert.equal((await fetch(`${base}/requests`, { headers: { ...auth, origin: "https://evil.example" }, signal: AbortSignal.timeout(2000) })).status, 403);
    const hostStatus = await new Promise((res, rej) => {
      const rq = request({ host: "127.0.0.1", port, path: "/requests", headers: { ...auth, host: "evil.example" }, timeout: 2000 }, (x) => res(x.statusCode));
      rq.on("error", rej);
      rq.end();
    });
    assert.equal(hostStatus, 403);
    // raw server errors are fixed-safe, never reflective
    assert.equal((await (await fetch(`${base}/requests`, { method: "POST", headers: auth, body: "not json", signal: AbortSignal.timeout(2000) })).json()).error, "malformed request");
    hook = runHook(payload, { tokenFile: baseTokenFile });
    p = await waitPending(base, auth, { spawned: hook });
    assert.equal((await (await decide(p.id, "yes")).json()).error, "decision must be allow or deny");
    await decide(p.id, "deny");
    await hook.result;

    // ready gate fails closed before startup completes
    {
      const closed = createReadyGate();
      const gated = await startServer({ port: 0, timeoutMs: 1500, gate: closed });
      try {
        const gbase = `http://127.0.0.1:${gated.port}`;
        const authz = { authorization: `Bearer ${gated.token}` };
        const status = (await fetch(`${gbase}/requests`, { headers: authz, signal: AbortSignal.timeout(2000) })).status;
        assert.equal(status, 503, "closed gate rejects approvals");
        closed.open();
        const after = (await fetch(`${gbase}/requests`, { headers: authz, signal: AbortSignal.timeout(2000) })).status;
        assert.equal(after, 200, "opened gate admits");
      } finally {
        gated.server.closeAllConnections?.();
        await gated.server.close();
      }
    }

    // occupied port -> startServer rejects (and never leaves a listener)
    {
      const { createServer: netCreate } = await import("node:net");
      const taker = netCreate();
      try {
        await new Promise((res, rej) => { taker.on("error", rej).listen(0, "127.0.0.1", res); });
        await assert.rejects(startServer({ port: taker.address().port, timeoutMs: 500 }), (e) => e?.code === "EADDRINUSE");
      } finally {
        await new Promise((res) => taker.close(res));
      }
    }

    // server down (existing token; true connect failure) -> silent, exit 0
    const closedPort = port;
    server.closeAllConnections?.();
    await server.close();
    server = null;
    r = await runHook(payload, { tokenFile: baseTokenFile, port: closedPort }).result;
    assert.equal(r.code, 0);
    assert.equal(r.out, "");
    assert.ok(r.err2.includes("server-unreachable"), r.err2);

    // --- token-file helper ---------------------------------------------------------
    const directToken = randomBytes(32).toString("hex");
    const directTarget = join(suite, "spike token #7 öko");
    assert.equal(existsSync(directTarget), false, "sanity: no preexisting target");
    await writeTokenFile({ target: directTarget, token: directToken });
    assert.ok(readFileSync(directTarget, "utf8") === directToken, "published token matches without logging its value");
    let cachedSid = null;
    if (isWin) {
      cachedSid = await windowsCurrentSid();
      assertOwnerOnlyDacl(directTarget, cachedSid);
    }
    assertReaddirClean();

    // replacing an existing weaker file keeps the published object private
    const weakTarget = join(suite, "weaker öko token");
    if (isWin) {
      closeSync(openSync(weakTarget, "w")); // created with default user ACL
      writeFileSync(weakTarget, "old weak token");
    } else {
      writeFileSync(weakTarget, "old weak token", { mode: 0o666 });
    }
    const replacedToken = randomBytes(32).toString("hex");
    await writeTokenFile({ target: weakTarget, token: replacedToken });
    assert.ok(readFileSync(weakTarget, "utf8") === replacedToken, "replacement token matches without logging its value");
    if (isWin) {
      assertOwnerOnlyDacl(weakTarget, cachedSid);
    } else {
      assert.equal(statSync(weakTarget).mode & 0o777, 0o600, "replacement stays 0600");
    }
    assertReaddirClean();

    // injected failures: fail closed, no publish, no leftovers, token kept
    if (isWin) {
      const before = readdirSync(suite).sort();
      await assert.rejects(
        writeTokenFile({ target: directTarget, token: "x".repeat(64), run: async () => { throw Object.assign(new Error("boom"), { code: 5 }); } }),
        (e) => e?.category === "native-exit",
      );
      assert.deepEqual(readdirSync(suite).sort(), before, "injected native-exit leaves no leftovers");
      assert.ok(readFileSync(directTarget, "utf8") === directToken, "existing token untouched by failed startup");

      await assert.rejects(
        writeTokenFile({ target: directTarget, token: "synthetic", run: async () => { throw Object.assign(new Error("missing"), { code: "ENOENT" }); } }),
        (e) => e?.category === "native-tool-missing",
      );
      assert.deepEqual(readdirSync(suite).sort(), before, "missing native tool leaves no leftovers");

      const fakeSid = "S-1-5-21-500-500-500-1000";
      for (const [label, parentDacl, stagingDacl, errorCategory] of [
        ["parent-delete-child", `D:P(A;;FA;;;${fakeSid})(A;;0x40;;;BU)`, null, "parent-untrusted"],
        ["parent-symbolic-write", `D:P(A;;FA;;;${fakeSid})(A;;FA;;;AU)`, null, "parent-untrusted"],
        ["extra-principal", `D:P(A;;FA;;;${fakeSid})`, `D:P(A;OICI;FA;;;${fakeSid})(A;;FR;;;BU)`, "acl-verify"],
        ["enabled-inheritance", `D:P(A;;FA;;;${fakeSid})`, `D:AI(A;OICI;FA;;;${fakeSid})`, "acl-verify"],
        ["null-dacl", `D:P(A;;FA;;;${fakeSid})`, "D:NO_ACCESS_CONTROL", "acl-format"],
        ["empty-dacl", `D:P(A;;FA;;;${fakeSid})`, "D:P", "acl-format"],
      ]) {
        const target = join(suite, `${label} öko`);
        await assert.rejects(writeTokenFile({ target, token: "synthetic", run: async (argv) => {
          if (argv.includes("/user")) return { stdout: Buffer.from(`"synthetic-user","${fakeSid}"`) };
          const saveAt = argv.indexOf("/save");
          if (saveAt !== -1) {
            const dump = argv[saveAt + 1];
            writeFileSync(dump, `synthetic-path\n${basename(dump) === "acl-parent.tmp" ? parentDacl : stagingDacl}\n`);
          }
          return { stdout: Buffer.from("") };
        } }), (e) => e?.category === errorCategory, `${label} fails closed`);
        assert.ok(!existsSync(target), `${label} never publishes a token`);
        assert.deepEqual(readdirSync(suite).sort(), before, `${label} leaves no staging files`);
      }

      const symbolicReadTarget = join(suite, "symbolic-readonly-parent öko");
      await writeTokenFile({ target: symbolicReadTarget, token: "synthetic", run: async (argv) => {
        if (argv.includes("/user")) return { stdout: Buffer.from(`"synthetic-user","${fakeSid}"`) };
        const saveAt = argv.indexOf("/save");
        if (saveAt !== -1) {
          const savedTarget = argv[1];
          const dump = argv[saveAt + 1];
          const isParent = savedTarget.toLowerCase() === suite.toLowerCase();
          const isDirectory = !isParent && statSync(savedTarget).isDirectory();
          const dacl = isParent
            ? `D:P(A;;FA;;;${fakeSid})(A;;FR;;;AU)`
            : isDirectory
              ? `D:P(A;OICI;FA;;;${fakeSid})`
              : `D:P(A;;FA;;;${fakeSid})`;
          writeFileSync(dump, `synthetic-path\n${dacl}\n`);
        }
        return { stdout: Buffer.from("") };
      } });
      assert.equal(readFileSync(symbolicReadTarget, "utf8"), "synthetic", "read-only symbolic parent trustee is accepted");
      rmSync(symbolicReadTarget, { force: true });
      assertReaddirClean();

      await assert.rejects(
        writeTokenFile({ target: join(suite, "sid-bad öko"), token: "x".repeat(64), run: async (argv) => {
          if (argv.includes("/user")) return { stdout: Buffer.from("garbage") };
          throw Object.assign(new Error(), { code: 1 }); // normalization turns this into native-exit
        } }),
        (e) => e?.category === "sid-format",
      );
      assertReaddirClean();

      await assert.rejects(
        writeTokenFile({ target: join(suite, "native-timeout öko"), token: "x".repeat(64), run: async (argv) => {
          if (argv.includes("/user")) return { stdout: Buffer.from('"m\\\\u","S-1-5-21-500-500-500-1000"') };
          throw Object.assign(new Error(), { code: "ETIMEDOUT", killed: true });
        } }),
        (e) => e?.category === "native-timeout",
      );
      assertReaddirClean();

      // unparseable parent permissions dump fails closed before any staging
      await assert.rejects(
        writeTokenFile({ target: join(suite, "parent-bad öko"), token: "x".repeat(64), run: async (argv) => {
          if (argv.includes("/save")) return { stdout: Buffer.from("MALFORMED") };
          if (argv.includes("/user")) return { stdout: Buffer.from('"m\\\\u","S-1-5-21-500-500-500-1000"') };
          return { stdout: Buffer.from("") };
        } }),
        (e) => e?.category === "acl-format" || e?.category === "parent-untrusted" || e?.category === "acl-verify",
      );
      assertReaddirClean();
    }
    assertReaddirClean();

    // publication failure: target inside a plain file fails closed
    {
      const blocked = join(suite, "blocked.txt");
      writeFileSync(blocked, "");
      const before = readdirSync(suite).sort();
      await assert.rejects(writeTokenFile({ target: join(blocked, "tok"), token: directToken }), (e) => e?.category === "parent-create" || e?.code === "ENOENT");
      assert.equal(readFileSync(blocked, "utf8"), "");
      assert.deepEqual(readdirSync(suite).sort(), before, "publication failure leaves no staging leftovers");
    }

    // unexpected existing target type (directory) fails closed
    {
      const asDir = join(suite, "target-is-dir öko");
      mkdirSync(asDir);
      const before = readdirSync(suite).sort();
      await assert.rejects(writeTokenFile({ target: asDir, token: directToken }), (e) => e?.category === "target-type");
      assert.equal(statSync(asDir).isDirectory(), true);
      assert.deepEqual(readdirSync(suite).sort(), before, "type-rejection leaves no staging leftovers");
    }

    // --- direct CLI: bind -> staged verified token -> ready ------------------------
    {
      const cliDir = join(suite, "cli dir #9");
      const cliTokenFile = join(cliDir, "token file #2 öko");
      const cli = spawnChild([process.execPath, serverCliPath], { timeoutMs: 20_000, env: { ...childEnvBase, SUPER_AGENT_PORT: "0", SUPER_AGENT_TOKEN_FILE: cliTokenFile } });
      try {
        const deadline = Date.now() + 15_000;
        while (!/approval server on http:\/\/127\.0\.0\.1:\d+/.test(cli.acc.out) && Date.now() < deadline) await sleep(50);
        const line = /approval server on http:\/\/127\.0\.0\.1:(\d+)/.exec(cli.acc.out);
        assert.ok(line, `CLI reported readiness (stdout: ${cli.acc.out.slice(0, 200)})`);
        const cliPort = Number(line[1]);
        assert.ok(existsSync(cliTokenFile), "CLI published the token file");
        const cliToken = readFileSync(cliTokenFile, "utf8");
        assert.ok(cliToken.length >= 64, "token file populated");
        if (isWin) assertOwnerOnlyDacl(cliTokenFile, cachedSid);

        const cliAuth = { authorization: `Bearer ${cliToken}`, "content-type": "application/json" };
        const cliBase = `http://127.0.0.1:${cliPort}`;
        hook = runHook({ ...payload, tool_name: "Bash" }, { tokenFile: cliTokenFile, port: cliPort });
        const cp = await waitPending(cliBase, cliAuth, { spawned: hook });
        await fetch(`${cliBase}/requests/${cp.id}/decision`, { method: "POST", headers: cliAuth, body: JSON.stringify({ decision: "allow" }), signal: AbortSignal.timeout(2000) });
        r = await hook.result;
        assert.deepEqual(JSON.parse(r.out), toHookOutput({ decision: "allow" }));
      } finally {
        await killChild(cli.child);
        assert.deepEqual(readdirSync(cliDir), [basename(cliTokenFile)], "no staging or dump leftovers after CLI startup");
      }
    }

    assertReaddirClean();
    console.log("selftest: all checks passed");
  } finally {
    for (const c of [...children]) await killChild(c);
    if (server) { try { server.closeAllConnections?.(); await server.close(); } catch {} }
    server = null;
    rmSync(suite, { recursive: true, force: true });
  }
}

if (isDirectRun(import.meta.url)) {
  await main().catch((err) => {
    console.error("selftest failed:", err?.message ?? err, err?.stack ? `\n${err.stack}` : "");
    process.exitCode = 1;
  });
}
