<script setup lang="ts">
import { watch, computed, shallowRef, ref, onMounted, onUnmounted } from 'vue'
import type { POI } from '@/types'
import { useMapStore, type DailyPlan } from '@/stores/map'
import { RouteLayerRenderer } from './RouteLayer.js'
import ItineraryTimeline from './ItineraryTimeline.vue'
import POIDetailCard from './POIDetailCard.vue'
import TripListDrawer from './TripListDrawer.vue'
import PoiSelectPanel from './PoiSelectPanel.vue'
import { useTripStore } from '@/stores/trip'
import { loadAMap } from '@/utils/amap'

// ── Constants ───────────────────────────────────────────────────────────────
const DEFAULT_CENTER: [number, number] = [116.4, 39.9]  // [lng, lat] — Amap order
const DEFAULT_ZOOM = 12

// ── Store ────────────────────────────────────────────────────────────────────
const mapStore = useMapStore()
const tripStore = useTripStore()

// ── Reactive State ───────────────────────────────────────────────────────────
const activePanel = ref<'trips' | null>(null)
const pois = computed(() => mapStore.pois)
const routes = computed(() => mapStore.routes)
const hasRoutes = computed(() => routes.value.length > 0)
const selectedPOI = computed(() => mapStore.selectedPOI)
const amapMap = shallowRef<AMap.Map | null>(null)
const amapSDK = shallowRef<typeof AMap | null>(null)
const routeRenderer = shallowRef<RouteLayerRenderer | null>(null)

const selectedPOIContext = computed(() => {
  if (!selectedPOI.value) return null
  return mapStore.findPOIContext(selectedPOI.value.id)
})

const mapCenter = computed<[number, number]>(() => {
  if (mapStore.center) {
    return [mapStore.center.lng, mapStore.center.lat]
  }
  return DEFAULT_CENTER
})

const mapZoom = computed(() => mapStore.zoom ?? DEFAULT_ZOOM)

// ── Dark Mode ────────────────────────────────────────────────────────────────
const isDark = ref(true)
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

// ── Amap initialisation ─────────────────────────────────────────────────────
onMounted(async () => {
  const AMap_sdk = await loadAMap()
  amapSDK.value = AMap_sdk

  const map = new AMap_sdk.Map('amap-container', {
    center: mapCenter.value,
    zoom: mapZoom.value,
    viewMode: '2D',
    resizeEnable: true,
    showBuildingBlock: false,
    dragEnable: true,
    zoomEnable: true,
    doubleClickZoom: true,
    scrollWheel: true,
    animateEnable: false,
  })

  amapMap.value = map
  ;(document.getElementById('amap-container') as any)._amap = map
  const renderer = new RouteLayerRenderer(AMap_sdk)
  renderer.attach(map)
  renderer.onPoiClick((poi) => {
    mapStore.selectPOI(poi as any)
  })
  routeRenderer.value = renderer

  // Render initial data if already present
  if (routes.value.length > 0) {
    renderer.setRoutes(routes.value as DailyPlan[], mapStore.activeDay)
    fitBoundsFromRoutes(AMap_sdk, routes.value as DailyPlan[])
  }
  if (pois.value.length > 0 && routes.value.length === 0) {
    renderer.setPois(pois.value)
    fitBoundsFromPOIs(AMap_sdk, pois.value)
  }
})

onUnmounted(() => {
  if (routeRenderer.value) {
    routeRenderer.value.destroy()
    routeRenderer.value = null
  }
  if (amapMap.value) {
    ;(amapMap.value as AMap.Map & { destroy?: () => void }).destroy?.()
    amapMap.value = null
  }
})

// ── Watch: routes change → re-render ────────────────────────────────────────
watch(
  () => routes.value,
  (newRoutes) => {
    const map = amapMap.value
    const renderer = routeRenderer.value
    const AMap = amapSDK.value
    if (!map || !renderer || !AMap) return
    renderer.setRoutes(newRoutes as DailyPlan[], mapStore.activeDay)
    if (newRoutes.length > 0) {
      fitBoundsFromRoutes(AMap, newRoutes as DailyPlan[])
    }
  },
)

watch(
  () => mapStore.activeDay,
  (day) => {
    routeRenderer.value?.setActiveDay(day)
  },
)

// ── Watch: POIs change → render immediately ─────────────────────────────
watch(
  () => pois.value,
  (newPois) => {
    const map = amapMap.value
    const AMap = amapSDK.value
    const renderer = routeRenderer.value
    if (!map || !AMap) return
    if (newPois.length > 0 && routes.value.length === 0) {
      renderer?.setPois(newPois)
      fitBoundsFromPOIs(AMap, newPois)
    }
  },
)

// ── Watch: selected POI → fly to ────────────────────────────────────────────
watch(
  () => mapStore.selectedPOI,
  (poi) => {
    const map = amapMap.value
    if (!map || !poi) return
    map.setZoomAndCenter(15, [poi.lng, poi.lat])
  },
)

// ── Fit bounds ──────────────────────────────────────────────────────────────
function fitBoundsFromRoutes(AMap_sdk: typeof AMap, routeList: DailyPlan[]): void {
  const map = amapMap.value
  if (!map) return
  const allPois = routeList
    .filter((r) => (r.pois?.length ?? 0) >= 2)
    .flatMap((r) => r.pois ?? [])
  if (allPois.length === 0) return

  const lngs = allPois.map((p) => p.lng)
  const lats = allPois.map((p) => p.lat)
  map.setBounds(
    new AMap_sdk.Bounds(
      [Math.min(...lngs), Math.min(...lats)],
      [Math.max(...lngs), Math.max(...lats)],
    ),
    false,
    [80, 80, 80, 80],
  )
}

function fitBoundsFromPOIs(AMap_sdk: typeof AMap, poiList: POI[]): void {
  const map = amapMap.value
  if (!map) return
  if (poiList.length === 0) return
  const lngs = poiList.map((p) => p.lng)
  const lats = poiList.map((p) => p.lat)
  map.setBounds(
    new AMap_sdk.Bounds(
      [Math.min(...lngs), Math.min(...lats)],
      [Math.max(...lngs), Math.max(...lats)],
    ),
    false,
    [80, 80, 80, 80],
  )
}

// ── UI event handlers ───────────────────────────────────────────────────────
function onPOICardClose(): void {
  mapStore.clearSelection()
}

function onTimelineClick(): void {
  if (mapStore.timelineOpen) {
    mapStore.timelineOpen = false
  } else {
    activePanel.value = null
    mapStore.timelineOpen = true
  }
}

function onTripsClick(): void {
  if (activePanel.value === 'trips') {
    activePanel.value = null
  } else {
    mapStore.timelineOpen = false
    mapStore.setPoiPanelOpen(false)
    activePanel.value = 'trips'
  }
}

function onPOIsClick(): void {
  mapStore.timelineOpen = false
  activePanel.value = null
  mapStore.togglePoiPanel()
}
</script>

<template>
  <div class="map-container" :class="{ 'dark-mode': effectiveDark }">
    <div id="amap-container" class="amap-container"></div>

    <!-- Top-left: segmented nav bar -->
    <div class="map-navbar">
      <button
        v-if="pois.length > 0 && !hasRoutes"
        class="map-navbar__btn"
        :class="{ 'is-active': mapStore.poiPanelOpen }"
        title="兴趣点"
        @click="onPOIsClick"
      >
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round" />
          <circle cx="12" cy="10" r="3" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span>兴趣点</span>
        <span class="map-navbar__badge numeric">{{ mapStore.poiCount }}</span>
      </button>
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

    <!-- 历史规划 panel -->
    <div v-if="activePanel === 'trips'" class="map-panel">
      <TripListDrawer @close="activePanel = null" />
    </div>

    <!-- 兴趣点 panel -->
    <div v-if="mapStore.poiPanelOpen && pois.length > 0 && !hasRoutes" class="map-panel">
      <PoiSelectPanel @close="mapStore.setPoiPanelOpen(false)" />
    </div>

    <!-- 行程 timeline panel -->
    <div v-if="hasRoutes && mapStore.timelineOpen" class="map-panel">
      <ItineraryTimeline />
    </div>

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
  isolation: isolate;
  z-index: 0;
}

.amap-container {
  width: 100%;
  height: 100%;
}

/* Day filter */
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

/* Dark/light mode toggle */
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

/* Panel */
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

.map-panel :deep(.itin),
.map-panel :deep(.trip-drawer),
.map-panel :deep(.poi-select-panel) {
  display: flex;
  flex-direction: column;
  width: 100% !important;
  max-width: 100% !important;
  height: 100% !important;
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

/* Vignette */
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
  opacity: 0.05;
  mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml;utf8,<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.4 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
}

/* Hide Amap attribution logo — our brand mark replaces it */
:deep(.amap-logo),
:deep(.amap-copyright) {
  display: none !important;
}
</style>
