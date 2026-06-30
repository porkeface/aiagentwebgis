<script setup lang="ts">
import { computed } from "vue";
import { useMapStore, type DailyPlan, type RoutePOI } from "@/stores/map";
import { DAY_COLORS } from "@/utils/constants";

// ── Store ────────────────────────────────────────────────────────────────────
const mapStore = useMapStore();

// ── Derived data ─────────────────────────────────────────────────────────────
const hasRoutes = computed(() => mapStore.routes.length > 0);

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

function formatDistance(km: number): string {
    if (km < 1) return `${Math.round(km * 1000)}m`;
    return `${km.toFixed(1)}km`;
}

function formatDuration(min: number): string {
    if (!min || min < 1) return "—";
    if (min < 60) return `${min} min`;
    const h = Math.floor(min / 60);
    const m = min % 60;
    return m === 0 ? `${h} hr` : `${h}h ${m}m`;
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

function formatTimeSlot(slot: string | undefined): string {
    if (!slot) return "";
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
                                    v-if="poi.time_slot"
                                    class="itin__chip itin__chip--time-slot"
                                >
                                    {{ formatTimeSlot(poi.time_slot) }}
                                </span>
                                <span v-if="poi.category" class="itin__chip">{{
                                    poi.category
                                }}</span>
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
                                <span class="itin__stop-next-rule"></span>
                                <span class="numeric">{{
                                    formatDistance(
                                        plan.segments[idx]?.distance_km ?? 0,
                                    )
                                }}</span>
                                <span class="itin__stop-next-dot">·</span>
                                <span>{{
                                    formatDuration(
                                        plan.segments[idx]?.duration_min ??
                                            Math.round(
                                                ((plan.segments[idx]
                                                    ?.distance_km ?? 0) /
                                                    30) *
                                                    60,
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
