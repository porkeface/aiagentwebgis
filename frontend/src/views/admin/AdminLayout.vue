<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const isActive = (path: string) => route.path === path

function navigate(path: string): void {
  router.push(path)
}
</script>

<template>
  <div class="admin-layout">
    <nav class="admin-sidebar">
      <div class="admin-sidebar__brand">
        <span class="eyebrow">Admin</span>
        <h2 class="serif">Console</h2>
      </div>

      <ul class="admin-sidebar__nav">
        <li>
          <button
            class="admin-sidebar__item"
            :class="{ active: isActive('/admin/models') }"
            @click="navigate('/admin/models')"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="2" y="2" width="20" height="20" rx="4" />
              <circle cx="8" cy="8" r="1.5" />
              <path d="M16 8l-6 6M10 16h5" stroke-linecap="round" />
            </svg>
            <span>模型配置</span>
          </button>
        </li>
        <li>
          <button
            class="admin-sidebar__item"
            :class="{ active: isActive('/admin/users') }"
            @click="navigate('/admin/users')"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="9" cy="7" r="4" />
              <path d="M3 21v-2a4 4 0 014-4h4a4 4 0 014 4v2" stroke-linecap="round" />
            </svg>
            <span>用户管理</span>
          </button>
        </li>
        <li>
          <button
            class="admin-sidebar__item"
            :class="{ active: isActive('/admin/data') }"
            @click="navigate('/admin/data')"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            <span>数据管理</span>
          </button>
        </li>
        <li>
          <button
            class="admin-sidebar__item"
            :class="{ active: isActive('/admin/database') }"
            @click="navigate('/admin/database')"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 7v10c0 2 4 3.5 8 3.5s8-1.5 8-3.5V7" />
              <path d="M12 3C8 3 4 4.5 4 7s4 4 8 4 8-1.5 8-4-4-4-8-4z" stroke-linejoin="round" />
            </svg>
            <span>数据库</span>
          </button>
        </li>
      </ul>

      <div class="admin-sidebar__foot">
        <button class="admin-sidebar__item" @click="router.push('/')">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3 12l9-9 9 9M5 10v10a1 1 0 001 1h3a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1h3a1 1 0 001-1V10" stroke-linejoin="round" />
          </svg>
          <span>返回首页</span>
        </button>
      </div>
    </nav>

    <main class="admin-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  height: 100vh;
  background: var(--color-bg-deep);
  color: var(--color-text-regular);
  overflow: hidden;
}

.admin-sidebar {
  width: 240px;
  background: var(--color-bg-base);
  border-right: 1px solid var(--color-hairline);
  display: flex;
  flex-direction: column;
  padding: var(--space-xl);
  gap: var(--space-xl);
  flex-shrink: 0;
}

.admin-sidebar__brand {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.admin-sidebar__brand h2 {
  font-family: var(--font-serif);
  font-size: var(--text-title);
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--letter-spacing-tight);
}

.admin-sidebar__nav {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  flex: 1;
}

.admin-sidebar__item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  font-weight: 500;
  color: var(--color-text-secondary);
  letter-spacing: var(--letter-spacing-wide);
  transition: all var(--duration-fast) var(--ease-out-expo);
  background: transparent;
  border: none;
  cursor: pointer;
}

.admin-sidebar__item:hover {
  color: var(--color-text-primary);
  background: rgba(243, 236, 225, 0.04);
}

.admin-sidebar__item.active {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}

.admin-sidebar__foot {
  border-top: 1px solid var(--color-hairline);
  padding-top: var(--space-md);
}

.admin-main {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3xl);
}

@media (max-width: 767px) {
  .admin-sidebar {
    width: 64px;
    padding: var(--space-md);
  }
  .admin-sidebar__brand,
  .admin-sidebar__item span,
  .admin-sidebar__brand h2,
  .admin-sidebar__brand .eyebrow {
    display: none;
  }
  .admin-sidebar__item {
    justify-content: center;
    padding: var(--space-md);
  }
}
</style>
