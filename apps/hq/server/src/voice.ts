// Voice calls: a second, lightweight voice agent runs in the browser against the OpenAI Realtime API
// (the browser gets a short-lived client secret; the API key stays here), speaks as the bot, and relays real work to the bot's main text agent loop.
// This module mints the ephemeral secret, builds the voice agent's prompt and tools, serves the relay
// tools, records call start/end rows, and proxies TTS (voice preview) and STT (composer dictation).
import { Hono } from 'hono';
import { z } from 'zod';
import { readJson } from './lib/request.js';
import { now } from './db.js';
import { env } from './env.js';
import { newId, sha256 } from './lib/ids.js';
import type { AuthVars } from './lib/auth.js';
import { appendRow, emitBot, getBotRow } from './store.js';
import { jobs, roles } from './ledger-client.js';
import { canContain } from './sandbox.js';
import type { EventBody, VoiceCallRecord, VoiceOption } from './types.js';

export const voiceApi = new Hono<AuthVars>();

const OPENAI = 'https://api.openai.com/v1';
const STT_MODEL = process.env.OPENAI_STT_MODEL ?? 'gpt-transcribe';
const SAMPLE_RATE = 24000;
const headers = () => ({ Authorization: `Bearer ${env.openaiKey}` });
const NO_KEY = 'OpenAI Realtime is disabled pending the synthetic voice spend approval.';

// ---------- voices / languages ----------

const VOICES: VoiceOption[] = [
  ['cedar', 'm'], ['marin', 'f'], ['alloy', 'f'], ['ash', 'm'], ['ballad', 'm'], ['coral', 'f'], ['echo', 'm'], ['sage', 'f'], ['shimmer', 'f'], ['verse', 'm'],
].map(([id, g]) => ({ id, name: id[0].toUpperCase() + id.slice(1), gender: g === 'f' ? 'female' : 'male' }));

export const LANGUAGES: { code: string; name: string }[] = [
  { code: 'auto', name: 'Auto-detect' }, { code: 'en', name: 'English' }, { code: 'ar-EG', name: 'Arabic (Egypt)' },
  { code: 'ar-SA', name: 'Arabic (Saudi Arabia)' }, { code: 'ar-AE', name: 'Arabic (UAE)' }, { code: 'bn', name: 'Bengali' },
  { code: 'zh', name: 'Chinese' }, { code: 'fr', name: 'French' }, { code: 'de', name: 'German' }, { code: 'hi', name: 'Hindi' },
  { code: 'id', name: 'Indonesian' }, { code: 'it', name: 'Italian' }, { code: 'ja', name: 'Japanese' }, { code: 'ko', name: 'Korean' },
  { code: 'pt-BR', name: 'Portuguese (Brazil)' }, { code: 'pt-PT', name: 'Portuguese (Portugal)' }, { code: 'ru', name: 'Russian' },
  { code: 'es-MX', name: 'Spanish (Mexico)' }, { code: 'es-ES', name: 'Spanish (Spain)' }, { code: 'tr', name: 'Turkish' }, { code: 'vi', name: 'Vietnamese' },
];
export const SPEEDS = [0.7, 0.85, 1, 1.15, 1.3, 1.5];

const clampSpeed = (s: unknown) => {
  const n = Number(s);
  return Number.isFinite(n) ? Math.min(1.5, Math.max(0.7, n)) : 1;
};
const langName = (code: string) => LANGUAGES.find((l) => l.code.toLowerCase() === code?.toLowerCase())?.name;
function settingsOf(bot: any) {
  const language = langName(bot.voice_language) ? String(bot.voice_language) : 'auto';
  return { voice: VOICES.some((v) => v.id === bot.voice) ? String(bot.voice) : 'cedar', speed: clampSpeed(bot.voice_speed ?? 1), language };
}

// ---------- helpers ----------

function ownBot(userId: string, botId: string | undefined) {
  if (!botId) return null;
  const b = getBotRow(botId);
  return b && b.user_id === userId ? b : null;
}

const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

const obj = (properties: Record<string, unknown>, required: string[] = []) => ({ type: 'object', properties, required });

export const VOICE_TOOLS = [
  {
    type: 'function', name: 'delegate_task',
    description: 'Queue a synthetic task with the specialist that should handle it. Use scout for research, forge for code, quill for writing, atlas for planning, and ops for diagnostics.',
    parameters: obj({
      request: { type: 'string' },
      role: { type: 'string', enum: roles },
    }, ['request', 'role']),
  },
  { type: 'function', name: 'end_the_call', description: 'End the call after saying goodbye.', parameters: obj({}) },
];

const voiceEnabled = () => !!(env.syntheticVoice && env.openaiKey && env.ledgerToken && canContain());
const voiceInstructions = () => 'You are Jarvis in a synthetic voice test. Do not request personal information. Use delegate_task for synthetic work. Report queue acceptance only. The dashboard shows the result. Keep replies brief.';

// ---------- calls ----------

interface ActiveCall { id: string; botId: string; userId: string; startedAt: number; startSeq: number; tasks: string[] }
const calls = new Map<string, ActiveCall>();

function callEvent(text: string, call: VoiceCallRecord): EventBody {
  return { type: 'event', event: 'voice-call', text, ref: call.id, call };
}

const fmtDuration = (ms: number) => {
  const s = Math.max(1, Math.round(ms / 1000));
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`;
};

voiceApi.get('/options', (c) => c.json({ voices: VOICES, enabled: voiceEnabled(), languages: LANGUAGES, speeds: SPEEDS }));

voiceApi.post('/session', async (c) => {
  const user = c.get('user');
  const { botId } = await readJson(c, z.strictObject({ botId: z.string().min(1) }));
  const bot = ownBot(user.id, botId);
  if (!bot) return c.json({ error: 'not found' }, 404);
  if (!voiceEnabled()) return c.json({ error: NO_KEY }, 403);
  const s = settingsOf(bot);

  const r = await fetch(`${OPENAI}/realtime/client_secrets`, {
    method: 'POST',
    headers: { ...headers(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ expires_after: { anchor: 'created_at', seconds: 300 }, session: { type: 'realtime', model: env.voiceModel } }),
    signal: AbortSignal.timeout(15_000),
  }).catch(() => ({ ok: false, status: 0 }) as any);
  if (!r.ok) {
    // Status only: the provider's error text can repeat part of the key.
    console.warn('[voice] client secret mint failed', r.status);
    return c.json({ error: r.status === 401 ? 'OpenAI rejected the API key.' : 'Could not start a voice session' }, 502);
  }
  const secret = (await r.json()) as { value: string; expires_at: number };

  const instructions = voiceInstructions();
  const session: Record<string, unknown> = {
    type: 'realtime',
    output_modalities: ['audio'],
    instructions,
    tools: VOICE_TOOLS,
    tool_choice: 'auto',
    audio: {
      input: {
        format: { type: 'audio/pcm', rate: SAMPLE_RATE },
        turn_detection: { type: 'server_vad' },
        transcription: { model: STT_MODEL },
      },
      output: { format: { type: 'audio/pcm', rate: SAMPLE_RATE }, voice: s.voice, speed: s.speed },
    },
  };

  const callId = newId('call');
  const startRow = appendRow(bot.id, 'event', callEvent(`Voice call with ${bot.name} started`, { id: callId, phase: 'started' }));
  calls.set(callId, { id: callId, botId: bot.id, userId: user.id, startedAt: now(), startSeq: startRow.seq, tasks: [] });
  emitBot(bot.id);

  return c.json({
    callId,
    clientSecret: secret.value,
    expiresAt: secret.expires_at,
    model: env.voiceModel,
    websocketUrl: `wss://api.openai.com/v1/realtime?model=${encodeURIComponent(env.voiceModel)}`,
    sampleRate: SAMPLE_RATE,
    instructions,
    voice: s.voice,
    speed: s.speed,
    language: s.language,
    tools: VOICE_TOOLS,
    session,
  });
});

voiceApi.post('/tool', async (c) => {
  const user = c.get('user');
  const { botId, callId, toolCallId, name, args } = await readJson(c, z.strictObject({
    botId: z.string().min(1), callId: z.string().min(1), toolCallId: z.string().min(1).max(128).optional(), name: z.string().min(1),
    args: z.record(z.string(), z.unknown()).optional(),
  }));
  const bot = ownBot(user.id, botId);
  if (!bot) return c.json({ error: 'not found' }, 404);
  const a = args ?? {};
  const call = calls.get(callId);
  if (!voiceEnabled() || !call || call.botId !== bot.id || call.userId !== user.id) {
    return c.json({ error: 'forbidden' }, 403);
  }
  if (name === 'end_the_call' && !Object.keys(a).length) return c.json({ output: 'Hanging up.' });
  if (name !== 'delegate_task' || !toolCallId) return c.json({ error: 'invalid voice tool' }, 400);
  const parsed = z.strictObject({ request: z.string().trim().min(1).max(1000), role: z.enum(roles) }).safeParse(a);
  if (!parsed.success) return c.json({ error: 'invalid task request' }, 400);
  const { request, role } = parsed.data;
  try {
    const job = await jobs.submit(role, sha256(`${user.id}:${callId}:${toolCallId}`), request);
    return c.json({ output: `Job ${job.id} is ${job.state}. Follow ${role} in the dashboard.` });
  } catch {
    return c.json({ error: 'ledger did not accept the task' }, 400);
  }

});

voiceApi.post('/end', async (c) => {
  const user = c.get('user');
  const { botId, callId, transcript, error } = await readJson(c, z.strictObject({
    botId: z.string().min(1), callId: z.string().min(1),
    transcript: z.array(z.strictObject({ role: z.enum(['user', 'assistant']), text: z.string() })).optional(),
    error: z.string().optional(),
  }));
  const bot = ownBot(user.id, botId);
  if (!bot) return c.json({ error: 'not found' }, 404);
  const call = calls.get(callId);
  if (!call || call.botId !== bot.id) return c.json({ ok: true, duplicate: true });
  calls.delete(callId);

  const durationMs = now() - call.startedAt;
  const lines = (Array.isArray(transcript) ? transcript : [])
    .filter((t) => t && (t.role === 'user' || t.role === 'assistant') && typeof t.text === 'string' && t.text.trim())
    .slice(-200)
    .map((t) => ({ role: t.role as 'user' | 'assistant', text: clip(t.text.trim(), 2000) }));
  const base = error ? `Voice call ended · ${fmtDuration(durationMs)} · ${clip(error, 120)}` : `Voice call ended · ${fmtDuration(durationMs)}`;
  const record: VoiceCallRecord = { id: callId, phase: 'ended', durationMs, transcript: lines, tasks: call.tasks };
  const row = appendRow(bot.id, 'event', callEvent(base, record));
  emitBot(bot.id);

  return c.json({ ok: true, seq: row.seq });
});

// Calls whose tab vanished without /end: close them after 2h so the map can't grow forever.
setInterval(() => {
  for (const call of calls.values()) {
    if (now() - call.startedAt < 2 * 3600_000) continue;
    calls.delete(call.id);
    appendRow(call.botId, 'event', callEvent('Voice call ended', { id: call.id, phase: 'ended', tasks: call.tasks }));
  }
}, 10 * 60_000).unref();

// Separate paid preview and dictation routes are outside this prototype.
voiceApi.post('/preview', (c) => c.json({ error: 'Voice preview is disabled' }, 403));
voiceApi.post('/stt', (c) => c.json({ error: 'Dictation is disabled' }, 403));
