<script setup lang="ts">
import { computed } from 'vue'
import { LPolyline, LMarker, LTooltip } from '@vue-leaflet/vue-leaflet'
import { divIcon } from 'leaflet'
import { useMapStore, type RouteData } from '@/stores/map'

// ── Types ──────────────────────────────────────────────────────────────────
interface DailyPlan {
  day: number
  pois: RoutePOI[]
  total_distance_km: number
  segments: RouteSegment[]
}

interface RoutePOI {
  id: number
  name: string
  category: string
  lng: number
  lat: number
  rating: number
  day_order?: number
  [key: string]: unknown
}

interface RouteSegment {
  from_poi_id: number | undefined
  to_poi_id: number | undefined
  distance_km: number
}

/** Shape for each rendered segment label */
interface SegmentLabel {
  key: string
  latLng: [number, number]
  text: string
}

/** Shape for each rendered POI stop marker */
interface StopMarker {
  key: string
  latLng: [number, number]
  icon: ReturnType<typeof divIcon>
  name: string
  category: string
  stopNumber: number
  dayColor: string
}

/** Shape for each rendered polyline */
interface RouteLine {
  key: string
  coords: [number, number][]
  color: string
  day: number
  totalDistanceKm: number
}

// ── Constants ──────────────────────────────────────────────────────────────
const DAY_COLORS = ['#1890ff', '#52c41a', '#fa8c16', '#a855f7'] as const
const AVG_CITY_SPEED_KMH = 30

// ── Store ──────────────────────────────────────────────────────────────────
const mapStore = useMapStore()

// ── Computed: parsed daily plans ───────────────────────────────────────────
const dailyPlans = computed<DailyPlan[]>(() => {
  return (mapStore.routes as RouteData[]).map((r) => ({
    day: (r.day as number) ?? 0,
    pois: (r.pois as RoutePOI[]) ?? [],
    total_distance_km: (r.total_distance_km as number) ?? 0,
    segments: (r.segments as RouteSegment[]) ?? [],
  }))
})

// ── Computed: route lines (one per day with >=2 POIs) ──────────────────────
const routeLines = computed<RouteLine[]>(() => {
  return dailyPlans.value
    .filter((p) => p.pois.length >= 2)
    .map((p) => ({
      key: `line-day-${p.day}`,
      coords: p.pois.map((poi) => [poi.lat, poi.lng] as [number, number]),
      color: getDayColor(p.day),
      day: p.day,
      totalDistanceKm: p.total_distance_km,
    }))
})

// ── Computed: all stop markers across all days ─────────────────────────────
const stopMarkers = computed<StopMarker[]>(() => {
  const markers: StopMarker[] = []
  for (const plan of dailyPlans.value) {
    const color = getDayColor(plan.day)
    plan.pois.forEach((poi, idx) => {
      markers.push({
        key: `stop-${plan.day}-${poi.id}-${idx}`,
        latLng: [poi.lat, poi.lng],
        icon: buildStopIcon(color, idx + 1),
        name: poi.name,
        category: poi.category,
        stopNumber: idx + 1,
        dayColor: color,
      })
    })
  }
  return markers
})

// ── Computed: segment labels at midpoints ──────────────────────────────────
const segmentLabels = computed<SegmentLabel[]>(() => {
  const labels: SegmentLabel[] = []
  for (const plan of dailyPlans.value) {
    for (let i = 0; i < plan.pois.length - 1; i++) {
      const from = plan.pois[i]
      const to = plan.pois[i + 1]
      const seg = findSegment(plan.segments, from.id, to.id)
      const dist = seg ? seg.distance_km : 0
      const dur = estimateDurationMin(dist)
      labels.push({
        key: `seg-${plan.day}-${from.id}-${to.id}`,
        latLng: [(from.lat + to.lat) / 2, (from.lng + to.lng) / 2],
        text: `${dist.toFixed(1)}km · ~${dur}min`,
      })
    }
  }
  return labels
})

// ── Helpers ────────────────────────────────────────────────────────────────

/**
 * Get color for a given day number (1-indexed).
 * Days 1-3 have distinct colors, day 4+ uses the last color (purple).
 */
function getDayColor(day: number): string {
  if (day < 1) return DAY_COLORS[0]
  const idx = Math.min(day - 1, DAY_COLORS.length - 1)
  return DAY_COLORS[idx]
}

/**
 * Estimate duration in minutes from distance in km.
 */
function estimateDurationMin(distanceKm: number): number {
  return Math.round((distanceKm / AVG_CITY_SPEED_KMH) * 60)
}

/**
 * Build a numbered circle divIcon for a POI stop along the route.
 */
function buildStopIcon(dayColor: string, stopNumber: number) {
  return divIcon({
    className: 'route-stop-icon',
    html: `<div class="route-stop-inner" style="background:${dayColor};border-color:${dayColor}"><span>${stopNumber}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })
}

/**
 * Find a segment by its from/to POI IDs.
 */
function findSegment(
  segments: RouteSegment[],
  fromId: number,
  toId: number,
): RouteSegment | undefined {
  return segments.find(
    (s) => s.from_poi_id === fromId && s.to_poi_id === toId,
  )
}

/** Transparent zero-size icon for segment label anchors */
const invisibleIcon = divIcon({
  className: 'route-segment-anchor',
  html: '',
  iconSize: [0, 0],
})
</script>

<template>
  <!-- Route polylines -->
  <l-polyline
    v-for="line in routeLines"
    :key="line.key"
    :lat-lngs="line.coords"
    :color="line.color"
    :weight="4"
    :opacity="0.85"
    :smooth-factor="1"
  >
    <l-tooltip>
      <span class="route-day-label">
        Day {{ line.day }} · {{ line.totalDistanceKm.toFixed(1) }} km
      </span>
    </l-tooltip>
  </l-polyline>

  <!-- Numbered stop markers at each POI -->
  <l-marker
    v-for="stop in stopMarkers"
    :key="stop.key"
    :lat-lng="stop.latLng"
    :icon="stop.icon"
  >
    <l-tooltip>
      <div class="route-stop-popup">
        <strong>{{ stop.stopNumber }}. {{ stop.name }}</strong>
        <span v-if="stop.category" class="route-stop-cat">{{ stop.category }}</span>
      </div>
    </l-tooltip>
  </l-marker>

  <!-- Segment distance/duration labels -->
  <l-marker
    v-for="label in segmentLabels"
    :key="label.key"
    :lat-lng="label.latLng"
    :icon="invisibleIcon"
    :interactive="false"
  >
    <l-tooltip :permanent="true" direction="center" :offset="[0, 0]">
      <span class="route-seg-label">{{ label.text }}</span>
    </l-tooltip>
  </l-marker>
</template>

<style>
/* Global styles — Leaflet renders outside Vue's scoped DOM */

.route-stop-icon {
  background: transparent !important;
  border: none !important;
}

.route-stop-inner {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: 700;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  border: 2px solid #fff;
  transition: transform var(--transition-fast);
}

.route-stop-inner:hover {
  transform: scale(1.15);
}

.route-stop-inner span {
  line-height: 1;
}

.route-segment-anchor {
  background: transparent !important;
  border: none !important;
}

.route-day-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  white-space: nowrap;
}

.route-stop-popup {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.route-stop-popup strong {
  font-size: 13px;
}

.route-stop-cat {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.route-seg-label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-primary);
  background: rgba(255, 255, 255, 0.95);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}
</style>
