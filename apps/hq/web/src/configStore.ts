import { create } from 'zustand';
import type { ServerEvent } from '@shared/types';
import { useStore } from './store';

/** UI state for bot settings, app settings, the Tasks view and the theme. Kept apart from store.ts on purpose. */

export const SKINS = ['arc', 'ember', 'carbon', 'paper'] as const;
export const SKIN_NAMES: Record<(typeof SKINS)[number], string> = {
  arc: 'Jarvis', ember: 'Mika', carbon: 'Carbon', paper: 'Paper',
};
/** The plain themes, or a skin (colours layered on the light or dark base). */
export type Theme = 'system' | 'light' | 'dark' | (typeof SKINS)[number];
export type BotSettingsTab = 'general' | 'skills' | 'memories' | 'routines';
export type AppSection = 'general' | 'computer' | 'permissions' | 'apps' | 'account';

interface ConfigUI {
  botSettings: { botId: string; tab: BotSettingsTab } | null;
  appSettings: AppSection | null;
  view: 'chat' | 'tasks';
  theme: Theme;
  /** Bumped by server events (tasks, memories) so open views refetch. Keys: 'tasks', 'memories:<botId>'. */
  versions: Record<string, number>;
  openBotSettings(botId: string, tab?: BotSettingsTab): void;
  closeBotSettings(): void;
  openAppSettings(section?: AppSection): void;
  closeAppSettings(): void;
  setView(v: 'chat' | 'tasks'): void;
  setTheme(t: Theme): void;
  bump(key: string): void;
}

const LS_THEME = 'hq.theme';
const readTheme = (): Theme => {
  // A new install opens in the Jarvis look.
  try { const t = localStorage.getItem(LS_THEME) as Theme | null; return t && (t === 'system' || t === 'light' || t === 'dark' || SKINS.includes(t)) ? t : 'arc'; } catch { return 'arc'; }
};

const darkQuery = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

export function applyTheme(t: Theme) {
  const skin = (SKINS as readonly string[]).includes(t) ? t : '';
  const resolved = skin ? (t === 'paper' ? 'light' : 'dark') : t === 'system' ? (darkQuery?.matches ? 'dark' : 'light') : (t as 'light' | 'dark');
  document.documentElement.dataset.skin = skin;
  document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = resolved;
}

export const useConfigUI = create<ConfigUI>((set, get) => ({
  botSettings: null,
  appSettings: null,
  view: 'chat',
  theme: readTheme(),
  versions: {},
  openBotSettings: (botId, tab = 'general') => set({ botSettings: { botId, tab } }),
  closeBotSettings: () => set({ botSettings: null }),
  openAppSettings: (section = 'general') => set({ appSettings: section }),
  closeAppSettings: () => set({ appSettings: null }),
  setView: (view) => set({ view }),
  setTheme: (theme) => {
    try { localStorage.setItem(LS_THEME, theme); } catch { /* ignore */ }
    applyTheme(theme);
    set({ theme });
  },
  bump: (key) => set({ versions: { ...get().versions, [key]: (get().versions[key] ?? 0) + 1 } }),
}));

// Apply the saved theme as early as possible, and follow the OS while on "system".
applyTheme(readTheme());
darkQuery?.addEventListener?.('change', () => { if (useConfigUI.getState().theme === 'system') applyTheme('system'); });

// store.ts forwards events it doesn't handle itself as a DOM event.
window.addEventListener('hq:event', (e) => {
  const ev = (e as CustomEvent<ServerEvent>).detail;
  const { bump } = useConfigUI.getState();
  if (ev.type === 'tasks') { bump('tasks'); bump(`tasks:${ev.botId}`); }
  if (ev.type === 'memories') bump(`memories:${ev.botId}`);
});

// Picking a bot anywhere (sidebar, search) goes back to its chat.
useStore.subscribe((s, prev) => {
  if (s.selectedBotId !== prev.selectedBotId && useConfigUI.getState().view !== 'chat') useConfigUI.getState().setView('chat');
});

export const useVersion = (key: string) => useConfigUI((s) => s.versions[key] ?? 0);
