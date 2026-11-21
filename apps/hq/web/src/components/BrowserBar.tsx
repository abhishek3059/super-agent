import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { configApi, type ScreenTab, type TabCommand } from '../lib/configApi';

const label = (t: ScreenTab) => t.title || (t.url.startsWith('file:') && t.url.endsWith('hq-home.html') ? 'Home' : t.url) || 'New tab';
const shown = (url: string) => (url.startsWith('file:') && url.endsWith('hq-home.html') ? '' : url);

/** Tabs, back, forward, reload and an address bar for a bot's browser, over the server's tab API. */
export function BrowserBar({ botId }: { botId: string }) {
  const [tabs, setTabs] = useState<ScreenTab[]>([]);
  const [address, setAddress] = useState('');
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [order, setOrder] = useState<string[]>([]);
  // The server lists the tab on screen first; keep the strip in opening order so tabs do not jump.
  const active = tabs[0];
  useEffect(() => setOrder((o) => [...o.filter((id) => tabs.some((t) => t.id === id)), ...tabs.map((t) => t.id).filter((id) => !o.includes(id))]), [tabs]);
  const strip = order.map((id) => tabs.find((t) => t.id === id)).filter((t): t is ScreenTab => !!t);

  // A browser always has a tab: an empty list is a missed poll, and would reset the strip's order.
  const load = useCallback(() => configApi.tabs(botId).then((r) => { if (r.tabs.length) setTabs(r.tabs); }).catch(() => {}), [botId]);
  useEffect(() => { void load(); const t = setInterval(load, 1500); return () => clearInterval(t); }, [load]);
  useEffect(() => { if (!editing) setAddress(shown(active?.url ?? '')); }, [active?.url, editing]);

  const run = (cmd: TabCommand) => {
    setError(null);
    configApi.tab(botId, cmd).then((r) => { if (r.tabs.length) setTabs(r.tabs); }).catch((e: Error) => setError(e.message || 'The browser did not answer.'));
  };
  const go = (e: FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    setEditing(false);
    (document.activeElement as HTMLElement | null)?.blur();
    run({ action: 'navigate', url: address });
  };

  return (
    <div className="browserbar">
      <div className="browserbar__tabs" role="tablist" aria-label="Tabs">
        {strip.map((t) => (
          <div key={t.id} className={`browserbar__tab${t === active ? ' is-active' : ''}`} role="tab" aria-selected={t === active}>
            <button type="button" className="browserbar__tab-title" title={t.url} onClick={() => t !== active && run({ action: 'activate', id: t.id })}>{label(t)}</button>
            {tabs.length > 1 && <button type="button" className="browserbar__x" aria-label={`Close ${label(t)}`} onClick={() => run({ action: 'close', id: t.id })}>×</button>}
          </div>
        ))}
        <button type="button" className="browserbar__new" aria-label="New tab" onClick={() => run({ action: 'new' })}>+</button>
      </div>
      <form className="browserbar__nav" onSubmit={go}>
        <button type="button" aria-label="Back" onClick={() => run({ action: 'back' })}>←</button>
        <button type="button" aria-label="Forward" onClick={() => run({ action: 'forward' })}>→</button>
        <button type="button" aria-label="Reload" onClick={() => run({ action: 'reload' })}>⟳</button>
        <button type="button" aria-label="Home" onClick={() => run({ action: 'home' })}>⌂</button>
        <input
          aria-label="Address" placeholder="Search Google or type a URL" value={address} spellCheck={false}
          onFocus={(e) => { setEditing(true); e.target.select(); }} onBlur={() => setEditing(false)}
          onChange={(e) => setAddress(e.target.value)}
        />
      </form>
      {error && <div className="browserbar__error" role="alert">{error}</div>}
    </div>
  );
}
