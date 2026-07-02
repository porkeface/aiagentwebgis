<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()

const dbUrl = ref('')

async function load(): Promise<void> {
  await store.fetchConfig()
  if (store.config) {
    dbUrl.value = store.config.DATABASE_URL?.value || ''
  }
}

async function save(): Promise<void> {
  const result = await store.saveConfig({ DATABASE_URL: dbUrl.value })
  if (result.requires_restart.length > 0) {
    ElMessage.warning('数据库配置已保存。需要重启后端才能生效。')
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <h1 class="admin-page__title">数据库配置</h1>

    <div class="admin-form" v-if="store.config">
      <label class="admin-form__field">
        <span class="admin-form__label">PostgreSQL 连接串</span>
        <input v-model="dbUrl" class="admin-form__input" placeholder="postgresql+asyncpg://user:pass@host:5432/db" />
        <span class="admin-form__hint">修改后需重启后端服务</span>
      </label>

      <button class="admin-btn admin-btn--primary" @click="save">保存配置</button>
    </div>
  </div>
</template>

<style scoped>
.admin-page { max-width: 640px; }
.admin-page__title {
  font-family: var(--font-serif);
  font-size: var(--text-headline);
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2xl);
}
.admin-form { display: flex; flex-direction: column; gap: var(--space-xl); }
.admin-form__field { display: flex; flex-direction: column; gap: var(--space-sm); }
.admin-form__label {
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  font-weight: 500;
  color: var(--color-text-secondary);
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
}
.admin-form__input {
  padding: var(--space-md) var(--space-lg);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-body);
  color: var(--color-text-primary);
  transition: border-color var(--duration-fast);
}
.admin-form__input:focus { outline: none; border-color: var(--color-accent); }
.admin-form__hint {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  margin-top: var(--space-xs);
}
.admin-btn {
  display: inline-flex; align-items: center; justify-content: center;
  padding: var(--space-md) var(--space-2xl);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans); font-size: var(--text-meta); font-weight: 600;
  letter-spacing: var(--letter-spacing-wide); text-transform: uppercase;
  transition: all var(--duration-fast) var(--ease-out-expo);
  border: none; cursor: pointer;
}
.admin-btn--primary { background: var(--color-accent); color: var(--color-bg-deep); }
.admin-btn--primary:hover { background: var(--color-accent-hover); }
</style>
