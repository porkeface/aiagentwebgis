<script setup lang="ts">
import type { TripDayPOI, DayPlanDetail } from '@/types'
import { DAY_COLORS } from '@/utils/constants'
import {
  defaultModeFor,
  estimateDuration,
  formatDistance,
  formatDuration,
  MODE_META,
  type TransportMode,
} from '@/utils/format'
import { useMapStore, type RouteSegment } from '@/stores/map'
import { computed } from 'vue'

// ── Props & Emits ──────────────────────────────────────────────────────────
interface Props {
  dayPlan: DayPlanDetail;
  dayNumber: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  selectPOI: [poi: TripDayPOI];
}>();

// ── Store ──────────────────────────────────────────────────────────────────
const mapStore = useMapStore();

// ── Constants ──────────────────────────────────────────────────────────────
/** Three-way switcher offered in the segment mode popover. Order matters —
 *  walking first because that's the safest urban default and matches the
 *  popover preview order. */
const MODE_OPTIONS: readonly TransportMode[] = ['walking', 'driving', 'transit'];

// ── Helpers ────────────────────────────────────────────────────────────────

/** Haversine distance between two POIs (km). */
function haversineKm(a: TripDayPOI, b: TripDayPOI): number {
  if (a.lat == null || a.lng == null || b.lat == null || b.lng == null) return 0;
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const aRad = (a.lat * Math.PI) / 180;
  const bRad = (b.lat * Math.PI) / 180;
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(aRad) * Math.cos(bRad) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

/** Format a time range for display. */
function formatTimeRange(
  arrival: string | null,
  departure: string | null,
): string {
  if (arrival && departure) return `${arrival} – ${departure}`;
  if (arrival) return arrival;
  return '—';
}

// ── Derived data ───────────────────────────────────────────────────────────

/** Per-segment list, mirroring `poiDistances`. Synthesises a segment object
 *  when the backend didn't ship one so the chip + duration always render. */
const segments = computed<RouteSegment[]>(() => {
  const pois = props.dayPlan.pois;
  const out: RouteSegment[] = [];
  for (let i = 0; i < pois.length - 1; i++) {
    const from = pois[i];
    const to = pois[i + 1];
    if (from.lat == null || from.lng == null || to.lat == null || to.lng == null) {
      continue;
    }
    const km = haversineKm(from, to);
    const backendSeg = props.dayPlan.segments?.[i];
    out.push(
      backendSeg ?? {
        distance_km: km,
        duration_min: estimateDuration(km, defaultModeFor(km)),
      },
    );
  }
  return out;
});

/** Total travel distance for the day, summed from the synthesised segments
 *  (which agree with the backend when segments are present). */
const totalDistanceKm = computed<number>(() =>
  segments.value.reduce((acc, s) => acc + (s.distance_km ?? 0), 0),
);

/** Total travel duration for this day only.
 *
 *  We deliberately sum the local segments rather than reading
 *  `mapStore.totalDurationMin`, which is a cross-day aggregate. Each
 *  DayCard header should show *its own* day's duration. */
const totalDurationMin = computed<number>(() =>
  segments.value.reduce((acc, _seg, i) => acc + getSegmentDurationMin(i), 0),
);

function getTotalDistance(): number {
  return totalDistanceKm.value;
}

function getTotalDuration(): number {
  return totalDurationMin.value;
}

// ── Segment helpers ────────────────────────────────────────────────────────

/** Effective mode for a segment, falling back through store → default → driving. */
function getSegmentMode(segIndex: number): TransportMode {
  return mapStore.getSegmentMode(props.dayNumber, segIndex);
}

/** Effective duration for a segment (minutes). */
function getSegmentDurationMin(segIndex: number): number {
  const seg = segments.value[segIndex];
  if (!seg) return 0;
  if (typeof seg.duration_min === 'number') return seg.duration_min;
  return estimateDuration(seg.distance_km ?? 0, getSegmentMode(segIndex));
}

/** User picked a new mode from the popover. */
function onModeChange(segIndex: number, mode: TransportMode): void {
  mapStore.setSegmentMode(props.dayNumber, segIndex, mode);
}

function getPOIColor(index: number): string {
  return DAY_COLORS[index % DAY_COLORS.length]
}

// ── POI Click ──────────────────────────────────────────────────────────────
function onPOIClick(poi: TripDayPOI): void {
  emit("selectPOI", poi);
}
</script>

<template>
  <div class="day-card">
    <div class="day-header">
      <div class="day-badge">
        <span class="day-number">Day {{ dayNumber }}</span>
      </div>
      <div class="day-meta">
        <span class="day-date">{{ dayPlan.date }}</span>
        <span class="day-stats" v-if="dayPlan.pois.length > 1">
          {{ formatDistance(getTotalDistance()) }} · {{ formatDuration(getTotalDuration()) }}
        </span>
      </div>
    </div>

    <div class="poi-list" v-if="dayPlan.pois.length > 0">
      <div
        v-for="(poi, index) in dayPlan.pois"
        :key="poi.poi_id"
        class="poi-item"
        :class="{ clickable: poi.lat != null && poi.lng != null }"
        @click="onPOIClick(poi)"
      >
        <div class="poi-index" :style="{ backgroundColor: getPOIColor(index) }">
          {{ index + 1 }}
        </div>

        <div class="poi-content">
          <div class="poi-name">{{ poi.name || `POI #${poi.poi_id}` }}</div>
          <div class="poi-category" v-if="poi.category">
            <span class="category-tag">{{ poi.category }}</span>
          </div>
          <div class="poi-details">
            <span class="poi-time" v-if="poi.arrival_time || poi.departure_time">
              🕐 {{ formatTimeRange(poi.arrival_time, poi.departure_time) }}
            </span>
            <span class="poi-rating" v-if="typeof poi.rating === 'number'">
              ★ {{ poi.rating.toFixed(1) }}
            </span>
            <span class="poi-score" v-if="poi.score != null">
              Score: {{ poi.score.toFixed(1) }}
            </span>
          </div>
          <div class="poi-address" v-if="poi.address">
            📍 {{ poi.address }}
          </div>
          <div class="poi-tags" v-if="poi.tags && poi.tags.length > 0">
            <span v-for="tag in poi.tags.slice(0, 3)" :key="tag" class="poi-tag">
              {{ tag }}
            </span>
          </div>
          <div class="poi-notes" v-if="poi.notes">
            {{ poi.notes }}
          </div>
        </div>

        <!-- Segment mode (segmented control, inline) + distance + duration
             between this POI and the next. Layout: [🚶 驾车 🚌] | 260m · 1 min.
             Click any option to switch the segment mode in place. -->
        <div
          v-if="index < segments.length"
          class="poi-segment"
          @click.stop
        >
          <div
            class="mode-group"
            role="radiogroup"
            :aria-label="`${poi.name} 到下一站的交通方式`"
          >
            <button
              v-for="m in MODE_OPTIONS"
              :key="m"
              type="button"
              role="radio"
              :aria-checked="getSegmentMode(index) === m"
              class="mode-group__opt"
              :class="{
                'mode-group__opt--active': getSegmentMode(index) === m,
                [`mode-group__opt--${m}`]: true,
              }"
              :title="`切到 ${MODE_META[m].label}（≈${formatDuration(estimateDuration(segments[index].distance_km ?? 0, m as TransportMode))}）`"
              @click="onModeChange(index, m as TransportMode)"
            >
              <span class="mode-group__icon">{{ MODE_META[m].icon }}</span>
              <span class="mode-group__label">{{ MODE_META[m].label }}</span>
            </button>
          </div>

          <div class="segment-stats">
            <span class="segment-dist">
              {{ formatDistance(segments[index].distance_km ?? 0) }}
            </span>
            <span class="segment-dur">
              {{ formatDuration(getSegmentDurationMin(index)) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="empty-day" v-else>
      No POIs planned for this day.
    </div>

    <div class="day-notes" v-if="dayPlan.notes">
      📝 {{ dayPlan.notes }}
    </div>
  </div>
</template>

<style scoped>
.day-card {
  background: var(--color-bg-overlay);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  margin-bottom: var(--space-lg);
  transition: box-shadow var(--transition-normal);
}

.day-card:hover {
  box-shadow: var(--shadow-lg);
}

.day-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-lg) var(--space-xl);
  background: linear-gradient(135deg, var(--color-day-1) 0%, var(--color-day-2) 100%);
  color: #fff;
}

.day-badge {
  flex-shrink: 0;
}

.day-number {
  display: inline-block;
  background: rgba(255, 255, 255, 0.25);
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  font-weight: 700;
  font-size: var(--font-size-base);
}

.day-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.day-date {
  font-size: var(--font-size-base);
  font-weight: 500;
}

.day-stats {
  font-size: var(--font-size-sm);
  opacity: 0.9;
}

.poi-list {
  padding: var(--space-lg) var(--space-xl);
}

.poi-item {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--color-border-light);
  transition: background-color var(--transition-fast);
}

.poi-item:last-child {
  border-bottom: none;
}

.poi-item.clickable {
  cursor: pointer;
}

.poi-item.clickable:hover {
  background-color: var(--color-bg-base);
  border-radius: var(--radius-md);
}

.poi-index {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-round);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: var(--font-size-base);
  box-shadow: var(--shadow-sm);
}

.poi-content {
  flex: 1;
  min-width: 0;
}

.poi-name {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-xs);
}

.poi-category {
  margin-bottom: 6px;
}

.category-tag {
  display: inline-block;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  background: var(--color-bg-muted);
  padding: 2px var(--space-sm);
  border-radius: 10px;
}

.poi-details {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xs);
}

.poi-time {
  color: var(--color-primary);
}

.poi-rating {
  color: var(--color-warning);
}

.poi-score {
  color: var(--color-success);
}

.poi-address {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xs);
}

.poi-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--space-xs);
}

.poi-tag {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  background: var(--color-primary-bg);
  padding: 2px var(--space-sm);
  border-radius: 10px;
}

.poi-notes {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-style: italic;
  margin-top: var(--space-xs);
}

/* ── Segment mode (segmented control) + distance + duration ─────────── */
.poi-segment {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  flex-shrink: 0;
  min-width: 200px;
}

.mode-group {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  background: var(--color-bg-overlay);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-pill);
}

.mode-group__opt {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.mode-group__opt:hover {
  color: var(--color-text-primary);
  background: rgba(0, 0, 0, 0.04);
}

.mode-group__opt--walking.mode-group__opt--active {
  background: rgba(126, 148, 112, 0.85);
  color: #fff;
}
.mode-group__opt--driving.mode-group__opt--active {
  background: rgba(59, 130, 246, 0.85);
  color: #fff;
}
.mode-group__opt--transit.mode-group__opt--active {
  background: rgba(232, 98, 60, 0.85);
  color: #fff;
}

.mode-group__icon {
  font-size: 13px;
}

.segment-stats {
  display: flex;
  align-items: baseline;
  gap: 4px;
  line-height: 1.2;
}

.segment-dist {
  font-weight: 600;
  color: var(--color-primary);
}

.segment-dur {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

/* ── Responsive ───────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .day-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-sm);
  }

  .poi-item {
    flex-wrap: wrap;
  }

  .poi-segment {
    margin-left: 44px;
    width: calc(100% - 44px);
    flex-direction: row;
    justify-content: flex-start;
    gap: var(--space-md);
  }
}
</style>
