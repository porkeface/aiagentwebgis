<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()

type PanelKey = 'users' | 'trips' | 'pois' | 'sessions'
const active = ref<PanelKey>('users')

function switchPanel(key: PanelKey): void {
  active.value = key
}

onMounted(async () => {
  await Promise.all([store.fetchStats(), store.fetchTrips(), store.fetchSessions(), store.fetchUsers(), store.fetchPois()])
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

async function removeUser(id: number, username: string): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除用户「${username}」？`, '确认删除', { type: 'warning' })
    await store.removeUser(id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}
</script>

<template>
  <div class="admin-page">
    <h1 class="admin-page__title">数据管理</h1>

    <!-- Stat cards row -->
    <div v-if="store.stats" class="stat-cards">
      <button class="stat-card" :class="{ 'is-active': active === 'users' }" @click="switchPanel('users')">
        <strong>{{ store.stats.users }}</strong>
        <span>用户</span>
      </button>
      <button class="stat-card" :class="{ 'is-active': active === 'trips' }" @click="switchPanel('trips')">
        <strong>{{ store.stats.trips }}</strong>
        <span>行程</span>
      </button>
      <button class="stat-card" :class="{ 'is-active': active === 'pois' }" @click="switchPanel('pois')">
        <strong>{{ store.stats.pois }}</strong>
        <span>POI</span>
      </button>
      <button class="stat-card" :class="{ 'is-active': active === 'sessions' }" @click="switchPanel('sessions')">
        <strong>{{ store.stats.chat_sessions }}</strong>
        <span>对话</span>
      </button>
    </div>

    <!-- Shared data panel -->
    <div class="data-panel">
      <div class="data-panel__scroll">
        <!-- Users -->
        <div v-if="active === 'users'" class="admin-table admin-table--users">
        <div class="admin-table__row admin-table__row--head">
          <span>ID</span><span>用户名</span><span>Admin</span><span>注册时间</span><span>操作</span>
        </div>
        <div v-for="u in store.users" :key="u.id" class="admin-table__row">
          <span class="numeric">{{ u.id }}</span>
          <span>{{ u.username }}</span>
          <span>{{ u.is_admin ? '是' : '否' }}</span>
          <span>{{ new Date(u.created_at).toLocaleDateString() }}</span>
          <button class="admin-btn admin-btn--small admin-btn--danger" @click="removeUser(u.id, u.username)">删除</button>
        </div>
        <p v-if="store.users.length === 0" class="admin-empty">暂无数据</p>
      </div>

      <!-- Trips -->
      <div v-if="active === 'trips'" class="admin-table admin-table--trips">
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

      <!-- POIs -->
      <div v-if="active === 'pois'" class="admin-table admin-table--pois">
        <div class="admin-table__row admin-table__row--head">
          <span>ID</span><span>名称</span><span>类别</span><span>城市</span><span>评分</span><span>时间</span>
        </div>
        <div v-for="p in store.pois" :key="p.id" class="admin-table__row">
          <span class="numeric">{{ p.id }}</span>
          <span>{{ p.name }}</span>
          <span>{{ p.category }}</span>
          <span>{{ p.city }}</span>
          <span>{{ p.rating != null ? p.rating.toFixed(1) : '-' }}</span>
          <span>{{ new Date(p.created_at).toLocaleDateString() }}</span>
        </div>
        <p v-if="store.pois.length === 0" class="admin-empty">暂无数据</p>
      </div>

      <!-- Sessions -->
      <div v-if="active === 'sessions'" class="admin-table admin-table--sessions">
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
      </div>
    </div>
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

/* ── Stat Cards Row ───────────────────────────────────────────────────── */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-2xl);
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding: var(--space-xl);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
  text-align: left;
}
.stat-card:hover {
  background: var(--color-bg-overlay);
  border-color: var(--color-hairline-strong);
}
.stat-card.is-active {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 1px var(--color-accent);
}

.stat-card strong {
  font-family: var(--font-serif);
  font-size: var(--text-display);
  font-weight: 500;
  color: var(--color-accent);
  line-height: 1;
}

.stat-card span {
  font-size: var(--text-meta);
  color: var(--color-text-secondary);
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
}

/* ── Data Panel ───────────────────────────────────────────────────────── */
.data-panel {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.data-panel__scroll {
  max-height: 420px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-hairline-strong) transparent;
}

/* ── Table ────────────────────────────────────────────────────────────── */
.admin-table { display: flex; flex-direction: column; }
.admin-table__row {
  display: grid;
  gap: var(--space-md);
  align-items: center;
  padding: var(--space-sm) var(--space-xl);
  font-size: var(--text-meta);
  border-bottom: 1px solid var(--color-hairline);
}
.admin-table--users .admin-table__row { grid-template-columns: 50px 1fr 50px 100px 60px; }
.admin-table--trips .admin-table__row { grid-template-columns: 50px 1fr 60px 60px 100px 60px; }
.admin-table--sessions .admin-table__row { grid-template-columns: 50px 1fr 60px 100px 60px; }
.admin-table--pois .admin-table__row { grid-template-columns: 50px 1fr 80px 80px 60px 100px; }
.admin-table__row:last-child { border-bottom: none; }
.admin-table__row--head {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--color-bg-elevated);
  color: var(--color-text-secondary);
  font-weight: 600;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  padding-top: var(--space-lg);
  padding-bottom: var(--space-md);
}
.admin-table__row--head::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: var(--space-xl);
  right: var(--space-xl);
  height: 1px;
  background: var(--color-hairline-strong);
}
.admin-empty { text-align: center; color: var(--color-text-muted); font-style: italic; padding: var(--space-2xl); }
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
