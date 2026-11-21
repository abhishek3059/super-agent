import { useEffect, useId, useRef, useState, type PointerEvent } from 'react';
import type { Bot } from '@shared/types';
import { SKINS, useConfigUI, type Theme } from '../configStore';
import { callLevels, endCall, isCallActive, startCall, useVoice } from '../voice/call';
import { Icon } from './Icon';

type Skin = (typeof SKINS)[number];

const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');

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

export function Companion({ bot, running, explaining, toggleExplain }: {
  bot: Bot; running: boolean; explaining: boolean; toggleExplain: () => void;
}) {
  const instructionId = useId();
  const stage = useRef<HTMLDivElement>(null);
  const pointerFrame = useRef(0);
  const pointer = useRef({ x: 0, y: 0 });
  useEffect(() => () => cancelAnimationFrame(pointerFrame.current), []);

  const followPointer = (event: PointerEvent<HTMLElement>) => {
    if (event.pointerType === 'touch' || motionPreference.matches) return;
    const { currentTarget } = event;
    pointer.current.x = event.clientX;
    pointer.current.y = event.clientY;
    if (pointerFrame.current) return;
    pointerFrame.current = requestAnimationFrame(() => {
      pointerFrame.current = 0;
      const { x, y, width, height } = currentTarget.getBoundingClientRect();
      if (!width || !height) return;
      stage.current?.style.setProperty('--look-x', `${((pointer.current.x - x) / width - 0.5) * 30}px`);
      stage.current?.style.setProperty('--look-y', `${((pointer.current.y - y) / height - 0.5) * 20}px`);
    });
  };
  const resetPointer = () => {
    cancelAnimationFrame(pointerFrame.current);
    pointerFrame.current = 0;
    stage.current?.style.removeProperty('--look-x');
    stage.current?.style.removeProperty('--look-y');
  };
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
    if (s.status === 'error') return 'Call unavailable';
    if (s.status === 'connecting') return 'Connecting';
    if (s.status !== 'live') return null;
    if (s.speaking) return 'Speaking';
    if (s.listening && !s.muted) return 'Listening';
    if (s.working.length || s.thinking) return 'Working';
    return s.muted ? 'Muted' : 'Listening';
  });
  const status = voiceState ?? (running ? 'Working' : 'Standing by');
  const meter = status === 'Speaking' ? 'out' : status === 'Listening' ? 'mic' : null;
  useEffect(() => {
    if (!meter) return;
    const element = stage.current;
    let frame = 0;
    let level = 0;
    let previousValue = '';
    const draw = () => {
      const sample = callLevels()[meter];
      level += (Math.min(1, sample * (meter === 'mic' ? 3 : 1.8)) - level) * 0.22;
      const value = level.toFixed(3);
      if (value !== previousValue) {
        element?.style.setProperty('--voice-level', value);
        previousValue = value;
      }
      frame = requestAnimationFrame(draw);
    };
    const sync = () => {
      cancelAnimationFrame(frame);
      level = 0;
      previousValue = '';
      element?.style.removeProperty('--voice-level');
      if (!motionPreference.matches && !document.hidden) frame = requestAnimationFrame(draw);
    };
    sync();
    motionPreference.addEventListener('change', sync);
    document.addEventListener('visibilitychange', sync);
    return () => {
      cancelAnimationFrame(frame);
      motionPreference.removeEventListener('change', sync);
      document.removeEventListener('visibilitychange', sync);
      element?.style.removeProperty('--voice-level');
    };
  }, [meter]);

  return (
    <section className="companion" aria-label={`${bot.name} companion`} data-status={status}
      onPointerMove={followPointer} onPointerLeave={resetPointer} onPointerCancel={resetPointer}
    >
      <div className="companion__stage" ref={stage}>
        <CompanionArt look={preview ?? theme} />
        <div className="companion__signal" aria-hidden="true"><i /><i /><i /><i /><i /></div>
      </div>
      <div className="companion__controls">
        <h1>{bot.name}</h1>
        <p className="companion__status" role="status"><span key={status}>{status}</span></p>
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
            <span key={guide.step}>{target ? `Step ${guide.step + 1} of 2 · Select ${skinNames[target]}` : 'Walkthrough complete.'}</span>
          </p>
          <button type="button" onClick={() => setGuide(null)}>{target ? 'Stop guide' : 'Done'}</button>
        </div>
      )}
    </section>
  );
}
