import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { POI } from "@/types";

export interface RouteData {
  [key: string]: unknown;
}

export interface MapCenter {
  lng: number;
  lat: number;
}

export const useMapStore = defineStore("map", () => {
  // ── State ──────────────────────────────────────────────────────────────────
  const pois = ref<POI[]>([]);
  const routes = ref<RouteData[]>([]);
  const selectedPOI = ref<POI | null>(null);
  const center = ref<MapCenter | null>(null);
  const zoom = ref<number>(13);

  // ── Getters ────────────────────────────────────────────────────────────────
  const poiCount = computed(() => pois.value.length);
  const hasSelection = computed(() => selectedPOI.value !== null);

  // ── Actions ────────────────────────────────────────────────────────────────
  function setPOIs(newPOIs: POI[]): void {
    pois.value = [...newPOIs];
  }

  function setRoutes(newRoutes: RouteData[]): void {
    routes.value = [...newRoutes];
  }

  function selectPOI(poi: POI): void {
    selectedPOI.value = poi;
    center.value = { lng: poi.lng, lat: poi.lat };
  }

  function clearSelection(): void {
    selectedPOI.value = null;
  }

  function clearMap(): void {
    pois.value = [];
    routes.value = [];
    selectedPOI.value = null;
    center.value = null;
  }

  function setCenter(newCenter: MapCenter): void {
    center.value = { ...newCenter };
  }

  function setZoom(newZoom: number): void {
    zoom.value = newZoom;
  }

  return {
    // state
    pois,
    routes,
    selectedPOI,
    center,
    zoom,
    // getters
    poiCount,
    hasSelection,
    // actions
    setPOIs,
    setRoutes,
    selectPOI,
    clearSelection,
    clearMap,
    setCenter,
    setZoom,
  };
});
