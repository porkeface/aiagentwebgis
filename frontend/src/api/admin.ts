import { request, authHeaders } from "../api/http";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ConfigEntry {
  value: string;
  masked: boolean;
}

export interface ConfigData {
  [key: string]: ConfigEntry;
}

export interface ConfigUpdateResult {
  updated: string[];
  requires_restart: string[];
}

export interface AdminUser {
  id: number;
  username: string;
  nickname: string;
  email: string | null;
  is_admin: boolean;
}

export interface AdminTrip {
  id: number;
  user_id: number;
  city: string;
  days: number;
  status: string;
  created_at: string;
}

export interface AdminSession {
  id: number;
  user_id: number;
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface AdminStats {
  users: number;
  trips: number;
  pois: number;
  chat_sessions: number;
}

// ── Config ─────────────────────────────────────────────────────────────────

export async function getConfig(): Promise<ConfigData> {
  const res = await request<{ success: boolean; data: ConfigData }>(
    "/admin/config",
    { headers: authHeaders() },
  );
  return res.data;
}

export async function updateConfig(
  updates: Record<string, string>,
): Promise<ConfigUpdateResult> {
  const res = await request<{ success: boolean; data: ConfigUpdateResult }>(
    "/admin/config",
    { method: "PUT", body: { updates }, headers: authHeaders() },
  );
  return res.data;
}

// ── Users ──────────────────────────────────────────────────────────────────

export async function listUsers(
  page = 1,
  size = 20,
): Promise<{ total: number; items: AdminUser[] }> {
  const res = await request<{
    success: boolean;
    data: { total: number; items: AdminUser[] };
  }>(`/admin/users?page=${page}&size=${size}`, { headers: authHeaders() });
  return res.data;
}

export async function patchUser(
  id: number,
  data: { is_admin?: boolean; password?: string },
): Promise<AdminUser> {
  const res = await request<{ success: boolean; data: AdminUser }>(
    `/admin/users/${id}`,
    { method: "PATCH", body: data, headers: authHeaders() },
  );
  return res.data;
}

export async function deleteUser(id: number): Promise<void> {
  await request(`/admin/users/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}

// ── Stats ──────────────────────────────────────────────────────────────────

export async function getStats(): Promise<AdminStats> {
  const res = await request<{ success: boolean; data: AdminStats }>(
    "/admin/stats",
    { headers: authHeaders() },
  );
  return res.data;
}

// ── Trips ──────────────────────────────────────────────────────────────────

export async function listAllTrips(
  page = 1,
  size = 20,
): Promise<{ total: number; items: AdminTrip[] }> {
  const res = await request<{
    success: boolean;
    data: { total: number; items: AdminTrip[] };
  }>(`/admin/trips?page=${page}&size=${size}`, { headers: authHeaders() });
  return res.data;
}

export async function deleteAnyTrip(id: number): Promise<void> {
  await request(`/admin/trips/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}

// ── Sessions ───────────────────────────────────────────────────────────────

export async function listAllSessions(
  page = 1,
  size = 20,
): Promise<{ total: number; items: AdminSession[] }> {
  const res = await request<{
    success: boolean;
    data: { total: number; items: AdminSession[] };
  }>(`/admin/sessions?page=${page}&size=${size}`, { headers: authHeaders() });
  return res.data;
}

export async function deleteAnySession(id: number): Promise<void> {
  await request(`/admin/sessions/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}

// ── Check ──────────────────────────────────────────────────────────────────

export async function checkIsAdmin(): Promise<boolean> {
  try {
    await request("/admin/check", { headers: authHeaders() });
    return true;
  } catch {
    return false;
  }
}
