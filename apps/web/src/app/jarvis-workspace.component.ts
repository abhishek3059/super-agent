import { ChangeDetectionStrategy, Component, computed, effect, input, output, signal, untracked } from '@angular/core';

export interface JarvisWorker {
  id: string;
  name: string;
  role: string;
  status: 'offline' | 'ready' | 'busy';
  desktopUrl?: string;
}

export interface JarvisJob {
  id: string;
  workerId: string;
  status: 'queued' | 'running' | 'waiting_for_approval' | 'cancel_requested'
    | 'succeeded' | 'failed' | 'cancelled' | 'unknown';
  prompt?: string;
  result?: string;
  receipt?: { runId: string; status: string; provider?: string; model?: string; resultTruncated?: boolean };
}

export interface JarvisDispatch {
  workerId: string;
  prompt: string;
}

const PLACEHOLDERS = ['Research', 'Documents', 'Code', 'Browser', 'Coordinator'];
const SKINS = ['Ember', 'Carbon', 'Paper'] as const;
const MAX_PROMPT_LENGTH = 2000;
const JOB_STATUS: Record<JarvisJob['status'], string> = {
  queued: 'Queued',
  running: 'Running',
  waiting_for_approval: 'Awaiting approval',
  cancel_requested: 'Stopping',
  succeeded: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
  unknown: 'Outcome unknown',
};

@Component({
  selector: 'app-jarvis-workspace',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './jarvis-workspace.component.html',
  styleUrl: './jarvis-workspace.component.css',
})
export class JarvisWorkspaceComponent {
  readonly workers = input<readonly JarvisWorker[]>([]);
  readonly jobs = input<readonly JarvisJob[]>([]);
  readonly connected = input(false);
  readonly submitting = input(false);
  readonly error = input('');
  readonly admitted = input<JarvisDispatch | null>(null);
  readonly dispatchJob = output<JarvisDispatch>();
  readonly cancelJob = output<string>();
  readonly connectRequested = output<void>();

  readonly draft = signal('');
  readonly skin = signal<(typeof SKINS)[number]>('Ember');
  readonly skins = SKINS;
  readonly maxPromptLength = MAX_PROMPT_LENGTH;
  private readonly selection = signal('');

  readonly roster = computed(() => {
    const workers = this.workers();
    const latestByWorker = new Map<string, JarvisJob>();
    for (const job of this.jobs()) latestByWorker.set(job.workerId, job);
    return PLACEHOLDERS.map((placeholder, index) => {
      const worker = workers[index];
      return {
        name: worker?.name ?? placeholder,
        role: worker?.role,
        status: worker === undefined ? 'Unconfigured' : this.workerStatus(worker),
        latest: worker && latestByWorker.get(worker.id),
        desktop: this.connected() && worker ? this.desktopUrl(worker.desktopUrl) : undefined,
      };
    });
  });

  readonly hasDesktop = computed(() => this.roster().some(worker => worker.desktop));
  readonly configuredWorkers = computed(() => this.workers().slice(0, PLACEHOLDERS.length));
  readonly availableWorkers = computed(() => this.connected()
    ? this.configuredWorkers().filter(worker => worker.status === 'ready') : []);
  readonly workerId = computed(() => this.selection() || this.availableWorkers()[0]?.id || '');
  readonly recentJobs = computed(() => this.jobs().slice(-5).reverse());
  readonly canDispatch = computed(() => this.availableWorkers().some(worker => worker.id === this.workerId())
    && Boolean(this.draft().trim())
    && this.draft().length <= MAX_PROMPT_LENGTH && !this.submitting());

  constructor() {
    effect(() => {
      const accepted = this.admitted();
      if (accepted && untracked(() => this.workerId() === accepted.workerId && this.draft().trim() === accepted.prompt)) {
        this.draft.set('');
      }
    });
  }

  setDraft(value: string): void {
    if (value && !this.selection()) this.selection.set(this.workerId());
    this.draft.set(value);
  }

  selectWorker(workerId: string): void {
    this.selection.set(workerId);
  }

  selectSkin(value: string): void {
    const skin = SKINS.find(name => name === value);
    if (skin) this.skin.set(skin);
  }

  submit(event: Event): void {
    event.preventDefault();
    if (this.canDispatch()) this.dispatchJob.emit({ workerId: this.workerId(), prompt: this.draft().trim() });
  }

  jobStatus(job: JarvisJob): string {
    return job.status === 'succeeded' && job.receipt?.status !== 'completed' ? 'Result unverified' : JOB_STATUS[job.status];
  }

  workerName(workerId: string): string {
    return this.configuredWorkers().find(worker => worker.id === workerId)?.name ?? 'Worker';
  }

  canCancel(job: JarvisJob): boolean {
    return this.connected() && ['queued', 'running', 'waiting_for_approval'].includes(job.status);
  }

  private workerStatus(worker: JarvisWorker): string {
    if (!this.connected() || worker.status === 'offline') return 'Offline';
    return worker.status === 'busy' ? 'Busy' : 'Ready';
  }

  private desktopUrl(value: string | undefined): string | undefined {
    if (!value) return undefined;
    try {
      const url = new URL(value);
      // A desktop link must use a configured local port and carry no credentials or tokens.
      if (url.protocol === 'http:' && url.hostname === '127.0.0.1' && Number(url.port) >= 1024
          && !url.username && !url.password && !url.search && !url.hash) return url.href;
    } catch {
      return undefined;
    }
    return undefined;
  }
}
