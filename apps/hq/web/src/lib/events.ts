import type { ServerEvent } from '@shared/types';
import { useStore } from '../store';
import { hqFetch } from './auth';

/** Authenticated SSE with backoff and state refresh after reconnect. */
export function startEvents(): () => void {
  const connection = new AbortController();
  let retry = 1000;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let everConnected = false;

  const resync = () => {
    const st = useStore.getState();
    st.loadBots().catch(() => {});
    st.loadComputer().catch(() => {});
    if (st.selectedBotId) {
      st.loadRows(st.selectedBotId).catch(() => {});
      st.loadRoutines(st.selectedBotId).catch(() => {});
    }
  };

  const open = async () => {
    try {
      const res = await hqFetch('/api/events', { signal: connection.signal });
      if (connection.signal.aborted) return;
      if (res.status === 401) {
        void useStore.getState().checkAuth();
        return;
      }
      if (!res.ok || !res.body || !res.headers.get('content-type')?.startsWith('text/event-stream')) {
        throw new Error('Could not open the HQ event stream');
      }

      retry = 1000;
      useStore.getState().set({ sseConnected: true });
      if (everConnected) resync();
      everConnected = true;

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      try {
        let pending = '';
        for (;;) {
          const { done, value } = await reader.read();
          if (done || connection.signal.aborted) break;
          // The server emits LF-delimited records. Keep the final partial frame for the next chunk.
          const frames = (pending + value).split('\n\n');
          pending = frames.pop()!;
          for (const frame of frames) {
            const data = frame.split('\n').filter((line) => line.startsWith('data:')).map((line) => line.slice(5).replace(/^ /, '')).join('\n');
            if (!data) continue;
            try { useStore.getState().handleEvent(JSON.parse(data) as ServerEvent); }
            catch { console.warn('Invalid HQ event'); }
          }
        }
      } finally { reader.releaseLock(); }
    } catch { /* reconnect below */ }

    if (!connection.signal.aborted) {
      useStore.getState().set({ sseConnected: false });
      timer = setTimeout(open, retry);
      retry = Math.min(retry * 2, 15_000);
    }
  };

  void open();
  return () => {
    clearTimeout(timer);
    connection.abort();
    useStore.getState().set({ sseConnected: false });
  };
}
