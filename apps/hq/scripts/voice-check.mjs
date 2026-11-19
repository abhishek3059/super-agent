#!/usr/bin/env node
// Opt-in, paid smoke check. Start an isolated HQ server as "Voice Check" first.
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { lstat, mkdtemp, readFile, realpath, rm } from 'node:fs/promises';
import { homedir, tmpdir } from 'node:os';
import { isAbsolute, join, resolve, sep } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { promisify } from 'node:util';
import { ownerLogin } from './owner-login.mjs';

const exec = promisify(execFile);
const ownerName = 'Voice Check';
const request = 'Ask Scout to open example dot com and tell me the page heading';
const scopedRequest = 'Ask Scout to open https://example.com and tell me the page heading.';
const heading = 'Example Domain';
const silence = Buffer.alloc(48_000);
const frameBytes = 960; // 20 ms at 24 kHz, mono PCM16.
const toolName = 'send_task';

class CheckFailure extends Error {}
function check(condition, state) {
  if (!condition) throw new CheckFailure(state);
}

function wavePcm(wave) {
  check(wave.length >= 12 && wave.toString('ascii', 0, 4) === 'RIFF'
    && wave.toString('ascii', 8, 12) === 'WAVE', 'invalid WAVE container');
  let matchingFormat = false;
  for (let offset = 12; offset + 8 <= wave.length;) {
    const kind = wave.toString('ascii', offset, offset + 4);
    const length = wave.readUInt32LE(offset + 4);
    const start = offset + 8;
    const end = start + length;
    check(end <= wave.length, 'truncated WAVE chunk');
    if (kind === 'fmt ' && length >= 16) {
      matchingFormat = wave.readUInt16LE(start) === 1 && wave.readUInt16LE(start + 2) === 1
        && wave.readUInt32LE(start + 4) === 24_000 && wave.readUInt16LE(start + 14) === 16;
    }
    if (kind === 'data') {
      check(matchingFormat && length >= frameBytes && length <= 480_000 && length % 2 === 0,
        'expected bounded 24 kHz mono PCM16');
      return wave.subarray(start, end);
    }
    offset = end + (length % 2);
  }
  throw new CheckFailure('WAVE data chunk missing');
}

async function synthesize(directory, name, phrase, signal) {
  const aiff = join(directory, name + '.aiff');
  const wave = join(directory, name + '.wav');
  await exec('/usr/bin/say', ['-v', 'Samantha', '-o', aiff, phrase], { signal });
  await exec('/usr/bin/afconvert', ['-f', 'WAVE', '-d', 'LEI16@24000', '-c', '1', aiff, wave], { signal });
  return wavePcm(await readFile(wave));
}

function approvedCall(event) {
  check(event?.name === toolName && typeof event.call_id === 'string'
    && typeof event.arguments === 'string' && event.arguments.length <= 1024, 'expected one bounded send_task call');
  let args;
  try { args = JSON.parse(event.arguments); } catch { throw new CheckFailure('invalid send_task arguments'); }
  const text = args?.request;
  check(typeof text === 'string' && /\bscout\b/i.test(text) && /\bexample\s*(?:\.|dot)\s*com\b/i.test(text)
    && /\b(?:heading|header|h1|title)\b/i.test(text), 'send_task did not match the synthetic request');
  // Match the intent, then send only the authorized literal to the worker.
  return { request: scopedRequest, already_announced: args.already_announced === true };
}

const mentionsHeading = (text) => typeof text === 'string' && /\bexample\s+domain\b/i.test(text);
const message = (row, role, kind, id) => row.body.type === 'message' && row.body.role === role
  && row.body.from?.kind === kind && row.body.from?.id === id;

async function run() {
  const start = performance.now();
  let stage = 'preflight';
  const state = (label) => {
    stage = label;
    console.log(`[${Math.round(performance.now() - start)} ms] ${label}`);
  };
  const signal = AbortSignal.timeout(84_000);
  setTimeout(() => { state('FAIL hard deadline'); process.exit(1); }, 90_000).unref();
  let directory, req, socket, botId, callId;
  let failed = false;
  try {
    check(process.platform === 'darwin' && typeof WebSocket === 'function', 'macOS and Node 22 required');
    const configured = process.env.HQ_DATA_DIR ?? '';
    check(isAbsolute(configured), 'set HQ_DATA_DIR to a fresh isolated HQ directory');
    const dataDir = await realpath(configured);
    const normalDir = join(await realpath(homedir()), '.super-agent', 'hq');
    const repo = resolve(import.meta.dirname, '../../..');
    check(dataDir !== normalDir && !dataDir.startsWith(normalDir + sep)
      && dataDir !== repo && !dataDir.startsWith(repo + sep), 'HQ_DATA_DIR must be outside the default HQ and the checkout');
    const dataStat = await lstat(dataDir);
    check(dataStat.isDirectory() && (dataStat.mode & 0o777) === 0o700
      && dataStat.uid === process.getuid(), 'expected an owner-only HQ directory');

    const port = Number(process.env.PORT ?? 8787);
    check(Number.isInteger(port) && port > 0 && port <= 65_535, 'invalid HQ port');
    const origin = `http://127.0.0.1:${port}`;
    const fetchHq = (path, options = {}) => fetch(origin + path, { redirect: 'manual', signal, ...options });

    directory = await mkdtemp(join(tmpdir(), 'hq-voice-check-'));
    const firstClip = await synthesize(directory, 'request', request, signal);
    const secondClip = await synthesize(directory, 'interruption', 'Wait, please stop talking for a moment.', signal);
    state('synthetic PCM ready');

    const signedInAfter = Date.now();
    const link = new URL(await ownerLogin(origin, dataDir, signal));
    const signIn = await fetchHq(link.pathname, { headers: { Accept: 'application/json' } });
    check(signIn.status === 200, `HQ owner link redemption HTTP ${signIn.status}`);
    const { token } = await signIn.json();
    check(typeof token === 'string' && /^[\w.-]{32,512}$/.test(token), 'HQ did not return an owner bearer token');
    req = async (path, { method, body, cleanup = false } = {}) => {
      const headers = { Authorization: `Bearer ${token}` };
      if (body) headers['Content-Type'] = 'application/json';
      const response = await fetchHq(path, { method, headers, body: body && JSON.stringify(body),
        signal: cleanup ? AbortSignal.timeout(2500) : signal });
      check(response.ok, `HQ ${path.startsWith('/api/voice/') ? path : 'local request'} HTTP ${response.status}`);
      return response.json();
    };
    const { user } = await req('/api/auth/me');
    check(user?.name === ownerName && user.email === 'owner@localhost', 'HQ owner must be Voice Check');

    const { bots, live } = await req('/api/bots');
    check(bots.map((bot) => bot.name).sort().join(',') === 'Atlas,Forge,Jarvis,Quill,Scout'
      && bots.every((bot) => bot.kind === 'agent' && bot.generation === 1 && bot.createdAt >= signedInAfter
        && !bot.instructions && !live[bot.id]?.isRunning), 'expected an idle, fresh default HQ team');
    const jarvis = bots.find((bot) => bot.name === 'Jarvis');
    const scout = bots.find((bot) => bot.name === 'Scout');
    botId = jarvis.id;
    const botPath = (id, suffix) => `/api/bots/${encodeURIComponent(id)}/${suffix}`;
    const rowsFor = async (id) => (await req(botPath(id, 'rows'))).rows;
    for (const bot of bots) {
      const [rows, { memories }, { routines }, { tasks }] = await Promise.all([
        rowsFor(bot.id), req(botPath(bot.id, 'memories')), req(botPath(bot.id, 'routines')), req(botPath(bot.id, 'tasks')),
      ]);
      check(!rows.length && !memories.length && !routines.length && !tasks.length, 'expected empty HQ conversations and state');
    }
    state('fresh synthetic owner and team verified');

    stage = 'mint Realtime session';
    const sessionResult = await req('/api/voice/session', { method: 'POST', body: { botId } });
    ({ callId } = sessionResult);
    const { websocketUrl, clientSecret, model, session, sampleRate } = sessionResult;
    check(sampleRate === 24_000 && /^[a-z0-9.-]+$/.test(model)
      && websocketUrl === `wss://api.openai.com/v1/realtime?model=${model}`
      && typeof clientSecret === 'string' && clientSecret.length > 0, 'unexpected Realtime session parameters');
    check(session.audio.input.turn_detection.type === 'server_vad'
      && session.audio.input.turn_detection.interrupt_response === false, 'expected manual cancellation with server VAD');
    state('ephemeral session minted');

    socket = new WebSocket(websocketUrl, ['realtime', `openai-insecure-api-key.${clientSecret}`]);
    const events = [];
    let socketFailure = '';
    let cursor = 0;
    socket.addEventListener('message', ({ data }) => {
      try {
        if (events.length >= 6000) throw new Error();
        const event = JSON.parse(data);
        if (event.type === 'error') {
          // OpenAI error descriptions can contain sensitive values.
          const code = event.error?.code;
          socketFailure = ['invalid_value', 'invalid_request_error', 'model_not_found', 'rate_limit_exceeded',
            'response_cancel_not_active', 'session_expired', 'unknown_parameter'].includes(code)
            ? `Realtime error ${code}` : 'Realtime error';
        }
        events.push(event);
      } catch {
        socketFailure = 'invalid or excessive Realtime events';
      }
    });
    socket.addEventListener('error', () => { socketFailure ||= 'Realtime socket error'; });
    socket.addEventListener('close', () => { socketFailure ||= 'Realtime socket closed'; });
    const healthy = () => check(!socketFailure, socketFailure);
    const send = (event) => {
      healthy();
      check(socket.readyState === WebSocket.OPEN, 'Realtime socket not open');
      socket.send(JSON.stringify(event));
    };
    const take = async (predicate) => {
      while (true) {
        signal.throwIfAborted();
        healthy();
        while (cursor < events.length) {
          const event = events[cursor++];
          if (predicate(event)) return event;
        }
        await delay(20, undefined, { signal });
      }
    };
    const sendClip = async (clip) => {
      for (let offset = 0; offset < clip.length; offset += frameBytes) {
        signal.throwIfAborted();
        send({ type: 'input_audio_buffer.append', audio: clip.subarray(offset, offset + frameBytes).toString('base64') });
        await delay(20, undefined, { signal });
      }
    };

    await take((event) => event.type === 'session.created');
    send({ type: 'session.update', session });
    await take((event) => event.type === 'session.updated');
    state('Realtime session updated');
    await sendClip(Buffer.concat([firstClip, silence]));
    state('synthetic request streamed');

    const tool = await take((event) => event.type === 'response.function_call_arguments.done');
    const completed = await take((event) => event.type === 'response.done' && event.response?.id === tool.response_id);
    const functionCalls = completed.response.output?.filter((item) => item.type === 'function_call') ?? [];
    check(completed.response.status === 'completed' && functionCalls.length === 1
      && functionCalls[0].call_id === tool.call_id && functionCalls[0].arguments === tool.arguments,
    'send_task response did not finish with a single matching call');
    const args = approvedCall(tool);
    const task = await req('/api/voice/tool', { method: 'POST', body: { botId, callId, name: toolName, args } });
    check(Number.isSafeInteger(task.taskSeq) && typeof task.output === 'string', 'send_task relay did not return a task');
    send({ type: 'conversation.item.create', item: { type: 'function_call_output', call_id: tool.call_id, output: task.output } });
    const voiceRow = (await rowsFor(botId)).find((row) => row.seq === task.taskSeq);
    check(voiceRow && message(voiceRow, 'user', 'voice', callId) && voiceRow.body.text === scopedRequest,
      'voice-sourced Jarvis message missing');
    state('send_task relayed and voice-sourced Jarvis message verified');

    let scoutHandoff = false;
    let scoutResult;
    let jarvisResult;
    state('waiting for Scout handoff and result');
    while (!jarvisResult) {
      healthy();
      const [jarvisRows, scoutRows] = await Promise.all([rowsFor(botId), rowsFor(scout.id)]);
      const delegated = scoutRows.find((row) => message(row, 'user', 'bot', botId));
      if (delegated && !scoutHandoff) {
        scoutHandoff = true;
        state('Jarvis handoff in Scout chat verified');
      }
      scoutResult = delegated && jarvisRows.find((row) => row.seq > task.taskSeq
        && message(row, 'user', 'bot', scout.id) && mentionsHeading(row.body.text));
      jarvisResult = scoutResult && jarvisRows.find((row) => row.seq > scoutResult.seq && row.body.type === 'message'
        && row.body.role === 'assistant' && !row.body.streaming && mentionsHeading(row.body.text));
      if (!jarvisResult) await delay(350, undefined, { signal });
    }
    state('Scout returned the heading and Jarvis replied');

    send({ type: 'conversation.item.create', item: { type: 'message', role: 'user',
      content: [{ type: 'input_text', text: `[work_landed] Scout confirmed the heading is "${heading}". Tell the caller.` }] } });
    send({ type: 'response.create', response: { tool_choice: 'none' } });
    const spoken = await take((event) => event.type === 'response.output_audio.delta' && event.delta);
    const caption = await take((event) => event.type === 'response.output_audio_transcript.done'
      && event.response_id === spoken.response_id);
    const spokenDone = await take((event) => event.type === 'response.done' && event.response?.id === spoken.response_id);
    check(spokenDone.response.status === 'completed' && mentionsHeading(caption.transcript), 'spoken response did not complete with the heading');
    state('spoken Scout result verified');

    // A deliberately long turn keeps generation active while the second clip reaches server VAD.
    send({ type: 'response.create', response: { tool_choice: 'none',
      instructions: 'Count aloud slowly and clearly from one to fifty. Say every number in full. Start immediately.' } });
    const interrupted = await take((event) => event.type === 'response.output_audio.delta' && event.delta);
    check(interrupted.response_id !== spoken.response_id, 'missing new audio response to interrupt');

    let terminalIndex;
    await Promise.all([sendClip(Buffer.concat([secondClip, silence])), (async () => {
      const speech = await take((event) => event.type === 'input_audio_buffer.speech_started'
        || (event.type === 'response.done' && event.response?.id === interrupted.response_id));
      check(speech.type === 'input_audio_buffer.speech_started', 'response ended before synthetic speech_started');
      state('interruption speech_started received');
      send({ type: 'response.cancel', response_id: interrupted.response_id });
      state('response.cancel sent');
      const cancelled = await take((event) => event.type === 'response.done' && event.response?.id === interrupted.response_id);
      check(cancelled.response.status === 'cancelled', 'Realtime did not confirm cancelled status');
      terminalIndex = cursor;
    })()]);
    await delay(800, undefined, { signal });
    healthy();
    check(!events.slice(terminalIndex).some((event) => event.response_id === interrupted.response_id
      && event.type === 'response.output_audio.delta'), 'audio continued after cancellation acknowledgement');
    state('cancellation confirmed with no further audio from that response');
  } catch (error) {
    failed = true;
    const reason = error instanceof CheckFailure ? error.message
      : signal.aborted ? 'deadline reached' : 'local I/O or event failure';
    state(`FAIL ${stage} (${reason})`);
  } finally {
    socket?.close();
    if (callId) {
      try {
        const ended = await req('/api/voice/end', { method: 'POST', body: { botId, callId, transcript: [] }, cleanup: true });
        check(ended.ok && Number.isSafeInteger(ended.seq), 'voice end record missing');
        state('voice call ended');
      } catch (error) {
        failed = true;
        state(`FAIL end call (${error instanceof CheckFailure ? error.message : 'local I/O failure'})`);
      }
    }
    if (directory) await rm(directory, { recursive: true, force: true });
  }
  if (failed) process.exitCode = 1;
  else state('PASS');
}

async function selfCheck() {
  const directory = await mkdtemp(join(tmpdir(), 'hq-voice-self-check-'));
  try {
    assert.ok((await synthesize(directory, 'request', request, AbortSignal.timeout(5000))).length >= frameBytes);
    assert.throws(() => wavePcm(Buffer.alloc(32)), CheckFailure);
    const call = { name: toolName, call_id: 'synthetic', arguments: JSON.stringify({ request: scopedRequest }) };
    assert.equal(approvedCall(call).request, scopedRequest);
    assert.throws(() => approvedCall({ ...call, arguments: '{"request":"browse another site"}' }), CheckFailure);
    assert.ok(mentionsHeading('The heading reads Example Domain.'));
    assert.ok(!mentionsHeading('The heading reads Example Domains.'));
    console.log('PASS offline synthetic-audio and request checks');
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

try {
  if (process.argv.includes('--self-check')) await selfCheck();
  else await run();
} catch {
  console.error('FAIL local check or cleanup');
  process.exitCode = 1;
}
