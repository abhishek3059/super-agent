import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class VoiceSessionService {
  readonly status = signal('stopped');
  readonly muted = signal(false);
  readonly error = signal('');

  private socket?: WebSocket;
  private stream?: MediaStream;
  private context?: AudioContext;
  private processor?: ScriptProcessorNode;
  private readonly playing = new Set<AudioBufferSourceNode>();

  async start(token: string): Promise<void> {
    if (this.socket || token.length < 32) {
      this.error.set(token.length < 32 ? 'Local token must contain at least 32 characters.' : 'Session already active.');
      return;
    }
    this.error.set('');
    this.status.set('connecting');
    const socket = new WebSocket('ws://127.0.0.1:8000/ws/voice');
    socket.binaryType = 'arraybuffer';
    this.socket = socket;
    socket.onopen = () => socket.send(JSON.stringify({ type: 'session.auth', token }));
    socket.onmessage = (event) => {
      void this.handleMessage(event).catch(() => this.fail('Invalid local voice response.'));
    };
    socket.onerror = () => this.fail('Local voice connection failed.');
    socket.onclose = () => void this.cleanup('stopped');
  }

  setMuted(value: boolean): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.muted.set(value);
    this.socket.send(JSON.stringify({ type: value ? 'capture.mute' : 'capture.unmute' }));
  }

  interrupt(): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.stopPlayback();
    this.socket.send(JSON.stringify({ type: 'playback.interrupt' }));
  }

  stop(): void {
    const socket = this.socket;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'session.stop' }));
    }
    void this.cleanup('stopped');
  }

  private async handleMessage(event: MessageEvent): Promise<void> {
    if (typeof event.data !== 'string') {
      this.playPcm(event.data as ArrayBuffer);
      return;
    }
    const message = JSON.parse(event.data) as { type?: string; category?: string };
    if (message.type === 'session.ready') {
      await this.startCapture();
      this.status.set('listening');
    } else if (message.type === 'playback.interrupted') {
      this.stopPlayback();
      this.status.set('listening');
    } else if (message.type === 'session.error') {
      this.fail(`Voice session failed: ${message.category ?? 'unknown'}`);
    }
  }

  private async startCapture(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      video: false,
    });
    const context = new AudioContext({ sampleRate: 16000 });
    const source = context.createMediaStreamSource(this.stream);
    const processor = context.createScriptProcessor(2048, 1, 1);
    this.context = context;
    this.processor = processor;
    processor.onaudioprocess = (audioEvent) => {
      if (this.muted() || this.socket?.readyState !== WebSocket.OPEN) return;
      const samples = audioEvent.inputBuffer.getChannelData(0);
      let energy = 0;
      for (const sample of samples) energy += sample * sample;
      if (this.playing.size && Math.sqrt(energy / samples.length) > 0.02) {
        this.interrupt();
      }
      const pcm = new Int16Array(samples.length);
      for (let index = 0; index < samples.length; index += 1) {
        const sample = Math.max(-1, Math.min(1, samples[index] ?? 0));
        pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      }
      this.socket?.send(pcm.buffer);
    };
    source.connect(processor);
    processor.connect(context.destination);
  }

  private playPcm(data: ArrayBuffer): void {
    const context = this.context;
    if (!context || this.muted()) return;
    const pcm = new Int16Array(data);
    const buffer = context.createBuffer(1, pcm.length, 16000);
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
    source.start();
  }

  private stopPlayback(): void {
    for (const source of this.playing) {
      try { source.stop(); } catch { /* already stopped */ }
    }
    this.playing.clear();
  }

  private fail(message: string): void {
    this.error.set(message);
    void this.cleanup('error');
  }

  private async cleanup(status: string): Promise<void> {
    this.stopPlayback();
    this.processor?.disconnect();
    this.processor = undefined;
    for (const track of this.stream?.getTracks() ?? []) track.stop();
    this.stream = undefined;
    const context = this.context;
    this.context = undefined;
    if (context && context.state !== 'closed') await context.close();
    const socket = this.socket;
    this.socket = undefined;
    if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
    this.muted.set(false);
    this.status.set(status);
  }
}
