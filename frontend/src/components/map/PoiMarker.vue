<script setup lang="ts">
import { computed } from 'vue'
import { LMarker, LPopup } from '@vue-leaflet/vue-leaflet'
import { createDivIcon } from '@/utils/constants'
import { useMapStore } from '@/stores/map'
import type { POI } from '@/types'

// ── Props ────────────────────────────────────────────────────────────────────
interface Props {
  poi: POI
  index: number
}

const props = defineProps<Props>()

// ── Emits ────────────────────────────────────────────────────────────────────
const emit = defineEmits<{
  select: [poi: POI]
}>()

const mapStore = useMapStore()

// ── Marker Position ──────────────────────────────────────────────────────────
const latLng = computed<[number, number]>(() => [props.poi.lat, props.poi.lng])

const isSelected = computed(() => mapStore.isPoiSelected(String(props.poi.id)))

// ── Custom DivIcon ───────────────────────────────────────────────────────────
const markerIcon = computed(() =>
  createDivIcon({
    className: `poi-marker-icon${isSelected.value ? ' poi-marker-icon--selected' : ''}`,
    html: isSelected.value
      ? `<div class="poi-marker-inner"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#fff" stroke-width="3"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round"/></svg></div>`
      : `<div class="poi-marker-inner"><span>${props.index + 1}</span></div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
  }),
)

// ── Click Handler ────────────────────────────────────────────────────────────
function onMarkerClick(): void {
  // Toggle selection on click
  mapStore.togglePoiSelection(String(props.poi.id))
  emit('select', props.poi)
}
</script>

<template>
  <l-marker
    :lat-lng="latLng"
    :icon="markerIcon"
    @click="onMarkerClick"
  >
    <l-popup>
      <div class="poi-popup">
        <p class="poi-popup-title">{{ poi.name }}</p>
        <span class="poi-popup-category">{{ poi.category }}</span>
        <p v-if="poi.rating != null" class="poi-popup-rating">
          ★ {{ Number(poi.rating).toFixed(1) }}
        </p>
        <p v-if="isSelected" class="poi-popup-selected">已选 ✓</p>
      </div>
    </l-popup>
  </l-marker>
</template>
