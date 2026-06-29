<script setup lang="ts">
import type { TripDayPOI, DayPlanDetail } from "@/types";

// ── Props & Emits ──────────────────────────────────────────────────────────
interface Props {
  dayPlan: DayPlanDetail;
  dayNumber: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  selectPOI: [poi: TripDayPOI];
}>();

// ── Constants ───────────────────────────────────────────────────────────────
const AVG_SPEED_KMH = 30;

// ── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Estimate travel duration in minutes from distance in km.
 */
function estimateDuration(distanceKm: number): number {
  return Math.round((distanceKm / AVG_SPEED_KMH) * 60);
}

/**
 * Format time range for display.
 */
function formatTimeRange(arrival: string | null, departure: string | null): string {
  if (arrival && departure) {
    return `${arrival} – ${departure}`;
  }
  if (arrival) return arrival;
  return "—";
}

/**
 * Calculate total distance for the day (sum of segment distances).
 * Uses Haversine if segment data unavailable.
 */
function calculateTotalDistance(): number {
  const pois = props.dayPlan.pois;
  if (pois.length < 2) return 0;
  let total = 0;
  for (let i = 0; i < pois.length - 1; i++) {
    total += haversineKm(pois[i], pois[i + 1]);
  }
  return total;
}

/**
 * Haversine distance between two points.
 */
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

// ── Computed-like derived values ────────────────────────────────────────────
function getTotalDistance(): number {
  return calculateTotalDistance();
}

function getTotalDuration(): number {
  return estimateDuration(getTotalDistance());
}

function getPOIColor(index: number): string {
  const colors = ["#1890ff", "#52c41a", "#fa8c16", "#a855f7"];
  return colors[index % colors.length];
}

// ── POI Click ───────────────────────────────────────────────────────────────
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
          {{ getTotalDistance().toFixed(1) }} km · ~{{ getTotalDuration() }} min
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
            <span class="poi-rating" v-if="poi.rating != null">
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

        <!-- Distance to next POI -->
        <div
          class="poi-distance"
          v-if="index < dayPlan.pois.length - 1 && poi.lat != null && poi.lng != null && dayPlan.pois[index + 1].lat != null"
        >
          <span class="distance-label">
            {{ haversineKm(poi, dayPlan.pois[index + 1]).toFixed(1) }} km
          </span>
          <span class="distance-duration">
            ~{{ estimateDuration(haversineKm(poi, dayPlan.pois[index + 1])) }} min
          </span>
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
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  margin-bottom: 16px;
}

.day-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #1890ff 0%, #52c41a 100%);
  color: #fff;
}

.day-badge {
  flex-shrink: 0;
}

.day-number {
  display: inline-block;
  background: rgba(255, 255, 255, 0.25);
  padding: 6px 14px;
  border-radius: 20px;
  font-weight: 700;
  font-size: 14px;
}

.day-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.day-date {
  font-size: 14px;
  font-weight: 500;
}

.day-stats {
  font-size: 12px;
  opacity: 0.9;
}

.poi-list {
  padding: 16px 20px;
}

.poi-item {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s;
}

.poi-item:last-child {
  border-bottom: none;
}

.poi-item.clickable {
  cursor: pointer;
}

.poi-item.clickable:hover {
  background-color: #f5f7fa;
  margin: 0 -20px;
  padding-left: 20px;
  padding-right: 20px;
  border-radius: 8px;
}

.poi-index {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
}

.poi-content {
  flex: 1;
  min-width: 0;
}

.poi-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
}

.poi-category {
  margin-bottom: 6px;
}

.category-tag {
  display: inline-block;
  font-size: 11px;
  color: #666;
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 10px;
}

.poi-details {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.poi-time {
  color: #1890ff;
}

.poi-rating {
  color: #fa8c16;
}

.poi-score {
  color: #52c41a;
}

.poi-address {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.poi-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 4px;
}

.poi-tag {
  font-size: 11px;
  color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
}

.poi-notes {
  font-size: 12px;
  color: #888;
  font-style: italic;
  margin-top: 4px;
}

.poi-distance {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  background: #f9f9f9;
  border-radius: 8px;
  font-size: 12px;
  flex-shrink: 0;
}

.distance-label {
  font-weight: 600;
  color: #1890ff;
}

.distance-duration {
  color: #999;
  font-size: 11px;
}

.empty-day {
  padding: 32px 20px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.day-notes {
  padding: 12px 20px;
  background: #fffbe6;
  border-top: 1px solid #ffe58f;
  font-size: 13px;
  color: #8c6d1f;
}

/* Responsive */
@media (max-width: 768px) {
  .day-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .poi-item {
    flex-wrap: wrap;
  }

  .poi-distance {
    margin-left: 44px;
    width: calc(100% - 44px);
  }
}
</style>
