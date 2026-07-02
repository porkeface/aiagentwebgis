<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()

onMounted(async () => {
  await Promise.all([store.fetchStats(), store.fetchTrips(), store.fetchSessions()])
})

async function removeTrip(id: number, city: string): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除行程「${city}」？`, '确认删除', { type: 'warning' })
    await store.removeTrip(id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}

async function removeSession(id: number, title: string): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除会话「${title}」？`, '确认删除', { type: 'warning' })
    await store.removeSession(id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}
</script>

<template>
  <div class="admin-page">
    <h1 class="admin-page__title">数据管理</h1>

    <!-- Stats -->
    <div v-if="store.stats" class="admin-stats">
      <div class="admin-stats__card"><strong>{{ store.stats.users }}</strong>用户</div>
      <div class="admin-stats__card"><strong>{{ store.stats.trips }}</strong>行程</div>
      <div class="admin-stats__card"><strong>{{ store.stats.pois }}</strong>POI</div>
      <div class="admin-stats__card"><strong>{{ store.stats.chat_sessions }}</strong>对话</div>
    </div>

    <!-- Trips -->
    <section class="admin-section">
      <h2 class="admin-section__title">所有行程</h2>
      <div class="admin-table">
        <div class="admin-table__row admin-table__row--head">
          <span>ID</span><span>城市</span><span>天数</span><span>用户</span><span>时间</span><span>操作</span>
        </div>
        <div v-for="t in store.trips" :key="t.id" class="admin-table__row">
          <span class="numeric">{{ t.id }}</span>
          <span>{{ t.city }}</span>
          <span>{{ t.days }}d</span>
          <span class="numeric">#{{ t.user_id }}</span>
          <span>{{ new Date(t.created_at).toLocaleDateString() }}</span>
          <button class="admin-btn admin-btn--small admin-btn--danger" @click="removeTrip(t.id, t.city)">删除</button>
        </div>
        <p v-if="store.trips.length === 0" class="admin-empty">暂无数据</p>
      </div>
    </section>

    <!-- Chat Sessions -->
    <section class="admin-section">
      <h2 class="admin-section__title">所有对话</h2>
      <div class="admin-table">
        <div class="admin-table__row admin-table__row--head">
          <span>ID</span><span>标题</span><span>用户</span><span>时间</span><span>操作</span>
        </div>
        <div v-for="s in store.sessions" :key="s.id" class="admin-table__row">
          <span class="numeric">{{ s.id }}</span>
          <span>{{ s.title }}</span>
          <span class="numeric">#{{ s.user_id }}</span>
          <span>{{ new Date(s.created_at).toLocaleDateString() }}</span>
          <button class="admin-btn admin-btn--small admin-btn--danger" @click="removeSession(s.id, s.title)">删除</button>
        </div>
        <p v-if="store.sessions.length === 0" class="admin-empty">暂无数据</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.admin-page { max-width: 900px; }
.admin-page__title {
  font-family: var(--font-serif);
  font-size: var(--text-headline);
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2xl);
}
.admin-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-lg);
  margin-bottom: var(--space-3xl);
}
.admin-stats__card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  text-align: center;
  font-size: var(--text-meta);
  color: var(--color-text-secondary);
  letter-spacing: var(--letter-spacing-wide);
}
.admin-stats__card strong {
  display: block;
  font-family: var(--font-serif);
  font-size: var(--text-display);
  font-weight: 500;
  color: var(--color-accent);
  line-height: 1;
  margin-bottom: var(--space-xs);
}
.admin-section { margin-bottom: var(--space-3xl); }
.admin-section__title {
  font-family: var(--font-sans);
  font-size: var(--text-subtitle);
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-lg);
}
.admin-table { display: flex; flex-direction: column; gap: var(--space-2xs); }
.admin-table__row {
  display: grid;
  grid-template-columns: 60px 1fr 60px 60px 100px 60px;
  gap: var(--space-md);
  align-items: center;
  padding: var(--space-md) var(--space-lg);
  background: var(--color-bg-elevated);
  border-radius: var(--radius-md);
  font-size: var(--text-meta);
}
.admin-table__row--head {
  background: transparent;
  color: var(--color-text-secondary);
  font-weight: 600;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
}
.admin-empty { text-align: center; color: var(--color-text-muted); font-style: italic; padding: var(--space-xl); }
.admin-btn {
  display: inline-flex; align-items: center; justify-content: center;
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius-pill);
  font-size: var(--text-caption); font-weight: 500;
  letter-spacing: var(--letter-spacing-wide);
  border: 1px solid var(--color-hairline-strong);
  background: var(--color-bg-base); color: var(--color-text-secondary);
  cursor: pointer; transition: all var(--duration-fast);
}
.admin-btn--small { padding: var(--space-xs) var(--space-md); font-size: var(--text-micro); }
.admin-btn:hover { background: var(--color-bg-overlay); color: var(--color-text-primary); }
.admin-btn--danger:hover { background: var(--color-accent-soft); color: var(--color-accent); border-color: var(--color-accent); }
</style>
