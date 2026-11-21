import { useEffect, useId, useRef, useState, type PointerEvent } from 'react';
import { createPortal } from 'react-dom';
import type { Bot } from '@shared/types';
import { SKINS, useConfigUI, type Theme } from '../configStore';
import { callLevels, endCall, isCallActive, startCall, useVoice } from '../voice/call';
import { Icon } from './Icon';
import { previewSkin } from '../lib/companionMirror';

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

function CursorCompanion({ area, theme }: { area: HTMLElement; theme: Theme }) {
  const sprite = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = sprite.current;
    const chat = area.closest('.chat');
    if (!element || !chat) return;
    let frame = 0;
    let x = 0;
    let y = 0;
    const hide = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      element.removeAttribute('data-visible');
    };
    const move = (raw: Event) => {
      const event = raw as globalThis.PointerEvent;
      if (motionPreference.matches || event.pointerType === 'touch') { hide(); return; }
      x = event.clientX;
      y = event.clientY;
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const bounds = chat.getBoundingClientRect();
        const left = x + 58 > bounds.right ? x - 58 : x + 16;
        const top = y + 50 > bounds.bottom ? y - 50 : y + 14;
        element.style.transform = `translate3d(${Math.max(bounds.left, left)}px, ${Math.max(bounds.top, top)}px, 0)`;
        element.setAttribute('data-visible', '');
      });
    };
    chat.addEventListener('pointermove', move);
    chat.addEventListener('pointerleave', hide);
    chat.addEventListener('pointercancel', hide);
    window.addEventListener('blur', hide);
    motionPreference.addEventListener('change', hide);
    return () => {
      hide();
      chat.removeEventListener('pointermove', move);
      chat.removeEventListener('pointerleave', hide);
      chat.removeEventListener('pointercancel', hide);
      window.removeEventListener('blur', hide);
      motionPreference.removeEventListener('change', hide);
    };
  }, [area]);

  return createPortal(<div className="companion-cursor" ref={sprite} aria-hidden="true"><CompanionArt look={theme} /></div>, document.body);
}

export function Companion({ bot, running, explaining, toggleExplain }: {
  bot: Bot; running: boolean; explaining: boolean; toggleExplain: () => void;
}) {
  const instructionId = useId();
  const panel = useRef<HTMLElement>(null);
  const marker = useRef<HTMLDivElement>(null);
  const [cursor, setCursor] = useState(false);
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
  const [preview, setPreviewState] = useState<Skin | null>(null);
  const setPreview = (skin: Skin | null) => { setPreviewState(skin); previewSkin(skin); };
  useEffect(() => () => previewSkin(null), []);
  const [guide, setGuide] = useState<{ targets: [Skin, Skin]; step: number } | null>(null);
  const target = guide?.targets[guide.step];
  const targetButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const button = targetButton.current;
    const root = panel.current;
    const pointer = marker.current;
    if (!target || !button || !root || !pointer) return;
    button.focus();
    const position = () => {
      const at = button.getBoundingClientRect();
      const bounds = root.getBoundingClientRect();
      pointer.style.left = `${at.left - bounds.left + at.width / 2}px`;
      pointer.style.top = `${at.top - bounds.top}px`;
    };
    position();
    const observer = new ResizeObserver(position);
    observer.observe(root);
    observer.observe(button);
    return () => observer.disconnect();
  }, [target]);

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
    <section ref={panel} className="companion" aria-label={`${bot.name} companion`} data-status={status}
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
          <button type="button" aria-pressed={cursor} onClick={() => setCursor(!cursor)}>Follow cursor</button>
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
      {cursor && panel.current && !target && <CursorCompanion area={panel.current} theme={preview ?? theme} />}
      {target && <div className="companion-guide-pointer" ref={marker} aria-hidden="true"><CompanionArt look={theme} /></div>}
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
