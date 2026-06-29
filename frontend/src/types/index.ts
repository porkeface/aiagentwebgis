// ── POI ────────────────────────────────────────────────────────────────────────
export interface POI {
  id: number;
  name: string;
  category: string;
  address: string | null;
  lng: number;
  lat: number;
  rating: number;
  review_count: number;
  tags: string[];
}

// ── Trip ─────────────────────────────────────────────────────────────────────
export interface Trip {
  id: number;
  city: string;
  days: number;
  status: string;
  title: string;
  created_at: string;
}

// ── Trip Day POI (in a daily plan) ────────────────────────────────────────────
export interface TripDayPOI {
  poi_id: number;
  sort_order: number;
  arrival_time: string | null;
  departure_time: string | null;
  score: number | null;
  notes: string | null;
  name: string | null;
  category: string | null;
  lng: number | null;
  lat: number | null;
  rating: number | null;
  address: string | null;
  tags: string[];
}

// ── Day Plan ─────────────────────────────────────────────────────────────────
export interface DayPlan {
  day: number;
  pois: POI[];
  total_distance_km: number;
}

// ── Day Plan Detail (from trip detail API) ────────────────────────────────────
export interface DayPlanDetail {
  day_number: number;
  date: string;
  notes: string | null;
  pois: TripDayPOI[];
}

// ── Trip Detail (from GET /trips/:id) ─────────────────────────────────────────
export interface TripDetail extends Trip {
  daily_plans: DayPlanDetail[];
}

// ── Chat ─────────────────────────────────────────────────────────────────────
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

// ── SSE Event ────────────────────────────────────────────────────────────────
export type SSEEventType =
  | "thinking"
  | "tool_calling"
  | "poi_result"
  | "route_result"
  | "plan_summary"
  | "text"
  | "error";

export interface SSEEvent {
  type: SSEEventType;
  data: unknown;
  content?: string;
}

// ── Parsed Intent ────────────────────────────────────────────────────────────
export interface ParsedIntent {
  intent: string;
  city: string | null;
  days: number | null;
  preferences: string[];
}
