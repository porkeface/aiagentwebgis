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
  background: var(--color-bg-base);
}

.timeline-header {
  padding: var(--space-xl) var(--space-2xl);
  background: var(--color-bg-overlay);
  border-bottom: 1px solid var(--color-border-light);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
}

.trip-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-xs);
}

.trip-subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0;
}

.timeline-body {
  padding: var(--space-xl) var(--space-2xl);
}

.timeline-track {
  position: relative;
  padding-left: var(--space-2xl);
}

.timeline-line {
  position: absolute;
  left: 12px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-border);
}

.timeline-item {
  position: relative;
  margin-bottom: var(--space-xl);
  animation: timeline-fade-in 0.4s ease-out;
}

@keyframes timeline-fade-in {
  from {
    opacity: 0;
    transform: translateX(-8px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-marker {
  position: absolute;
  left: calc(-1 * var(--space-2xl));
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
  border-radius: var(--radius-round);
  background: var(--color-primary);
  border: 3px solid var(--color-bg-overlay);
  box-shadow: 0 0 0 2px var(--color-primary);
}

.timeline-content {
  background: transparent;
}

.timeline-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px var(--space-2xl);
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: var(--space-lg);
}

/* Responsive */
@media (max-width: 768px) {
  .timeline-header {
    padding: var(--space-lg) var(--space-lg);
  }

  .trip-title {
    font-size: var(--font-size-xl);
  }

  .timeline-body {
    padding: var(--space-lg);
  }

  .timeline-track {
    padding-left: var(--space-xl);
  }

  .timeline-marker {
    left: calc(-1 * var(--space-xl));
  }
}
</style>
