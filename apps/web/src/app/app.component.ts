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
      @if (session.error()) { <p class="error">{{ session.error() }}</p> }
      <div class="controls">
        <button (click)="start()" [disabled]="session.status() !== 'stopped'">Start</button>
        <button (click)="session.setMuted(!session.muted())"
          [disabled]="session.status() === 'stopped'">
          {{ session.muted() ? 'Unmute' : 'Mute' }}
        </button>
        <button (click)="session.interrupt()" [disabled]="session.status() === 'stopped'">Interrupt</button>
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
