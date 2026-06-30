<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useTripStore } from '@/stores/trip'
import { useMapStore, type DailyPlan, type RoutePOI } from '@/stores/map'
import { useChatStore } from '@/stores/chat'
import { getToken } from '@/api/auth'
import type { Trip, TripDetail } from '@/types'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const tripStore = useTripStore()
const mapStore = useMapStore()
const chatStore = useChatStore()
const isLoggedIn = ref(!!getToken())

onMounted(() => {
  if (isLoggedIn.value) {
    tripStore.fetchTrips(1, 30).catch(() => {
      ElMessage.warning('加载行程列表失败')
    })
  }
})

// Refresh auth state from ChatPanel's auth flow
watch(
  () => chatStore.historySessions,
  () => {
    isLoggedIn.value = !!getToken()
  },
)

async function openTrip(trip: Trip): Promise<void> {
  try {
    const detail = await tripStore.fetchTripDetail(trip.id)
    if (detail) {
      loadTripToMap(detail)
      emit('close')
      ElMessage.success(`已加载「${trip.city}」行程`)
    }
  } catch {
    ElMessage.error('加载行程失败')
  }
}

async function removeTrip(trip: Trip, event: Event): Promise<void> {
  event.stopPropagation()
  const ok = await tripStore.deleteTrip(trip.id)
  if (ok) {
    ElMessage.success('行程已删除')
  } else {
    ElMessage.error(tripStore.error ?? '删除失败')
  }
}

/**
 * Save current map routes as a trip if there are any active routes.
 */
async function saveCurrentTrip(): Promise<void> {
  if (!isLoggedIn.value) {
    ElMessage.warning('保存行程需要先登录')
    return
  }
  const routes = mapStore.routes as DailyPlan[]
  if (!routes.length) {
    ElMessage.info('当前没有可保存的路线')
    return
  }

  const summary = mapStore.planSummary
  const city = summary?.city ?? '未命名城市'
  const days = summary?.days ?? routes.length

  const daily_plans = routes.map((r) => ({
    day: r.day,
    day_title: r.day_title || `第${r.day}天`,
    pois: (r.pois ?? []).map((p: RoutePOI) => ({
      id: p.id,
      name: p.name,
      category: p.category,
      lng: p.lng,
      lat: p.lat,
      rating: p.rating ?? null,
      address: p.address ?? null,
      tags: p.tags ?? [],
      photo: p.photo ?? undefined,
    })),
    total_distance_km: r.total_distance_km ?? 0,
  }))

  try {
    const trip = await tripStore.savePlan({ city, days, daily_plans })
    if (trip) {
      ElMessage.success(`行程已保存 (#${trip.id})`)
    }
  } catch {
    ElMessage.error('保存失败')
  }
}

/** Convert TripDetail to mapStore routes + POIs and render on map. */
function loadTripToMap(trip: TripDetail): void {
  if (!trip.daily_plans) return

  mapStore.clearMap()
  mapStore.setActiveDay(0)

  const allPois = trip.daily_plans.flatMap((day) =>
    day.pois
      .filter((poi) => poi.lat != null && poi.lng != null)
      .map((poi) => ({
        id: poi.poi_id,
        name: poi.name || `POI #${poi.poi_id}`,
        category: poi.category || '',
        address: poi.address,
        lng: poi.lng!,
        lat: poi.lat!,
        rating: poi.rating || 0,
        review_count: 0,
        tags: poi.tags || [],
      })),
  )

  const routes: DailyPlan[] = trip.daily_plans
    .filter((day) => day.pois.length > 0)
    .map((day) => ({
      day: day.day_number,
      day_title: `第${day.day_number}天`,
      pois: day.pois
        .filter((poi) => poi.lat != null && poi.lng != null)
        .map((poi) => ({
          id: poi.poi_id,
          name: poi.name || `POI #${poi.poi_id}`,
          category: poi.category || '',
          lng: poi.lng!,
          lat: poi.lat!,
          rating: poi.rating || 0,
          address: poi.address,
          tags: poi.tags || [],
        })),
    }))

  mapStore.setPOIs(allPois)
  mapStore.setRoutes(routes)
  mapStore.setPlanSummary({ city: trip.city, days: trip.days })
}
</script>

<template>
  <div class="trip-drawer">
    <div class="trip-drawer__head">
      <div class="trip-drawer__title-group">
        <span class="eyebrow">Collection</span>
        <h2 class="serif">My Itineraries</h2>
      </div>
      <button class="trip-drawer__close" @click="emit('close')">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M6 6l12 12M18 6L6 18" stroke-linecap="round" />
        </svg>
      </button>
    </div>
    <div class="trip-drawer__body">
      <div v-if="tripStore.loading" class="trip-drawer__empty">
        <p>Loading…</p>
      </div>
      <div v-else-if="tripStore.trips.length === 0" class="trip-drawer__empty">
        <p class="serif">No saved journeys yet.</p>
        <p class="trip-drawer__hint">Plan a route in chat, then save it here.</p>
      </div>
      <ul v-else class="trip-drawer__list">
        <li
          v-for="trip in tripStore.trips"
          :key="trip.id"
          class="trip-drawer__item"
          @click="openTrip(trip)"
        >
          <div class="trip-drawer__item-main">
            <div class="trip-drawer__item-meta">
              <span class="numeric">{{ trip.days }}d</span>
              <span class="trip-drawer__item-status" :class="`is-${trip.status}`">
                {{ trip.status === 'planned' ? 'Planned' : trip.status === 'draft' ? 'Draft' : trip.status }}
              </span>
            </div>
            <div class="trip-drawer__item-title serif">{{ trip.city }}</div>
            <div class="trip-drawer__item-sub">
              {{ new Date(trip.created_at).toLocaleDateString() }}
            </div>
          </div>
          <button
            class="trip-drawer__item-del"
            title="删除行程"
            @click="removeTrip(trip, $event)"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
            </svg>
          </button>
        </li>
      </ul>
      <button
        v-if="mapStore.routes.length > 0"
        class="trip-drawer__save-btn"
        @click="saveCurrentTrip"
      >
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 5v14M5 12h14" stroke-linecap="round" />
        </svg>
        <span>保存当前路线</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.trip-drawer {
  width: 360px;
  max-height: 100%;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.trip-drawer__body {
  overflow-y: auto;
  padding: var(--space-md) var(--space-xl) var(--space-xl);
  flex: 1;
}

.trip-drawer__body::-webkit-scrollbar {
  width: 4px;
}

.trip-drawer__body::-webkit-scrollbar-thumb {
  background: var(--color-hairline-strong);
  border-radius: 2px;
}

.trip-drawer__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: var(--space-lg) var(--space-xl);
  border-bottom: 1px solid var(--color-hairline);
  flex-shrink: 0;
}

.trip-drawer__title-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.trip-drawer__title-group h2 {
  font-family: var(--font-serif);
  font-size: var(--text-title);
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--letter-spacing-tight);
}

.trip-drawer__close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: var(--radius-circle);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.trip-drawer__close:hover {
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
}

.trip-drawer__body {
  overflow-y: auto;
  padding: var(--space-md) var(--space-xl) var(--space-xl);
}

.trip-drawer__empty {
  text-align: center;
  padding: var(--space-2xl) 0;
  color: var(--color-text-secondary);
  font-family: var(--font-serif);
  font-size: var(--text-body);
  font-style: italic;
}

.trip-drawer__hint {
  font-size: var(--text-meta);
  color: var(--color-text-muted);
  margin-top: var(--space-xs);
  font-style: normal;
  font-family: var(--font-sans);
}

.trip-drawer__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.trip-drawer__item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-base);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  position: relative;
}

.trip-drawer__item:hover {
  border-color: var(--color-accent);
  background: var(--color-bg-overlay);
  transform: translateX(2px);
}

.trip-drawer__item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.trip-drawer__item-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  color: var(--color-text-secondary);
}

.trip-drawer__item-meta .numeric {
  font-weight: 600;
  color: var(--color-accent);
  letter-spacing: 0.05em;
}

.trip-drawer__item-status {
  padding: 1px var(--space-sm);
  border-radius: var(--radius-pill);
  background: var(--color-bg-muted);
  font-size: var(--text-micro);
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  color: var(--color-text-secondary);
}

.trip-drawer__item-status.is-planned {
  color: var(--color-sage);
  background: var(--color-sage-soft);
}

.trip-drawer__item-status.is-draft {
  color: var(--color-amber);
  background: var(--color-amber-soft);
}

.trip-drawer__item-title {
  font-family: var(--font-serif);
  font-size: var(--text-subtitle);
  font-weight: 500;
  color: var(--color-text-primary);
  letter-spacing: var(--letter-spacing-tight);
  line-height: 1.2;
}

.trip-drawer__item-sub {
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  letter-spacing: var(--letter-spacing-wide);
}

.trip-drawer__item-del {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--color-text-muted);
  border-radius: var(--radius-circle);
  opacity: 0;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.trip-drawer__item:hover .trip-drawer__item-del {
  opacity: 1;
}

.trip-drawer__item-del:hover {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}

.trip-drawer__save-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  width: 100%;
  margin-top: var(--space-md);
  padding: var(--space-md);
  background: var(--color-accent);
  color: var(--color-bg-deep);
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  font-weight: 500;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.trip-drawer__save-btn:hover {
  background: var(--color-accent-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent);
}
</style>
