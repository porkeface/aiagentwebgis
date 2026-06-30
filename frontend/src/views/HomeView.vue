<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import MapView from '@/components/map/MapView.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'

const route = useRoute()

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
    <!-- The map fills the full viewport but is inset on the right by the
         chat panel's width. This way the map's tiles never bleed under the
         panel and the two never fight for stacking-context dominance. -->
    <div class="home-view__map">
      <MapView />
    </div>

    <!-- The chat panel is its own floating surface, lifted above the map
         by z-index. It owns the right edge of the screen and always wins. -->
    <aside class="home-view__panel">
      <ChatPanel />
    </aside>
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
  }
  .home-view__panel {
    width: 100%;
    border-left: none;
    box-shadow: none;
    z-index: 20;
  }
}
</style>