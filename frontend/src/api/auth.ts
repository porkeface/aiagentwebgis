import { request } from "./http";

const TOKEN_KEY = "auth_token";

export interface AuthResponse {
  access_token: string;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function register(username: string, password: string, email: string): Promise<AuthResponse> {
  const res = await request<AuthResponse>("/auth/register", {
    method: "POST",
    body: { username, password, email },
  });
  if (res.access_token) {
    setToken(res.access_token);
  }
  return res;
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  const res = await request<AuthResponse>("/auth/login", {
    method: "POST",
    body: { username, password },
  });
  if (res.access_token) {
    setToken(res.access_token);
  }
  return res;
}
