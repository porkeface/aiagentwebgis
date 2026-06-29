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
  background: #f5f7fa;
}

/* Header */
.detail-header {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  z-index: 100;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 32px;
}

.back-btn {
  background: #f0f0f0;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #e0e0e0;
  color: #1890ff;
}

.header-title {
  flex: 1;
}

.header-title h1 {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 4px;
}

.header-meta {
  font-size: 13px;
  color: #999;
  margin: 0;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 16px;
  color: #999;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #1890ff;
  border-radius: 50%;
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
  background: #f5f7fa;
  border-right: 1px solid #e8e8e8;
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
  gap: 16px;
  color: #666;
}

.error-icon {
  font-size: 48px;
}

.retry-btn {
  background: #1890ff;
  color: #fff;
  border: none;
  padding: 10px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: #40a9ff;
}

/* Responsive */
@media (max-width: 1024px) {
  .header-content {
    padding: 16px 20px;
  }

  .header-title h1 {
    font-size: 20px;
  }

  .detail-content {
    flex-direction: column;
  }

  .timeline-panel {
    width: 100%;
    height: 50%;
    border-right: none;
    border-bottom: 1px solid #e8e8e8;
  }

  .map-panel {
    width: 100%;
    height: 50%;
  }
}

@media (max-width: 768px) {
  .header-content {
    padding: 12px 16px;
    gap: 12px;
  }

  .header-title h1 {
    font-size: 18px;
  }

  .back-btn {
    padding: 6px 12px;
    font-size: 13px;
  }
}
</style>
