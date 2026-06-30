import { request } from "./http";

const TOKEN_KEY = "auth_token";
const USERNAME_KEY = "auth_username";

export interface AuthResponse {
  access_token: string;
}

/**
 * In-tab auth change channel. Components like ChatPanel subscribe to this so
 * the avatar/header updates immediately when AuthDialog succeeds or the user
 * logs out — without waiting for a page reload or another tab's storage event.
 */
type AuthChangeListener = () => void;
const authChangeListeners = new Set<AuthChangeListener>();

export function setAuthChangeListener(listener: AuthChangeListener): () => void {
  authChangeListeners.add(listener);
  return () => authChangeListeners.delete(listener);
}

function emitAuthChange(): void {
  for (const listener of authChangeListeners) {
    try {
      listener();
    } catch {
      /* listeners must not break each other */
    }
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  emitAuthChange();
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  emitAuthChange();
}

export function getUsername(): string | null {
  return localStorage.getItem(USERNAME_KEY);
}

export function setUsername(name: string): void {
  localStorage.setItem(USERNAME_KEY, name);
  emitAuthChange();
}

export function clearUsername(): void {
  localStorage.removeItem(USERNAME_KEY);
  emitAuthChange();
}

export function logout(): void {
  clearToken();
  clearUsername();
}

export async function register(
  username: string,
  password: string,
  email: string,
): Promise<AuthResponse> {
  const res = await request<AuthResponse>("/auth/register", {
    method: "POST",
    body: { username, password, email },
  });
  if (res.access_token) {
    setToken(res.access_token);
    setUsername(username);
  }
  return res;
}

export async function login(
  username: string,
  password: string,
): Promise<AuthResponse> {
  const res = await request<AuthResponse>("/auth/login", {
    method: "POST",
    body: { username, password },
  });
  if (res.access_token) {
    setToken(res.access_token);
    setUsername(username);
  }
  return res;
}
