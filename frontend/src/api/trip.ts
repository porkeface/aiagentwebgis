import { request } from "./http";
import { getToken } from "./auth";
import type { Trip } from "../types";

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

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export async function createTrip(data: TripCreateData): Promise<Trip> {
  return request<Trip>("/trips", {
    method: "POST",
    body: data,
    headers: authHeaders(),
  });
}

export async function listTrips(page = 1, size = 20): Promise<Trip[]> {
  const query = new URLSearchParams({
    page: String(page),
    size: String(size),
  });
  return request<Trip[]>(`/trips?${query.toString()}`, {
    headers: authHeaders(),
  });
}

export async function getTrip(id: number): Promise<Trip> {
  return request<Trip>(`/trips/${id}`, {
    headers: authHeaders(),
  });
}

export async function updateTrip(id: number, data: TripUpdateData): Promise<Trip> {
  return request<Trip>(`/trips/${id}`, {
    method: "PATCH",
    body: data,
    headers: authHeaders(),
  });
}

export async function deleteTrip(id: number): Promise<void> {
  return request<void>(`/trips/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}
