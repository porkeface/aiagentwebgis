<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useMapStore } from '@/stores/map'
import { useChatStore } from '@/stores/chat'
import type { POI } from '@/types'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const mapStore = useMapStore()
const chatStore = useChatStore()

const pois = computed<POI[]>(() => mapStore.pois)
const selected = computed<Set<string>>(() => mapStore.selectedPoiIds)
const selectedCount = computed(() => mapStore.selectedPoiCount)

function toggle(poi: POI): void {
  mapStore.togglePoiSelection(String(poi.id))
}

function selectAll(): void {
  if (selectedCount.value === pois.value.length) {
    mapStore.deselectAllPois()
  } else {
    mapStore.selectAllPois()
  }
}

const selectAllLabel = computed(() =>
  selectedCount.value === pois.value.length && pois.value.length > 0 ? '取消全选' : '全选',
)

function showDetail(poi: POI, event: Event): void {
  // Click on info area — open detail card without toggling checkbox
  event.stopPropagation()
  mapStore.selectPOI(poi)
}

function startPlanning(): void {
  const selectedPois = mapStore.getSelectedPois()
  if (selectedPois.length === 0) {
    ElMessage.warning('请先勾选兴趣点')
    return
  }

  const city = selectedPois[0]?.city || '未知城市'
  const items = selectedPois
    .map((p) => `- ${p.name} | id:${p.id} | lng:${p.lng} | lat:${p.lat}`)
    .join('\n')
  const message = `请直接用以下 ${selectedPois.length} 个 POI 在${city}规划行程。每个 POI 已有完整坐标，禁止调用 search_pois 重新搜索。根据 POI 数量和地理分布自行判断适合的天数：\n${items}`

  emit('close')
  chatStore.sendMessage(message)
}

function formatRating(r: number | undefined | null): string {
  if (r == null) return '暂无评分'
  return `★ ${Number(r).toFixed(1)}`
}

function formatReviews(n: number | undefined | null): string {
  if (n == null) return ''
  if (n >= 10000) return `${(n / 10000).toFixed(1)}w`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}
</script>

<template>
  <div class="poi-select-panel">
    <div class="poi-select-panel__header">
      <h3 class="poi-select-panel__title">兴趣点 ({{ pois.length }})</h3>
      <button class="poi-select-panel__select-all" @click="selectAll">
        {{ selectAllLabel }}
      </button>
      <button
        v-if="selectedCount > 0"
        class="poi-select-panel__header-plan"
        @click="startPlanning"
      >
        规划 ({{ selectedCount }})
      </button>
      <button class="poi-select-panel__close" @click="emit('close')">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
    </div>

    <div class="poi-select-panel__list">
      <div
        v-for="poi in pois"
        :key="poi.id"
        class="poi-card"
        :class="{ 'is-selected': selected.has(String(poi.id)) }"
        @click="toggle(poi)"
      >
        <div class="poi-card__check">
          <span class="poi-card__checkbox" :class="{ 'is-checked': selected.has(String(poi.id)) }">
            <svg v-if="selected.has(String(poi.id))" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3">
              <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
        </div>
        <div class="poi-card__info" @click="showDetail(poi, $event)">
          <p class="poi-card__name">{{ poi.name }}</p>
          <div class="poi-card__meta">
            <span class="poi-card__category">{{ poi.category }}</span>
            <span class="poi-card__rating">{{ formatRating(poi.rating) }}</span>
            <span v-if="(poi.review_count ?? 0) > 0" class="poi-card__reviews">{{ formatReviews(poi.review_count) }}</span>
          </div>
          <p v-if="poi.address" class="poi-card__address">{{ poi.address }}</p>
          <div v-if="poi.tags && poi.tags.length" class="poi-card__tags">
            <span v-for="tag in poi.tags.slice(0, 4)" :key="tag" class="poi-card__tag">{{ tag }}</span>
          </div>
        </div>
      </div>

      <div v-if="pois.length === 0" class="poi-select-panel__empty">
        <p>暂无兴趣点</p>
        <p class="secondary">搜索城市景点后会出现在这里</p>
      </div>
    </div>

    <div class="poi-select-panel__footer">
      <button
        class="poi-select-panel__plan-btn"
        :disabled="selectedCount === 0"
        @click="startPlanning"
      >
        按此规划线路 ({{ selectedCount }})
      </button>
    </div>
  </div>
</template>

<style scoped>
.poi-select-panel {
  display: flex;
  flex-direction: column;
  width: 360px;
  height: 100%;
  max-width: 90vw;
  background: var(--color-bg-base);
  border-right: 1px solid var(--color-hairline);
  box-shadow: 32px 0 64px -16px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  z-index: 2000;
  pointer-events: auto;
  backdrop-filter: blur(16px) saturate(1.4);
}

.poi-select-panel__header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-lg) var(--space-xl);
  border-bottom: 1px solid var(--color-hairline);
}

.poi-select-panel__title {
  flex: 1;
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-text-primary);
}

.poi-select-panel__select-all {
  padding: var(--space-xs) var(--space-md);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 0.6875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  white-space: nowrap;
}
.poi-select-panel__select-all:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.poi-select-panel__header-plan {
  padding: var(--space-xs) var(--space-md);
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: #fff;
  font-size: 0.6875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  white-space: nowrap;
}
.poi-select-panel__header-plan:hover {
  filter: brightness(1.1);
}

.poi-select-panel__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-circle);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}
.poi-select-panel__close:hover {
  background: var(--color-bg-subtle);
  color: var(--color-text-primary);
}

/* ── List ──────────────────────────────────────────────────────────────── */
.poi-select-panel__list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-md) var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.poi-select-panel__empty {
  padding: var(--space-3xl) var(--space-xl);
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 0.8125rem;
}
.poi-select-panel__empty .secondary {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
  margin-top: var(--space-xs);
}

/* ── POI Card ──────────────────────────────────────────────────────────── */
.poi-card {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out-expo);
  border-radius: var(--radius-md);
  background: var(--color-bg-subtle);
}
.poi-card:hover {
  background: var(--color-bg-subtle);
}
.poi-card.is-selected {
  background: var(--color-accent-subtle, rgba(232, 99, 60, 0.06));
}

.poi-card__check {
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
}

.poi-card__checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 1.5px solid var(--color-text-tertiary);
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  transition: all var(--duration-fast) var(--ease-out-expo);
  flex-shrink: 0;
}
.poi-card__checkbox.is-checked {
  border-color: var(--color-accent);
  background: var(--color-accent);
  color: #fff;
}
.poi-card.is-selected .poi-card__checkbox {
  border-color: var(--color-accent);
}

.poi-card__info {
  flex: 1;
  min-width: 0;
}

.poi-card__name {
  margin: 0 0 4px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.poi-card__meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: 2px;
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
}

.poi-card__category {
  padding: 1px var(--space-sm);
  border-radius: var(--radius-xs);
  background: var(--color-bg-subtle);
  font-size: 0.625rem;
  font-weight: 500;
}

.poi-card__rating {
  color: var(--color-accent);
  font-weight: 600;
}

.poi-card__reviews {
  color: var(--color-text-tertiary);
}

.poi-card__address {
  margin: 2px 0 0;
  font-size: 0.6875rem;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.poi-card__tags {
  display: flex;
  gap: var(--space-xs);
  margin-top: var(--space-xs);
  flex-wrap: wrap;
}

.poi-card__tag {
  padding: 1px var(--space-sm);
  border-radius: var(--radius-xs);
  background: rgba(232, 99, 60, 0.08);
  color: var(--color-accent);
  font-size: 0.625rem;
  font-weight: 500;
}

/* ── Footer ────────────────────────────────────────────────────────────── */
.poi-select-panel__footer {
  padding: var(--space-lg) var(--space-xl);
  border-top: 1px solid var(--color-hairline);
}

.poi-select-panel__plan-btn {
  width: 100%;
  padding: var(--space-md) var(--space-xl);
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-accent);
  color: #fff;
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}
.poi-select-panel__plan-btn:hover:not(:disabled) {
  filter: brightness(1.1);
}
.poi-select-panel__plan-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
