<script setup lang="ts">
import { computed, watch } from 'vue'
import { LPolyline, LMarker, LTooltip } from '@vue-leaflet/vue-leaflet'
import type { Icon, IconOptions } from 'leaflet'
import { useMapStore, type DailyPlan, type RoutePOI, type RouteSegment } from '@/stores/map'
import { createDivIcon, DAY_COLORS } from '@/utils/constants'

// ── Constants ──────────────────────────────────────────────────────────────
const AVG_CITY_SPEED_KMH = 30
const FADED_OPACITY = 0.22
const ACTIVE_OPACITY = 0.92

// ── Store ──────────────────────────────────────────────────────────────────
const mapStore = useMapStore()

// ── Polyline decoder ───────────────────────────────────────────────────────
function decodeAmapPolyline(polyline: string): [number, number][] {
  if (!polyline) return []
  return polyline
    .split(';')
    .map((pair) => {
      const [lng, lat] = pair.split(',').map(Number)
      return [lat, lng] as [number, number]
    })
    .filter(([lat, lng]) => !isNaN(lat) && !isNaN(lng))
}

// ── Computed: all daily plans with normalised fields ───────────────────────
const dailyPlans = computed<DailyPlan[]>(() => {
  return (mapStore.routes as DailyPlan[]).map((r) => ({
    day: r.day ?? 0,
    day_title: r.day_title ?? '',
    pois: (r.pois ?? []) as RoutePOI[],
    total_distance_km: r.total_distance_km ?? 0,
    segments: (r.segments ?? []) as RouteSegment[],
    polyline: (r as DailyPlan).polyline ?? '',
  }))
})

const visibleDays = computed<Set<number>>(() => {
  const active = mapStore.activeDay
  if (active === 0) return new Set(dailyPlans.value.map((p) => p.day))
  return new Set([active])
})

// ── Computed: route polylines ──────────────────────────────────────────────
const routeLines = computed(() => {
  return dailyPlans.value
    .map((p) => {
      const isActive = visibleDays.value.has(p.day)
      let coords: [number, number][]
      // Prefer Amap real-road polyline; fallback to straight-line POI coords
      if (p.polyline) {
        coords = decodeAmapPolyline(p.polyline)
        if (coords.length < 2) coords = []
      } else {
        coords = []
      }
      if (coords.length < 2) {
        const validPois = (p.pois ?? []).filter(
          (poi) => typeof poi.lat === 'number' && typeof poi.lng === 'number',
        )
        if (validPois.length < 2) return null
        coords = validPois.map((poi) => [poi.lat, poi.lng] as [number, number])
      }
      return {
        key: `line-day-${p.day}`,
        coords,
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
        photo: poi.photo,
        description: poi.description,
        tags: poi.tags as string[] | undefined,
      })
    })
  }
  return markers
})

// ── Helpers ────────────────────────────────────────────────────────────────
function getDayColor(day: number): string {
  return DAY_COLORS[(day - 1) % DAY_COLORS.length]!
}

function buildStopIcon(
  color: string,
  num: number,
  position: string,
  isActive: boolean,
): Icon<IconOptions> {
  const size = position === 'start' || position === 'end' ? 28 : 24
  const opacity = isActive ? 1 : 0.35
  const html = `<div style="
    width:${size}px;height:${size}px;
    background:${color};opacity:${opacity};
    border-radius:50%;display:flex;align-items:center;justify-content:center;
    color:#fff;font-size:11px;font-weight:700;
    border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.3);
  ">${num}</div>`
  return createDivIcon({ html, className: 'rte-stop-marker', iconSize: [size, size] })
}

function haversineKm(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const R = 6371
  const dLat = ((b.lat - a.lat) * Math.PI) / 180
  const dLng = ((b.lng - a.lng) * Math.PI) / 180
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a.lat * Math.PI) / 180) *
      Math.cos((b.lat * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x))
}

function estimateDurationMin(distanceKm: number): number {
  return Math.round((distanceKm / AVG_CITY_SPEED_KMH) * 60)
}

function findSegment(
  segments: RouteSegment[],
  fromId: number | string | undefined,
  toId: number | string | undefined,
): RouteSegment | undefined {
  if (!fromId || !toId) return undefined
  return segments.find(
    (s) =>
      String(s.from_poi_id) === String(fromId) && String(s.to_poi_id) === String(toId),
  )
}

function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)}m`
  return `${km.toFixed(1)}km`
}

function formatDuration(min: number): string {
  if (min < 60) return `~${Math.round(min)}min`
  const h = Math.floor(min / 60)
  const m = Math.round(min % 60)
  return m > 0 ? `~${h}h${m}min` : `~${h}h`
}

// ── Segment label markers ──────────────────────────────────────────────────
interface SegmentLabel {
  key: string
  latLng: [number, number]
  text: string
  isActive: boolean
}

const segmentLabels = computed<SegmentLabel[]>(() => {
  const labels: SegmentLabel[] = []
  for (const plan of dailyPlans.value) {
    const isActive = visibleDays.value.has(plan.day)
    const pois = plan.pois
    for (let i = 0; i < pois.length - 1; i++) {
      const from = pois[i]
      const to = pois[i + 1]
      if (!from?.lat || !from?.lng || !to?.lat || !to?.lng) continue

      const midLat = (from.lat + to.lat) / 2
      const midLng = (from.lng + to.lng) / 2

      const seg = i < (plan.segments?.length ?? 0)
        ? plan.segments![i]
        : findSegment(plan.segments ?? [], from.id, to.id)

      const dist = seg?.distance_km ?? haversineKm(from, to)
      const dur = seg?.duration_min ?? estimateDurationMin(dist)
      const modeText = seg?.mode ? `${_modeIcon(seg.mode)} ` : ''

      labels.push({
        key: `seg-${plan.day}-${from.id}-${to.id}`,
        latLng: [midLat, midLng],
        text: `${modeText}${formatDistance(dist)} · ${formatDuration(dur)}`,
        isActive,
      })
    }
  }
  return labels
})

function _modeIcon(mode: string): string {
  const icons: Record<string, string> = {
    driving: '🚗',
    walking: '🚶',
    bicycling: '🚴',
    transit: '🚌',
  }
  return icons[mode] || ''
}

const invisibleIcon = createDivIcon({
  className: 'rte-seg-anchor',
  html: '',
  iconSize: [0, 0],
})
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
  >
    <l-tooltip>
      <span class="rte-stop-name">{{ stop.name }}</span>
      <span v-if="stop.category" class="rte-stop-cat">{{ stop.category }}</span>
    </l-tooltip>
  </l-marker>

  <l-marker
    v-for="label in segmentLabels"
    :key="label.key"
    :lat-lng="label.latLng"
    :icon="invisibleIcon"
    :z-index-offset="-1"
  >
    <l-tooltip :options="{ permanent: label.isActive, direction: 'center', className: 'rte-seg-tooltip' }">
      <span :class="['rte-seg-text', { 'rte-seg-text--faded': !label.isActive }]">
        {{ label.text }}
      </span>
    </l-tooltip>
  </l-marker>
</template>

<style scoped>
.rte-day-label {
  font-size: 0.75rem;
  font-weight: 500;
}
.rte-day-label__dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
}
.rte-stop-name {
  font-weight: 600;
  font-size: 0.8rem;
}
.rte-stop-cat {
  display: block;
  font-size: 0.7rem;
  color: var(--color-text-secondary);
}
.rte-seg-text {
  font-size: 0.65rem;
  background: var(--color-bg-elevated);
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
}
.rte-seg-text--faded {
  opacity: 0.35;
}
</style>
