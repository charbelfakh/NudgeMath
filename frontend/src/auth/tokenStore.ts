// Admin session persistence. Kept dependency-free so the Apollo auth link can
// read the token without importing React state.

const TOKEN_KEY = "nudgemath_token";
const USERNAME_KEY = "nudgemath_username";
const EXPIRES_KEY = "nudgemath_expires_at";

export type Session = { token: string; username: string; expiresAt: number | null };

function isExpired(expiresAt: number | null): boolean {
  return expiresAt !== null && Date.now() / 1000 >= expiresAt;
}

function readExpiresAt(): number | null {
  const raw = localStorage.getItem(EXPIRES_KEY);
  const parsed = raw ? Number(raw) : NaN;
  return Number.isFinite(parsed) ? parsed : null;
}

export function getToken(): string | null {
  try {
    // A token the server would reject (expired) is as good as absent — don't
    // attach it to requests or the UI will render admin state that always 401s.
    if (isExpired(readExpiresAt())) return null;
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getSession(): Session | null {
  try {
    const expiresAt = readExpiresAt();
    if (isExpired(expiresAt)) {
      clearSession();
      return null;
    }
    const token = localStorage.getItem(TOKEN_KEY);
    const username = localStorage.getItem(USERNAME_KEY);
    return token && username ? { token, username, expiresAt } : null;
  } catch {
    return null;
  }
}

export function saveSession(session: Session): void {
  try {
    localStorage.setItem(TOKEN_KEY, session.token);
    localStorage.setItem(USERNAME_KEY, session.username);
    if (session.expiresAt !== null) {
      localStorage.setItem(EXPIRES_KEY, String(session.expiresAt));
    } else {
      localStorage.removeItem(EXPIRES_KEY);
    }
  } catch {
    /* storage unavailable (private mode) — session stays in-memory only */
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    localStorage.removeItem(EXPIRES_KEY);
  } catch {
    /* ignore */
  }
}
