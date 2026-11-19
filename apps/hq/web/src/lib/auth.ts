const SESSION_KEY = 'hq_session';

export function sessionToken(): string | null {
  const token = sessionStorage.getItem(SESSION_KEY);
  return token && /^[A-Za-z0-9_-]{43}$/.test(token) ? token : null;
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY);
}

/** Attach the browser session only to requests for this HQ instance. */
export function hqFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const url = new URL(path, location.origin);
  if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) {
    return Promise.reject(new Error('Invalid HQ API address'));
  }
  const headers = new Headers(init.headers);
  const token = sessionToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...init, headers, credentials: 'omit', redirect: 'error' });
}
