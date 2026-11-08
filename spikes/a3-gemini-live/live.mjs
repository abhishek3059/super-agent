// Spike A3: measure Gemini Live latency with one tool call, using text input
// and synthetic job data only (no microphone, no personal context).
// Key: GEMINI_API_KEY env var, or ~/.super-agent/gemini-key (mode 0600). Never logged.
import { GoogleGenAI, Modality } from "@google/genai";
import { readFileSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";

const MODEL = process.env.SUPER_AGENT_LIVE_MODEL ?? "gemini-3.8-live";
const RUNS = Number(process.env.SUPER_AGENT_RUNS ?? 5);
const PROMPT = "What are my agent jobs doing right now?";
const AUDIO_BYTES_PER_SEC = 24_000 * 2; // 24 kHz, 16-bit mono PCM output

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

function readKey() {
  if (process.env.GEMINI_API_KEY) return process.env.GEMINI_API_KEY;
  return readFileSync(join(homedir(), ".super-agent", "gemini-key"), "utf8").trim();
}

const median = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
};

async function runOnce(ai, i) {
  const t = { start: performance.now() };
  const audio = [];
  let transcript = "";
  let toolArgs;
  let session;

  const done = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timed out after 30s")), 30_000);
    const callbacks = {
      onmessage: (msg) => {
        if (msg.setupComplete) t.setup = performance.now();
        if (msg.toolCall) {
          t.toolCall ??= performance.now();
          const fcs = msg.toolCall.functionCalls ?? [];
          toolArgs = fcs.map((fc) => fc.name);
          session.sendToolResponse({
            functionResponses: fcs.map((fc) => ({ id: fc.id, name: fc.name, response: { jobs: JOBS } })),
          });
          t.toolSent = performance.now();
        }
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
          clearTimeout(timer);
          resolve();
        }
      },
      onerror: (e) => (clearTimeout(timer), reject(new Error(e.message ?? "websocket error"))),
      onclose: (e) => !t.turnComplete && (clearTimeout(timer), reject(new Error(`closed: ${e.code} ${e.reason}`))),
    };
    ai.live
      .connect({ model: MODEL, callbacks, config: { responseModalities: [Modality.AUDIO], tools, outputAudioTranscription: {} } })
      .then((s) => {
        session = s;
        t.connected = performance.now();
        t.sent = performance.now();
        s.sendClientContent({ turns: [{ role: "user", parts: [{ text: PROMPT }] }], turnComplete: true });
      }, reject);
  });

  try {
    await done;
  } finally {
    session?.close();
  }

  const pcm = Buffer.concat(audio);
  if (i === 0) writeFileSync(join(tmpdir(), "super-agent-a3-reply.pcm"), pcm);
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

if (import.meta.url === `file://${process.argv[1]}`) {
  const ai = new GoogleGenAI({ apiKey: readKey() });
  const results = [];
  for (let i = 0; i < RUNS; i++) {
    try {
      const r = await runOnce(ai, i);
      results.push(r);
      console.log(`run ${i + 1}:`, JSON.stringify(r));
    } catch (err) {
      console.log(`run ${i + 1}: FAILED ${err.message}`);
    }
  }
  const ok = results.filter((r) => r.firstAudioMs != null);
  if (ok.length) {
    const summary = Object.fromEntries(
      ["connectMs", "toolCallMs", "firstAudioAfterToolMs", "firstAudioMs", "totalMs", "audioSec"].map((k) => [k, median(ok.map((r) => r[k]).filter((v) => v != null))]),
    );
    console.log(`\nmodel ${MODEL}, ${ok.length}/${RUNS} runs ok, medians:`, JSON.stringify(summary));
    console.log(`tool called in ${results.filter((r) => r.toolCalled !== "none").length}/${results.length} runs`);
    console.log(`first reply audio saved to ${join(tmpdir(), "super-agent-a3-reply.pcm")} (play: ffplay -f s16le -ar 24000 -ac 1 <file>)`);
  }
}
