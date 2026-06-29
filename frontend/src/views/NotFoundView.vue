<script setup lang="ts">
</script>

<template>
  <div class="not-found-view">
    <h1>404 - Page Not Found</h1>
    <p>The page you are looking for does not exist.</p>
    <router-link to="/">Go Home</router-link>
  </div>
</template>

<style scoped>
.not-found-view {
  max-width: 800px;
  margin: 4rem auto;
  text-align: center;
}
</style>
