import { useState, type PointerEvent } from 'react';
import type { Bot } from '@shared/types';
import { SKINS, useConfigUI, type Theme } from '../configStore';
import { endCall, isCallActive, startCall, useVoice } from '../voice/call';
import { Icon } from './Icon';

type Skin = (typeof SKINS)[number];

const skinNames: Record<Skin, string> = { arc: 'Arc', ember: 'Ember', carbon: 'Carbon', paper: 'Paper' };

function CompanionArt({ look }: { look: Theme }) {
  return (
    <div className="companion__art" data-look={look} aria-hidden="true">
      <div className="companion__orbit" />
      <div className="companion__head">
        <div className="companion__face"><i /><i /></div>
      </div>
      <div className="companion__shadow" />
    </div>
  );
}

function trackPointer(event: PointerEvent<HTMLElement>) {
  if (event.pointerType === 'touch') return;
  const { currentTarget, clientX, clientY } = event;
  const bounds = currentTarget.getBoundingClientRect();
  currentTarget.style.setProperty('--look-x', `${(clientX - bounds.x - bounds.width / 2) / bounds.width * 24}px`);
  currentTarget.style.setProperty('--look-y', `${(clientY - bounds.y - bounds.height / 2) / bounds.height * 18}px`);
}

export function Companion({ bot, running }: { bot: Bot; running: boolean }) {
  const theme = useConfigUI((s) => s.theme);
  const setTheme = useConfigUI((s) => s.setTheme);
  const [preview, setPreview] = useState<Skin | null>(null);
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
    <section className="companion" aria-label={`${bot.name} companion`} data-status={status}
      onPointerMove={trackPointer}
      onPointerLeave={(event) => {
        event.currentTarget.style.removeProperty('--look-x');
        event.currentTarget.style.removeProperty('--look-y');
      }}
    >
      <div className="companion__stage">
        <CompanionArt look={preview ?? theme} />
      </div>
      <div className="companion__controls">
        <h1>{bot.name}</h1>
        <p role="status">{status}</p>
        <button className="companion__call" type="button" onClick={inCall ? endCall : () => startCall(bot.id)}>
          <Icon name={inCall ? 'stop' : 'voice_a'} size={17} />
          {inCall ? 'End voice call' : 'Start voice chat'}
        </button>
      </div>
      <div className="companion__skins" role="group" aria-label="Companion appearance">
        {SKINS.map((skin) => (
          <button key={skin} type="button" aria-pressed={theme === skin} className="companion__skin"
            onPointerEnter={(event) => { if (event.pointerType === 'mouse') setPreview(skin); }}
            onPointerLeave={() => setPreview(null)}
            onClick={() => { setTheme(skin); setPreview(null); }}
          >
            <CompanionArt look={skin} />
            {skinNames[skin]}
          </button>
        ))}
      </div>
    </section>
  );
}
