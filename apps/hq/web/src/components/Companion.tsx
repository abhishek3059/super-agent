import { useEffect, useId, useRef, useState, type PointerEvent } from 'react';
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

export function Companion({ bot, running, explaining, toggleExplain }: {
  bot: Bot; running: boolean; explaining: boolean; toggleExplain: () => void;
}) {
  const instructionId = useId();
  const theme = useConfigUI((s) => s.theme);
  const setTheme = useConfigUI((s) => s.setTheme);
  const [preview, setPreview] = useState<Skin | null>(null);
  const [guide, setGuide] = useState<{ targets: [Skin, Skin]; step: number } | null>(null);
  const target = guide?.targets[guide.step];
  const targetButton = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (target) targetButton.current?.focus(); }, [target]);

  const startGuide = () => {
    const first = theme === 'ember' ? 'arc' : 'ember';
    const original = SKINS.find((skin) => skin === theme) ?? 'arc';
    setGuide({ targets: [first, original], step: 0 });
  };

  const chooseSkin = (skin: Skin) => {
    setTheme(skin);
    setPreview(null);
    if (guide && skin === target) setGuide({ ...guide, step: guide.step + 1 });
  };
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
        <div className="companion__actions">
          <button type="button" aria-pressed={explaining} onClick={toggleExplain}>Explain</button>
          <button type="button" onClick={startGuide} disabled={!!target}>Show me how</button>
        </div>
      </div>
      <div className="companion__skins" role="group" aria-label="Companion appearance">
        {SKINS.map((skin) => (
          <button key={skin} type="button" aria-pressed={theme === skin} className="companion__skin"
            ref={skin === target ? targetButton : undefined}
            data-guide-target={skin === target ? '' : undefined}
            aria-describedby={skin === target ? instructionId : undefined}
            onPointerEnter={(event) => { if (event.pointerType === 'mouse') setPreview(skin); }}
            onPointerLeave={() => setPreview(null)}
            onClick={() => chooseSkin(skin)}
          >
            <CompanionArt look={skin} />
            {skinNames[skin]}
          </button>
        ))}
      </div>
      {guide && (
        <div className="companion__guide" aria-label="Appearance walkthrough">
          <p id={instructionId} aria-live="polite">
            {target ? `Step ${guide.step + 1} of 2 · Select ${skinNames[target]}` : 'Walkthrough complete.'}
          </p>
          <button type="button" onClick={() => setGuide(null)}>{target ? 'Stop guide' : 'Done'}</button>
        </div>
      )}
    </section>
  );
}
