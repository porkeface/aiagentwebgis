<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()

const amapApiKey = ref('')
const viteAmapKey = ref('')

async function load(): Promise<void> {
  await store.fetchConfig()
  if (store.config) {
    amapApiKey.value = store.config.AMAP_API_KEY?.value || ''
    viteAmapKey.value = store.config.VITE_AMAP_KEY?.value || ''
  }
}

async function save(): Promise<void> {
  const updates: Record<string, string> = {}
  if (amapApiKey.value && !amapApiKey.value.startsWith('****')) {
    updates.AMAP_API_KEY = amapApiKey.value
  }
  if (viteAmapKey.value && !viteAmapKey.value.startsWith('****')) {
    updates.VITE_AMAP_KEY = viteAmapKey.value
  }
  if (Object.keys(updates).length === 0) {
    ElMessage.info('未修改任何值')
    return
  }
  try {
    const result = await store.saveConfig(updates)
    if (result.requires_restart.length > 0) {
      ElMessage.warning(`配置已保存。以下需要重启: ${result.requires_restart.join(', ')}`)
    } else {
      ElMessage.success('高德地图配置已保存并生效')
    }
  } catch {
    ElMessage.error('保存失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <h1 class="admin-page__title">高德地图</h1>

    <div class="admin-form" v-if="store.config">
      <label class="admin-form__field">
        <span class="admin-form__label">后端 API Key（服务端调用）</span>
        <input v-model="amapApiKey" class="admin-form__input" type="password" placeholder="AMAP_API_KEY" />
        <span class="admin-form__hint">用于后端 POI搜索、路径规划等服务调用</span>
      </label>
      <label class="admin-form__field">
        <span class="admin-form__label">前端 API Key（浏览器加载地图）</span>
        <input v-model="viteAmapKey" class="admin-form__input" type="password" placeholder="VITE_AMAP_KEY" />
        <span class="admin-form__hint">用于前端加载高德地图 JS SDK。修改后需重启前端服务（Vite）</span>
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
