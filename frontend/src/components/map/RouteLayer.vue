<script setup lang="ts">
import { computed, watch } from 'vue'
import { LPolyline, LMarker, LTooltip } from '@vue-leaflet/vue-leaflet'
import type { Icon, IconOptions } from 'leaflet'
import { useMapStore, type DailyPlan, type RoutePOI, type RouteSegment } from '@/stores/map'
import { createDivIcon, DAY_COLORS } from '@/utils/constants'

// ── Constants ──────────────────────────────────────────────────────────────
const AVG_CITY_SPEED_KMH = 30

/** Opacity for days that are currently NOT selected */
const FADED_OPACITY = 0.22
const ACTIVE_OPACITY = 0.92

// ── Store ──────────────────────────────────────────────────────────────────
const mapStore = useMapStore()

// ── Computed: all daily plans with normalised fields ───────────────────────
const dailyPlans = computed<DailyPlan[]>(() => {
  return (mapStore.routes as DailyPlan[]).map((r) => ({
    day: r.day ?? 0,
    day_title: r.day_title ?? '',
    pois: (r.pois ?? []) as RoutePOI[],
    total_distance_km: r.total_distance_km ?? 0,
    segments: (r.segments ?? []) as RouteSegment[],
  }))
})

/** Days that are currently considered "active" (visible at full opacity). */
const visibleDays = computed<Set<number>>(() => {
  const active = mapStore.activeDay
  if (active === 0) {
    return new Set(dailyPlans.value.map((p) => p.day))
  }
  return new Set([active])
})

// ── Computed: route polylines (one per day with >=2 valid POIs) ────────────
const routeLines = computed(() => {
  return dailyPlans.value
    .map((p) => {
      // Drop POIs with null/undefined coordinates BEFORE drawing the line,
      // otherwise Leaflet renders a polyline with a NaN point and the whole
      // route breaks (or worse, silently jumps to (0,0)).
      const validPois = (p.pois ?? []).filter(
        (poi) => typeof poi.lat === "number" && typeof poi.lng === "number",
      )
      if (validPois.length < 2) return null
      const isActive = visibleDays.value.has(p.day)
      return {
        key: `line-day-${p.day}`,
        coords: validPois.map((poi) => [poi.lat, poi.lng] as [number, number]),
        color: getDayColor(p.day),
        day: p.day,
        totalDistanceKm: p.total_distance_km,
        isActive,
        weight: isActive ? 5 : 3,
        opacity: isActive ? ACTIVE_OPACITY : FADED_OPACITY,
      }
    })
    .filter((x): x is NonNullable<typeof x> => x !== null)
})

// ── Computed: stop markers (start / end / intermediate) ────────────────────
const stopMarkers = computed(() => {
  const markers: Array<{
    key: string
    latLng: [number, number]
    icon: Icon<IconOptions>
    name: string
    category: string
    stopNumber: number
    dayColor: string
    day: number
    position: 'start' | 'end' | 'mid'
    isActive: boolean
    poiId: number | string
    rating?: number | null
    address?: string | null
    photo?: string | null
    description?: string | null
    tags?: string[]
  }> = []

  for (const plan of dailyPlans.value) {
    const color = getDayColor(plan.day)
    const isActive = visibleDays.value.has(plan.day)
    const count = plan.pois.length
    plan.pois.forEach((poi, idx) => {
      let position: 'start' | 'end' | 'mid' = 'mid'
      if (count === 1) position = 'start'
      else if (idx === 0) position = 'start'
      else if (idx === count - 1) position = 'end'

      markers.push({
        key: `stop-${plan.day}-${poi.id}-${idx}`,
        latLng: [poi.lat, poi.lng],
        icon: buildStopIcon(color, idx + 1, position, isActive),
        name: poi.name,
        category: poi.category,
        stopNumber: idx + 1,
        dayColor: color,
        day: plan.day,
        position,
        isActive,
        poiId: poi.id,
        rating: poi.rating,
        address: poi.address,
        photo: poi.photo ?? null,
        description: poi.description ?? null,
        tags: poi.tags,
      })
    })
  }
  return markers
})

// ── Computed: segment labels at midpoints ──────────────────────────────────
const segmentLabels = computed(() => {
  const labels: Array<{
    key: string
    latLng: [number, number]
    text: string
    isActive: boolean
  }> = []
  for (const plan of dailyPlans.value) {
    const isActive = visibleDays.value.has(plan.day)
    for (let i = 0; i < plan.pois.length - 1; i++) {
      const from = plan.pois[i]
      const to = plan.pois[i + 1]
      const seg = findSegment(plan.segments || [], from.id, to.id)
      const dist = seg?.distance_km ?? haversineKm(from, to)
      const dur = seg?.duration_min ?? estimateDurationMin(dist)
      labels.push({
        key: `seg-${plan.day}-${from.id}-${to.id}`,
        latLng: [(from.lat + to.lat) / 2, (from.lng + to.lng) / 2],
        text: `${formatDistance(dist)} · ${formatDuration(dur)}`,
        isActive,
      })
    }
  }
  return labels
})

// ── Click handler: select a POI on the map ─────────────────────────────────
function onMarkerClick(marker: {
  poiId: number | string
  name: string
  category: string
  latLng: [number, number]
  rating?: number | null
  address?: string | null
  photo?: string | null
  description?: string | null
  tags?: string[]
}): void {
  mapStore.selectPOI({
    id: marker.poiId,
    name: marker.name,
    category: marker.category,
    address: marker.address ?? null,
    lng: marker.latLng[1],
    lat: marker.latLng[0],
    rating: marker.rating ?? null,
    review_count: null,
    tags: marker.tags ?? [],
    photo: marker.photo ?? undefined,
    description: marker.description ?? undefined,
  })
}

// ── Helpers ────────────────────────────────────────────────────────────────

function getDayColor(day: number): string {
  if (day < 1) return DAY_COLORS[0]
  const idx = Math.min(day - 1, DAY_COLORS.length - 1)
  return DAY_COLORS[idx]
}

function estimateDurationMin(distanceKm: number): number {
  return Math.round((distanceKm / AVG_CITY_SPEED_KMH) * 60)
}

function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)}m`
  return `${km.toFixed(1)}km`
}

function formatDuration(min: number): string {
  if (min < 1) return '<1min'
  if (min < 60) return `~${min}min`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m === 0 ? `~${h}h` : `~${h}h${m}min`
}

function haversineKm(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
): number {
  const R = 6371
  const dLat = ((b.lat - a.lat) * Math.PI) / 180
  const dLng = ((b.lng - a.lng) * Math.PI) / 180
  const aRad = (a.lat * Math.PI) / 180
  const bRad = (b.lat * Math.PI) / 180
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(aRad) * Math.cos(bRad) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x))
}

function findSegment(
  segments: RouteSegment[],
  fromId: number | string,
  toId: number | string,
): RouteSegment | undefined {
  // Normalize IDs to strings so a numeric "1" and string "1" both match —
  // otherwise segments silently fall back to haversine distance and the
  // displayed route mismatches the planned route.
  const from = String(fromId)
  const to = String(toId)
  return segments.find(
    (s) => String(s.from_poi_id) === from && String(s.to_poi_id) === to,
  )
}

/**
 * Build a numbered circle divIcon for a POI stop along the route.
 * - START: slightly larger, ring + inner dot (origin of the day)
 * - END:   small flag marker (destination)
 * - MID:   default numbered circle
 */
function buildStopIcon(
  dayColor: string,
  stopNumber: number,
  position: 'start' | 'end' | 'mid',
  isActive: boolean,
): Icon<IconOptions> {
  const opacity = isActive ? 1 : 0.45
  let html: string
  let size: [number, number]
  let anchor: [number, number]

  if (position === 'start') {
    size = [34, 34]
    anchor = [17, 17]
    html = `
      <div class="rte-stop rte-stop--start" style="opacity:${opacity}">
        <div class="rte-stop__ring" style="background:${dayColor};box-shadow:0 0 0 3px rgba(255,255,255,0.9), 0 2px 8px rgba(0,0,0,0.35)">
          <span class="rte-stop__num">${stopNumber}</span>
        </div>
        <div class="rte-stop__tail" style="background:${dayColor}"></div>
      </div>`
  } else if (position === 'end') {
    size = [30, 36]
    anchor = [15, 36]
    html = `
      <div class="rte-stop rte-stop--end" style="opacity:${opacity}">
        <div class="rte-stop__pin" style="background:${dayColor}">
          <span class="rte-stop__flag">⚑</span>
        </div>
      </div>`
  } else {
    size = [26, 26]
    anchor = [13, 13]
    html = `
      <div class="rte-stop rte-stop--mid" style="opacity:${opacity}">
        <div class="rte-stop__dot" style="background:${dayColor}">
          <span>${stopNumber}</span>
        </div>
      </div>`
  }

  return createDivIcon({
    className: 'rte-stop-icon',
    html,
    iconSize: size,
    iconAnchor: anchor,
  })
}

/** Transparent zero-size icon for segment label anchors */
const invisibleIcon = createDivIcon({
  className: 'rte-seg-anchor',
  html: '',
  iconSize: [0, 0],
})

// ── Watch activeDay: force re-render of marker icons by bumping a key ──────
// Reactivity is handled by the `stopMarkers` computed which depends on
// `visibleDays`, which in turn depends on `mapStore.activeDay`.
// No additional watch needed.
</script>

<template>
  <!-- Route polylines — white outline underneath for separation -->
  <template v-for="line in routeLines" :key="`${line.key}-wrap`">
    <l-polyline
      :lat-lngs="line.coords"
      :color="'#ffffff'"
      :weight="line.weight + 4"
      :opacity="line.isActive ? 0.9 : 0.35"
      :smooth-factor="1.5"
      :interactive="false"
    />
    <l-polyline
      :lat-lngs="line.coords"
      :color="line.color"
      :weight="line.weight"
      :opacity="line.opacity"
      :smooth-factor="1.5"
      line-cap="round"
      line-join="round"
    >
      <l-tooltip>
        <span class="rte-day-label">
          <span class="rte-day-label__dot" :style="{ background: line.color }"></span>
          Day {{ line.day }} · {{ formatDistance(line.totalDistanceKm ?? 0) }}
        </span>
      </l-tooltip>
    </l-polyline>
  </template>

  <l-marker
    v-for="stop in stopMarkers"
    :key="stop.key"
    :lat-lng="stop.latLng"
    :icon="stop.icon"
    :z-index-offset="stop.isActive ? (stop.position === 'start' ? 1000 : 500) : 0"
    @click="onMarkerClick(stop)"
  >
    <l-tooltip>
      <div class="rte-stop-popup">
        <div class="rte-stop-popup__head">
          <span class="rte-stop-popup__num" :style="{ background: stop.dayColor }">
            {{ stop.stopNumber }}
          </span>
          <strong>{{ stop.name }}</strong>
        </div>
        <div class="rte-stop-popup__meta">
          <span v-if="stop.category" class="rte-chip">{{ stop.category }}</span>
          <span v-if="stop.rating != null" class="rte-chip rte-chip--rating">★ {{ Number(stop.rating).toFixed(1) }}</span>
        </div>
        <div class="rte-stop-popup__hint">Day {{ stop.day }} · {{ stop.position === 'start' ? '起点' : stop.position === 'end' ? '终点' : '途经' }}</div>
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
    <l-tooltip
      :permanent="label.isActive"
      direction="center"
      :offset="[0, 0]"
      :class-name="label.isActive ? 'rte-seg-tip rte-seg-tip--active' : 'rte-seg-tip'"
    >
      <span class="rte-seg-label">{{ label.text }}</span>
    </l-tooltip>
  </l-marker>
</template>

<style>
/* ── Route stop markers ───────────────────────────────────────────────────── */

.rte-stop-icon {
  background: transparent !important;
  border: none !important;
}

.rte-stop {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform var(--transition-fast);
  cursor: pointer;
}

.rte-stop:hover {
  transform: scale(1.12);
  z-index: 2000 !important;
}

/* Middle: simple numbered circle */
.rte-stop--mid .rte-stop__dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
  font-weight: 700;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
  line-height: 1;
}

.rte-stop--mid .rte-stop__dot span {
  transform: translateY(-0.5px);
}

/* Start: larger circle with pin tail */
.rte-stop--start {
  width: 34px;
  height: 40px;
}

.rte-stop--start .rte-stop__ring {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: var(--font-size-base);
  position: relative;
  z-index: 2;
}

.rte-stop--start .rte-stop__num {
  line-height: 1;
}

.rte-stop--start .rte-stop__tail {
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 8px solid currentColor;
  margin-top: -2px;
  position: relative;
  z-index: 1;
}

/* End: flag pin */
.rte-stop--end {
  width: 30px;
  height: 36px;
}

.rte-stop--end .rte-stop__pin {
  width: 24px;
  height: 30px;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
}

.rte-stop--end .rte-stop__flag {
  transform: rotate(45deg);
  color: #fff;
  font-size: 13px;
  line-height: 1;
}

/* ── Popup inside tooltip ─────────────────────────────────────────────────── */

.rte-stop-popup {
  min-width: 140px;
  padding: 2px 0;
}

.rte-stop-popup__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.rte-stop-popup__num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.rte-stop-popup__head strong {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.3;
}

.rte-stop-popup__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 4px;
}

.rte-chip {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.rte-chip--rating {
  background: var(--color-note-bg);
  color: var(--color-warning);
}

.rte-stop-popup__hint {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}

/* ── Day label in polyline tooltip ────────────────────────────────────────── */

.rte-day-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
}

.rte-day-label__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

/* ── Segment labels ───────────────────────────────────────────────────────── */

.rte-seg-anchor {
  background: transparent !important;
  border: none !important;
}

.rte-seg-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-primary);
  background: rgba(255, 255, 255, 0.96);
  padding: 2px 7px;
  border-radius: var(--radius-pill);
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(0, 0, 0, 0.05);
  letter-spacing: 0.01em;
}

.rte-seg-tip .leaflet-tooltip {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
  opacity: 0.85;
}

.rte-seg-tip--active .leaflet-tooltip {
  opacity: 1;
}

/* Override default leaflet tooltip arrow for segment tips */
.rte-seg-tip.leaflet-tooltip::before {
  display: none;
}
</style>
