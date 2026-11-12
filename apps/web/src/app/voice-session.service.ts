import { Injectable, signal } from '@angular/core';
import { PlaybackEpochTracker } from './playback-epoch';
import { inputRms, pcmIsAudible } from './audio-signal';

/**
 * Fixed redaction allowlist for `session.error`. Only these backend
 * categories reach the page; any other value is shown as "unknown", so an
 * unexpected provider or host string can never surface verbatim.
 */
const ERROR_CATEGORIES = new Set([
  'max-duration',
  'session-timeout',
  'session-failed',
  'provider-unavailable',
  'provider-session-ended',
  'invalid-audio',
  'invalid-control',
]);

@Injectable({ providedIn: 'root' })
export class VoiceSessionService {
  readonly status = signal('stopped');
  readonly muted = signal(false);
  readonly error = signal('');
  readonly inputLevel = signal(0);
  readonly provider = signal('');

  private socket?: WebSocket;
  private stream?: MediaStream;
  private context?: AudioContext;
  private processor?: ScriptProcessorNode;
  private readonly playing = new Set<AudioBufferSourceNode>();
  private epochs = new PlaybackEpochTracker();
  private pendingRateHz?: number;
  private interruptPending = false;
  /** When the last scheduled chunk ends; chunks that arrive early queue behind it. */
  private nextPlayAt = 0;
  /**
   * Monotonic identity of the current session. Every async continuation
   * (permission result, socket event, deferred audio-context close)
   * captures this value plus its own socket and is ignored once the
   * generation changed, so a stopped or replaced session can never mutate
   * the state of a newer one.
   */
  private generation = 0;
  /** Guards against a repeated ready allocating a second microphone stream. */
  private capturing = false;
  /**
   * False until capture may ship microphone PCM: set only after the audio
   * context is running (an initially suspended context must finish
   * `resume()` first), so no samples or meter updates cross the boundary
   * before capture is actually ready.
   */
  private captureReady = false;

  async start(token: string): Promise<void> {
    if (this.socket || token.length < 32) {
      this.error.set(token.length < 32 ? 'Local token must contain at least 32 characters.' : 'Session already active.');
      return;
    }
    this.generation += 1;
    const generation = this.generation;
    this.error.set('');
    this.status.set('connecting');
    // A fresh session always starts unmuted to match the backend default.
    // The old session's mute is either already reset by its cleanup or was
    // skipped by its generation guard, so it must not be inherited here.
    // The invalid/busy path above leaves the current session untouched.
    this.muted.set(false);
    // Every socket gets its own epoch tracker. A restart after an interrupt
    // in the previous session must accept the fresh epoch 0 the backend
    // sends; reusing the old tracker would drop all new audio.
    this.epochs = new PlaybackEpochTracker();
    this.pendingRateHz = undefined;
    this.interruptPending = false;
    this.capturing = false;
    this.captureReady = false;
    const socket = new WebSocket('ws://127.0.0.1:8000/ws/voice');
    socket.binaryType = 'arraybuffer';
    this.socket = socket;
    socket.onopen = () => {
      if (this.socket !== socket || this.generation !== generation) return;
      socket.send(JSON.stringify({ type: 'session.auth', token }));
    };
    socket.onmessage = (event) => {
      if (this.socket !== socket || this.generation !== generation) return;
      void this.handleMessage(event, socket, generation).catch(() => {
        if (this.socket === socket && this.generation === generation) {
          this.fail('Invalid local voice response.');
        }
      });
    };
    socket.onerror = () => {
      if (this.socket === socket && this.generation === generation) {
        this.fail('Local voice connection failed.');
      }
    };
    socket.onclose = () => {
      if (this.socket === socket && this.generation === generation) {
        void this.cleanup('stopped', generation);
      }
    };
  }

  setMuted(value: boolean): void {
    const socket = this.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    this.muted.set(value);
    if (value) {
      this.inputLevel.set(0);
      this.stopPlayback();
    }
    // The session track stays open, so the browser or OS microphone indicator
    // may remain visible while muted; that depends on the browser, not on us.
    // Setting enabled=false stops samples reaching the page, and the processor
    // callback below additionally drops every frame, so no microphone audio
    // crosses the browser boundary while muted.
    for (const track of this.stream?.getAudioTracks() ?? []) {
      track.enabled = !value;
    }
    socket.send(JSON.stringify({ type: value ? 'capture.mute' : 'capture.unmute' }));
    this.status.set(value ? 'muted' : this.playing.size ? 'speaking' : 'listening');
  }

  interrupt(): void {
    const socket = this.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    this.epochs.onLocalInterrupt();
    this.interruptPending = true;
    this.pendingRateHz = undefined;
    this.stopPlayback();
    socket.send(JSON.stringify({ type: 'playback.interrupt' }));
  }

  stop(): void {
    const socket = this.socket;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'session.stop' }));
    }
    void this.cleanup('stopped', this.generation);
  }

  private async handleMessage(
    event: MessageEvent,
    socket: WebSocket,
    generation: number,
  ): Promise<void> {
    if (typeof event.data !== 'string') {
      this.playPcm(event.data as ArrayBuffer);
      return;
    }
    const message = JSON.parse(event.data) as {
      type?: string;
      category?: string;
      playbackEpoch?: number;
      rateHz?: number;
      channels?: number;
      format?: string;
      provider?: string;
    };
    if (message.type === 'session.ready') {
      if (this.capturing) {
        // Fail closed: a repeated ready would otherwise allocate a second
        // microphone stream while the first capture is still in flight.
        this.fail('Duplicate session.ready received.');
        return;
      }
      this.capturing = true;
      this.provider.set(message.provider === 'local' || message.provider === 'fake' ? message.provider : 'unknown');
      this.epochs.onReady(message.playbackEpoch);
      try {
        await this.startCapture(socket, generation);
      } catch {
        // Only this session may carry this error out; a newer session is
        // never poisoned by a stale attach failure.
        if (this.socket === socket && this.generation === generation) {
          this.fail('Microphone access was not granted. Local capture stays off.');
        }
        return;
      }
      if (this.socket !== socket || this.generation !== generation
        || socket.readyState !== WebSocket.OPEN) return;
      // A socket that is closing but has not raised its close event must
      // never publish a listening session. When capture completes while
      // audible model playback runs (for example during a deferred resume),
      // the existing speaking state is kept; it is not downgraded.
      this.status.set(this.muted() ? 'muted' : this.playing.size ? 'speaking' : 'listening');
    } else if (message.type === 'audio.chunk') {
      if (message.channels !== 1 || message.format !== 'pcm16'
        || ![8000, 16000, 24000, 48000].includes(message.rateHz ?? 0)) {
        throw new Error('Unsupported audio metadata.');
      }
      this.epochs.onChunkMeta(message.playbackEpoch);
      this.pendingRateHz = message.rateHz;
    } else if (message.type === 'turn.complete') {
      this.epochs.onTurnComplete(message.playbackEpoch);
    } else if (message.type === 'playback.interrupted') {
      // The backend epoch is authoritative and clears the pending interrupt.
      this.epochs.onServerInterrupt(message.playbackEpoch);
      this.interruptPending = false;
      this.pendingRateHz = undefined;
      this.stopPlayback();
      this.status.set(this.muted() ? 'muted' : 'listening');
    } else if (message.type === 'session.error') {
      const category = message.category !== undefined
        && ERROR_CATEGORIES.has(message.category) ? message.category : 'unknown';
      this.fail(`Voice session failed: ${category}`);
    } else if (message.type === 'session.state') {
      // Only acknowledgements arrive here (mute, unmute, stopping); local
      // state is already authoritative and the final event precedes close.
    }
  }

  private async startCapture(socket: WebSocket, generation: number): Promise<void> {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
        video: false,
      });
    } catch {
      // A rejection is this session's failure only while this socket and
      // generation still own the session; a rejected stale permission must
      // not fail a newer session.
      if (this.socket === socket && this.generation === generation) {
        this.fail('Microphone access was not granted. Local capture stays off.');
      }
      return;
    }
    // Permission can resolve after Stop or after a different session started.
    if (this.socket !== socket || this.generation !== generation
      || socket.readyState !== WebSocket.OPEN) {
      for (const track of stream.getTracks()) track.stop();
      return;
    }
    await this.attachCapture(stream, socket, generation);
  }

  private async attachCapture(
    stream: MediaStream,
    socket: WebSocket,
    generation: number,
  ): Promise<void> {
    this.stream = stream;
    // Respect a mute that happened before permission resolved.
    for (const track of this.stream.getAudioTracks()) {
      track.enabled = !this.muted();
    }
    try {
      const context = new AudioContext({ sampleRate: 16000 });
      // Tracked immediately: any later factory throw must not leak an
      // owned but unclosed context.
      this.context = context;
      const processor = context.createScriptProcessor(2048, 1, 1);
      // Same rule for the processor.
      this.processor = processor;
      const source = context.createMediaStreamSource(stream);
      processor.onaudioprocess = (audioEvent) => {
        if (this.socket !== socket || this.generation !== generation) return;
        this.onAudioProcess(socket, audioEvent);
      };
      source.connect(processor);
      processor.connect(context.destination);
    } catch {
      // Local capture setup failed; the message names the local capture
      // stage and never exposes any underlying detail.
      this.fail('Local audio capture failed.');
      return;
    }
    const context = this.context;
    if (context && context.state === 'suspended') {
      // An initially suspended context must be running before microphone
      // frames may ship and before the UI claims a listening session.
      try {
        await context.resume();
      } catch {
        if (this.socket === socket && this.generation === generation) {
          this.fail('Local audio capture failed.');
        }
        return;
      }
    }
    // A late resume result belongs to this session only; a Stop or a new
    // Start in the meantime must not become ready or fail from it.
    if (this.socket !== socket || this.generation !== generation) return;
    this.captureReady = true;
  }

  private onAudioProcess(socket: WebSocket, audioEvent: AudioProcessingEvent): void {
    // Until capture is ready (context running) and unmuted, no microphone
    // sample is metered or sent.
    if (!this.captureReady || this.muted() || socket.readyState !== WebSocket.OPEN) return;
    const samples = audioEvent.inputBuffer.getChannelData(0);
    const level = inputRms(samples);
    this.inputLevel.set(level);
    // Automatic barge-in fires only while audible model playback runs and no
    // interrupt is pending; repeated loud frames during a pending interrupt
    // are ignored until the backend acknowledges a new epoch.
    if (this.playing.size && !this.interruptPending && level > 0.02) {
      this.interrupt();
    }
    const pcm = new Int16Array(samples.length);
    for (let index = 0; index < samples.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, samples[index] ?? 0));
      pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    socket.send(pcm.buffer);
  }

  private playPcm(data: ArrayBuffer): void {
    const context = this.context;
    const rateHz = this.pendingRateHz;
    this.pendingRateHz = undefined;
    const currentEpoch = this.epochs.acceptBinary();
    if (!context || this.muted() || !currentEpoch || rateHz === undefined) return;
    if (!data.byteLength || data.byteLength % 2 || data.byteLength > 32 * 1024) {
      throw new Error('Invalid PCM frame.');
    }
    // Binary frames are untagged; only a frame covered by a current-epoch
    // JSON chunk may play. Stale or untagged audio is dropped here.
    const pcm = new Int16Array(data);
    if (!pcmIsAudible(pcm)) return;
    const buffer = context.createBuffer(1, pcm.length, rateHz);
    const output = buffer.getChannelData(0);
    for (let index = 0; index < pcm.length; index += 1) {
      output[index] = (pcm[index] ?? 0) / 0x8000;
    }
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    source.onended = () => {
      this.playing.delete(source);
      if (!this.playing.size && this.status() === 'speaking') this.status.set('listening');
    };
    this.playing.add(source);
    this.status.set('speaking');
    // A local model synthesizes faster than real time, so chunks are queued
    // end to end and never start on top of each other.
    const at = Math.max(context.currentTime, this.nextPlayAt);
    this.nextPlayAt = at + buffer.duration;
    source.start(at);
  }

  private stopPlayback(): void {
    for (const source of this.playing) {
      try { source.stop(); } catch { /* already stopped */ }
    }
    this.playing.clear();
    this.nextPlayAt = 0;
    if (this.status() === 'speaking') this.status.set(this.muted() ? 'muted' : 'listening');
  }

  private fail(message: string): void {
    this.error.set(message);
    void this.cleanup('error', this.generation);
  }

  private async cleanup(status: string, generation: number): Promise<void> {
    // Detach every session resource synchronously, before any await, so a
    // Stop or a new Start during the deferred audio-context close below can
    // never inherit old resources or lose new ones.
    this.stopPlayback();
    this.processor?.disconnect();
    this.processor = undefined;
    const stream = this.stream;
    this.stream = undefined;
    for (const track of stream?.getTracks() ?? []) track.stop();
    this.inputLevel.set(0);
    this.provider.set('');
    this.pendingRateHz = undefined;
    this.interruptPending = false;
    this.capturing = false;
    this.captureReady = false;
    const context = this.context;
    this.context = undefined;
    const socket = this.socket;
    this.socket = undefined;
    // Unbind this session's callbacks before closing; close events from a
    // socket that lost its session are stale and must be ignored anyway.
    if (socket) {
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      socket.onopen = null;
      if (socket.readyState < WebSocket.CLOSING) socket.close();
    }
    if (this.generation !== generation) return;
    // The requested final state is applied before the awaited close, so a
    // hanging or failing close can never leave the UI locked out (Start
    // stays available from the recorded stopped or error state). A recorded
    // error is not downgraded to "stopped" here either.
    this.muted.set(false);
    this.status.set(this.error() ? 'error' : status);
    // Audio-context close is last; its outcome changes nothing visible.
    // A rejection or throw is swallowed deliberately: the session is fully
    // detached and the user already has a fixed final state, so no raw
    // detail is exposed and the void promise can never be unhandled.
    try {
      if (context && context.state !== 'closed') await context.close();
    } catch {
      /* the session is already detached; no user-visible impact */
    }
    // After this await the cleanup never mutates state: a newer session
    // that started in the meantime keeps its own status, level, and mute.
  }
}
