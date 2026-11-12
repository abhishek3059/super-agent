import { ChangeDetectionStrategy, Component, OnDestroy, computed, inject, signal } from '@angular/core';
import { VoiceSessionService } from './voice-session.service';
import { formatElapsed, pipelineSummary, spectrumBarHeight, statusLabel } from './voice-ui-state';

@Component({
  selector: 'app-root',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnDestroy {
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
  readonly statusLabel = computed(() => statusLabel(this.session.status()));
  readonly isSessionActive = computed(() => !['stopped', 'error'].includes(this.session.status()));
  readonly isSessionReady = computed(() => ['listening', 'speaking', 'muted'].includes(this.session.status()));
  readonly canControlSession = computed(() => this.isSessionReady());
  readonly pipelineSummary = computed(() => pipelineSummary(this.session.status()));

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
  }

  closeSettings(): void {
    this.token = '';
    this.settingsOpen.set(false);
  }

  closeSettingsFromBackdrop(event: MouseEvent): void {
    if (event.target === event.currentTarget) this.closeSettings();
  }

  start(): void {
    const token = this.token.trim();
    this.sessionStartedAt = performance.now();
    this.elapsedMs.set(0);
    void this.session.start(token);
    if (token.length >= 32) {
      this.token = '';
      this.settingsOpen.set(false);
    }
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
