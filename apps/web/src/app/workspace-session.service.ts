import { Injectable, signal } from '@angular/core';
import { JarvisDispatch, JarvisJob, JarvisWorker } from './jarvis-workspace.component';
import { hex, proveLocalBackend } from './voice-session.service';

@Injectable({ providedIn: 'root' })
export class WorkspaceSessionService {
  readonly workers = signal<readonly JarvisWorker[]>([]);
  readonly jobs = signal<readonly JarvisJob[]>([]);
  readonly connected = signal(false);
  readonly submitting = signal(false);
  readonly error = signal('');
  readonly admitted = signal<JarvisDispatch | null>(null);

  private socket?: WebSocket;
  private timer?: number;
  private waiting = false;
  private pending?: { id: string; job: JarvisDispatch };

  connect(token: string): void {
    if (this.socket) return;
    this.error.set('');
    if (token.length < 32 || !globalThis.crypto?.subtle) {
      this.error.set('Use the current local token in a secure browser context.');
      return;
    }
    const socket = new WebSocket('ws://127.0.0.1:8000/ws/workspace');
    this.socket = socket;
    const clientNonce = hex(crypto.getRandomValues(new Uint8Array(32)));
    let phase: 'waiting' | 'verifying' | 'proved' = 'waiting';
    const owns = () => this.socket === socket && socket.readyState === WebSocket.OPEN;
    const fail = (message: string) => {
      if (this.socket !== socket) return;
      this.disconnect();
      this.error.set(message);
    };
    socket.onopen = () => {
      if (owns()) socket.send(JSON.stringify({ type: 'session.hello', clientNonce }));
    };
    socket.onmessage = ({ data }) => {
      if (!owns()) return;
      if (phase === 'waiting') {
        phase = 'verifying';
        const key = new TextEncoder().encode(token);
        token = '';
        void proveLocalBackend(key, clientNonce, data, 'workspace').then(proof => {
          if (!owns()) return;
          phase = 'proved';
          socket.send(JSON.stringify({ type: 'session.auth', proof }));
        }).catch(() => fail('Could not verify the local workspace backend.'));
      } else if (phase !== 'proved' || !this.receive(data)) {
        fail('Invalid local workspace response.');
      }
    };
    socket.onerror = () => fail('The local workspace backend is unavailable.');
    socket.onclose = () => fail('Workspace disconnected. Reconnect to check your jobs.');
    this.timer = window.setInterval(() => {
      if (owns() && this.connected() && !this.waiting) this.send({ type: 'workspace.snapshot' });
    }, 700);
  }

  disconnect(): void {
    const socket = this.socket;
    this.socket = undefined;
    socket?.close();
    window.clearInterval(this.timer);
    this.connected.set(false);
    this.submitting.set(false);
    this.pending = undefined;
    this.admitted.set(null);
    this.waiting = false;
    this.workers.set([]);
    this.jobs.set([]);
  }

  submit(job: JarvisDispatch): void {
    if (this.submitting()) return;
    this.error.set('');
    const id = crypto.randomUUID();
    if (this.send({ type: 'workspace.submit', ...job, requestId: id })) {
      this.pending = { id, job };
      this.submitting.set(true);
    } else {
      this.error.set('Request was not sent. Check the local connection.');
    }
  }

  cancel(jobId: string): void {
    this.error.set('');
    if (!this.send({ type: 'workspace.cancel', jobId })) {
      this.error.set('Stop request was not sent. Check the connection and retry.');
    }
  }

  private send(command: object): boolean {
    const socket = this.socket;
    if (!this.connected() || socket?.readyState !== WebSocket.OPEN || socket.bufferedAmount > 4096) return false;
    socket.send(JSON.stringify(command));
    this.waiting = true;
    return true;
  }

  private receive(data: unknown): boolean {
    if (typeof data !== 'string' || data.length > 65_536) return false;
    try {
      const message = JSON.parse(data);
      if (message.type === 'workspace.snapshot' && Array.isArray(message.workers) && Array.isArray(message.jobs)) {
        this.workers.set(message.workers);
        this.jobs.set(message.jobs);
        this.waiting = false;
        this.connected.set(true);
        return true;
      }
      if (message.type === 'workspace.admitted') {
        if (!this.pending || message.jobId !== this.pending.id) return false;
        this.admitted.set(this.pending.job);
        this.pending = undefined;
        this.submitting.set(false);
        return true;
      }
      if (message.type === 'workspace.error') {
        if (message.operation === 'submit') {
          this.pending = undefined;
          this.submitting.set(false);
        }
        this.error.set(message.category === 'worker-unavailable'
          ? 'That worker is unavailable or already active.' : 'The workspace could not accept that request.');
        return true;
      }
    } catch {
      return false;
    }
    return false;
  }
}
