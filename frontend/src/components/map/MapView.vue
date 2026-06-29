<script setup lang="ts">
import { watch, computed, shallowRef } from 'vue'
import { LMap, LTileLayer } from '@vue-leaflet/vue-leaflet'
import { latLngBounds } from 'leaflet'
import type { POI } from '@/types'
import { useMapStore } from '@/stores/map'
import PoiMarker from './PoiMarker.vue'
import RouteLayer from './RouteLayer.vue'

// ── Constants ────────────────────────────────────────────────────────────────
const DEFAULT_CENTER: [number, number] = [39.9, 116.4] // Beijing [lat, lng]
const DEFAULT_ZOOM = 12
const FLY_DURATION = 1.2 // seconds for flyTo animation

// ── Store ────────────────────────────────────────────────────────────────────
const mapStore = useMapStore()

// ── Reactive State ───────────────────────────────────────────────────────────
const pois = computed(() => mapStore.pois)
const routes = computed(() => mapStore.routes)
const leafletMap = shallowRef<L.Map | null>(null)

// ── Computed: center from store or default ───────────────────────────────────
const mapCenter = computed<[number, number]>(() => {
  if (mapStore.center) {
    return [mapStore.center.lat, mapStore.center.lng]
  }
  return DEFAULT_CENTER
})

const mapZoom = computed(() => mapStore.zoom || DEFAULT_ZOOM)

// ── Tile Layer ───────────────────────────────────────────────────────────────
const tileUrl = 'https://webrd0{s}.is.autonavi.com/maptile?style=8&x={x}&y={y}&z={z}'
const tileSubdomains = '1,2,3,4'

// ── Map Ready Handler ────────────────────────────────────────────────────────
function onMapReady(map: L.Map): void {
  leafletMap.value = map
  fitBounds(map, pois.value)
}

// ── Auto-fit bounds when POIs change (smooth flyTo) ─────────────────────────
watch(
  pois,
  (newPois) => {
    const map = leafletMap.value
    if (!map) return
    flyToBounds(map, newPois)
  },
  { deep: true }
)

// ── Auto-fit bounds when routes change (smooth flyTo) ───────────────────────
watch(
  routes,
  (newRoutes) => {
    const map = leafletMap.value
    if (!map || !newRoutes.length) return
    flyToBoundsFromRoutes(newRoutes)
  },
  { deep: true }
)

// ── Smooth fly when selected POI changes ─────────────────────────────────────
watch(
  () => mapStore.selectedPOI,
  (poi) => {
    const map = leafletMap.value
    if (!map || !poi) return
    map.flyTo([poi.lat, poi.lng], 15, { duration: FLY_DURATION })
  }
)

/**
 * Smoothly fly to bounds containing all POIs from routes.
 */
function flyToBoundsFromRoutes(routeList: { pois?: { lat: number; lng: number }[] }[]): void {
  const allPois = routeList.flatMap((r) => r.pois ?? [])
  if (allPois.length === 0) return

  const lngs = allPois.map((p) => p.lng)
  const lats = allPois.map((p) => p.lat)
  const bounds = latLngBounds(
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)]
  )
  leafletMap.value?.flyToBounds(bounds, {
    padding: [50, 50],
    maxZoom: 15,
    duration: FLY_DURATION,
  })
}

/**
 * Smoothly fly to bounds containing all POIs.
 * Skips when POIs array is empty or map not ready.
 */
function flyToBounds(map: L.Map, poiList: POI[]): void {
  if (poiList.length === 0) return

  const lngs = poiList.map((p) => p.lng)
  const lats = poiList.map((p) => p.lat)
  const bounds = latLngBounds(
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)]
  )
  map.flyToBounds(bounds, {
    padding: [50, 50],
    maxZoom: 15,
    duration: FLY_DURATION,
  })
}

/**
 * Fit map bounds instantly (used on initial map ready).
 */
function fitBounds(map: L.Map, poiList: POI[]): void {
  if (poiList.length === 0) return

  const lngs = poiList.map((p) => p.lng)
  const lats = poiList.map((p) => p.lat)
  const bounds = latLngBounds(
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)]
  )
  map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 })
}

// ── POI Selection ────────────────────────────────────────────────────────────
function onPoiSelect(poi: POI): void {
  mapStore.selectPOI(poi)
}
</script>

<template>
  <div class="map-container">
    <l-map
      :center="mapCenter"
      :zoom="mapZoom"
      :attribution-control="false"
      @ready="onMapReady"
    >
      <l-tile-layer
        :url="tileUrl"
        :subdomains="tileSubdomains"
        layer-type="base"
        name="Amap"
      />

      <RouteLayer />

      <PoiMarker
        v-for="(poi, index) in pois"
        :key="poi.id"
        :poi="poi"
        :index="index"
        @select="onPoiSelect"
      />
    </l-map>
  </div>
</template>

<style scoped>
.map-container {
  width: 100%;
  height: 100%;
  min-height: 300px;
}
</style>
