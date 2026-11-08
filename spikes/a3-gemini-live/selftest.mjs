// node spikes/a3-gemini-live/selftest.mjs : offline selftest for the A3 seams.
// No key read, no real client construction, no network, no default-file writes.
// Windows requires the approved test root in SUPER_AGENT_TEST_TMP; POSIX may
// fall back to the system temp dir. See docs/design/windows-spike-compatibility.md.
import assert from "node:assert/strict";
import { existsSync, mkdirSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { isDirectRun } from "../entrypoint.mjs";

async function main() {
// Check the test root before any module import or credential path can be touched.
const testRootOverride = process.env.SUPER_AGENT_TEST_TMP;
if (process.platform === "win32" && !testRootOverride) {
  console.error("FAIL not run: Windows requires SUPER_AGENT_TEST_TMP set to the approved test root (C:\\Users\\user\\AppData\\Local\\Temp\\opencode)");
  process.exit(1);
}
const testRoot = testRootOverride ?? tmpdir();
try {
  if (!statSync(testRoot).isDirectory()) throw new Error("not a directory");
} catch {
  console.error(`FAIL not run: SUPER_AGENT_TEST_TMP root ${testRoot} is not a usable directory`);
  process.exit(1);
}

// Unique suite directory with spaces and non-ASCII characters under the override.
const suiteDir = join(testRoot, `super-agent a3 selftest ${process.pid} ${process.hrtime.bigint()} først rún ünï`);
const suiteFile = join(suiteDir, "répl y out.pcm");
const defaultReplyPath = join(tmpdir(), "super-agent-a3-reply.pcm");
const defaultReplyExisted = existsSync(defaultReplyPath);
const unhandled = [];
const onUnhandled = (reason) => unhandled.push(reason instanceof Error ? reason.message : String(reason));

const { buildToolResponses, runOnce, runCli, JOBS } = await import("./live.mjs");
const liveUrl = new URL("./live.mjs", import.meta.url).href;
mkdirSync(suiteDir, { recursive: true });
process.on("unhandledRejection", onUnhandled);

function makeFakeAi({ deferConnect = false, throwOnToolSend = false, throwOnClose = false } = {}) {
  const connections = [];
  return {
    connections,
    ai: {
      live: {
        connect({ callbacks }) {
          return new Promise((resolve) => {
            const connection = { callbacks, session: null, resolveConnect: null, closed: false, clientSends: 0, toolSends: 0 };
            connection.resolveConnect = () => {
              connection.resolveConnect = null;
              resolve(connection.session);
            };
            connection.session = {
              sendClientContent() {
                connection.clientSends += 1;
              },
              sendToolResponse() {
                connection.toolSends += 1;
                if (throwOnToolSend) throw new Error("raw tool-send failure SENTINEL");
              },
              close() {
                this.closed = true;
                connection.closed = true;
                if (throwOnClose) throw new Error("raw close failure SENTINEL");
              },
            };
            connections.push(connection);
            if (!deferConnect) connection.resolveConnect();
          });
        },
      },
    },
  };
}

const oneSecondB64 = Buffer.alloc(24_000 * 2).toString("base64");

async function testGuardAndImports() {
  // Importing live.mjs must not start the CLI (import side effect); the guard
  // stays about the entry URL, not about voice or any other signal.
  const liveFile = fileURLToPath(new URL("./live.mjs", import.meta.url));
  assert.ok(isDirectRun(liveUrl, liveFile), "direct run of live.mjs is direct");
  assert.ok(!isDirectRun(liveUrl, fileURLToPath(new URL("./selftest.mjs", import.meta.url))), "argv pointing at selftest is not a live run");
  assert.ok(!isDirectRun(liveUrl, undefined), "missing argv is imported");
  assert.ok(isDirectRun(pathToFileURL(join(suiteDir, "først rún ünï", "live.mjs")).href, join(suiteDir, "først rún ünï", "live.mjs")), "non-ASCII path with spaces compares through the URL form");
}

async function testValidBatches() {
  const batch = buildToolResponses([{ name: "get_agent_jobs", id: "call-a" }, { name: "get_agent_jobs", args: {} }]);
  assert.deepEqual(batch, {
    functionResponses: [
      { id: "call-a", name: "get_agent_jobs", response: { jobs: JOBS } },
      { id: undefined, name: "get_agent_jobs", response: { jobs: JOBS } },
    ],
  });
  const sixteen = Array.from({ length: 16 }, () => ({ name: "get_agent_jobs" }));
  assert.equal(buildToolResponses(sixteen).functionResponses.length, 16);
}

async function testInvalidBatches() {
  const cases = [
    ["too many tool calls", Array.from({ length: 17 }, () => ({ name: "get_agent_jobs" }))],
    ["empty tool call batch", []],
    ["malformed tool call batch", "not an array"],
    ["malformed tool call batch", [5]],
    ["malformed tool call batch", ["get_agent_jobs"]],
    ["unsupported tool call", [{ name: "make_purchase" }]],
    ["unsupported tool call", [{ id: "c1", name: "buy_domain_adv" }]],
    ["invalid tool call arguments", [{ name: "get_agent_jobs", args: { x: 1 } }]],
    ["invalid tool call arguments", [{ name: "get_agent_jobs", args: "jobs" }]],
    ["invalid tool call arguments", [{ name: "get_agent_jobs", args: [] }]],
    ["invalid tool call arguments", [{ name: "get_agent_jobs", args: null }]],
    ["invalid tool call id", [{ name: "get_agent_jobs", id: "" }]],
    ["invalid tool call id", [{ name: "get_agent_jobs", id: 7 }]],
    ["invalid tool call id", [{ name: "get_agent_jobs", id: "x".repeat(257) }]],
  ];
  for (const [idx, [category, input]] of cases.entries()) {
    assert.throws(() => buildToolResponses(input), { message: category }, `batch case ${idx} must reject with ${category}`);
  }
  assert.throws(() => buildToolResponses([{ name: "get_agent_jobs", id: "same" }, { name: "get_agent_jobs", id: "same" }]), { message: "duplicate tool call id" });
}

async function testSuccessRoundTrip() {
  const { ai, connections } = makeFakeAi();
  const pending = runOnce(ai, 0, { replyPath: suiteFile });
  assert.equal(connections.length, 1);
  const { callbacks, session, resolveConnect } = connections[0];
  assert.equal(resolveConnect, null, "non-deferred fake resolved immediately");
  await Promise.resolve(); // Let the connect handler attach the session first.
  callbacks.onmessage({ setupComplete: true });
  callbacks.onmessage({ toolCall: { functionCalls: [{ name: "get_agent_jobs", id: "call-a" }, { name: "get_agent_jobs", args: {} }] } });
  callbacks.onmessage({ serverContent: { outputTranscription: { text: "Two jobs." } } });
  callbacks.onmessage({ serverContent: { modelTurn: { parts: [{ inlineData: { data: oneSecondB64 } }] }, turnComplete: true } });
  const result = await pending;

  assert.equal(session.closed, true, "session closed on success");
  assert.ok(result.connectMs >= 0);
  assert.ok(result.toolCallMs != null);
  assert.ok(result.firstAudioAfterToolMs != null);
  assert.ok(result.firstAudioMs >= 0);
   assert.ok(Number.isFinite(result.totalMs) && result.totalMs >= 0, "total duration is a measured finite number, not null");
  assert.equal(result.audioSec, 1);
  assert.equal(result.toolCalled, "get_agent_jobs,get_agent_jobs");
  assert.equal(result.transcript, "Two jobs.");
  assert.ok(existsSync(suiteFile), "synthetic reply written to the private suite file");
  rmSync(suiteFile);
  assert.equal(existsSync(suiteFile), false, "synthetic reply cleaned up");

  // Events after settlement are ignored - no throw, no unhandled rejection.
  callbacks.onmessage({ toolCall: { functionCalls: [{ name: "get_agent_jobs" }] } });
  callbacks.onerror(new Error("late provider SENTINEL"));
  callbacks.onclose({ code: 4001, reason: "late close reason SENTINEL" });
  assert.deepEqual(result.toolCalled, "get_agent_jobs,get_agent_jobs");
}

async function testReplyOutputDisabled() {
  const { ai, connections } = makeFakeAi();
  const pending = runOnce(ai, 0, { replyPath: null });
  const { callbacks } = connections[0];
  await Promise.resolve(); // Let the connect handler attach the session first.
  callbacks.onmessage({ toolCall: { functionCalls: [{ name: "get_agent_jobs" }] } });
  callbacks.onmessage({ serverContent: { modelTurn: { parts: [{ inlineData: { data: oneSecondB64 } }] }, turnComplete: true } });
  await pending;
  assert.equal(existsSync(defaultReplyPath), defaultReplyExisted, "disabled reply output leaves the default file untouched");
}

async function testUnknownToolRunNoPartialSend() {
  const { ai, connections } = makeFakeAi();
  const pending = runOnce(ai, 0, { timeoutMs: 300, replyPath: null }).catch((err) => err);
  const { callbacks, session } = connections[0];
  await Promise.resolve(); // Let the connect handler attach the session first.
  callbacks.onmessage({ toolCall: { functionCalls: [{ name: "make_purchase" }, { name: "get_agent_jobs" }] } });
  const err = await pending;
  assert.equal(err.message, "unsupported tool call");
  assert.equal(connections[0].toolSends, 0, "no jobs or partial response after a rejected batch");
  assert.equal(session.closed, true, "session closed on validation failure");
}

async function testToolCallBeforeReady() {
  const { ai, connections } = makeFakeAi({ deferConnect: true });
  const pending = runOnce(ai, 0, { timeoutMs: 300, replyPath: null });
  const { callbacks, session, resolveConnect } = connections[0];
  callbacks.onmessage({ toolCall: { functionCalls: [{ name: "get_agent_jobs" }] } });
  await assert.rejects(pending, { message: "tool call before session ready" });
  assert.equal(connections[0].toolSends, 0);
  assert.equal(session.closed, undefined, "nothing existed to close yet");
  resolveConnect(); // The still-open connection resolves behind the settled failure.
  await new Promise((r) => setTimeout(r, 10));
  assert.equal(session.closed, true, "deferred connection closed after rejection");
  assert.equal(connections[0].clientSends + connections[0].toolSends, 0, "deferred connection sent nothing");
}

async function testTimeoutAndLateConnection() {
  const { ai, connections } = makeFakeAi({ deferConnect: true });
  const pending = runOnce(ai, 0, { timeoutMs: 40, replyPath: null });
  assert.equal(connections.length, 1);
  await assert.rejects(pending, { message: "timed out after 40ms" });
  connections[0].resolveConnect();
  await new Promise((r) => setTimeout(r, 10));
  assert.equal(connections[0].clientSends + connections[0].toolSends, 0, "late connection sends no prompt or tools");
  assert.equal(connections[0].closed, true, "late connection is closed");
}

async function testWebsocketErrorCategory() {
  const { ai, connections } = makeFakeAi();
  const pending = runOnce(ai, 0, { timeoutMs: 300, replyPath: null }).catch((err) => err);
  const { callbacks, session } = connections[0];
  await Promise.resolve(); // Let the connect handler attach the session first.
  callbacks.onerror(new Error("raw websocket detail SENTINEL"));
  const err = await pending;
  assert.equal(err.message, "websocket error");
  assert.ok(!err.message.includes("SENTINEL"), "no raw provider error leaks");
  assert.equal(session.closed, true, "session closed on websocket error");
}

async function testEarlyCloseCategory() {
  const { ai, connections } = makeFakeAi();
  const pending = runOnce(ai, 0, { timeoutMs: 300, replyPath: null }).catch((err) => err);
  const { callbacks, session } = connections[0];
  await Promise.resolve(); // Let the connect handler attach the session first.
  callbacks.onclose({ code: 1006, reason: "raw close reason SENTINEL" });
  const err = await pending;
  assert.equal(err.message, "connection closed early");
  assert.ok(!err.message.includes("SENTINEL"), "no raw close reason leaks");
  assert.equal(session.closed, true, "session closed on early close");
}

async function testConnectRejection() {
  const ai = { live: { connect: () => Promise.reject(new Error("raw connect failure SENTINEL")) } };
  const err = await runOnce(ai, 0, { timeoutMs: 300, replyPath: null }).catch((e) => e);
  assert.equal(err.message, "connect failed");
  assert.ok(!err.message.includes("SENTINEL"), "no raw connect error leaks");
}

async function testSynchronousConnectFailure() {
  const ai = { live: { connect() { throw new Error("raw connect SENTINEL"); } } };
  await assert.rejects(runOnce(ai, 0, { timeoutMs: 300, replyPath: null }), { message: "connect failed" });
}

async function testPromptSendFailure() {
  const { ai, connections } = makeFakeAi({ deferConnect: true });
  const pending = runOnce(ai, 0, { timeoutMs: 300, replyPath: null });
  connections[0].session.sendClientContent = () => { throw new Error("raw prompt SENTINEL"); };
  connections[0].resolveConnect();
  await assert.rejects(pending, { message: "sending prompt failed" });
  assert.equal(connections[0].closed, true);
}

async function testOfflineCliFailures() {
  const lines = [];
  const output = (...args) => lines.push(args.join(" "));
  let clients = 0;
  const createClient = () => { clients += 1; return {}; };
  for (const runs of [0, -1, 1.5, NaN, Infinity]) {
    assert.equal(await runCli({ runs, createClient, log: output, error: output }), 1);
  }
  assert.equal(clients, 0, "invalid run counts never read credentials or create a client");
  lines.length = 0;
  assert.equal(await runCli({ runs: 1, createClient, run: async () => { throw new Error("raw failure SENTINEL"); }, log: output, error: output }), 1);
  assert.ok(!lines.some((line) => line.includes("runs ok")), "zero successes prints no successful summary");
  assert.ok(!lines.some((line) => line.includes("SENTINEL")), "run failure is redacted");
  lines.length = 0;
  assert.equal(await runCli({ runs: 1, createClient: () => { throw new Error("raw key SENTINEL"); }, log: output, error: output }), 1);
  assert.ok(!lines.some((line) => line.includes("SENTINEL")), "client setup failure is redacted");
}

async function testOfflineCliSuccess() {
  const lines = [];
  const sample = { connectMs: 1, toolCallMs: 2, firstAudioAfterToolMs: 3, firstAudioMs: 4, totalMs: 5, audioSec: 1, toolCalled: "get_agent_jobs", transcript: "Synthetic jobs." };
  const createClient = () => ({});
  const log = (...args) => lines.push(args.join(" "));
  assert.equal(await runCli({ runs: 1, createClient, run: async () => sample, log }), 0);
  assert.ok(lines.some((line) => line.includes("1/1 runs ok")), "successful CLI prints its summary");
  assert.ok(lines.some((line) => line.includes('"totalMs":5')), "summary retains measured total duration");
  lines.length = 0;
  assert.equal(await runCli({ runs: 2, createClient, run: async (_ai, i) => { if (i === 0) throw new Error("first run failed"); return sample; }, log }), 0);
  assert.ok(!lines.some((line) => line.includes("audio saved")), "does not claim a saved reply when the first run failed");
}

async function testMalformedMessage() {
  const { ai, connections } = makeFakeAi();
  const pending = runOnce(ai, 0, { timeoutMs: 300, replyPath: null });
  await Promise.resolve();
  connections[0].callbacks.onmessage(null);
  await assert.rejects(pending, { message: "message handling failed" });
  assert.equal(connections[0].closed, true);
}

async function testReplyWriteFailure() {
  const { ai, connections } = makeFakeAi();
  const pending = runOnce(ai, 0, { replyPath: suiteDir });
  await Promise.resolve();
  connections[0].callbacks.onmessage({ serverContent: { modelTurn: { parts: [{ inlineData: { data: oneSecondB64 } }] }, turnComplete: true } });
  await assert.rejects(pending, { message: "reply write failed" });
  assert.equal(connections[0].closed, true);
}

async function testSendFailure() {
  const { ai, connections } = makeFakeAi({ throwOnToolSend: true });
  const pending = runOnce(ai, 0, { timeoutMs: 300, replyPath: null }).catch((err) => err);
  const { callbacks, session } = connections[0];
  await Promise.resolve(); // Let the connect handler attach the session first.
  callbacks.onmessage({ toolCall: { functionCalls: [{ name: "get_agent_jobs", id: "call-1" }] } });
  const err = await pending;
  assert.equal(err.message, "sending tool response failed");
  assert.ok(!err.message.includes("SENTINEL"), "no raw send failure leaks");
  assert.equal(session.closed, true, "session closed on send failure");
}

async function testCloseThrowSwallowed() {
  const { ai, connections } = makeFakeAi({ throwOnClose: true });
  const pending = runOnce(ai, 0, { replyPath: null });
  const { callbacks } = connections[0];
  await Promise.resolve(); // Let the connect handler attach the session first.
  callbacks.onmessage({ toolCall: { functionCalls: [{ name: "get_agent_jobs" }] } });
  callbacks.onmessage({ serverContent: { modelTurn: { parts: [{ inlineData: { data: oneSecondB64 } }] }, turnComplete: true } });
  await pending; // A throwing close must not turn success into a failure.
}

const tests = [
  ["entrypoint guard and import behavior", testGuardAndImports],
  ["buildToolResponses accepts valid batches", testValidBatches],
  ["buildToolResponses rejects bad batches", testInvalidBatches],
  ["runOnce success: jobs, audio, reply file, settlement", testSuccessRoundTrip],
  ["runOnce success: disabled reply output", testReplyOutputDisabled],
  ["runOnce rejects unknown tool with no partial send", testUnknownToolRunNoPartialSend],
  ["runOnce rejects tool call before session ready", testToolCallBeforeReady],
  ["runOnce timeout then late connection", testTimeoutAndLateConnection],
  ["runOnce websocket error category", testWebsocketErrorCategory],
  ["runOnce early close category", testEarlyCloseCategory],
  ["runOnce connect rejection", testConnectRejection],
  ["runOnce synchronous connect failure", testSynchronousConnectFailure],
  ["runOnce prompt send failure", testPromptSendFailure],
  ["CLI validation and failures without credentials", testOfflineCliFailures],
  ["CLI successful summary without credentials", testOfflineCliSuccess],
  ["malformed message fails safely", testMalformedMessage],
  ["reply write failure closes the session", testReplyWriteFailure],
  ["runOnce send failure", testSendFailure],
  ["runOnce throwing close does not mask success", testCloseThrowSwallowed],
];

let failed = 0;
try {
  for (const [name, test] of tests) {
    try {
      await test();
      console.log(`ok - ${name}`);
    } catch (err) {
      failed += 1;
      console.log(`FAILED - ${name}: ${err?.stack ?? err}`);
    }
  }
} finally {
  process.removeListener("unhandledRejection", onUnhandled);
  rmSync(suiteDir, { recursive: true, force: true });
  assert.equal(unhandled.length, 0, `unhandled promise rejections: ${unhandled.join("; ")}`);
  assert.equal(existsSync(suiteFile), false, "selftest left no synthetic reply file behind");
  assert.equal(existsSync(defaultReplyPath), defaultReplyExisted, "selftest left the default reply file untouched");
  assert.equal(existsSync(suiteDir), false, "selftest removed its unique suite directory");
}

console.log(failed ? `${failed} failed` : `all ${tests.length} passed`);
process.exitCode = failed ? 1 : 0;
}

if (isDirectRun(import.meta.url)) {
  await main().catch((err) => {
    console.error("A3 selftest failed:", err?.stack ?? err);
    process.exitCode = 1;
  });
}
