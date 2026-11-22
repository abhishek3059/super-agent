import type { CompanionState } from '@shared/types';
import { useConfigUI } from '../configStore';
import { useStore } from '../store';
import { callLevels, useVoice } from '../voice/call';
import { req } from './api';

type Skin = CompanionState['skin'];
let preview: Skin | null = null;
let refresh = () => {};
/** The skin under the pointer in HQ's picker, shown on the desktop overlay at once. */
export function previewSkin(skin: Skin | null) { preview = skin; refresh(); }

function status(): CompanionState['status'] {
  const v = useVoice.getState();
  if (v.status === 'live') {
    if (v.speaking) return 'speaking';
    if (v.thinking || v.working.length) return 'thinking';
    return v.listening && !v.muted ? 'listening' : 'idle';
  }
  return Object.values(useStore.getState().live).some((l) => l?.isRunning) ? 'thinking' : 'idle';
}

/** Posts HQ's companion state for the desktop overlay: on every change, and voice energy at 10 Hz while it moves. */
export function startCompanionMirror(): () => void {
  let sent = '';
  let sentAt = 0;
  const push = () => {
    const theme = useConfigUI.getState().theme;
    const s = status();
    const levels = callLevels();
    const raw = s === 'speaking' ? levels.out * 1.8 : s === 'listening' ? levels.mic * 3 : 0;
    const state: CompanionState = {
      status: s,
      level: Math.round(Math.min(1, raw) * 20) / 20,
      skin: preview ?? theme,
    };
    const key = JSON.stringify(state);
    // Refresh active state even when speech energy or the thinking state is unchanged.
    const now = Date.now();
    if (key === sent && (s === 'idle' || now - sentAt < 4000)) return;
    sent = key;
    sentAt = now;
    req('POST', '/companion', state).catch(() => { sent = ''; });
  };
  refresh = push;
  const timer = setInterval(() => { if (status() !== 'idle') push(); }, 100);
  const unsubs = [useVoice.subscribe(push), useConfigUI.subscribe(push), useStore.subscribe((s, p) => {
    const reconnected = s.sseConnected && !p.sseConnected;
    if (reconnected) sent = '';
    if (s.live !== p.live || reconnected) push();
  })];
  push();
  return () => { clearInterval(timer); unsubs.forEach((u) => u()); refresh = () => {}; };
}
