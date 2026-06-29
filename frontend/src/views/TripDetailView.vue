<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import type { TripDayPOI } from "@/types";
import { useTripStore } from "@/stores/trip";
import { useMapStore } from "@/stores/map";
import TripTimeline from "@/components/trip/TripTimeline.vue";
import MapView from "@/components/map/MapView.vue";

// ── Store ───────────────────────────────────────────────────────────────────
const tripStore = useTripStore();
const mapStore = useMapStore();
const route = useRoute();
const router = useRouter();

// ── Load Trip ───────────────────────────────────────────────────────────────
async function loadTrip(): Promise<void> {
  const tripId = Number(route.params.id);
  if (isNaN(tripId)) {
    ElMessage.error("无效的行程ID");
    router.push("/");
    return;
  }

  try {
    await tripStore.fetchTrip(tripId);
    if (tripStore.currentTrip) {
      setupMapData();
    } else {
      ElMessage.error("行程不存在或已删除");
      router.push("/");
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "加载行程失败";
    ElMessage.error(message);
    router.push("/");
  }
}

// ── Setup Map Data ──────────────────────────────────────────────────────────
function setupMapData(): void {
  const trip = tripStore.currentTrip;
  if (!trip || !trip.daily_plans) return;

  // Flatten all POIs from all days
  const allPois = trip.daily_plans.flatMap((day) =>
    day.pois
      .filter((poi) => poi.lat != null && poi.lng != null)
      .map((poi) => ({
        id: poi.poi_id,
        name: poi.name || `POI #${poi.poi_id}`,
        category: poi.category || "",
        address: poi.address,
        lng: poi.lng!,
        lat: poi.lat!,
        rating: poi.rating || 0,
        review_count: 0,
        tags: poi.tags || [],
      }))
  );

  mapStore.setPOIs(allPois);

  // Setup routes for each day
  const routes = trip.daily_plans
    .filter((day) => day.pois.length > 0)
    .map((day) => {
      const dayPois = day.pois
        .filter((poi) => poi.lat != null && poi.lng != null)
        .map((poi) => ({
          id: poi.poi_id,
          name: poi.name || `POI #${poi.poi_id}`,
          category: poi.category || "",
          lng: poi.lng!,
          lat: poi.lat!,
          rating: poi.rating || 0,
        }));

      return {
        day: day.day_number,
        pois: dayPois,
        total_distance_km: calculateDayDistance(dayPois),
      };
    });

  mapStore.setRoutes(routes);
}

// ── Calculate Day Distance ──────────────────────────────────────────────────
function calculateDayDistance(pois: { lat: number; lng: number }[]): number {
  if (pois.length < 2) return 0;
  let total = 0;
  for (let i = 0; i < pois.length - 1; i++) {
    total += haversineKm(pois[i], pois[i + 1]);
  }
  return total;
}

// ── Haversine Distance ──────────────────────────────────────────────────────
function haversineKm(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number }
): number {
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

// ── POI Selection Handler ───────────────────────────────────────────────────
function onPOISelect(poi: TripDayPOI): void {
  if (poi.lat == null || poi.lng == null) {
    ElMessage.warning("该地点无坐标信息");
    return;
  }

  const mapPoi = {
    id: poi.poi_id,
    name: poi.name || `POI #${poi.poi_id}`,
    category: poi.category || "",
    address: poi.address,
    lng: poi.lng,
    lat: poi.lat,
    rating: poi.rating || 0,
    review_count: 0,
    tags: poi.tags || [],
  };

  mapStore.selectPOI(mapPoi);
}

// ── Watch for trip changes ──────────────────────────────────────────────────
watch(
  () => tripStore.currentTrip,
  (newTrip) => {
    if (newTrip) {
      setupMapData();
    }
  }
);

// ── Lifecycle ───────────────────────────────────────────────────────────────
onMounted(() => {
  loadTrip();
});
</script>

<template>
  <div class="trip-detail-view">
    <!-- Header -->
    <header class="detail-header" v-if="tripStore.currentTrip">
      <div class="header-content">
        <button class="back-btn" @click="router.push('/')">
          <span>←</span> 返回
        </button>
        <div class="header-title">
          <h1>{{ tripStore.currentTrip.city }} {{ tripStore.currentTrip.days }}日游</h1>
          <p class="header-meta">
            创建于 {{ new Date(tripStore.currentTrip.created_at).toLocaleDateString() }}
          </p>
        </div>
      </div>
    </header>

    <!-- Loading State -->
    <div class="loading-container" v-if="tripStore.loading">
      <div class="loading-spinner"></div>
      <p>加载行程中...</p>
    </div>

    <!-- Main Content -->
    <main class="detail-content" v-if="tripStore.currentTrip && !tripStore.loading">
      <aside class="timeline-panel">
        <TripTimeline :trip="tripStore.currentTrip" @selectPOI="onPOISelect" />
      </aside>

      <section class="map-panel">
        <MapView />
      </section>
    </main>

    <!-- Error State -->
    <div class="error-container" v-if="tripStore.error">
      <div class="error-icon">⚠️</div>
      <p>{{ tripStore.error }}</p>
      <button class="retry-btn" @click="loadTrip">重试</button>
    </div>
  </div>
</template>

<style scoped>
.trip-detail-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg-base);
}

/* Header */
.detail-header {
  background: var(--color-bg-overlay);
  border-bottom: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
  z-index: var(--z-sticky);
}

.header-content {
  display: flex;
  align-items: center;
  gap: var(--space-xl);
  padding: var(--space-lg) var(--space-2xl);
}

.back-btn {
  background: var(--color-bg-muted);
  border: none;
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.back-btn:hover {
  background: var(--color-border);
  color: var(--color-primary);
}

.header-title {
  flex: 1;
}

.header-title h1 {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-xs);
}

.header-meta {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: var(--space-lg);
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border-light);
  border-top: 3px solid var(--color-primary);
  border-radius: var(--radius-round);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* Main Content */
.detail-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.timeline-panel {
  width: 50%;
  overflow-y: auto;
  background: var(--color-bg-base);
  border-right: 1px solid var(--color-border-light);
}

.map-panel {
  width: 50%;
  position: relative;
}

/* Error */
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: var(--space-lg);
  color: var(--color-text-regular);
}

.error-icon {
  font-size: 48px;
}

.retry-btn {
  background: var(--color-primary);
  color: #fff;
  border: none;
  padding: 10px 24px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-base);
  transition: background var(--transition-fast);
}

.retry-btn:hover {
  background: var(--color-primary-hover);
}

/* Responsive */
@media (max-width: 1024px) {
  .header-content {
    padding: var(--space-lg) var(--space-lg);
  }

  .header-title h1 {
    font-size: var(--font-size-xl);
  }

  .detail-content {
    flex-direction: column;
  }

  .timeline-panel {
    width: 100%;
    height: 50%;
    border-right: none;
    border-bottom: 1px solid var(--color-border-light);
  }

  .map-panel {
    width: 100%;
    height: 50%;
  }
}

@media (max-width: 768px) {
  .header-content {
    padding: var(--space-md) var(--space-lg);
    gap: var(--space-md);
  }

  .header-title h1 {
    font-size: var(--font-size-lg);
  }

  .back-btn {
    padding: 6px var(--space-md);
    font-size: 13px;
  }
}
</style>
