<script setup lang="ts">
import { computed, ref } from "vue";
import { useMapStore, type DailyPlan, type RoutePOI } from "@/stores/map";
import { DAY_COLORS } from "@/utils/constants";
import {
  estimateDuration,
  formatDistance,
  formatDuration,
  MODE_META,
  type TransportMode,
} from "@/utils/format";

// ── Store ────────────────────────────────────────────────────────────────────
const mapStore = useMapStore();

// ── Transport mode helpers ───────────────────────────────────────────────────
// MODE_META is the single source of truth (see utils/format.ts).
function modeMeta(mode: string): { icon: string; label: string } {
  return MODE_META[mode as TransportMode] ?? { icon: '🚶', label: mode };
}
const MODE_OPTIONS: readonly TransportMode[] = ['walking', 'driving', 'transit'];

function getSegmentMode(day: number, idx: number): TransportMode {
  return mapStore.getSegmentMode(day, idx);
}
const segmentLoading = ref<Record<string, boolean>>({});

async function onSegmentModeChange(day: number, idx: number, m: TransportMode): Promise<void> {
  const key = `${day}-${idx}`;
  segmentLoading.value = { ...segmentLoading.value, [key]: true };
  try {
    await mapStore.setSegmentMode(day, idx, m);
  } finally {
    segmentLoading.value = { ...segmentLoading.value, [key]: false };
  }
}

// ── Derived data ─────────────────────────────────────────────────────────────
const dailyPlans = computed<DailyPlan[]>(() =>
    (mapStore.routes as DailyPlan[]).map((r) => ({
        day: r.day ?? 0,
        day_title: r.day_title ?? "",
        pois: (r.pois ?? []) as RoutePOI[],
        total_distance_km: r.total_distance_km ?? 0,
        segments: r.segments ?? [],
    })),
);

const dayDurationMin = computed(() =>
    dailyPlans.value.reduce<Record<number, number>>((acc, plan) => {
        let mins = 0;
        for (const seg of plan.segments || []) {
            mins +=
                seg.duration_min ??
                Math.round(((seg.distance_km ?? 0) / 30) * 60);
        }
        acc[plan.day] = mins;
        return acc;
    }, {}),
);

// ── Helpers ──────────────────────────────────────────────────────────────────
function getDayColor(day: number): string {
    if (day < 1) return DAY_COLORS[0];
    const idx = Math.min(day - 1, DAY_COLORS.length - 1);
    return DAY_COLORS[idx];
}

function onSelectPOI(poi: RoutePOI, day: number): void {
    if (poi.lat == null || poi.lng == null) return;
    mapStore.setActiveDay(day);
    mapStore.selectPOI({
        id: poi.id,
        name: poi.name,
        category: poi.category,
        address: poi.address ?? null,
        lng: poi.lng,
        lat: poi.lat,
        rating: poi.rating ?? null,
        review_count: null,
        tags: poi.tags ?? [],
    });
}

function hexToRgb(hex: string): string {
    const cleaned = hex.replace("#", "");
    if (cleaned.length !== 6) return "0,0,0";
    const r = parseInt(cleaned.slice(0, 2), 16);
    const g = parseInt(cleaned.slice(2, 4), 16);
    const b = parseInt(cleaned.slice(4, 6), 16);
    return `${r},${g},${b}`;
}

const TIME_SLOT_LABELS: Record<string, string> = {
    morning: "上午",
    noon: "午餐",
    afternoon: "下午",
    evening: "晚间",
};

/** Category → icon mapping. Rendered as a small chip before the category label. */
const CATEGORY_ICONS: Record<string, string> = {
    "风景名胜": "🏔",
    "国家级景点": "🏔",
    "世界遗产": "🏛",
    "博物馆": "🏛",
    "展览馆": "🏛",
    "美术馆": "🎨",
    "科技馆": "🔬",
    "寺庙道观": "🛕",
    "教堂": "⛪",
    "纪念馆": "🏛",
    "公园": "🌿",
    "城市广场": "⛲",
    "动物园": "🦁",
    "植物园": "🌺",
    "水族馆": "🐠",
    "游乐园": "🎢",
    "主题公园": "🎢",
    "国家级森林公园": "🌲",
    "海滩": "🏖",
    "岛屿": "🏝",
    "温泉": "♨",
    "文化街区": "🏘",
    "历史遗址": "🏚",
    "古村镇": "🏡",
    "特色街区": "🏘",
    "创意园区": "🎨",
    "购物中心": "🛍",
    "商业步行街": "🛍",
    "夜市": "🏮",
    "美食街": "🍜",
    "特色餐厅": "🍜",
    "电影院": "🎬",
    "剧院": "🎭",
    "音乐厅": "🎵",
    "夜游": "🌃",
    "游船": "⛵",
    "观景台": "🔭",
    "缆车": "🚡",
    "运动场馆": "⚽",
    "滑雪场": "⛷",
    "高尔夫球场": "⛳",
    "登山": "🥾",
    "徒步路线": "🥾",
    "会展中心": "🏢",
    "用餐": "🍴",
    "自然风光": "🌄",
    "休闲娱乐": "🎯",
    "特色村落": "🏡",
    "宗教场所": "🛕",
    "历史文化街区": "🏘",
};

function categoryIcon(cat: string | undefined): string {
    if (!cat) return "";
    if (CATEGORY_ICONS[cat]) return CATEGORY_ICONS[cat];
    // Try substring match
    for (const [key, icon] of Object.entries(CATEGORY_ICONS)) {
        if (cat.includes(key)) return icon;
    }
    return "📍";
}

/** Clean Amap multi-level category (e.g. "风景名胜;风景名胜;寺庙道观" → "风景名胜") */
function cleanCategory(cat: string | undefined): string {
    if (!cat) return "";
    // Take first segment before semicolon, strip redundant suffixes
    const first = cat.split(";")[0] || "";
    return first.replace(/;.*$/, "").trim();
}

function formatTimeSlot(slot: string | undefined): string {
    if (!slot) return "";
    // New format: "09:00 - 10:30" — display as-is
    if (slot.includes(" - ")) return slot;
    // Legacy format: "morning", "noon", etc.
    return TIME_SLOT_LABELS[slot] || slot;
}
</script>

<template>
    <aside class="itin">
        <!-- Header -->
        <header class="itin__header">
            <div class="itin__brand">
                <span class="itin__brand-eyebrow">Itinerary</span>
                <h2 class="itin__city serif" v-if="mapStore.planSummary">
                    {{ mapStore.planSummary.city }}
                    <span class="itin__days numeric"
                        >{{ mapStore.planSummary.days }}日</span
                    >
                </h2>
                <h2 class="itin__city serif" v-else>My Itinerary</h2>
            </div>
            <button
                class="itin__close"
                title="收起行程面板"
                @click="mapStore.closeTimeline()"
            >
                <svg
                    viewBox="0 0 24 24"
                    width="14"
                    height="14"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                >
                    <path d="M6 6l12 12M18 6L6 18" stroke-linecap="round" />
                </svg>
            </button>
        </header>

        <!-- Summary stats -->
        <div class="itin__summary">
            <div class="itin__stat">
                <span class="itin__stat-num numeric serif">{{
                    mapStore.totalStopCount
                }}</span>
                <span class="itin__stat-label">stops</span>
            </div>
            <div class="itin__stat-divider"></div>
            <div class="itin__stat">
                <span class="itin__stat-num numeric serif">{{
                    formatDistance(mapStore.totalDistanceKm)
                }}</span>
                <span class="itin__stat-label">distance</span>
            </div>
            <div class="itin__stat-divider"></div>
            <div class="itin__stat">
                <span class="itin__stat-num numeric serif">{{
                    formatDuration(mapStore.totalDurationMin)
                }}</span>
                <span class="itin__stat-label">duration</span>
            </div>
        </div>

        <!-- Day tabs -->
        <nav class="itin__tabs" v-if="dailyPlans.length > 1">
            <button
                class="itin__tab"
                :class="{ 'itin__tab--active': mapStore.activeDay === 0 }"
                @click="mapStore.setActiveDay(0)"
            >
                <span class="itin__tab-mark">∗</span>
                <span class="itin__tab-label">All</span>
            </button>
            <button
                v-for="day in mapStore.availableDays"
                :key="day"
                class="itin__tab"
                :class="{ 'itin__tab--active': mapStore.activeDay === day }"
                @click="mapStore.setActiveDay(day)"
            >
                <span class="itin__tab-num numeric">{{
                    day.toString().padStart(2, "0")
                }}</span>
                <span class="itin__tab-label">Day</span>
            </button>
        </nav>

        <!-- Body: per-day cards -->
        <div class="itin__body">
            <section
                v-for="plan in dailyPlans"
                :key="plan.day"
                class="itin__day"
                :class="{
                    'itin__day--faded':
                        mapStore.activeDay !== 0 &&
                        mapStore.activeDay !== plan.day,
                }"
            >
                <div class="itin__day-head">
                    <div
                        class="itin__day-num serif"
                        :style="{ color: getDayColor(plan.day) }"
                    >
                        {{ plan.day.toString().padStart(2, "0") }}
                    </div>
                    <div class="itin__day-meta">
                        <div class="itin__day-title serif">
                            {{ plan.day_title || `第${plan.day}天` }}
                        </div>
                        <div class="itin__day-stats eyebrow">
                            {{ plan.pois.length }} stops ·
                            {{ formatDistance(plan.total_distance_km ?? 0) }}
                            <span class="itin__day-stats-divider">·</span>
                            {{ formatDuration(dayDurationMin[plan.day] || 0) }}
                        </div>
                    </div>
                </div>

                <ol class="itin__stops">
                    <li
                        v-for="(poi, idx) in plan.pois"
                        :key="`${plan.day}-${poi.id}-${idx}`"
                        class="itin__stop"
                        :class="{
                            'itin__stop--selected':
                                mapStore.selectedPOI?.id === poi.id,
                        }"
                        @click="onSelectPOI(poi, plan.day)"
                    >
                        <div class="itin__stop-rail">
                            <div
                                class="itin__stop-dot"
                                :style="{
                                    background: getDayColor(plan.day),
                                    boxShadow: `0 0 0 3px rgba(${hexToRgb(getDayColor(plan.day))}, 0.18)`,
                                }"
                            >
                                <span class="numeric">{{
                                    (idx + 1).toString().padStart(2, "0")
                                }}</span>
                            </div>
                            <div
                                v-if="idx < plan.pois.length - 1"
                                class="itin__stop-line"
                                :style="{ background: getDayColor(plan.day) }"
                            ></div>
                        </div>

                        <div class="itin__stop-body">
                            <div class="itin__stop-name serif">
                                {{ poi.name }}
                            </div>
                            <div class="itin__stop-meta">
                                <span
                                    v-if="poi.visit_duration_min"
                                    class="itin__chip itin__chip--duration"
                                >
                                    {{ formatDuration(poi.visit_duration_min) }}
                                </span>
                                <span
                                    v-if="poi.time_slot"
                                    class="itin__chip itin__chip--time-slot"
                                >
                                    {{ formatTimeSlot(poi.time_slot) }}
                                </span>
                                <span v-if="poi.category" class="itin__chip itin__chip--category">
                                    {{ categoryIcon(poi.category) }} {{ cleanCategory(poi.category) }}
                                </span>
                                <span
                                    v-if="poi.rating != null"
                                    class="itin__chip itin__chip--rating"
                                >
                                    ★ {{ Number(poi.rating).toFixed(1) }}
                                </span>
                            </div>
                            <div
                                v-if="
                                    idx < plan.pois.length - 1 &&
                                    plan.segments &&
                                    plan.segments[idx]
                                "
                                class="itin__stop-next"
                            >
                                <div
                                    class="mode-group"
                                    role="radiogroup"
                                    :aria-label="`${plan.pois[idx]?.name ?? ''} 到下一站的交通方式`"
                                >
                                    <button
                                        v-for="m in MODE_OPTIONS"
                                        :key="m"
                                        type="button"
                                        role="radio"
                                        :aria-checked="getSegmentMode(plan.day, idx) === m"
                                        class="mode-group__opt"
                                        :class="{
                                            'mode-group__opt--active': getSegmentMode(plan.day, idx) === m,
                                            [`mode-group__opt--${m}`]: true,
                                        }"
                                        :title="`切到 ${MODE_META[m].label}（≈${formatDuration(estimateDuration(plan.segments[idx]?.distance_km ?? 0, m))}）`"
                                        @click="onSegmentModeChange(plan.day, idx, m)"
                                    >
                                        <span class="mode-group__icon">{{ MODE_META[m].icon }}</span>
                                        <span class="mode-group__label">{{ MODE_META[m].label }}</span>
                                    </button>
                                </div>
                                <span class="numeric">{{
                                    formatDistance(
                                        plan.segments[idx]?.distance_km ?? 0,
                                    )
                                }}</span>
                                <span class="itin__stop-next-dot">·</span>
                                <span>{{
                                    formatDuration(
                                        plan.segments[idx]?.duration_min ??
                                            estimateDuration(
                                                plan.segments[idx]
                                                    ?.distance_km ?? 0,
                                                (plan.segments[idx]?.mode ??
                                                    'driving') as TransportMode,
                                            ),
                                    )
                                }}</span>
                            </div>
                        </div>
                    </li>
                </ol>
            </section>
        </div>

        <!-- Footer legend -->
        <footer class="itin__footer">
            <div class="itin__legend">
                <span class="itin__legend-item">
                    <span
                        class="itin__legend-dot itin__legend-dot--start"
                    ></span>
                    <span class="eyebrow">Origin</span>
                </span>
                <span class="itin__legend-item">
                    <span class="itin__legend-dot itin__legend-dot--mid"></span>
                    <span class="eyebrow">Stop</span>
                </span>
                <span class="itin__legend-item">
                    <span class="itin__legend-dot itin__legend-dot--end"></span>
                    <span class="eyebrow">End</span>
                </span>
            </div>
        </footer>
    </aside>
</template>

<style scoped>
.itin {
    width: var(--timeline-width);
    max-width: 340px;
    height: 100%;
    background: var(--color-bg-base);
    backdrop-filter: blur(20px) saturate(1.4);
    -webkit-backdrop-filter: blur(20px) saturate(1.4);
    border: 1px solid var(--color-hairline-strong);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-lg);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

/* ── Header ───────────────────────────────────────────────────────────── */
.itin__header {
    padding: var(--space-xl) var(--space-xl) var(--space-md);
    border-bottom: 1px solid var(--color-hairline);
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-md);
}

.itin__brand {
    display: flex;
    flex-direction: column;
    gap: var(--space-2xs);
    min-width: 0;
}

.itin__brand-eyebrow {
    font-family: var(--font-sans);
    font-size: var(--text-caption);
    font-weight: 500;
    letter-spacing: var(--letter-spacing-eyebrow);
    text-transform: uppercase;
    color: var(--color-accent);
}

.itin__city {
    font-family: var(--font-serif);
    font-size: var(--text-title);
    font-weight: 500;
    color: var(--color-text-primary);
    margin: 0;
    letter-spacing: var(--letter-spacing-tight);
    line-height: 1.1;
    display: flex;
    align-items: baseline;
    gap: var(--space-sm);
}

.itin__days {
    font-family: var(--font-sans);
    font-size: var(--text-meta);
    font-weight: 400;
    color: var(--color-text-secondary);
    letter-spacing: var(--letter-spacing-wide);
    text-transform: uppercase;
}

.itin__close {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    color: var(--color-text-secondary);
    border-radius: var(--radius-circle);
    flex-shrink: 0;
    transition: all var(--duration-fast) var(--ease-out-expo);
}

.itin__close:hover {
    background: var(--color-bg-muted);
    color: var(--color-text-primary);
}

/* ── Summary ─────────────────────────────────────────────────────────── */
.itin__summary {
    display: flex;
    align-items: center;
    gap: var(--space-md);
    padding: var(--space-md) var(--space-xl);
    border-bottom: 1px solid var(--color-hairline);
}

.itin__stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.itin__stat-num {
    font-family: var(--font-serif);
    font-size: var(--text-subtitle);
    font-weight: 500;
    font-style: italic;
    color: var(--color-text-primary);
    line-height: 1;
}

.itin__stat-label {
    font-family: var(--font-sans);
    font-size: var(--text-micro);
    color: var(--color-text-muted);
    letter-spacing: var(--letter-spacing-wide);
    text-transform: uppercase;
}

.itin__stat-divider {
    width: 1px;
    height: 24px;
    background: var(--color-hairline-strong);
}

/* ── Tabs ────────────────────────────────────────────────────────────── */
.itin__tabs {
    display: flex;
    gap: var(--space-2xs);
    padding: var(--space-sm) var(--space-md);
    border-bottom: 1px solid var(--color-hairline);
    overflow-x: auto;
    scrollbar-width: none;
}

.itin__tabs::-webkit-scrollbar {
    display: none;
}

.itin__tab {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2xs);
    padding: var(--space-xs) var(--space-md);
    background: transparent;
    color: var(--color-text-secondary);
    border-radius: var(--radius-pill);
    font-family: var(--font-sans);
    font-size: var(--text-caption);
    font-weight: 500;
    letter-spacing: var(--letter-spacing-wide);
    text-transform: uppercase;
    transition: all var(--duration-fast) var(--ease-out-expo);
    white-space: nowrap;
    border: 1px solid transparent;
}

.itin__tab:hover {
    color: var(--color-text-primary);
    background: rgba(243, 236, 225, 0.04);
}

.itin__tab--active {
    color: var(--color-text-primary);
    background: var(--color-bg-elevated);
    border-color: var(--color-hairline-strong);
}

.itin__tab-mark,
.itin__tab-num {
    font-family: var(--font-serif);
    font-style: italic;
    font-weight: 500;
    text-transform: none;
    letter-spacing: 0;
    font-size: var(--text-body);
    opacity: 0.85;
}

.itin__tab--active .itin__tab-mark,
.itin__tab--active .itin__tab-num {
    color: var(--color-accent);
    opacity: 1;
}

/* ── Body ────────────────────────────────────────────────────────────── */
.itin__body {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-lg);
}

.itin__day {
    margin-bottom: var(--space-2xl);
    transition: opacity var(--duration-normal);
}

.itin__day:last-child {
    margin-bottom: 0;
}

.itin__day--faded {
    opacity: 0.32;
}

.itin__day-head {
    display: flex;
    align-items: flex-start;
    gap: var(--space-md);
    margin-bottom: var(--space-lg);
    padding-bottom: var(--space-md);
    border-bottom: 1px solid var(--color-hairline);
}

.itin__day-num {
    font-family: var(--font-serif);
    font-size: var(--text-headline);
    font-weight: 500;
    font-style: italic;
    line-height: 1;
    letter-spacing: var(--letter-spacing-tight);
}

.itin__day-meta {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2xs);
    padding-top: var(--space-xs);
}

.itin__day-title {
    font-family: var(--font-serif);
    font-size: var(--text-subtitle);
    font-weight: 500;
    color: var(--color-text-primary);
    letter-spacing: var(--letter-spacing-tight);
    line-height: 1.2;
}

.itin__day-stats {
    font-family: var(--font-sans);
    font-size: var(--text-caption);
    color: var(--color-text-secondary);
    letter-spacing: var(--letter-spacing-wide);
}

.itin__day-stats-divider {
    margin: 0 var(--space-2xs);
    color: var(--color-text-muted);
}

/* ── Stops ───────────────────────────────────────────────────────────── */
.itin__stops {
    list-style: none;
    margin: 0;
    padding: 0;
}

.itin__stop {
    display: flex;
    gap: var(--space-md);
    cursor: pointer;
    padding: var(--space-sm) var(--space-xs);
    border-radius: var(--radius-md);
    transition: background var(--duration-fast) var(--ease-out-expo);
}

.itin__stop:hover {
    background: rgba(243, 236, 225, 0.04);
}

.itin__stop--selected {
    background: var(--color-accent-soft);
}

.itin__stop-rail {
    position: relative;
    width: 28px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: var(--space-xs);
}

.itin__stop-dot {
    width: 28px;
    height: 28px;
    border-radius: var(--radius-circle);
    color: var(--color-bg-deep);
    font-family: var(--font-sans);
    font-size: var(--text-micro);
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    z-index: 2;
    border: 2px solid var(--color-bg-base);
    transition: transform var(--duration-fast) var(--ease-out-expo);
}

.itin__stop:hover .itin__stop-dot {
    transform: scale(1.08);
}

.itin__stop-line {
    position: absolute;
    left: 50%;
    top: 30px;
    bottom: -8px;
    width: 1px;
    transform: translateX(-50%);
    z-index: 1;
    opacity: 0.4;
}

.itin__stop-body {
    flex: 1;
    min-width: 0;
    padding: var(--space-2xs) 0 var(--space-md);
}

.itin__stop-name {
    font-family: var(--font-serif);
    font-size: var(--text-body);
    font-weight: 500;
    color: var(--color-text-primary);
    letter-spacing: -0.005em;
    line-height: 1.3;
    margin-bottom: var(--space-2xs);
}

.itin__stop--selected .itin__stop-name {
    color: var(--color-accent);
}

.itin__stop-meta {
    display: flex;
    gap: var(--space-xs);
    flex-wrap: wrap;
    margin-bottom: var(--space-2xs);
}

.itin__chip {
    font-family: var(--font-sans);
    font-size: var(--text-micro);
    font-weight: 500;
    letter-spacing: var(--letter-spacing-wide);
    text-transform: uppercase;
    padding: 2px var(--space-sm);
    border-radius: var(--radius-pill);
    background: var(--color-bg-elevated);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-hairline);
}

.itin__chip--rating {
    color: var(--color-amber);
    background: var(--color-amber-soft);
    border-color: var(--color-amber);
}

.itin__chip--time-slot {
    font-family: var(--font-serif);
    font-style: italic;
    font-weight: 500;
    letter-spacing: 0;
    text-transform: none;
    color: var(--color-accent);
    background: rgba(232, 98, 60, 0.08);
    border-color: rgba(232, 98, 60, 0.25);
}

.itin__chip--duration {
    color: var(--color-sage);
    background: rgba(126, 148, 112, 0.08);
    border-color: rgba(126, 148, 112, 0.25);
}

.itin__chip--category {
    text-transform: none;
    letter-spacing: normal;
    font-size: var(--text-xs);
}

/* ── Inline segregated mode switcher (replaces single .itin__chip--mode) ── */
.mode-group {
    display: inline-flex;
    gap: 2px;
    padding: 2px;
    background: var(--color-bg-overlay);
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-pill);
    flex-shrink: 0;
}
.mode-group__opt {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 2px 8px;
    border-radius: var(--radius-pill);
    font-size: 0.65rem;
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
.mode-group__icon { font-size: 11px; }
.itin__stop-next .mode-group {
    margin-right: var(--space-md);
}

.itin__stop-next {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    margin-top: var(--space-sm);
    font-family: var(--font-sans);
    font-size: var(--text-caption);
    color: var(--color-text-muted);
    letter-spacing: var(--letter-spacing-wide);
}

.itin__stop-next-rule {
    flex: 1;
    height: 1px;
    background: var(--color-hairline-strong);
    margin-right: var(--space-xs);
}

.itin__stop-next-dot {
    color: var(--color-text-muted);
}

/* ── Footer ──────────────────────────────────────────────────────────── */
.itin__footer {
    padding: var(--space-md) var(--space-xl);
    border-top: 1px solid var(--color-hairline);
    background: var(--color-bg-elevated);
}

.itin__legend {
    display: flex;
    gap: var(--space-lg);
    align-items: center;
    justify-content: space-between;
}

.itin__legend-item {
    display: inline-flex;
    align-items: center;
    gap: var(--space-sm);
}

.itin__legend-dot {
    width: 8px;
    height: 8px;
    border-radius: var(--radius-circle);
    background: var(--color-text-muted);
}

.itin__legend-dot--start {
    background: var(--color-accent);
}

.itin__legend-dot--mid {
    background: var(--color-amber);
}

.itin__legend-dot--end {
    background: var(--color-sage);
}

.itin__legend .eyebrow {
    font-size: var(--text-micro);
    color: var(--color-text-muted);
}
</style>
