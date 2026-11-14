import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  afterRenderEffect,
  computed,
  inject,
  signal,
} from '@angular/core';
import { VoiceSessionService } from './voice-session.service';
import {
  formatElapsed,
  isSessionActive,
  isSessionReady,
  providerCopy,
  pipelineSummary,
  spectrumBarHeight,
  statusLabel,
} from './voice-ui-state';

@Component({
  selector: 'app-root',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnDestroy {
  @ViewChild('settingsButton') private settingsButton?: ElementRef<HTMLButtonElement>;
  @ViewChild('settingsPanel') private settingsPanel?: ElementRef<HTMLElement>;
  @ViewChild('tokenInput') private tokenInput?: ElementRef<HTMLInputElement>;
  @ViewChild('transcript') private transcript?: ElementRef<HTMLElement>;

  readonly session = inject(VoiceSessionService);
  readonly settingsOpen = signal(false);
  readonly elapsedMs = signal(0);
  readonly bars = Array.from({ length: 40 }, (_, index) => {
    const center = Math.sin(((index + 1) / 41) * Math.PI);
    return 0.35 + center * (0.5 + ((index * 17) % 7) / 35);
  });
  readonly visualState = computed(() => this.session.status() === 'stopped'
    ? 'disconnected'
    : this.session.status());
  readonly copy = computed(() => providerCopy(this.session.provider()));
  readonly statusLabel = computed(() => statusLabel(this.session.status(), this.session.provider()));
  readonly isSessionActive = computed(() => isSessionActive(this.session.status()));
  readonly isSessionReady = computed(() => isSessionReady(this.session.status()));
  readonly canControlSession = computed(() => this.isSessionReady());
  readonly pipelineSummary = computed(() => pipelineSummary(this.session.status(), this.session.provider()));

  // Keeps the newest line in view; reads the signal so it reruns per entry.
  private readonly followTranscript = afterRenderEffect(() => {
    this.session.conversation();
    const el = this.transcript?.nativeElement;
    if (el) el.scrollTop = el.scrollHeight;
  });

  token = '';
  private sessionStartedAt = 0;
  private readonly timer = window.setInterval(() => {
    if (!this.isSessionActive()) {
      this.sessionStartedAt = 0;
      this.elapsedMs.set(0);
      return;
    }
    if (!this.sessionStartedAt) this.sessionStartedAt = performance.now();
    this.elapsedMs.set(performance.now() - this.sessionStartedAt);
  }, 100);

  ngOnDestroy(): void {
    window.clearInterval(this.timer);
  }

  openSettings(): void {
    this.settingsOpen.set(true);
    window.setTimeout(() => this.tokenInput?.nativeElement.focus());
  }

  closeSettings(): void {
    const wasOpen = this.settingsOpen();
    this.token = '';
    this.settingsOpen.set(false);
    if (wasOpen) window.setTimeout(() => this.settingsButton?.nativeElement.focus());
  }

  closeSettingsFromBackdrop(event: MouseEvent): void {
    if (event.target === event.currentTarget) this.closeSettings();
  }

  onSettingsKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Tab') return;
    const panel = this.settingsPanel?.nativeElement;
    if (!panel) return;
    const focusable = Array.from(panel.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled])'));
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  start(): void {
    const token = this.token.trim();
    this.sessionStartedAt = performance.now();
    this.elapsedMs.set(0);
    void this.session.start(token);
    this.closeSettings();
  }

  centerAction(): void {
    if (!this.isSessionActive() || this.session.status() === 'error') {
      this.openSettings();
      return;
    }
    if (this.session.status() !== 'connecting') this.toggleMute();
  }

  toggleMute(): void {
    if (this.canControlSession()) this.session.setMuted(!this.session.muted());
  }

  stop(): void {
    this.session.stop();
  }

  endOrStart(): void {
    if (this.isSessionActive()) this.stop();
    else this.openSettings();
  }

  elapsedLabel(): string {
    return formatElapsed(this.elapsedMs());
  }

  barHeight(strength: number): number {
    return spectrumBarHeight(this.session.status(), this.session.inputLevel(), strength);
  }
}
