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

// ── Trip ───────────────────────────────────────────────────────────────────────
export interface Trip {
  id: number;
  city: string;
  days: number;
  status: string;
  title: string;
  created_at: string;
}

// ── Day Plan ───────────────────────────────────────────────────────────────────
export interface DayPlan {
  day: number;
  pois: POI[];
  total_distance_km: number;
}

// ── Chat ───────────────────────────────────────────────────────────────────────
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

// ── SSE Event ──────────────────────────────────────────────────────────────────
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

// ── Parsed Intent ──────────────────────────────────────────────────────────────
export interface ParsedIntent {
  intent: string;
  city: string | null;
  days: number | null;
  preferences: string[];
}
