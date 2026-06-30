<script setup lang="ts">
import { computed } from 'vue'
import { LMarker, LPopup } from '@vue-leaflet/vue-leaflet'
import { createDivIcon } from '@/utils/constants'
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

// ── Marker Position ──────────────────────────────────────────────────────────
const latLng = computed<[number, number]>(() => [props.poi.lat, props.poi.lng])

// ── Custom DivIcon ───────────────────────────────────────────────────────────
const markerIcon = computed(() =>
  createDivIcon({
    className: 'poi-marker-icon',
    html: `<div class="poi-marker-inner"><span>${props.index + 1}</span></div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
  })
)

// ── Click Handler ────────────────────────────────────────────────────────────
function onMarkerClick(): void {
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
        <p class="poi-popup-rating" v-if="poi.rating != null">
          ★ {{ Number(poi.rating).toFixed(1) }}
        </p>
      </div>
    </l-popup>
  </l-marker>
</template>
