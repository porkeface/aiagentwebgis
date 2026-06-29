<script setup lang="ts">
import type { TripDetail, TripDayPOI } from "@/types";
import DayCard from "./DayCard.vue";

// ── Props & Emits ──────────────────────────────────────────────────────────
interface Props {
  trip: TripDetail;
}

defineProps<Props>();

const emit = defineEmits<{
  selectPOI: [poi: TripDayPOI];
}>();

// ── POI Click ───────────────────────────────────────────────────────────────
function onPOISelect(poi: TripDayPOI): void {
  emit("selectPOI", poi);
}
</script>

<template>
  <div class="trip-timeline">
    <template v-if="trip.daily_plans && trip.daily_plans.length > 0">
      <div class="timeline-header">
        <h2 class="trip-title">{{ trip.city }} {{ trip.days }}日游</h2>
        <p class="trip-subtitle">{{ trip.daily_plans.length }} 天行程</p>
      </div>

      <div class="timeline-body">
        <div class="timeline-track">
          <div class="timeline-line"></div>

          <div
            v-for="dayPlan in trip.daily_plans"
            :key="dayPlan.day_number"
            class="timeline-item"
          >
            <div class="timeline-marker">
              <div class="marker-dot"></div>
            </div>

            <div class="timeline-content">
              <DayCard :dayPlan="dayPlan" :dayNumber="dayPlan.day_number" @selectPOI="onPOISelect" />
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="timeline-empty">
      <div class="empty-icon">📭</div>
      <p>暂无行程数据</p>
    </div>
  </div>
</template>

<style scoped>
.trip-timeline {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  background: #f5f7fa;
}

.timeline-header {
  padding: 24px 32px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  position: sticky;
  top: 0;
  z-index: 10;
}

.trip-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 4px;
}

.trip-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.timeline-body {
  padding: 24px 32px;
}

.timeline-track {
  position: relative;
  padding-left: 32px;
}

.timeline-line {
  position: absolute;
  left: 12px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #d9d9d9;
}

.timeline-item {
  position: relative;
  margin-bottom: 24px;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-marker {
  position: absolute;
  left: -32px;
  top: 20px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #1890ff;
  border: 3px solid #fff;
  box-shadow: 0 0 0 2px #1890ff;
}

.timeline-content {
  background: transparent;
}

.timeline-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 32px;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

/* Responsive */
@media (max-width: 768px) {
  .timeline-header {
    padding: 16px 20px;
  }

  .trip-title {
    font-size: 20px;
  }

  .timeline-body {
    padding: 16px 20px;
  }

  .timeline-track {
    padding-left: 24px;
  }

  .timeline-marker {
    left: -24px;
  }
}
</style>
