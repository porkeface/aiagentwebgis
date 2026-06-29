<script setup lang="ts">
import MapView from '@/components/map/MapView.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
</script>

<template>
  <div class="home-view">
    <div class="home-view__map">
      <MapView />
    </div>
    <div class="home-view__chat">
      <ChatPanel />
    </div>
  </div>
</template>

<style scoped>
.home-view {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
}

.home-view__map {
  flex: 0 0 60%;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.home-view__chat {
  flex: 0 0 40%;
  height: 100%;
  overflow: hidden;
  border-left: 1px solid var(--color-border);
}

/* Responsive: stack vertically on mobile */
@media (max-width: 767px) {
  .home-view {
    flex-direction: column;
  }

  .home-view__map {
    flex: 0 0 45vh;
    min-height: 200px;
  }

  .home-view__chat {
    flex: 1;
    border-left: none;
    border-top: 1px solid var(--color-border);
  }
}

/* Small phones */
@media (max-width: 374px) {
  .home-view__map {
    flex: 0 0 35vh;
  }
}
</style>
