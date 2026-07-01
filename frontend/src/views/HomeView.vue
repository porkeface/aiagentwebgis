<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import MapView from '@/components/map/MapView.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'

const route = useRoute()

// ── Mobile view toggle ────────────────────────────────────────────────────
const mobileView = ref<'map' | 'chat'>('chat')

function showMap(): void {
  mobileView.value = 'map'
}

function showChat(): void {
  mobileView.value = 'chat'
}

function handleAuthHint(): void {
  if (route.query.auth === 'required') {
    ElMessage.warning('请先登录后再访问行程详情')
  }
}

onMounted(handleAuthHint)
watch(() => route.query.auth, handleAuthHint)
</script>

<template>
  <div class="home-view">
    <!-- Desktop: map fills inset space; chat panel is fixed to the right -->
    <div class="home-view__map" :class="{ 'is-visible': mobileView === 'map' }">
      <MapView />
    </div>

    <aside class="home-view__panel" :class="{ 'is-visible': mobileView === 'chat' }">
      <ChatPanel />
    </aside>

    <!-- Mobile toggle bar -->
    <div class="mobile-toggle">
      <button
        class="mobile-toggle__btn"
        :class="{ 'is-active': mobileView === 'map' }"
        @click="showMap"
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M1 6v12a3 3 0 003 3h16a3 3 0 003-3V6a3 3 0 00-3-3H4a3 3 0 00-3 3z" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M9 3v18" stroke-linecap="round"/>
          <path d="M1 9h8M1 15h8" stroke-linecap="round"/>
        </svg>
        <span>地图</span>
      </button>
      <button
        class="mobile-toggle__btn"
        :class="{ 'is-active': mobileView === 'chat' }"
        @click="showChat"
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>对话</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  position: relative;
  height: 100vh;
  width: 100%;
  overflow: hidden;
  background: var(--color-bg-deep);
  isolation: isolate; /* Establishes a stacking context for the children. */
}

.home-view__map {
  position: absolute;
  inset: 0;
  /* The map shrinks to leave room for the chat panel on wide screens. */
  right: var(--sidebar-width);
  overflow: hidden;
  z-index: 0;
}

.home-view__panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: var(--sidebar-width);
  z-index: 10;
  background: var(--color-bg-base);
  border-left: 1px solid var(--color-hairline);
  box-shadow: -32px 0 64px -16px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

/* Tablet: narrower drawer, map shrinks less */
@media (max-width: 1024px) {
  .home-view__map {
    right: 340px;
  }
  .home-view__panel {
    width: 340px;
  }
}

/* Mobile: full-screen sheet; the map is hidden behind the panel and the
   user explicitly toggles the chat to see it. */
@media (max-width: 767px) {
  .home-view__map {
    right: 0;
    z-index: 0;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-fast) var(--ease-out-expo);
  }
  .home-view__map.is-visible {
    opacity: 1;
    pointer-events: auto;
  }
  .home-view__panel {
    width: 100%;
    border-left: none;
    box-shadow: none;
    z-index: 20;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-fast) var(--ease-out-expo);
  }
  .home-view__panel.is-visible {
    opacity: 1;
    pointer-events: auto;
  }
}

/* ── Mobile Toggle Bar ────────────────────────────────────────────────── */
.mobile-toggle {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  height: 56px;
  background: var(--color-bg-base);
  border-top: 1px solid var(--color-hairline);
  backdrop-filter: blur(16px) saturate(1.4);
}
.mobile-toggle__btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  font-size: 0.625rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-out-expo);
}
.mobile-toggle__btn.is-active {
  color: var(--color-accent);
}

@media (max-width: 767px) {
  .mobile-toggle {
    display: flex;
  }
  /* Add bottom padding so content isn't hidden behind the toggle bar */
  .home-view__panel {
    padding-bottom: 56px;
  }
}
</style>