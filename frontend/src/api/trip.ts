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

/** Shape of one POI stop inside a save-plan day */
export interface SavePlanPOI {
  id: number | string;
  name: string;
  category: string;
  lng: number;
  lat: number;
  rating?: number | null;
  address?: string | null;
  tags?: string[];
}

/** Shape of one day inside a save-plan request */
export interface SavePlanDay {
  day: number;
  day_title?: string;
  pois: SavePlanPOI[];
  total_distance_km: number;
  total_duration_min?: number;
}

/** Body of POST /trips/save-plan */
export interface SavePlanData {
  city: string;
  days: number;
  title?: string;
  daily_plans: SavePlanDay[];
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

/**
 * Persist a full AI planner output as a Trip.
 * Throws if the request fails (e.g. 401 if not logged in, 400 on bad input).
 */
export async function savePlan(data: SavePlanData): Promise<Trip> {
  const res = await request<Envelope<Trip>>("/trips/save-plan", {
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
    method: "PUT",
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
