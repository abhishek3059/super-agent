import type { CompanionState } from '@shared/types';
import { useConfigUI } from '../configStore';
import { useStore } from '../store';
import { callLevels, useVoice } from '../voice/call';
import { hqFetch } from './auth';

function status(v: ReturnType<typeof useVoice.getState>): CompanionState['status'] {
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
  let retryAt = 0;
  let sending = false;
  let stopped = false;
  const publish = async () => {
    const now = Date.now();
    if (stopped || now < retryAt) return;
    const voice = useVoice.getState();
    // A background tab should not compete with the visible view unless it is running a call.
    if (document.hidden && voice.status !== 'live') return;
    const theme = useConfigUI.getState().theme;
    const s = status(voice);
    const levels = callLevels();
    const raw = s === 'speaking' ? levels.out * 1.8 : s === 'listening' ? levels.mic * 3 : 0;
    const state: CompanionState = {
      status: s,
      level: Math.round(Math.min(1, raw) * 20) / 20,
      skin: theme,
    };
    const key = JSON.stringify(state);
    // Refresh active state even when speech energy or the thinking state is unchanged.
    if (key === sent && (s === 'idle' || now - sentAt < 4000)) return;
    try {
      const response = await hqFetch('/api/companion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: key,
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) throw new Error('Companion relay rejected the update');
      sent = key;
      sentAt = Date.now();
    } catch {
      sent = '';
      retryAt = Date.now() + 1000;
    }
  };
  const push = async () => {
    if (stopped || sending || Date.now() < retryAt) return;
    sending = true;
    try {
      // Tabs share this lock. Read the current selection only once it is our turn to send.
      if (navigator.locks) await navigator.locks.request('hq-companion', publish);
      else await publish();
    } catch {
      retryAt = Date.now() + 1000;
    } finally {
      sending = false;
    }
  };
  const timer = setInterval(push, 100);
  const unsubs = [useVoice.subscribe(push), useConfigUI.subscribe((s, p) => {
    if (s.theme !== p.theme) push();
  }), useStore.subscribe((s, p) => {
    const reconnected = s.sseConnected && !p.sseConnected;
    if (reconnected) sent = '';
    if (s.live !== p.live || reconnected) push();
  })];
  document.addEventListener('visibilitychange', push);
  push();
  return () => {
    stopped = true;
    document.removeEventListener('visibilitychange', push);
    clearInterval(timer);
    unsubs.forEach((u) => u());
  };
}
