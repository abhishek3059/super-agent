import { useMemo, useState, useSyncExternalStore } from 'react';
import { BotAvatarFor } from '../avatar/BotAvatar';
import { api } from '../lib/api';
import { botVars } from '../lib/colors';
import { displayName, sortedRows, useSelectedBot, useStore } from '../store';
import { useConfigUI } from '../configStore';
import { Companion } from './Companion';
import { Composer } from './Composer';
import { Icon } from './Icon';
import { Menu } from './Menu';
import { Transcript } from './Transcript';
import { VoiceCallBar } from './VoiceCallBar';

const narrowChat = window.matchMedia('(max-width: 780px)');
function watchNarrowChat(listener: () => void) {
  narrowChat.addEventListener('change', listener);
  return () => narrowChat.removeEventListener('change', listener);
}

export function ChatView() {
  const bot = useSelectedBot();
  const narrow = useSyncExternalStore(watchNarrowChat, () => narrowChat.matches);
  const transcript = useStore((s) => (bot ? s.transcripts[bot.id] : undefined));
  const live = useStore((s) => (bot ? s.live[bot.id] : undefined));
  const detailsOpen = useStore((s) => s.detailsOpen);
  const set = useStore((s) => s.set);
  const [companionOpen, setCompanionOpen] = useState(() => new URLSearchParams(window.location.search).has('companion'));
  const [explainBotId, setExplainBotId] = useState<string | null>(null);
  const [menu, setMenu] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const rows = useMemo(() => sortedRows(transcript), [transcript]);

  if (!bot) {
    return (
      <main className="chat chat--empty">
        <div className="empty-chat"><div className="empty-chat__sub">No Bot selected.</div></div>
      </main>
    );
  }

  const canOpenCompanion = bot.kind !== 'room';
  const showCompanion = canOpenCompanion && companionOpen;
  const explaining = showCompanion && explainBotId === bot.id;
  const canShowDetails = !showCompanion && !narrow;
  const toggleCompanion = () => {
    const url = new URL(window.location.href);
    if (companionOpen) url.searchParams.delete('companion');
    else url.searchParams.set('companion', '');
    window.history.replaceState(window.history.state, '', url);
    setCompanionOpen(!companionOpen);
  };

  const flash = (t: string) => { setToast(t); setTimeout(() => setToast(null), 2000); };

  return (
    <main className={`chat${showCompanion ? ' chat--companion' : ''}`} style={botVars(bot.avatarColor)}>
      {showCompanion && (
        <Companion key={bot.id} bot={bot} running={!!live?.isRunning} explaining={explaining}
          toggleExplain={() => setExplainBotId(explaining ? null : bot.id)} />
      )}
      <div className="chat__conversation">
        <Transcript bot={bot} rows={rows} live={live} loaded={!!transcript?.loaded} />
        <VoiceCallBar />
        <Composer bot={bot} running={!!live?.isRunning} sketch={explaining} />
      </div>
      <header className="chat__header">
        <span className="chat__pill-anchor">
          <button type="button" className="chat__pill" onClick={() => setMenu(!menu)} aria-haspopup="menu" aria-expanded={menu}>
            <BotAvatarFor bot={bot} size={24} />
            <span className="chat__pill-name">{displayName(bot)}</span>
          </button>
          {menu && (
            <Menu
              align={showCompanion ? 'left' : 'center'}
              onClose={() => setMenu(false)}
              items={[
                ...(canShowDetails ? [{ label: detailsOpen ? 'Hide details' : 'Show details', hint: '⇧⌘,', onSelect: () => set({ detailsOpen: !detailsOpen }) }] : []),
                ...(narrow || showCompanion ? [{ label: 'Switch bot', onSelect: () => set({ modal: 'search' }) }] : []),
                { label: 'Open computer', onSelect: () => set({ viewerOpen: true, viewerMode: 'watch', viewerHint: null }) },
                { label: 'New conversation', onSelect: () => api.fresh(bot.id).then(() => flash('Started a new conversation')).catch((e) => flash(e.message)) },
                { label: 'Bot settings', onSelect: () => useConfigUI.getState().openBotSettings(bot.id) },
              ]}
            />
          )}
        </span>
        <div className="chat__header-right">
          {canOpenCompanion && (
            <button type="button" className="share-btn companion-toggle" onClick={toggleCompanion}>
              {showCompanion ? 'Back to chat' : 'Companion'}
            </button>
          )}
          {canShowDetails && !detailsOpen && (
            <button type="button" className="icon-btn icon-btn--bordered" onClick={() => set({ detailsOpen: true })} aria-label="Show details" title="Show details">
              <Icon name="sidebar" opacity={0.66} style={{ transform: 'scaleX(-1)' }} />
            </button>
          )}
          {!showCompanion && <button type="button" className="share-btn" onClick={() => flash('Sharing isn’t available yet')}>Share</button>}
        </div>
      </header>
      {toast && <div className="toast" role="status">{toast}</div>}
    </main>
  );
}
