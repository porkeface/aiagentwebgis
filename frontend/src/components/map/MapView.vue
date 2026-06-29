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

// ── Auto-fit bounds when POIs change ─────────────────────────────────────────
watch(
  pois,
  (newPois) => {
    const map = leafletMap.value
    if (!map) return
    fitBounds(map, newPois)
  },
  { deep: true }
)

// ── Auto-fit bounds when routes change ───────────────────────────────────────
watch(
  routes,
  (newRoutes) => {
    const map = leafletMap.value
    if (!map || !newRoutes.length) return
    fitBoundsFromRoutes(newRoutes)
  },
  { deep: true }
)

/**
 * Fit map bounds to contain all POIs from all routes with padding.
 */
function fitBoundsFromRoutes(routeList: { pois?: { lat: number; lng: number }[] }[]): void {
  const allPois = routeList.flatMap((r) => r.pois ?? [])
  if (allPois.length === 0) return

  const lngs = allPois.map((p) => p.lng)
  const lats = allPois.map((p) => p.lat)
  const bounds = latLngBounds(
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)]
  )
  leafletMap.value?.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 })
}

/**
 * Fit map bounds to contain all POIs with padding.
 * Skips when POIs array is empty or map not ready.
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

<!--
  Global styles for Leaflet-rendered DOM elements.
  Leaflet renders markers/popups outside Vue's DOM tree,
  so scoped styles cannot reach them.
-->
<style>
.poi-marker-icon {
  background: transparent !important;
  border: none !important;
}

.poi-marker-inner {
  width: 32px;
  height: 32px;
  border-radius: 50% 50% 50% 0;
  background: #1890ff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  transform: rotate(-45deg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  border: 2px solid #fff;
}

.poi-marker-inner span {
  transform: rotate(45deg);
}

.poi-popup .poi-popup-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 6px;
}

.poi-popup .poi-popup-category {
  display: inline-block;
  font-size: 12px;
  color: #fff;
  background: #1890ff;
  padding: 2px 8px;
  border-radius: 10px;
  margin-bottom: 6px;
}

.poi-popup .poi-popup-rating {
  font-size: 13px;
  color: #fa8c16;
}
</style>
