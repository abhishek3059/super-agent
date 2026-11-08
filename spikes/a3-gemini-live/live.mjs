// Spike A3: measure Gemini Live latency with one tool call, using text input
// and synthetic job data only (no microphone, no personal context).
// Key: GEMINI_API_KEY env var, or ~/.super-agent/gemini-key (mode 0600). Never logged.
import { GoogleGenAI, Modality } from "@google/genai";
import { readFileSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { isDirectRun } from "../entrypoint.mjs";

const MODEL = process.env.SUPER_AGENT_LIVE_MODEL ?? "gemini-3.8-live";
const RUNS = Number(process.env.SUPER_AGENT_RUNS ?? 5);
const PROMPT = "What are my agent jobs doing right now?";
const TOOL_NAME = "get_agent_jobs";
const MAX_TOOL_CALLS = 16;
const MAX_TOOL_ID_CHARS = 256;
const THIRTY_S_MS = 30_000;
const AUDIO_BYTES_PER_SEC = 24_000 * 2; // 24 kHz, 16-bit mono PCM output
const DEFAULT_REPLY_PATH = () => join(tmpdir(), "super-agent-a3-reply.pcm");

// Synthetic ledger snapshot; stands in for the A2 approval server's pending list.
export const JOBS = [
  { id: "job-1", agent: "claude-code", task: "refactor auth module", state: "running", step: "editing src/auth.ts" },
  { id: "job-2", agent: "claude-code", task: "fix flaky test", state: "waiting_for_approval", pending: "Bash: npm test" },
];

const tools = [
  {
    functionDeclarations: [
      {
        name: "get_agent_jobs",
        description: "List the user's background agent jobs with their current state.",
        parameters: { type: "OBJECT", properties: {} },
      },
    ],
  },
];

// Fixed failure categories. Provider error text, close reasons, URLs, and
// credential values must never reach a log line, so every reject uses one of these.
const BATCH_ERRORS = new Set([
  "malformed tool call batch",
  "empty tool call batch",
  "too many tool calls",
  "unsupported tool call",
  "invalid tool call arguments",
  "invalid tool call id",
  "duplicate tool call id",
]);

const isPlainObject = (v) => typeof v === "object" && v !== null && !Array.isArray(v) && [Object.prototype, null].includes(Object.getPrototypeOf(v));

function readKey() {
  if (process.env.GEMINI_API_KEY) return process.env.GEMINI_API_KEY;
  return readFileSync(join(homedir(), ".super-agent", "gemini-key"), "utf8").trim();
}

// Validate the complete tool-call batch before any response is sent. Returns
// the sendToolResponse payload; throws a fixed category on the first bad call.
export function buildToolResponses(functionCalls) {
  if (!Array.isArray(functionCalls)) throw new Error("malformed tool call batch");
  if (functionCalls.length === 0) throw new Error("empty tool call batch");
  if (functionCalls.length > MAX_TOOL_CALLS) throw new Error("too many tool calls");

  const seenIds = new Set();
  const functionResponses = functionCalls.map((fc) => {
    if (!isPlainObject(fc)) throw new Error("malformed tool call batch");
    if (fc.name !== TOOL_NAME) throw new Error("unsupported tool call");
    if (!(fc.args === undefined || (isPlainObject(fc.args) && Object.keys(fc.args).length === 0))) {
      throw new Error("invalid tool call arguments");
    }
    if (fc.id !== undefined) {
      if (typeof fc.id !== "string" || fc.id.length < 1 || fc.id.length > MAX_TOOL_ID_CHARS) {
        throw new Error("invalid tool call id");
      }
      if (seenIds.has(fc.id)) throw new Error("duplicate tool call id");
      seenIds.add(fc.id);
    }
    return { id: fc.id, name: fc.name, response: { jobs: JOBS } };
  });
  return { functionResponses };
}

const median = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
};

export async function runOnce(ai, i, options = {}) {
  const { timeoutMs = THIRTY_S_MS, replyPath = DEFAULT_REPLY_PATH() } = options;
  const t = { start: performance.now() };
  const audio = [];
  let transcript = "";
  let toolArgs;
  let session;
  let timer;
  let settled = false;
  let closed = false;

  // Close at most once; a throwing close must not mask the real outcome. A
  // timeout with no session yet must not block closing a late connection.
  const closeSession = () => {
    const s = session;
    session = undefined;
    if (!s || closed) return;
    closed = true;
    try {
      s.close();
    } catch {
      // Closing an already dead session must not escape as an exception.
    }
  };

  const done = new Promise((resolve, reject) => {
    const fail = (category) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      closeSession();
      reject(new Error(category));
    };
    timer = setTimeout(() => fail(`timed out after ${timeoutMs}ms`), timeoutMs);

    const handleToolCall = (msg) => {
      if (!session) {
        fail("tool call before session ready");
        return;
      }
      t.toolCall ??= performance.now();
      let batch;
      try {
        batch = buildToolResponses(msg.toolCall.functionCalls);
      } catch (err) {
        fail(BATCH_ERRORS.has(err?.message) ? err.message : "malformed tool call batch");
        return;
      }
      toolArgs = batch.functionResponses.map((r) => r.name);
      try {
        session.sendToolResponse(batch);
      } catch {
        fail("sending tool response failed");
        return;
      }
      t.toolSent = performance.now();
    };

    const callbacks = {
      onmessage: (msg) => {
        if (settled) return; // Ignore events after settlement.
        try {
          if (msg.setupComplete) t.setup = performance.now();
          if (msg.toolCall) handleToolCall(msg);
          if (settled) return;
          const sc = msg.serverContent;
          for (const part of sc?.modelTurn?.parts ?? []) {
            if (part.inlineData?.data) {
              t.firstAudio ??= performance.now();
              audio.push(Buffer.from(part.inlineData.data, "base64"));
            }
          }
          if (sc?.outputTranscription?.text) transcript += sc.outputTranscription.text;
          // The tool-call turn completes before the spoken reply; wait for the turn that carries audio.
          if (sc?.turnComplete && audio.length) {
            t.turnComplete = performance.now();
            settled = true;
            clearTimeout(timer);
            resolve();
          }
        } catch {
          fail("message handling failed");
        }
      },
      // Provider error/close objects carry raw detail; emit fixed categories only.
      onerror: () => fail("websocket error"),
      onclose: () => fail("connection closed early"),
    };

    try {
      ai.live
      .connect({ model: MODEL, callbacks, config: { responseModalities: [Modality.AUDIO], tools, outputAudioTranscription: {} } })
      .then((s) => {
        if (settled) {
          session = s;
          closeSession(); // Late connection: close it, send nothing.
          return;
        }
        session = s;
        t.connected = performance.now();
        t.sent = performance.now();
        try {
          s.sendClientContent({ turns: [{ role: "user", parts: [{ text: PROMPT }] }], turnComplete: true });
        } catch {
          fail("sending prompt failed");
        }
      }, () => {
        if (!settled) fail("connect failed");
      }).catch(() => fail("connect failed"));
    } catch {
      fail("connect failed");
    }
  });

  try {
    await done;
  } finally {
    closeSession();
  }

  const pcm = Buffer.concat(audio);
  if (i === 0 && replyPath) {
    try {
      writeFileSync(replyPath, pcm);
    } catch {
      throw new Error("reply write failed");
    }
  }
  const ms = (a, b) => (t[a] && t[b] ? Math.round(t[b] - t[a]) : null);
  return {
    connectMs: ms("start", "connected"),
    toolCallMs: ms("sent", "toolCall"),
    firstAudioAfterToolMs: ms("toolSent", "firstAudio"),
    firstAudioMs: ms("sent", "firstAudio"),
    totalMs: ms("sent", "turnComplete"),
    audioSec: +(pcm.length / AUDIO_BYTES_PER_SEC).toFixed(1),
    toolCalled: toolArgs?.join(",") ?? "none",
    transcript: transcript.trim(),
  };
}

// Dependencies are injectable so CLI failure paths can be tested without a key.
export async function runCli({ runs = RUNS, createClient = () => new GoogleGenAI({ apiKey: readKey() }), run = runOnce, log = console.log, error = console.error } = {}) {
  if (!Number.isInteger(runs) || runs < 1) {
    error("SUPER_AGENT_RUNS must be a finite positive integer");
    return 1;
  }
  let ai;
  try {
    ai = createClient();
  } catch {
    error("Gemini client setup failed; check your external key configuration");
    return 1;
  }
  const results = [];
  let firstReplySaved = false;
  for (let i = 0; i < runs; i++) {
    try {
      const r = await run(ai, i);
      results.push(r);
      if (i === 0) firstReplySaved = true;
      log(`run ${i + 1}:`, JSON.stringify(r));
    } catch {
      log(`run ${i + 1}: FAILED experiment run failed`);
    }
  }
  const ok = results.filter((r) => r.firstAudioMs != null);
  if (ok.length) {
    const summary = Object.fromEntries(
      ["connectMs", "toolCallMs", "firstAudioAfterToolMs", "firstAudioMs", "totalMs", "audioSec"].map((k) => [k, median(ok.map((r) => r[k]).filter((v) => v != null))]),
    );
    log(`\nmodel ${MODEL}, ${ok.length}/${runs} runs ok, medians:`, JSON.stringify(summary));
    log(`tool called in ${results.filter((r) => r.toolCalled !== "none").length}/${results.length} runs`);
    if (firstReplySaved) log(`first reply audio saved to ${join(tmpdir(), "super-agent-a3-reply.pcm")} (play: ffplay -f s16le -ar 24000 -ac 1 <file>)`);
    return 0;
  }
  return 1;
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await runCli();
}
