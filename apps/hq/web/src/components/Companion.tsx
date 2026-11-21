import { useId } from 'react';
import type { Bot } from '@shared/types';
import { useConfigUI, type Theme } from '../configStore';
import { endCall, isCallActive, startCall, useVoice } from '../voice/call';
import { Icon } from './Icon';

const appearances: Record<Theme, string> = {
  arc: 'Arc',
  ember: 'Ember',
  carbon: 'Carbon',
  paper: 'Paper',
  system: 'System',
  light: 'Light',
  dark: 'Dark',
};

export function Companion({ bot, running }: { bot: Bot; running: boolean }) {
  const appearanceId = useId();
  const theme = useConfigUI((s) => s.theme);
  const setTheme = useConfigUI((s) => s.setTheme);
  const inCall = useVoice((s) => s.botId === bot.id && isCallActive(s));
  const voiceState = useVoice((s) => {
    if (s.botId !== bot.id) return null;
    if (s.status === 'connecting') return 'Connecting';
    if (s.status !== 'live') return null;
    if (s.speaking) return 'Speaking';
    if (s.listening) return 'Listening';
    if (s.working.length || s.thinking) return 'Working';
    return s.muted ? 'Muted' : 'Listening';
  });
  const status = voiceState ?? (running ? 'Working' : 'Standing by');

  return (
    <section className="companion" aria-label={`${bot.name} companion`} data-status={status}>
      <div className="companion__appearance">
        <label htmlFor={appearanceId}>Appearance</label>
        <select id={appearanceId} value={theme} onChange={(e) => setTheme(e.target.value as Theme)}>
          {Object.entries(appearances).map(([value, name]) => <option key={value} value={value}>{name}</option>)}
        </select>
      </div>
      <div className="companion__art" aria-hidden="true">
        <div className="companion__orbit" />
        <div className="companion__head">
          <div className="companion__face">
            <i /><i />
          </div>
        </div>
        <div className="companion__shadow" />
      </div>
      <div className="companion__controls">
        <h1>{bot.name}</h1>
        <p role="status">{status}</p>
        <button className="companion__call" type="button" onClick={inCall ? endCall : () => startCall(bot.id)}>
          <Icon name={inCall ? 'stop' : 'voice_a'} size={17} />
          {inCall ? 'End voice call' : 'Start voice chat'}
        </button>
      </div>
    </section>
  );
}
