<script setup lang="ts">
import { watch, computed, shallowRef, ref, onMounted, onUnmounted } from 'vue'
import { LMap, LTileLayer } from '@vue-leaflet/vue-leaflet'
import { latLngBounds } from 'leaflet'
import type { POI } from '@/types'
import { useMapStore, type DailyPlan } from '@/stores/map'
import PoiMarker from './PoiMarker.vue'
import RouteLayer from './RouteLayer.vue'
import ItineraryTimeline from './ItineraryTimeline.vue'
import POIDetailCard from './POIDetailCard.vue'
import TripListDrawer from './TripListDrawer.vue'
import PoiSelectPanel from './PoiSelectPanel.vue'
import { useTripStore } from '@/stores/trip'

// ── Constants ───────────────────────────────────────────────────────────────
const DEFAULT_CENTER: [number, number] = [39.9, 116.4]
const DEFAULT_ZOOM = 12
const FLY_DURATION = 1.2

// ── Store ────────────────────────────────────────────────────────────────────
const mapStore = useMapStore()
const tripStore = useTripStore()

// ── Reactive State ───────────────────────────────────────────────────────────
const activePanel = ref<'trips' | null>(null)
const pois = computed(() => mapStore.pois)
const routes = computed(() => mapStore.routes)
const hasRoutes = computed(() => routes.value.length > 0)
const showPoiButton = computed(() => pois.value.length > 0 && !hasRoutes.value)
const showPoiPanel = computed(() => showPoiButton.value && mapStore.poiPanelOpen)
const selectedPOI = computed(() => mapStore.selectedPOI)
const leafletMap = shallowRef<L.Map | null>(null)

const selectedPOIContext = computed(() => {
  if (!selectedPOI.value) return null
  return mapStore.findPOIContext(selectedPOI.value.id)
})

const mapCenter = computed<[number, number]>(() => {
  if (mapStore.center) {
    return [mapStore.center.lat, mapStore.center.lng]
  }
  return DEFAULT_CENTER
})

const mapZoom = computed(() => mapStore.zoom ?? DEFAULT_ZOOM)

// ── Tile Layer ───────────────────────────────────────────────────────────────
const isDark = ref(true) // Default to dark — matches the editorial canvas
const darkModeOverride = ref<boolean | null>(null)

const effectiveDark = computed(() => {
  return darkModeOverride.value !== null ? darkModeOverride.value : isDark.value
})

const checkDarkMode = () => {
  isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
}

function toggleDarkMode(): void {
  if (darkModeOverride.value === null) {
    darkModeOverride.value = !effectiveDark.value
  } else if (darkModeOverride.value) {
    darkModeOverride.value = false
  } else {
    darkModeOverride.value = null
  }
}

let mediaQuery: MediaQueryList | null = null

onMounted(() => {
  checkDarkMode()
  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', checkDarkMode)
})

onUnmounted(() => {
  if (mediaQuery) {
    mediaQuery.removeEventListener('change', checkDarkMode)
  }
})

const tileUrl = computed(() => {
  return 'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}'
})
const tileSubdomains = '1234'

function onMapReady(map: L.Map): void {
  leafletMap.value = map
  flyToBounds(map, pois.value)
}

watch(
  [pois, routes],
  ([newPois, newRoutes]) => {
    const map = leafletMap.value
    if (!map) return
    if (newRoutes.length > 0) {
      flyToBoundsFromRoutes(newRoutes as DailyPlan[])
    } else if (newPois.length > 0) {
      flyToBounds(map, newPois)
    }
  },
)

watch(
  () => mapStore.selectedPOI,
  (poi) => {
    const map = leafletMap.value
    if (!map || !poi) return
    map.flyTo([poi.lat, poi.lng], 15, { duration: FLY_DURATION })
  },
)

function flyToBoundsFromRoutes(routeList: DailyPlan[]): void {
  const allPois = routeList
    .filter((r) => (r.pois?.length ?? 0) >= 2)
    .flatMap((r) => r.pois ?? [])
  if (allPois.length === 0) return

  const lngs = allPois.map((p) => p.lng)
  const lats = allPois.map((p) => p.lat)
  const bounds = latLngBounds(
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)],
  )
  leafletMap.value?.flyToBounds(bounds, {
    padding: [80, 80],
    maxZoom: 15,
    duration: FLY_DURATION,
  })
}

function flyToBounds(map: L.Map, poiList: POI[]): void {
  if (poiList.length === 0) return

  const lngs = poiList.map((p) => p.lng)
  const lats = poiList.map((p) => p.lat)
  const bounds = latLngBounds(
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)],
  )
  map.flyToBounds(bounds, {
    padding: [80, 80],
    maxZoom: 15,
    duration: FLY_DURATION,
  })
}

function onPoiSelect(poi: POI): void {
  mapStore.selectPOI(poi)
}

function onPOICardClose(): void {
  mapStore.clearSelection()
}

function onTimelineClick(): void {
  if (mapStore.timelineOpen) {
    mapStore.timelineOpen = false
  } else {
    activePanel.value = null            // mutually exclusive
    mapStore.timelineOpen = true
  }
}

function onTripsClick(): void {
  if (activePanel.value === 'trips') {
    activePanel.value = null
  } else {
    mapStore.timelineOpen = false        // mutually exclusive
    activePanel.value = 'trips'
  }
}
</script>

<template>
  <div class="map-container" :class="{ 'dark-mode': effectiveDark }">
    <l-map
      :center="mapCenter"
      :zoom="mapZoom"
      @ready="onMapReady"
    >
      <l-tile-layer
        :url="tileUrl"
        :subdomains="tileSubdomains"
        layer-type="base"
        name="高德地图"
        attribution="&copy; 高德地图"
      />

      <RouteLayer />

      <PoiMarker
        v-if="!hasRoutes"
        v-for="(poi, index) in pois"
        :key="poi.id"
        :poi="poi"
        :index="index"
        @select="onPoiSelect"
      />
    </l-map>

    <!-- Top-left: segmented nav bar — 查看行程 + 历史规划 -->
    <div class="map-navbar">
      <button
        v-if="hasRoutes"
        class="map-navbar__btn"
        :class="{ 'is-active': mapStore.timelineOpen }"
        title="行程规划"
        @click="onTimelineClick"
      >
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M3 6h18M3 12h12M3 18h6" stroke-linecap="round" />
        </svg>
        <span>行程规划</span>
      </button>
      <button
        class="map-navbar__btn"
        :class="{ 'is-active': activePanel === 'trips' }"
        title="历史规划"
        @click="onTripsClick"
      >
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.4">
          <path d="M4 7l8-4 8 4-8 4-8-4z" />
          <path d="M4 12l8 4 8-4M4 17l8 4 8-4" stroke-linejoin="round" />
        </svg>
        <span>历史规划</span>
        <span v-if="tripStore.tripCount > 0" class="map-navbar__badge numeric">{{ tripStore.tripCount }}</span>
      </button>
    </div>

    <!-- 历史规划 panel — below the navbar -->
    <div v-if="activePanel === 'trips'" class="map-panel">
      <TripListDrawer @close="activePanel = null" />
    </div>

    <!-- POI 兴趣点选择面板 — browse mode only -->
    <div v-if="showPoiPanel" class="map-panel">
      <PoiSelectPanel @close="mapStore.setPoiPanelOpen(false)" />
    </div>

    <!-- 查看行程 panel — ItineraryTimeline in the same .map-panel slot -->
    <div v-if="hasRoutes && mapStore.timelineOpen" class="map-panel">
      <ItineraryTimeline />
    </div>

    <!-- Floating POI button — visible when browse-mode POIs are loaded -->
    <button
      v-if="showPoiButton"
      class="map-poi-btn"
      @click="mapStore.togglePoiPanel()"
    >
      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round" />
        <circle cx="12" cy="10" r="3" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span>兴趣点</span>
      <span class="map-poi-btn__badge">{{ mapStore.poiCount }}</span>
    </button>

    <button
      class="map-dark-toggle"
      :title="effectiveDark ? '切换浅色' : '切换深色'"
      @click="toggleDarkMode"
    >
      <svg v-if="effectiveDark" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" stroke-linecap="round" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke-linejoin="round" />
      </svg>
    </button>

    <div
      v-if="hasRoutes && !mapStore.timelineOpen && mapStore.availableDays.length > 1"
      class="day-filter"
    >
      <button
        class="day-filter__btn"
        :class="{ active: mapStore.activeDay === 0 }"
        @click="mapStore.setActiveDay(0)"
      >
        <span class="day-filter__index">∗</span>
        <span>全部</span>
      </button>
      <button
        v-for="day in mapStore.availableDays"
        :key="day"
        class="day-filter__btn"
        :class="{ active: mapStore.activeDay === day }"
        @click="mapStore.setActiveDay(day)"
      >
        <span class="day-filter__index numeric">{{ day.toString().padStart(2, '0') }}</span>
        <span>Day</span>
      </button>
    </div>

    <POIDetailCard
      v-if="selectedPOI"
      :poi="selectedPOI"
      :day="selectedPOIContext?.day"
      :stop-number="selectedPOIContext ? selectedPOIContext.stopIndex + 1 : undefined"
      :accent-color="selectedPOIContext?.dayColor ?? '#e8623c'"
      @close="onPOICardClose"
    />

    <div class="map-vignette" aria-hidden="true"></div>
  </div>
</template>

<style scoped>
.map-container {
  width: 100%;
  height: 100%;
  min-height: 300px;
  position: relative;
  background: var(--color-bg-deep);
  /* Establish a stacking context so children's z-index (POI card,
     timeline, etc.) is honored against the leaflet tile-pane which
     uses z-index 200 internally. */
  isolation: isolate;
  z-index: 0;
}

/* Dark-mode tile treatment: invert + warm duotone */
.map-container.dark-mode :deep(.leaflet-tile) {
  filter: invert(1) hue-rotate(190deg) brightness(0.78) contrast(0.92) saturate(0.85);
}
.map-container.dark-mode :deep(.leaflet-container) {
  background: var(--color-bg-deep);
}
.map-container:not(.dark-mode) :deep(.leaflet-tile) {
  filter: saturate(0.6) contrast(0.92) brightness(0.96);
}
.map-container:not(.dark-mode) :deep(.leaflet-container) {
  background: #f1ebe1;
}

/* Day filter — editorial numbered tabs */
.day-filter {
  position: absolute;
  top: var(--space-xl);
  left: 50%;
  transform: translateX(-50%);
  z-index: 1100;
  display: flex;
  gap: var(--space-2xs);
  padding: var(--space-xs);
  background: rgba(20, 24, 31, 0.78);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-md);
  animation: filter-fade-in var(--duration-normal) var(--ease-out-expo);
}

@keyframes filter-fade-in {
  from { opacity: 0; transform: translate(-50%, -6px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}

.day-filter__btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  font-weight: 500;
  color: var(--color-text-secondary);
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  transition: all var(--duration-fast) var(--ease-out-expo);
  white-space: nowrap;
}

.day-filter__btn:hover {
  color: var(--color-text-primary);
  background: rgba(243, 236, 225, 0.04);
}

.day-filter__btn.active {
  background: var(--color-text-primary);
  color: var(--color-bg-deep);
}

.day-filter__index {
  font-family: var(--font-serif);
  font-size: var(--text-body);
  font-weight: 500;
  font-style: italic;
  letter-spacing: 0;
  text-transform: none;
  opacity: 0.7;
}

.day-filter__btn.active .day-filter__index {
  opacity: 1;
}

/* Top-left segmented nav bar */
.map-navbar {
  position: absolute;
  top: var(--space-xl);
  left: var(--space-xl);
  z-index: 1150;
  display: flex;
  gap: var(--space-2xs);
  padding: var(--space-xs);
  background: rgba(20, 24, 31, 0.78);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-md);
}

/* Dark/light mode toggle — top-right */
.map-dark-toggle {
  position: absolute;
  top: var(--space-xl);
  right: var(--space-xl);
  z-index: 1150;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(20, 24, 31, 0.78);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-circle);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  box-shadow: var(--shadow-md);
}

.map-dark-toggle:hover {
  color: var(--color-text-primary);
  background: rgba(243, 236, 225, 0.08);
}

/* ── Floating POI button ───────────────────────────────────────────────── */
.map-poi-btn {
  position: absolute;
  bottom: var(--space-xl);
  left: var(--space-xl);
  z-index: 1150;
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  background: rgba(20, 24, 31, 0.78);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-pill);
  color: var(--color-text-secondary);
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  font-weight: 500;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  box-shadow: var(--shadow-md);
}
.map-poi-btn:hover {
  color: var(--color-text-primary);
  background: rgba(243, 236, 225, 0.08);
  border-color: var(--color-accent);
}
.map-poi-btn__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: var(--color-accent);
  color: #fff;
  font-size: 0.625rem;
  font-weight: 600;
}

.map-navbar__btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  font-weight: 500;
  color: var(--color-text-secondary);
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  transition: all var(--duration-fast) var(--ease-out-expo);
  white-space: nowrap;
  background: transparent;
}

.map-navbar__btn:hover {
  color: var(--color-text-primary);
  background: rgba(243, 236, 225, 0.04);
}

.map-navbar__btn.is-active {
  background: var(--color-text-primary);
  color: var(--color-bg-deep);
}

.map-navbar__badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  background: var(--color-accent);
  color: var(--color-bg-deep);
  font-family: var(--font-sans);
  font-size: var(--text-micro);
  font-weight: 600;
  border-radius: var(--radius-pill);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--color-bg-elevated);
}

/* Panel — sits below the navbar, inside the map container */
.map-panel {
  position: absolute;
  top: calc(var(--space-xl) + 56px);
  left: var(--space-xl);
  z-index: 1100;
  width: 360px;
  max-height: calc(100vh - var(--space-xl) - 56px - var(--space-xl));
  overflow-y: auto;
  overflow-x: hidden;
  border-radius: var(--radius-xl);
}

/* Fill the panel — both ItineraryTimeline and TripListDrawer */
.map-panel :deep(.itin),
.map-panel :deep(.trip-drawer),
.map-panel :deep(.poi-select-panel) {
  display: flex;
  flex-direction: column;
  width: 100% !important;
  max-width: 100% !important;
  height: 100% !important;
}

/* Atmospheric vignette + grain — must sit BELOW every UI overlay
   (brand mark, day filter, POI card, timeline) so the overlays remain
   fully visible. pointer-events: none keeps it click-through. */
.map-vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
  background:
    radial-gradient(ellipse at center, transparent 50%, rgba(14, 17, 22, 0.4) 100%),
    linear-gradient(180deg, rgba(14, 17, 22, 0.35) 0%, transparent 20%, transparent 80%, rgba(14, 17, 22, 0.5) 100%);
}

.dark-mode .map-vignette {
  background:
    radial-gradient(ellipse at center, transparent 40%, rgba(14, 17, 22, 0.6) 100%),
    linear-gradient(180deg, rgba(14, 17, 22, 0.5) 0%, transparent 20%, transparent 75%, rgba(14, 17, 22, 0.65) 100%);
}

.map-container:not(.dark-mode) .map-vignette {
  background:
    radial-gradient(ellipse at center, transparent 55%, rgba(241, 235, 225, 0.35) 100%),
    linear-gradient(180deg, rgba(241, 235, 225, 0.3) 0%, transparent 25%, transparent 75%, rgba(241, 235, 225, 0.4) 100%);
}

.map-vignette::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml;utf8,<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.4 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  opacity: 0.05;
  mix-blend-mode: overlay;
}

:deep(.leaflet-control-zoom) {
  display: none;
}

:deep(.leaflet-control-attribution) {
  background: transparent !important;
  color: var(--color-text-muted) !important;
  font-family: var(--font-sans);
  font-size: var(--text-micro) !important;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  padding: 0 !important;
}

:deep(.leaflet-control-attribution a) {
  color: var(--color-text-secondary) !important;
}
</style>