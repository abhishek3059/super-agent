import { useCallback, useEffect, useRef, useState } from 'react';
import { configApi, type SignIn } from '../lib/configApi';

type Accounts = { chatgpt: boolean; claude: boolean };

/**
 * Accounts shared by every bot: ChatGPT through OpenAI's own sign-in page (Hermes' Codex OAuth),
 * Claude with an Anthropic API key. Both land in the dedicated HQ Hermes seed; `onConnected`
 * restarts the bot so it picks them up. Hidden when HQ runs on the operator's own ~/.hermes.
 */
export function ProviderSignIn({ onConnected }: { onConnected: () => void }) {
  const [signin, setSignin] = useState<SignIn | null>(null);
  const [accounts, setAccounts] = useState<Accounts | null>(null);
  const [editingKey, setEditingKey] = useState(false);
  const [key, setKey] = useState('');
  const [note, setNote] = useState<string | null>(null);
  const popup = useRef<Window | null>(null);
  const opened = useRef<string | null>(null);
  const wasPending = useRef(false);
  const pending = signin?.status === 'pending';

  const refresh = useCallback(() => configApi.signIn().then((r) => { setSignin(r.signin); setAccounts(r.accounts); }).catch(() => {}), []);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    if (!pending) return;
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
  }, [pending, refresh]);

  // Send the person to OpenAI's page once the link is known. Keep the handle (and drop the page's
  // way back to us) so the plain callback tab can be closed for them when sign-in finishes.
  useEffect(() => {
    if (!pending || !signin?.url || opened.current === signin.url) return;
    opened.current = signin.url;
    const w = window.open(signin.url, '_blank');
    if (w) w.opener = null;
    popup.current = w;
  }, [pending, signin?.url]);

  useEffect(() => {
    if (wasPending.current && !pending) {
      try { popup.current?.close(); } catch { /* already closed */ }
      popup.current = null;
      window.focus();
      if (signin?.status === 'done') { setNote(null); onConnected(); }
    }
    wasPending.current = pending;
  }, [pending, signin?.status, onConnected]);

  const start = () => { setNote(null); configApi.startCodexSignIn().then((r) => setSignin(r.signin)).catch((e: Error) => setNote(e.message)); };
  const cancel = () => configApi.cancelSignIn().then((r) => setSignin(r.signin)).catch(() => {});
  const saveKey = () => {
    setNote(null);
    configApi.saveAnthropicKey(key)
      .then(() => { setEditingKey(false); void refresh(); onConnected(); })
      .catch((e: Error) => setNote(e.message))
      .finally(() => setKey(''));
  };

  if (!accounts) return null;
  const showKeyField = !accounts.claude || editingKey;
  return (
    <div className="accounts">
      <div className="accounts__title">Accounts</div>

      <div className="account">
        <span className="account__logo account__logo--openai" aria-hidden>◎</span>
        <span className="account__name">
          ChatGPT
          <span className={`account__state${accounts.chatgpt ? ' is-on' : ''}`}><i aria-hidden />{pending ? 'Waiting for OpenAI…' : accounts.chatgpt ? 'Connected' : 'Not connected'}</span>
        </span>
        {pending
          ? <button type="button" className="link-btn link-btn--small" onClick={cancel}>Cancel</button>
          : <button type="button" className={accounts.chatgpt ? 'link-btn link-btn--small' : 'btn btn--sm btn--bot'} onClick={start}>{accounts.chatgpt ? 'Reconnect' : 'Sign in'}</button>}
      </div>
      {pending && (
        <div className="account__hint">
          Finish on OpenAI’s page{signin?.url && <> (<a href={signin.url} target="_blank" rel="noreferrer">open it again</a>)</>}
          {signin?.code && <>. Enter code <b>{signin.code}</b></>}. This tab closes itself when you’re done.
        </div>
      )}

      <div className="account">
        <span className="account__logo account__logo--claude" aria-hidden>✳</span>
        <span className="account__name">
          Claude
          <span className={`account__state${accounts.claude ? ' is-on' : ''}`}><i aria-hidden />{accounts.claude ? 'API key saved' : 'Not connected'}</span>
        </span>
        {accounts.claude && !editingKey && <button type="button" className="link-btn link-btn--small" onClick={() => setEditingKey(true)}>Replace key</button>}
      </div>
      {showKeyField && (
        <form className="account__key" onSubmit={(e) => { e.preventDefault(); if (key) saveKey(); }}>
          <input type="password" placeholder="Anthropic API key (sk-ant-…)" value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" aria-label="Anthropic API key" />
          <button type="submit" className="btn btn--sm" disabled={!key}>Save</button>
          {editingKey && <button type="button" className="link-btn link-btn--small" onClick={() => { setEditingKey(false); setKey(''); }}>Cancel</button>}
        </form>
      )}

      {signin?.status === 'error' && signin.error && <div className="voice-error" role="alert">{signin.error}</div>}
      {note && <div className="voice-error" role="alert">{note}</div>}
    </div>
  );
}
