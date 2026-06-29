import { request } from "./http";
import { getToken } from "./auth";
import type { Trip, TripDetail } from "../types";

export interface TripCreateData {
  city: string;
  days: number;
  title?: string;
}

export interface TripUpdateData {
  city?: string;
  days?: number;
  title?: string;
  status?: string;
}

/** Backend envelope shape: { success: boolean; data?: T } */
interface Envelope<T> {
  success: boolean;
  data: T;
}

/** Backend paginated envelope: { success: boolean; data: { total: number; items: T[] } } */
interface PagedEnvelope<T> {
  success: boolean;
  data: {
    total: number;
    items: T[];
  };
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export async function createTrip(data: TripCreateData): Promise<Trip> {
  const res = await request<Envelope<Trip>>("/trips", {
    method: "POST",
    body: data,
    headers: authHeaders(),
  });
  return res.data;
}

export async function listTrips(page = 1, size = 20): Promise<Trip[]> {
  const query = new URLSearchParams({
    page: String(page),
    size: String(size),
  });
  const res = await request<PagedEnvelope<Trip>>(`/trips?${query.toString()}`, {
    headers: authHeaders(),
  });
  return res.data.items;
}

export async function getTrip(id: number): Promise<TripDetail> {
  const res = await request<Envelope<TripDetail>>(`/trips/${id}`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function updateTrip(id: number, data: TripUpdateData): Promise<Trip> {
  const res = await request<Envelope<Trip>>(`/trips/${id}`, {
    method: "PATCH",
    body: data,
    headers: authHeaders(),
  });
  return res.data;
}

export async function deleteTrip(id: number): Promise<void> {
  await request<Envelope<{ deleted: boolean }>>(`/trips/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}
