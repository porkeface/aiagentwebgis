<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()

const model = ref('')
const baseUrl = ref('')
const apiKey = ref('')

async function load(): Promise<void> {
  await store.fetchConfig()
  if (store.config) {
    model.value = store.config.LLM_MODEL?.value || 'qwen-plus'
    baseUrl.value = store.config.LLM_BASE_URL?.value || ''
    apiKey.value = store.config.DASHSCOPE_API_KEY?.value || ''
  }
}

async function save(): Promise<void> {
  const updates: Record<string, string> = {
    LLM_MODEL: model.value,
    LLM_BASE_URL: baseUrl.value,
  }
  // Only update API key if the user changed it (not masked)
  if (apiKey.value && !apiKey.value.startsWith('****')) {
    updates.DASHSCOPE_API_KEY = apiKey.value
  }
  try {
    const result = await store.saveConfig(updates)
    if (result.requires_restart.length > 0) {
      ElMessage.warning(`配置已保存。以下需要重启: ${result.requires_restart.join(', ')}`)
    } else {
      ElMessage.success('模型配置已保存并生效')
    }
  } catch {
    ElMessage.error('保存失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <h1 class="admin-page__title">模型配置</h1>

    <div class="admin-form" v-if="store.config">
      <label class="admin-form__field">
        <span class="admin-form__label">模型名称</span>
        <input v-model="model" class="admin-form__input" placeholder="qwen-plus" />
      </label>
      <label class="admin-form__field">
        <span class="admin-form__label">API Base URL</span>
        <input v-model="baseUrl" class="admin-form__input" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
      </label>
      <label class="admin-form__field">
        <span class="admin-form__label">DashScope API Key</span>
        <input v-model="apiKey" class="admin-form__input" placeholder="sk-xxxx" />
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
.admin-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-md) var(--space-2xl);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  font-weight: 600;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  transition: all var(--duration-fast) var(--ease-out-expo);
  border: none;
  cursor: pointer;
}
.admin-btn--primary { background: var(--color-accent); color: var(--color-bg-deep); }
.admin-btn--primary:hover { background: var(--color-accent-hover); }
</style>
