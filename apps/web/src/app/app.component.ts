import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { VoiceSessionService } from './voice-session.service';

@Component({
  selector: 'app-root',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main>
      <p class="eyebrow">Super-agent voice foundation</p>
      <h1>Local voice session</h1>
      <p>This scaffold uses a local fake provider. Audio is not stored or sent to Gemini.</p>
      <label for="token">Local session token</label>
      <input id="token" type="password" autocomplete="off"
        [value]="token" (input)="token = tokenInput.value" #tokenInput>
      <section class="status" aria-live="polite">
        <span [class.active]="session.status() !== 'stopped'">●</span>
        {{ session.status() }}
      </section>
      <label for="input-level">Microphone input level (not speech detection)</label>
      <meter id="input-level" min="0" max="1" [value]="session.inputLevel()"></meter>
      @if (session.error()) { <p class="error">{{ session.error() }}</p> }
      <div class="controls">
        <!-- Start is also allowed after an error: the service can restart from the error state. -->
        <button (click)="start()" [disabled]="session.status() !== 'stopped' && session.status() !== 'error'">Start</button>
        <!-- Mute and manual stop playback are no-ops unless a session is live;
             they re-enable only for a session that can act on them. The
             service API still accepts a mute while permission is pending. -->
        <button (click)="session.setMuted(!session.muted())"
          [disabled]="session.status() === 'connecting' || session.status() === 'stopped' || session.status() === 'error'">
          {{ session.muted() ? 'Unmute' : 'Mute' }}
        </button>
        <button (click)="session.interrupt()" [disabled]="session.status() === 'connecting' || session.status() === 'stopped' || session.status() === 'error'">Stop playback</button>
        <button class="stop" (click)="session.stop()" [disabled]="session.status() === 'stopped'">Stop</button>
      </div>
    </main>
  `,
})
export class AppComponent {
  readonly session = inject(VoiceSessionService);
  token = '';

  start(): void {
    void this.session.start(this.token);
    this.token = '';
  }
}
