import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { POI } from "@/types";
import { DAY_COLORS } from "@/utils/constants";

export interface PlanSummary {
  city: string;
  days: number;
}

/** Route segment between two POIs in a daily plan */
export interface RouteSegment {
  from_poi_id?: number | string;
  to_poi_id?: number | string;
  distance_km: number;
  duration_min?: number;
  polyline?: string;   // Amap polyline for this segment ("lng,lat;lng,lat;...")
  mode?: string;        // "driving" | "walking" | "bicycling" | "transit"
}

/** A single POI stop inside a daily plan */
export interface RoutePOI {
  id: number | string;
  name: string;
  category: string;
  lng: number;
  lat: number;
  rating?: number | null;
  address?: string | null;
  tags?: string[];
  photo?: string | null;
  description?: string | null;
  review_count?: number | null;
  time_slot?: string;        // "morning" | "noon" | "afternoon" | "evening"
  visit_duration_min?: number;
  meal_type?: string;        // "breakfast" | "lunch" | "dinner" | null
  [key: string]: unknown;
}

/** One day's plan as sent by the backend's `route_result` SSE event.
 *  Fields are optional on input because older callers (TripDetailView)
 *  and legacy data may omit them. */
export interface DailyPlan {
  day: number;
  day_title?: string;
  pois: RoutePOI[];
  total_distance_km?: number;
  total_duration_min?: number;
  total_transit_min?: number;
  segments?: RouteSegment[];
  polyline?: string;   // Full-day Amap polyline (for map rendering)
}

/**
 * Legacy alias — the map store keeps `RouteData` for backwards
 * compatibility with older callers (e.g. TripDetailView).
 * New code should prefer `DailyPlan`.
 */
export type RouteData = DailyPlan;

export interface MapCenter {
  lng: number;
  lat: number;
}

/** Average urban travel speed used for duration estimation */
const AVG_URBAN_SPEED_KMH = 30;

/**
 * Haversine distance in km between two [lat, lng] points.
 */
function haversineKm(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
): number {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const aRad = (a.lat * Math.PI) / 180;
  const bRad = (b.lat * Math.PI) / 180;
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(aRad) * Math.cos(bRad) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

/**
 * Estimate travel duration in minutes from distance in km.
 */
function estimateDurationMin(distanceKm: number): number {
  return Math.round((distanceKm / AVG_URBAN_SPEED_KMH) * 60);
}

/**
 * Compute segment distances + durations for a daily plan
 * when the backend doesn't ship them (fallback for legacy data).
 */
function backfillSegments(plan: DailyPlan): DailyPlan {
  if (plan.segments && plan.segments.length > 0) return plan;
  const segments: RouteSegment[] = [];
  for (let i = 0; i < plan.pois.length - 1; i++) {
    const from = plan.pois[i];
    const to = plan.pois[i + 1];
    if (from?.lat != null && from?.lng != null && to?.lat != null && to?.lng != null) {
      const distance_km = haversineKm(from, to);
      segments.push({
        from_poi_id: from.id,
        to_poi_id: to.id,
        distance_km,
        duration_min: estimateDurationMin(distance_km),
      });
    }
  }
  return { ...plan, segments };
}

export const useMapStore = defineStore("map", () => {
  // ── State ──────────────────────────────────────────────────────────────────
  const pois = ref<POI[]>([]);
  const routes = ref<DailyPlan[]>([]);
  const selectedPOI = ref<POI | null>(null);
  const center = ref<MapCenter | null>(null);
  const zoom = ref<number>(13);
  const planSummary = ref<PlanSummary | null>(null);
  const activeDay = ref<number>(0); // 0 = all days, 1+ = specific day
  const timelineOpen = ref<boolean>(true);

  // ── POI selection for planning ─────────────────────────────────────────────
  const selectedPoiIds = ref<Set<string>>(new Set());
  const poiPanelOpen = ref(false);

  // ── Getters ────────────────────────────────────────────────────────────────
  const poiCount = computed(() => pois.value.length);
  const selectedPoiCount = computed(() => selectedPoiIds.value.size);
  const hasSelection = computed(() => selectedPOI.value !== null);
  const hasPlan = computed(() => planSummary.value !== null);

  const availableDays = computed<number[]>(() => {
    if (routes.value.length === 0) return [];
    return Array.from(
      new Set(routes.value.map((r) => r.day).filter((d) => d > 0)),
    ).sort((a, b) => a - b);
  });

  /** Sum of POIs across all days */
  const totalStopCount = computed<number>(() =>
    routes.value.reduce((acc, r) => acc + (r.pois?.length ?? 0), 0),
  );

  /** Sum of distance across all days (km) */
  const totalDistanceKm = computed<number>(() =>
    routes.value.reduce((acc, r) => acc + (r.total_distance_km ?? 0), 0),
  );

  /** Sum of travel duration across all days (minutes) */
  const totalDurationMin = computed<number>(() => {
    let total = 0;
    for (const r of routes.value) {
      for (const seg of r.segments ?? []) {
        total += seg.duration_min ?? estimateDurationMin(seg.distance_km ?? 0);
      }
    }
    return total;
  });

  // ── Actions ────────────────────────────────────────────────────────────────
  function setPOIs(newPOIs: POI[]): void {
    pois.value = [...newPOIs];
  }

  /**
   * Replace the routes state with a fresh daily-plans list.
   * Each plan gets its segments backfilled if absent (legacy data support).
   */
  function setRoutes(newRoutes: DailyPlan[]): void {
    routes.value = newRoutes.map((r) =>
      backfillSegments({
        day: r.day ?? 0,
        day_title: r.day_title,
        pois: r.pois ?? [],
        total_distance_km: r.total_distance_km ?? 0,
        total_duration_min: r.total_duration_min ?? 0,
        total_transit_min: r.total_transit_min ?? 0,
        segments: r.segments ?? [],
        polyline: (r as DailyPlan).polyline ?? '',
      }),
    );
  }

  function selectPOI(poi: POI): void {
    selectedPOI.value = poi;
    center.value = { lng: poi.lng, lat: poi.lat };
  }

  function clearSelection(): void {
    selectedPOI.value = null;
  }

  /**
   * Find the day number and stop index of a POI inside the current routes.
   * Returns null if the POI isn't part of any planned day.
   */
  function findPOIContext(poiId: number | string): {
    day: number;
    stopIndex: number;
    dayColor: string;
  } | null {
    for (const plan of routes.value) {
      const idx = plan.pois.findIndex((p) => p.id === poiId);
      if (idx !== -1) {
        const dayIdx = Math.min(
          Math.max((plan.day ?? 1) - 1, 0),
          DAY_COLORS.length - 1,
        );
        return {
          day: plan.day ?? 1,
          stopIndex: idx,
          dayColor: DAY_COLORS[dayIdx],
        };
      }
    }
    return null;
  }

  function clearMap(): void {
    pois.value = [];
    routes.value = [];
    selectedPOI.value = null;
    selectedPoiIds.value = new Set();
    center.value = null;
    planSummary.value = null;
    activeDay.value = 0;
  }

  function setCenter(newCenter: MapCenter): void {
    center.value = { ...newCenter };
  }

  function setZoom(newZoom: number): void {
    zoom.value = newZoom;
  }

  function setPlanSummary(summary: PlanSummary): void {
    planSummary.value = { ...summary };
  }

  function setActiveDay(day: number): void {
    activeDay.value = day;
  }

  // -- POI selection helpers ---------------------------------------------------

  function togglePoiSelection(poiId: string): void {
    const next = new Set(selectedPoiIds.value);
    if (next.has(poiId)) {
      next.delete(poiId);
    } else {
      next.add(poiId);
    }
    selectedPoiIds.value = next;
  }

  function isPoiSelected(poiId: string): boolean {
    return selectedPoiIds.value.has(poiId);
  }

  function selectAllPois(): void {
    selectedPoiIds.value = new Set(pois.value.map((p) => String(p.id)));
  }

  function deselectAllPois(): void {
    selectedPoiIds.value = new Set();
  }

  function getSelectedPois(): POI[] {
    const ids = selectedPoiIds.value;
    return pois.value.filter((p) => ids.has(String(p.id)));
  }

  function setPoiPanelOpen(open: boolean): void {
    poiPanelOpen.value = open;
  }

  function togglePoiPanel(): void {
    poiPanelOpen.value = !poiPanelOpen.value;
  }

  function toggleTimeline(): void {
    timelineOpen.value = !timelineOpen.value;
  }

  /** Let MapView sync timelineOpen when ItineraryTimeline's close button fires. */
  function closeTimeline(): void {
    timelineOpen.value = false;
  }

  return {
    // state
    pois,
    routes,
    selectedPOI,
    selectedPoiIds,
    poiPanelOpen,
    center,
    zoom,
    planSummary,
    activeDay,
    timelineOpen,
    // getters
    poiCount,
    selectedPoiCount,
    hasSelection,
    hasPlan,
    availableDays,
    totalStopCount,
    totalDistanceKm,
    totalDurationMin,
    // actions
    setPOIs,
    setRoutes,
    selectPOI,
    clearSelection,
    findPOIContext,
    clearMap,
    setCenter,
    setZoom,
    setPlanSummary,
    setActiveDay,
    toggleTimeline,
    closeTimeline,
    togglePoiSelection,
    isPoiSelected,
    selectAllPois,
    deselectAllPois,
    getSelectedPois,
    setPoiPanelOpen,
    togglePoiPanel,
  };
});
