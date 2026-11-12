// Service-level self-test for VoiceSessionService. No test framework is
// added: the pinned `typescript` package transpiles the real service sources,
// `@angular/core` is the genuine Angular runtime already installed (real
// signal behavior), and the WebSocket, AudioContext, and getUserMedia
// environments are hand-written fakes below. Every promise is controlled;
// there are no sleeps, only microtask flushes.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { basename, dirname, join, resolve } from 'node:path';
import vm from 'node:vm';
import ts from 'typescript';

const srcDir = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'app');

const compilerOptions = {
  module: ts.ModuleKind.CommonJS,
  target: ts.ScriptTarget.ES2020,
  experimentalDecorators: true,
};

// The environment a test selects. Each test begins with beginTest().
const env = {
  sockets: [],
  contexts: [],
  processors: [],
  micCalls: 0,
  getUserMedia: null,
  deferContextClose: false,
  // Audio-context close failure modes (F1): a true close() throws
  // synchronously; a rejecting close() rejects; both are deterministic.
  throwOnClose: false,
  closeReject: false,
  // Capture factory failure modes (F2).
  failSourceCreate: false,
  failProcessorCreate: false,
  // Suspended-context resume controls (F5).
  initialContextState: 'running',
  deferResume: false,
  rejectResume: false,
};
let current = env;

class FakeTrack {
  constructor(id) {
    this.id = id;
    this.enabled = true;
    this.stopped = false;
  }
  stop() { this.stopped = true; }
}

function fakeStream() {
  const track = new FakeTrack('mic-1');
  return {
    track,
    getAudioTracks: () => [track],
    getTracks: () => [track],
  };
}

class FakeWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  constructor(url) {
    this.url = url;
    this.binaryType = 'blob';
    this.readyState = FakeWebSocket.CONNECTING;
    this.sent = [];
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;
    current.sockets.push(this);
  }
  send(data) {
    assert.equal(this.readyState, FakeWebSocket.OPEN, 'send on a non-open socket');
    this.sent.push(data);
  }
  close() {
    if (this.readyState < FakeWebSocket.CLOSING) this.readyState = FakeWebSocket.CLOSED;
  }
  // Test controls.
  open() {
    if (this.readyState === FakeWebSocket.CONNECTING) {
      this.readyState = FakeWebSocket.OPEN;
      this.onopen?.();
    }
  }
  fireMessage(data) {
    // JSON messages and binary frames are delivered the way the browser does:
    // plain wire objects are stringified, strings and raw buffers pass as-is.
    const isBinary = data instanceof ArrayBuffer || ArrayBuffer.isView(data);
    this.onmessage?.({ data: (isBinary || typeof data === 'string') ? data : JSON.stringify(data) });
  }
  fireError() { this.onerror?.(new Error('fake transport error')); }
  fireClose() {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.();
  }
  lastText() {
    const texts = this.sent.filter((frame) => typeof frame === 'string');
    return JSON.parse(texts.at(-1) ?? '{}');
  }
  countText(type) {
    return this.sent
      .filter((frame) => typeof frame === 'string')
      .filter((frame) => JSON.parse(frame).type === type).length;
  }
  countBinary() {
    return this.sent.filter((frame) => typeof frame !== 'string').length;
  }
}

class FakeAudioContext {
  constructor(options) {
    this.sampleRate = options?.sampleRate ?? 48000;
    this.state = current.initialContextState;
    this.destination = { kind: 'destination' };
    this.buffers = [];
    this.sources = [];
    current.contexts.push(this);
  }
  createMediaStreamSource(stream) {
    if (current.failSourceCreate) throw new Error('fake source factory failure');
    return { connect() { /* fake graph */ } };
  }
  createScriptProcessor() {
    if (current.failProcessorCreate) throw new Error('fake processor factory failure');
    const node = {
      onaudioprocess: null,
      connect() { /* fake graph */ },
      disconnect() { /* fake graph */ },
    };
    current.processors.push(node);
    return node;
  }
  currentTime = 0;
  createBuffer(channels, length, rate) {
    const buffer = {
      numberOfChannels: channels,
      length,
      sampleRate: rate,
      duration: length / rate,
      getChannelData: () => new Float32Array(length),
    };
    this.buffers.push(buffer);
    return buffer;
  }
  createBufferSource() {
    const source = {
      buffer: null,
      onended: null,
      started: false,
      stopped: false,
      connect() { /* fake graph */ },
      start(at) { this.started = true; this.startedAt = at; },
      stop() { this.stopped = true; this.onended?.(); },
    };
    this.sources.push(source);
    return source;
  }
  close() {
    if (current.throwOnClose) throw new Error('fake sync close failure');
    if (this.state === 'closed') return Promise.resolve();
    if (current.closeReject) {
      this.state = 'closed';
      return Promise.reject(new Error('fake async close failure'));
    }
    if (!current.deferContextClose) {
      this.state = 'closed';
      return Promise.resolve();
    }
    const deferred = defer();
    this.state = 'closing';
    this.finishClose = () => {
      this.state = 'closed';
      deferred.resolve();
    };
    return deferred.promise;
  }
  resume() {
    assert.notEqual(this.state, 'closed', 'resume on a closed context');
    if (this.state === 'running') return Promise.resolve();
    if (current.rejectResume) {
      return Promise.reject(new Error('fake resume denied'));
    }
    if (current.deferResume) {
      const deferred = defer();
      this.finishResume = () => {
        this.state = 'running';
        deferred.resolve();
      };
      this.denyResume = () => deferred.reject(new Error('fake denied later'));
      this.state = 'resuming';
      return deferred.promise;
    }
    this.state = 'running';
    return Promise.resolve();
  }
}

function proxyClass(kind) {
  const pick = () => (kind === 'ws' ? FakeWebSocket : FakeAudioContext);
  return new Proxy(function fakeClass() { /* only reached via the "new" trap */ }, {
    construct: (_target, args) => new (pick())(...args),
    get: (_target, prop) => pick()[prop],
  });
}

const browserGlobals = {
  WebSocket: proxyClass('ws'),
  AudioContext: proxyClass('ctx'),
  navigator: {
    get mediaDevices() {
      return {
        getUserMedia: (constraints) => {
          current.micCalls += 1;
          assert.ok(current.getUserMedia, 'unexpected getUserMedia call');
          return current.getUserMedia(constraints);
        },
      };
    },
  },
};

// Load the real sources with real Angular signals, relative sibling imports,
// and the fake browser environment bound as wrapper parameters.
const angularCore = await import('@angular/core');
const moduleCache = new Map();
function loadModule(file) {
  const key = join(srcDir, file);
  if (moduleCache.has(key)) return moduleCache.get(key);
  const code = ts.transpileModule(readFileSync(key, 'utf8'), { compilerOptions }).outputText;
  const factory = vm.runInThisContext(
    `(function (require, module, exports, WebSocket, AudioContext, navigator) {\n${code}\n})`,
    { filename: key },
  );
  const moduleObj = { exports: {} };
  const requireShim = (request) => {
    if (request === '@angular/core') return angularCore;
    assert.ok(request.startsWith('.'), `unexpected bare import: ${request}`);
    return loadModule(`${basename(request)}.ts`);
  };
  factory(requireShim, moduleObj, moduleObj.exports, browserGlobals.WebSocket,
    browserGlobals.AudioContext, browserGlobals.navigator);
  moduleCache.set(key, moduleObj.exports);
  return moduleObj.exports;
}
const { VoiceSessionService } = loadModule('voice-session.service.ts');

// ---------- helpers ----------
const TOKEN = 'x'.repeat(40);
const READY = {
  type: 'session.ready', playbackEpoch: 0, outputRateHz: 16000, provider: 'fake',
};
const chunk = (rate, epoch) => ({
  type: 'audio.chunk', playbackEpoch: epoch, rateHz: rate, channels: 1, format: 'pcm16',
});
const flushed = async () => {
  for (let i = 0; i < 25; i += 1) await Promise.resolve();
};
function defer() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}
let casesRun = 0;
function beginTest(name) {
  for (const list of [env.sockets, env.contexts, env.processors]) list.length = 0;
  env.micCalls = 0;
  env.getUserMedia = null;
  env.deferContextClose = false;
  env.throwOnClose = false;
  env.closeReject = false;
  env.failSourceCreate = false;
  env.failProcessorCreate = false;
  env.initialContextState = 'running';
  env.deferResume = false;
  env.rejectResume = false;
  current = env;
  casesRun += 1;
  return name;
}
const lastSocket = () => {
  assert.ok(env.sockets.length, 'no socket was created');
  return env.sockets.at(-1);
};
const lastContext = () => env.contexts.at(-1);
const lastProcessor = () => env.processors.at(-1);
const micDeferred = () => {
  const deferred = defer();
  env.getUserMedia = () => deferred.promise;
  return deferred;
};
const micResolved = () => {
  const stream = fakeStream();
  env.getUserMedia = () => Promise.resolve(stream);
  return stream;
};
/**
 * Starts a session, answers auth with session.ready, and lets permission
 * resolve immediately. The caller must have set the mic via micResolved().
 */
async function startLive(service) {
  assert.ok(env.getUserMedia, 'startLive requires micResolved() or a custom stub');
  await service.start(TOKEN);
  const socket = lastSocket();
  await flushed();
  socket.open();
  await flushed();
  assert.deepEqual(socket.lastText(), { type: 'session.auth', token: TOKEN });
  socket.fireMessage(READY);
  await flushed();
  return socket;
}
/** Starts a session and delivers ready while permission stays pending. */
async function startReadyPending(service) {
  const deferred = micDeferred();
  await service.start(TOKEN);
  const socket = lastSocket();
  await flushed();
  socket.open();
  await flushed();
  socket.fireMessage(READY);
  await flushed();
  return { socket, deferred };
}
const loudSamples = () => new Float32Array(2048).fill(0.5); // RMS 0.5
function micFrame(samples) {
  const processor = lastProcessor();
  processor.onaudioprocess({ inputBuffer: { getChannelData: () => samples } });
}
function pcmBuffer(values) {
  const pcm = new Int16Array(values.length);
  for (let index = 0; index < values.length; index += 1) pcm[index] = values[index];
  return pcm.buffer;
}
const audibleFrame = () => pcmBuffer(new Array(256).fill(20000)); // RMS ~0.61
const silentFrame = () => pcmBuffer(new Array(256).fill(0)); // RMS 0
const oddFrame = () => new Uint8Array(1).buffer;
const oversizedFrame = () => new Uint8Array(32770).buffer; // 32770 > 32 * 1024

// ---------- cases ----------

await (async function connectingBeforeReady() {
  beginTest('stays connecting and requests no microphone before ready');
  env.getUserMedia = () => assert.fail('getUserMedia must not run before ready');
  const service = new VoiceSessionService();
  await service.start(TOKEN);
  const socket = lastSocket();
  await flushed();
  assert.equal(service.status(), 'connecting');
  assert.equal(env.micCalls, 0);
  socket.open();
  await flushed();
  assert.equal(service.status(), 'connecting');
  assert.equal(env.micCalls, 0);
})();

await (async function silentPcmIsNotSpeaking() {
  beginTest('silent PCM does not make speaking');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(silentFrame());
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(lastContext().buffers.length, 0);
})();

await (async function audibleCurrentEpochSpeaks() {
  beginTest('audible PCM of the current epoch sets speaking, ended returns to listening');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
  const source = lastContext().sources.at(-1);
  assert.ok(source.started);
  assert.equal(lastContext().buffers[0].sampleRate, 16000);
  source.stop();
  await flushed();
  assert.equal(service.status(), 'listening');
})();

await (async function createBufferUsesMetadataRate() {
  beginTest('createBuffer uses the 24 kHz rate from audio.chunk metadata');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(chunk(24000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
  assert.equal(lastContext().buffers.at(-1).sampleRate, 24000);
})();

await (async function chunksQueueEndToEnd() {
  beginTest('chunks that arrive early are scheduled end to end, and an interrupt resets the queue');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  for (let index = 0; index < 3; index += 1) {
    socket.fireMessage(chunk(24000, 0));
    socket.fireMessage(audibleFrame());
  }
  await flushed();
  const context = lastContext();
  const length = context.buffers[0].duration;
  assert.ok(length > 0);
  assert.deepEqual(context.sources.map((source) => source.startedAt), [0, length, 2 * length]);
  service.interrupt();
  socket.fireMessage(JSON.stringify({ type: 'playback.interrupted', playbackEpoch: 1 }));
  // Earlier than the old queue end, so only a reset queue can start here.
  context.currentTime = length;
  socket.fireMessage(chunk(24000, 1));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(context.sources.at(-1).startedAt, length);
})();

await (async function untaggedAndConsumedTags() {
  beginTest('untagged binary is dropped and one tag permits exactly one frame');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(audibleFrame()); // no tag before it
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  socket.fireMessage(audibleFrame()); // no fresh tag
  await flushed();
  assert.equal(service.status(), 'speaking');
  assert.equal(lastContext().buffers.length, 1);
})();

await (async function oldEpochDiscardedAfterInterrupt() {
  beginTest('a stale old-epoch frame after a server interrupt does not play');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  service.interrupt();
  socket.fireMessage({ type: 'playback.interrupted', playbackEpoch: 1, source: 'local' });
  await flushed();
  assert.equal(service.status(), 'listening');
  // A tag from the old epoch no longer owns the next binary frame.
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(lastContext().buffers.length, 0);
  // The new epoch plays.
  socket.fireMessage(chunk(16000, 1));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
  assert.equal(lastContext().buffers.length, 1);
})();

await (async function muteEndToEnd() {
  beginTest('mute disables tracks, drops input, clears level and playback');
  const service = new VoiceSessionService();
  const stream = micResolved();
  const socket = await startLive(service);
  micFrame(loudSamples());
  assert.ok(service.inputLevel() > 0);
  assert.equal(socket.countBinary(), 1);
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
  service.setMuted(true);
  assert.equal(service.status(), 'muted');
  assert.equal(stream.track.enabled, false);
  assert.equal(service.inputLevel(), 0);
  assert.ok(lastContext().sources.at(0).stopped);
  micFrame(loudSamples()); // muted frames must not leave the page
  await flushed();
  assert.equal(socket.countBinary(), 1, 'no PCM is sent while muted');
  assert.equal(service.inputLevel(), 0);
  service.setMuted(false);
  assert.equal(stream.track.enabled, true);
  assert.equal(service.status(), 'listening');
  assert.equal(socket.countText('capture.mute'), 1);
  assert.equal(socket.countText('capture.unmute'), 1);
})();

await (async function automaticBargeIn() {
  beginTest('a loud input frame barges in while audible playback runs, and only once');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
  micFrame(loudSamples());
  await flushed();
  assert.equal(socket.countText('playback.interrupt'), 1);
  assert.equal(service.status(), 'listening');
  assert.ok(lastContext().sources.at(0).stopped);
  // A second loud frame while the interrupt is still pending must not send
  // another interrupt.
  micFrame(loudSamples());
  await flushed();
  assert.equal(socket.countText('playback.interrupt'), 1);
  // Old-epoch audio stays dropped until the backend acknowledges epoch 1.
  const buffersBefore = lastContext().buffers.length;
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(lastContext().buffers.length, buffersBefore, 'old-epoch frame must not play');
  socket.fireMessage({ type: 'playback.interrupted', playbackEpoch: 1, source: 'provider' });
  socket.fireMessage(chunk(16000, 1));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
})();

await (async function rapidManualInterrupts() {
  beginTest('two rapid manual interrupts stay pending until both are acknowledged');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  service.interrupt();
  service.interrupt();
  assert.equal(socket.countText('playback.interrupt'), 2);
  socket.fireMessage({ type: 'playback.interrupted', playbackEpoch: 1, source: 'local' });
  socket.fireMessage(chunk(16000, 1));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(lastContext().buffers.length, 0, 'the second interrupt is still pending');
  socket.fireMessage({ type: 'playback.interrupted', playbackEpoch: 2, source: 'local' });
  socket.fireMessage(chunk(16000, 2));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
  assert.equal(lastContext().buffers.length, 1);
})();

await (async function stopWithSilentSource() {
  beginTest('stop with a silent event source closes tracks, context, and socket');
  const service = new VoiceSessionService();
  const stream = micResolved();
  const socket = await startLive(service);
  micFrame(loudSamples());
  assert.ok(service.inputLevel() > 0);
  service.stop();
  await flushed();
  assert.equal(service.status(), 'stopped');
  assert.equal(service.error(), '');
  assert.ok(stream.track.stopped);
  assert.equal(lastContext().state, 'closed');
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  assert.equal(service.inputLevel(), 0);
})();

await (async function latePermissionAfterStop() {
  beginTest('a late permission grant after Stop stops the stream and attaches nothing');
  const service = new VoiceSessionService();
  const { deferred } = await startReadyPending(service);
  service.stop();
  await flushed();
  assert.equal(service.status(), 'stopped');
  const lateStream = fakeStream();
  deferred.resolve(lateStream);
  await flushed();
  assert.equal(lateStream.track.stopped, true, 'the late stream must be stopped');
  assert.equal(service.status(), 'stopped');
  assert.equal(service.error(), '');
  // No new context was ever created for the late stream.
  assert.ok(!env.contexts.length || env.contexts.at(-1).state === 'closed');
})();

await (async function latePermissionAfterNewStart() {
  beginTest('a late permission grant for the old session never attaches to the new one');
  const service = new VoiceSessionService();
  const { deferred } = await startReadyPending(service);
  service.stop();
  await flushed();
  // A new session starts first; the old permission resolves afterwards.
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
  const oldStream = fakeStream();
  deferred.resolve(oldStream);
  await flushed();
  assert.equal(oldStream.track.stopped, true, 'the old returned stream must be stopped');
  assert.equal(service.status(), 'listening');
  assert.equal(second.readyState, FakeWebSocket.OPEN);
  // The attached context belongs to the new session and is still running.
  assert.equal(lastContext().state, 'running');
})();

await (async function lateRejectionAfterStop() {
  beginTest('a late permission rejection after Stop does not poison the state');
  const service = new VoiceSessionService();
  const { deferred } = await startReadyPending(service);
  service.stop();
  await flushed();
  deferred.reject(new Error('fake denied'));
  await flushed();
  assert.equal(service.status(), 'stopped');
  assert.equal(service.error(), '');
})();

await (async function lateRejectionAfterNewStart() {
  beginTest('a late permission rejection never fails the newer session');
  const service = new VoiceSessionService();
  const { deferred } = await startReadyPending(service);
  service.stop();
  await flushed();
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
  deferred.reject(new Error('fake denied'));
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(service.error(), '');
  assert.equal(second.readyState, FakeWebSocket.OPEN);
})();

await (async function duplicateReadyFailsClosed() {
  beginTest('a repeated session.ready fails closed without a second mic stream');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Duplicate session.ready received.');
  assert.equal(env.micCalls, 1);
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
})();

await (async function deferredContextCloseVersusRestart() {
  beginTest('an old audio-context close that resolves after a new Start touches nothing new');
  const service = new VoiceSessionService();
  const oldStream = micResolved();
  const oldSocket = await startLive(service);
  assert.equal(env.contexts.length, 1);
  env.deferContextClose = true;
  service.stop();
  // Detachment is synchronous: the old socket closes and tracks stop at once.
  assert.equal(oldSocket.readyState, FakeWebSocket.CLOSED);
  assert.ok(oldStream.track.stopped);
  assert.equal(env.contexts[0].state, 'closing');
  // A new session starts while the old close is still in flight.
  const newStream = micResolved();
  await service.start(TOKEN);
  const newSocket = lastSocket();
  await flushed();
  newSocket.open();
  await flushed();
  newSocket.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.notStrictEqual(newSocket, oldSocket);
  // The old close resolves now; the tail of cleanup must not run for it.
  env.contexts[0].finishClose();
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(service.error(), '');
  assert.equal(newSocket.readyState, FakeWebSocket.OPEN);
  assert.equal(service.muted(), false);
  // The new session keeps playing after the old resources close.
  newSocket.fireMessage(chunk(16000, 0));
  newSocket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
  assert.equal(newStream.track.enabled, true);
  assert.equal(env.contexts.at(-1).state, 'running');
})();

await (async function restartFromError() {
  beginTest('start succeeds from the error state without a reload (CT-11)');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage({ type: 'session.error', category: 'session-failed' });
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Voice session failed: session-failed');
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  // Restart is allowed immediately.
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(service.error(), '');
  // An unknown category stays redacted, never shown raw.
  second.fireMessage({ type: 'session.error', category: 'SENTINEL-provider-detail' });
  await flushed();
  assert.equal(service.error(), 'Voice session failed: unknown');
  assert.equal(service.status(), 'error');
})();

await (async function freshEpochZeroOnRestart() {
  beginTest('a restart after interrupt and stop accepts the fresh epoch 0');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  service.interrupt();
  socket.fireMessage({ type: 'playback.interrupted', playbackEpoch: 1, source: 'local' });
  await flushed();
  service.stop();
  await flushed();
  assert.equal(service.status(), 'stopped');
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  // Epoch 0 again: the new tracker must accept it.
  second.fireMessage(chunk(16000, 0));
  second.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
})();

await (async function invalidMetadataCleansUp() {
  beginTest('invalid chunk metadata fails the session and cleans up');
  const service = new VoiceSessionService();
  const stream = micResolved();
  const socket = await startLive(service);
  socket.fireMessage({ type: 'audio.chunk', playbackEpoch: 0, rateHz: 44100, channels: 1, format: 'pcm16' });
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Invalid local voice response.');
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  assert.ok(stream.track.stopped);
  assert.equal(lastContext().state, 'closed');
})();

await (async function malformedTaggedBinaryFails() {
  beginTest('odd tagged binary fails the session');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(oddFrame());
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Invalid local voice response.');
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
})();

await (async function oversizedTaggedBinaryFails() {
  beginTest('oversized tagged binary fails the session');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(oversizedFrame());
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Invalid local voice response.');
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
})();

await (async function oversizedUntaggedDropped() {
  beginTest('an oversized untagged binary is dropped silently');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage(oversizedFrame());
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(service.error(), '');
})();

await (async function malformedJsonFails() {
  beginTest('malformed JSON fails the session with the fixed message');
  const service = new VoiceSessionService();
  micResolved();
  const socket = await startLive(service);
  socket.fireMessage('not-json');
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Invalid local voice response.');
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
})();

await (async function guardedStarts() {
  beginTest('a short token and a live session are both rejected without a socket');
  const service = new VoiceSessionService();
  await service.start('short');
  assert.equal(service.error(), 'Local token must contain at least 32 characters.');
  assert.equal(env.sockets.length, 0);
  env.getUserMedia = () => assert.fail('no microphone without ready');
  await service.start(TOKEN);
  const socket = lastSocket();
  await flushed();
  socket.open();
  await flushed();
  await service.start(TOKEN);
  assert.equal(service.error(), 'Session already active.');
  assert.equal(env.sockets.length, 1);
})();

await (async function localCaptureFactoryThrowSource() {
  beginTest('a createMediaStreamSource throw fails closed with no leaked context');
  const service = new VoiceSessionService();
  const stream = micResolved();
  env.failSourceCreate = true;
  const socket = await startLive(service);
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Local audio capture failed.');
  assert.ok(stream.track.stopped);
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  assert.equal(env.contexts[0].state, 'closed', 'the tracked context must be closed');
  // Restart is recoverable without a reload.
  env.failSourceCreate = false;
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
})();

await (async function localCaptureFactoryThrowProcessor() {
  beginTest('a createScriptProcessor throw fails closed with no leaked context');
  const service = new VoiceSessionService();
  const stream = micResolved();
  env.failProcessorCreate = true;
  const socket = await startLive(service);
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Local audio capture failed.');
  assert.ok(stream.track.stopped);
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  assert.equal(env.contexts[0].state, 'closed', 'the tracked context must be closed');
  env.failProcessorCreate = false;
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
})();

await (async function syncThrowUponCloseDuringStop() {
  beginTest('a synchronously throwing audio-context close still finalizes Stop');
  const service = new VoiceSessionService();
  const stream = micResolved();
  const socket = await startLive(service);
  micFrame(loudSamples());
  assert.ok(service.inputLevel() > 0);
  env.throwOnClose = true;
  service.stop();
  // The requested state is applied before the awaited close, synchronously.
  assert.equal(service.status(), 'stopped');
  await flushed();
  assert.equal(service.error(), '');
  assert.ok(stream.track.stopped);
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  assert.equal(service.inputLevel(), 0);
  assert.equal(service.muted(), false);
  assert.equal(env.contexts[0].state, 'running', 'close threw before closing; no detail shown');
  // The session is fully detached despite the failed close, so a restart works.
  env.throwOnClose = false;
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
})();

await (async function rejectingCloseDuranteFail() {
  beginTest('a rejecting audio-context close during fail keeps the error category');
  const service = new VoiceSessionService();
  const stream = micResolved();
  const socket = await startLive(service);
  env.closeReject = true;
  socket.fireMessage({ type: 'session.error', category: 'session-failed' });
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Voice session failed: session-failed');
  assert.ok(stream.track.stopped);
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  assert.equal(env.contexts[0].state, 'closed');
  // No rejection escaped the void cleanup promise, and a restart works.
  env.closeReject = false;
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
})();

await (async function hangingCloseFailureFinalizesImmediately() {
  beginTest('a hanging audio-context close cannot lock the UI after a fail');
  const service = new VoiceSessionService();
  const stream = micResolved();
  const socket = await startLive(service);
  env.deferContextClose = true;
  socket.fireMessage({ type: 'session.error', category: 'provider-session-ended' });
  // Final state is deterministic before the close resolves.
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Voice session failed: provider-session-ended');
  assert.ok(stream.track.stopped);
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  env.contexts[0].finishClose();
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Voice session failed: provider-session-ended');
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
})();

await (async function suspendedResumeSuccess() {
  beginTest('an initially suspended context resumes before listening and before PCM');
  const service = new VoiceSessionService();
  const stream = micResolved();
  env.initialContextState = 'suspended';
  env.deferResume = true;
  const socket = await startLive(service);
  await flushed();
  // No listening is published while the context is not running.
  assert.equal(service.status(), 'connecting');
  assert.equal(service.error(), '');
  micFrame(loudSamples());
  await flushed();
  assert.equal(socket.countBinary(), 0, 'no microphone PCM ships before resume');
  assert.equal(service.inputLevel(), 0, 'no meter updates before resume');
  env.contexts[0].finishResume();
  await flushed();
  assert.equal(service.status(), 'listening');
  micFrame(loudSamples());
  await flushed();
  assert.equal(socket.countBinary(), 1);
  assert.ok(service.inputLevel() > 0);
  assert.ok(stream.track.enabled);
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
})();

await (async function suspendedResumeReject() {
  beginTest('a failed resume fails the session with the fixed local capture error');
  const service = new VoiceSessionService();
  const stream = micResolved();
  env.initialContextState = 'suspended';
  env.rejectResume = true;
  const socket = await startLive(service);
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Local audio capture failed.');
  assert.ok(stream.track.stopped);
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  assert.equal(env.contexts[0].state, 'closed');
})();

await (async function stopAndNewStartDuringDeferredResume() {
  beginTest('stop plus new start during a deferred resume: the resolve cannot poison');
  const service = new VoiceSessionService();
  const oldStream = micResolved();
  env.initialContextState = 'suspended';
  env.deferResume = true;
  const oldSocket = await startLive(service);
  assert.equal(service.status(), 'connecting');
  service.stop();
  await flushed();
  assert.equal(service.status(), 'stopped');
  assert.ok(oldStream.track.stopped);
  assert.equal(oldSocket.readyState, FakeWebSocket.CLOSED);
  // A new session starts while the old resume is still pending, on a
  // normally running context.
  env.initialContextState = 'running';
  env.deferResume = false;
  const newStream = micResolved();
  await service.start(TOKEN);
  const newSocket = lastSocket();
  await flushed();
  newSocket.open();
  await flushed();
  newSocket.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(service.error(), '');
  // The old resume resolves now; it must not touch the new session.
  env.contexts[0].finishResume();
  await flushed();
  assert.equal(newStream.track.stopped, false);
  assert.equal(service.status(), 'listening');
  assert.equal(service.error(), '');
  assert.equal(newSocket.readyState, FakeWebSocket.OPEN);
  assert.equal(service.muted(), false);
  newSocket.fireMessage(chunk(16000, 0));
  newSocket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
})();

await (async function stopAndNewStartDuringDeferredResumeReject() {
  beginTest('stop plus new start during a deferred resume: the rejection cannot fail it');
  const service = new VoiceSessionService();
  const oldStream = micResolved();
  env.initialContextState = 'suspended';
  env.deferResume = true;
  const oldSocket = await startLive(service);
  service.stop();
  await flushed();
  env.initialContextState = 'running';
  env.deferResume = false;
  const newStream = micResolved();
  await service.start(TOKEN);
  const newSocket = lastSocket();
  await flushed();
  newSocket.open();
  await flushed();
  newSocket.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
  // The old resume now rejects; only the old session may carry the failure.
  env.contexts[0].denyResume();
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(service.error(), '');
  assert.equal(newSocket.readyState, FakeWebSocket.OPEN);
  assert.ok(newStream.track.enabled);
  assert.equal(service.muted(), false);
  // Silence in the new session remains possible afterwards.
  newSocket.fireMessage(chunk(16000, 0));
  newSocket.fireMessage(silentFrame());
  await flushed();
  assert.equal(service.status(), 'listening');
})();

await (async function staleSocketCallbacksCannotTouchNewSession() {
  beginTest('captured old socket handlers cannot act on a stopped or new session');
  const service = new VoiceSessionService();
  const oldStream = micResolved();
  const oldSocket = await startLive(service);
  // Capture the real handler references before Stop.
  const oldOnopen = oldSocket.onopen;
  const oldOnmessage = oldSocket.onmessage;
  const oldOnerror = oldSocket.onerror;
  const oldOnclose = oldSocket.onclose;
  service.stop();
  await flushed();
  assert.equal(oldSocket.onopen, null);
  assert.equal(oldSocket.onmessage, null);
  assert.equal(oldSocket.onerror, null);
  assert.equal(oldSocket.onclose, null);
  // A new session becomes live.
  const newStream = micResolved();
  await service.start(TOKEN);
  const newSocket = lastSocket();
  await flushed();
  newSocket.open();
  await flushed();
  newSocket.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
  newSocket.fireMessage(chunk(16000, 0));
  newSocket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
  const softSamples = () => new Float32Array(2048).fill(0.005); // below barge-in
  micFrame(softSamples());
  const binariesBefore = newSocket.countBinary();
  const micCallsBefore = env.micCalls;
  const oldSentBefore = oldSocket.sent.length;
  // Invoke the captured old handlers directly.
  oldOnopen(new Event('open'));
  oldOnmessage({ data: JSON.stringify(READY) });
  oldOnerror(new Error('fake stale error'));
  oldOnclose();
  await flushed();
  // Nothing changed in either session.
  assert.equal(oldSocket.countText('session.auth'), 1, 'no extra auth from the stale open');
  assert.equal(oldSocket.sent.length, oldSentBefore, 'no stale writes');
  assert.equal(env.micCalls, micCallsBefore, 'no duplicate microphone request');
  assert.equal(newSocket.countBinary(), binariesBefore, 'no new-session side effects');
  assert.equal(service.status(), 'speaking', 'status is untouched');
  assert.equal(service.error(), '');
  assert.equal(service.muted(), false);
  assert.equal(service.inputLevel() > 0, true);
  assert.ok(newStream.track.enabled && oldStream.track.stopped);
})();

await (async function errorDuringPendingPermissionThenLateFulfill() {
  beginTest('a session.error during pending permission fails cleanly and the late grant stops');
  const service = new VoiceSessionService();
  const { socket, deferred } = await startReadyPending(service);
  assert.equal(service.status(), 'connecting');
  assert.equal(socket.readyState, FakeWebSocket.OPEN);
  socket.fireMessage({ type: 'session.error', category: 'session-failed' });
  await flushed();
  assert.equal(service.status(), 'error');
  assert.equal(service.error(), 'Voice session failed: session-failed');
  const lateStream = fakeStream();
  deferred.resolve(lateStream);
  await flushed();
  assert.equal(lateStream.track.stopped, true, 'the late grant must be stopped');
  assert.equal(service.status(), 'error');
  micResolved();
  await service.start(TOKEN);
  const second = lastSocket();
  await flushed();
  second.open();
  await flushed();
  second.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(service.error(), '');
  second.fireMessage(chunk(16000, 0));
  second.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
})();

await (async function mutedStopRestartDoesNotInheritMute() {
  beginTest('mute, stop with a slow old close, then a new start starts unmuted');
  const service = new VoiceSessionService();
  const oldStream = micResolved();
  const socket = await startLive(service);
  micFrame(loudSamples());
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  service.setMuted(true);
  assert.equal(service.muted(), true);
  assert.equal(service.status(), 'muted');
  env.deferContextClose = true;
  service.stop();
  await flushed();
  // The old cleanup must have reset the mute state; the new session must not
  // inherit it against the backend default.
  assert.equal(service.muted(), false);
  assert.equal(service.status(), 'stopped');
  assert.ok(oldStream.track.stopped);
  assert.equal(socket.readyState, FakeWebSocket.CLOSED);
  const newStream = micResolved();
  await service.start(TOKEN);
  const newSocket = lastSocket();
  assert.equal(service.muted(), false);
  await flushed();
  newSocket.open();
  await flushed();
  newSocket.fireMessage(READY);
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(newStream.track.enabled, true);
  micFrame(loudSamples());
  await flushed();
  assert.equal(newSocket.countBinary(), 1, 'input frames reach the new socket');
  assert.ok(service.inputLevel() > 0);
  env.contexts[0].finishClose();
  await flushed();
  assert.equal(service.status(), 'listening');
  assert.equal(service.muted(), false);
  assert.equal(service.error(), '');
  assert.equal(newSocket.readyState, FakeWebSocket.OPEN);
})();

await (async function mutingDuringPendingPermissionStaysPossible() {
  beginTest('mute during a pending permission disables the track that arrives later');
  const service = new VoiceSessionService();
  const { socket, deferred } = await startReadyPending(service);
  service.setMuted(true);
  assert.equal(service.status(), 'muted');
  const lateStream = fakeStream();
  deferred.resolve(lateStream);
  await flushed();
  assert.equal(lateStream.track.enabled, false, 'the late track honors the pending mute');
  assert.equal(service.status(), 'muted');
  service.setMuted(false);
  assert.equal(lateStream.track.enabled, true);
  assert.equal(service.status(), 'listening');
  assert.equal(socket.countText('capture.unmute'), 1);
})();

await (async function closingSocketLatePermissionFinalizesStopped() {
  beginTest('a closing socket without its close event never publishes listening');
  const service = new VoiceSessionService();
  const { socket, deferred } = await startReadyPending(service);
  assert.equal(service.status(), 'connecting');
  // The transport begins closing but has not raised the close event yet.
  socket.readyState = FakeWebSocket.CLOSING;
  const lateStream = fakeStream();
  deferred.resolve(lateStream);
  await flushed();
  // The late permission is dropped and listening is never published.
  assert.equal(lateStream.track.stopped, true);
  assert.equal(service.status(), 'connecting', 'no listening on a closing socket');
  assert.equal(service.error(), '');
  assert.equal(env.contexts.length, 0, 'no capture attached for the closing socket');
  // The eventual close event finalizes the stopped state.
  socket.fireClose();
  await flushed();
  assert.equal(service.status(), 'stopped');
  assert.equal(service.error(), '');
  assert.equal(lateStream.track.stopped, true);
})();

await (async function speakingStateKeptThroughDeferredResume() {
  beginTest('audible playback during a deferred resume keeps speaking after resume');
  const service = new VoiceSessionService();
  const stream = micResolved();
  env.initialContextState = 'suspended';
  env.deferResume = true;
  const socket = await startLive(service);
  assert.equal(service.status(), 'connecting');
  // Valid current-epoch output arrives while capture is still resuming. The
  // owned buffer may start now; the speaking state must survive the later
  // capture completion.
  socket.fireMessage(chunk(16000, 0));
  socket.fireMessage(audibleFrame());
  await flushed();
  assert.equal(service.status(), 'speaking');
  assert.equal(lastContext().buffers.length, 1);
  env.contexts[0].finishResume();
  await flushed();
  assert.equal(service.status(), 'speaking', 'resume must not downgrade to listening');
  assert.equal(stream.track.enabled, true);
  const source = lastContext().sources.at(0);
  assert.ok(source.started);
  // Capture is ready afterwards: the input meter works and speech ends normally.
  const softSamples = () => new Float32Array(2048).fill(0.005);
  micFrame(softSamples());
  await flushed();
  assert.equal(socket.countBinary(), 1);
  source.stop();
  await flushed();
  assert.equal(service.status(), 'listening');
})();

// Any failed assert above throws and exits with a non-zero code.
console.log(`voice-session self-test: PASS (${casesRun} cases)`);
