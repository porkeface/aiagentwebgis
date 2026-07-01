<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { POI } from '@/types'

// ── Props & Emits ────────────────────────────────────────────────────────────
interface Props {
  poi: POI
  day?: number
  stopNumber?: number
  accentColor?: string
}

const props = withDefaults(defineProps<Props>(), {
  day: undefined,
  stopNumber: undefined,
  accentColor: '#e8623c',
})

const emit = defineEmits<{ close: [] }>()

// ── Derived ──────────────────────────────────────────────────────────────────
const hasRating = computed(() => typeof props.poi.rating === 'number' && props.poi.rating > 0)
const ratingFixed = computed(() =>
  hasRating.value ? Number(props.poi.rating).toFixed(1) : '—',
)
const visibleTags = computed(() => {
  const raw = props.poi.tags ?? []
  return [...new Set(raw)].filter(Boolean).slice(0, 4)
})
const hasAddress = computed(() => {
  const addr = props.poi.address
  return typeof addr === 'string' && addr.trim().length > 0
})
const photoFailed = ref(false)
watch(() => props.poi?.id, () => { photoFailed.value = false })
const hasPhoto = computed(() => !!props.poi.photo && !photoFailed.value)

function onClose(): void {
  emit('close')
}
</script>

<template>
  <transition name="card">
    <article v-if="poi" class="poi-card" :style="{ '--accent': accentColor }">
      <!-- Hero photo -->
      <div v-if="hasPhoto" class="poi-card__hero">
        <img
          :src="poi.photo!"
          :alt="poi.name"
          class="poi-card__photo"
          loading="lazy"
          @error="photoFailed = true"
        />
        <div class="poi-card__hero-overlay"></div>

        <button class="poi-card__close" title="关闭" @click="onClose">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M6 6l12 12M18 6L6 18" stroke-linecap="round" />
          </svg>
        </button>

        <div v-if="stopNumber != null" class="poi-card__stop-badge">
          <span class="poi-card__stop-num numeric serif">{{ stopNumber.toString().padStart(2, '0') }}</span>
          <span v-if="day != null" class="eyebrow">Day {{ day }}</span>
        </div>
      </div>

      <!-- No photo: header-only layout -->
      <header v-else class="poi-card__head">
        <div v-if="stopNumber != null" class="poi-card__stop-badge poi-card__stop-badge--inline">
          <span class="poi-card__stop-num numeric serif">{{ stopNumber.toString().padStart(2, '0') }}</span>
          <span v-if="day != null" class="eyebrow">Day {{ day }}</span>
        </div>
        <button class="poi-card__close" title="关闭" @click="onClose">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M6 6l12 12M18 6L6 18" stroke-linecap="round" />
          </svg>
        </button>
      </header>

      <!-- Content -->
      <div class="poi-card__body">
        <div class="poi-card__eyebrow eyebrow">
          <span v-if="poi.category">{{ poi.category }}</span>
        </div>

        <h3 class="poi-card__name serif">{{ poi.name }}</h3>

        <div v-if="hasRating" class="poi-card__rating">
          <span class="poi-card__rating-star">★</span>
          <span class="poi-card__rating-num numeric">{{ ratingFixed }}</span>
          <span v-if="poi.review_count" class="poi-card__rating-count">
            · {{ poi.review_count }} reviews
          </span>
        </div>

        <p v-if="hasAddress" class="poi-card__address">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 22s8-7.5 8-13a8 8 0 0 0-16 0c0 5.5 8 13 8 13z" stroke-linejoin="round" />
            <circle cx="12" cy="9" r="3" />
          </svg>
          <span>{{ poi.address }}</span>
        </p>

        <p v-if="poi.description" class="poi-card__description serif italic">
          {{ poi.description }}
        </p>

        <div v-if="visibleTags.length" class="poi-card__tags">
          <span v-for="tag in visibleTags" :key="tag" class="poi-card__tag">{{ tag }}</span>
        </div>
      </div>
    </article>
  </transition>
</template>

<style scoped>
.card-enter-active, .card-leave-active {
  transition: all var(--duration-slow) var(--ease-out-expo);
}
.card-enter-from, .card-leave-to {
  opacity: 0;
  transform: translateY(16px);
}

.poi-card {
  position: absolute;
  left: 50%;
  bottom: var(--space-xl);
  transform: translateX(-50%);
  width: min(420px, calc(100vw - var(--sidebar-width) - 48px));
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card-hover);
  overflow: hidden;
  /* Must exceed map overlay z-index so the card always wins against popups. */
  z-index: 1000;
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

/* On mobile, span full width with side padding */
@media (max-width: 767px) {
  .poi-card {
    width: calc(100vw - var(--space-xl) * 2);
    left: var(--space-xl);
    transform: none;
  }
}

/* ── Hero photo ───────────────────────────────────────────────────────── */
.poi-card__hero {
  position: relative;
  width: 100%;
  height: 180px;
  overflow: hidden;
  background: var(--color-bg-deep);
}

.poi-card__photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform var(--duration-slower) var(--ease-out-expo);
}

.poi-card:hover .poi-card__photo {
  transform: scale(1.04);
}

.poi-card__hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 40%, rgba(14, 17, 22, 0.65) 100%);
  pointer-events: none;
}

.poi-card__close {
  position: absolute;
  top: var(--space-md);
  right: var(--space-md);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(14, 17, 22, 0.6);
  backdrop-filter: blur(8px);
  color: var(--color-text-primary);
  border-radius: var(--radius-circle);
  transition: all var(--duration-fast) var(--ease-out-expo);
  z-index: 2;
}

.poi-card__close:hover {
  background: var(--color-accent);
  color: var(--color-bg-deep);
  transform: rotate(90deg);
}

.poi-card__stop-badge {
  position: absolute;
  bottom: var(--space-md);
  left: var(--space-md);
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xs) var(--space-md) var(--space-xs) var(--space-xs);
  background: rgba(14, 17, 22, 0.7);
  backdrop-filter: blur(8px);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-pill);
  z-index: 2;
}

.poi-card__stop-badge--inline {
  position: static;
  background: transparent;
  backdrop-filter: none;
  border: none;
  padding: 0;
  color: var(--color-accent);
}

.poi-card__stop-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 var(--space-sm);
  background: var(--color-accent);
  color: var(--color-bg-deep);
  border-radius: var(--radius-pill);
  font-family: var(--font-serif);
  font-style: italic;
  font-size: var(--text-meta);
  font-weight: 500;
}

.poi-card__stop-badge--inline .poi-card__stop-num {
  background: var(--color-accent-soft);
  color: var(--color-accent);
  border: 1px solid var(--color-accent);
}

.poi-card__stop-badge .eyebrow {
  color: var(--color-text-primary);
}

/* ── Header (no photo case) ─────────────────────────────────────────── */
.poi-card__head {
  position: relative;
  padding: var(--space-lg) var(--space-lg) 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-md);
}

.poi-card__head .poi-card__close {
  position: static;
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-hairline);
}

.poi-card__head .poi-card__close:hover {
  background: var(--color-accent);
  color: var(--color-bg-deep);
  border-color: var(--color-accent);
}

/* ── Body ────────────────────────────────────────────────────────────── */
.poi-card__body {
  padding: var(--space-lg) var(--space-lg) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.poi-card__eyebrow {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-accent);
}

.poi-card__name {
  font-family: var(--font-serif);
  font-size: var(--text-title);
  font-weight: 500;
  color: var(--color-text-primary);
  line-height: 1.15;
  letter-spacing: var(--letter-spacing-tight);
  margin: 0;
}

.poi-card__rating {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  font-family: var(--font-sans);
  color: var(--color-amber);
  font-size: var(--text-meta);
}

.poi-card__rating-star {
  font-size: var(--text-body);
  line-height: 1;
}

.poi-card__rating-num {
  font-weight: 600;
  font-size: var(--text-body);
  letter-spacing: 0.02em;
}

.poi-card__rating-count {
  color: var(--color-text-muted);
  font-size: var(--text-caption);
}

.poi-card__address {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
}

.poi-card__address svg {
  color: var(--color-text-muted);
  flex-shrink: 0;
  margin-top: 2px;
}

.poi-card__description {
  font-family: var(--font-serif);
  font-size: var(--text-body);
  font-style: italic;
  color: var(--color-text-regular);
  line-height: var(--line-height-relaxed);
  margin: var(--space-xs) 0 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.poi-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
  margin-top: var(--space-xs);
}

.poi-card__tag {
  font-family: var(--font-sans);
  font-size: var(--text-micro);
  font-weight: 500;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  padding: 2px var(--space-sm);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-hairline-strong);
}
</style>