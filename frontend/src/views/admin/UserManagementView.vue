<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAdminStore } from '@/stores/admin'

const store = useAdminStore()
const newPassword = ref('')

onMounted(() => store.fetchUsers())

async function toggleAdmin(id: number, current: boolean): Promise<void> {
  await store.updateUser(id, { is_admin: !current })
  ElMessage.success('已更新')
}

async function resetPassword(id: number): Promise<void> {
  if (!newPassword.value || newPassword.value.length < 4) {
    ElMessage.warning('密码至少 4 位')
    return
  }
  await store.updateUser(id, { password: newPassword.value })
  newPassword.value = ''
  ElMessage.success('密码已重置')
}

async function remove(id: number, username: string): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除用户「${username}」及其所有数据？`, '确认删除', {
      type: 'warning',
    })
    await store.removeUser(id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}
</script>

<template>
  <div class="admin-page">
    <h1 class="admin-page__title">用户管理</h1>

    <div class="admin-table">
      <div class="admin-table__row admin-table__row--head">
        <span>ID</span><span>用户名</span><span>Admin</span><span>操作</span>
      </div>
      <div v-for="u in store.users" :key="u.id" class="admin-table__row">
        <span class="numeric">{{ u.id }}</span>
        <span>{{ u.username }}</span>
        <span>{{ u.is_admin ? '是' : '否' }}</span>
        <span class="admin-table__actions">
          <button class="admin-btn admin-btn--small" @click="toggleAdmin(u.id, u.is_admin)">
            {{ u.is_admin ? '降权' : '升权' }}
          </button>
          <input v-model="newPassword" class="admin-table__pw" placeholder="新密码" style="width:80px" />
          <button class="admin-btn admin-btn--small" @click="resetPassword(u.id)">重置</button>
          <button class="admin-btn admin-btn--small admin-btn--danger" @click="remove(u.id, u.username)">删除</button>
        </span>
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
.admin-table { display: flex; flex-direction: column; gap: var(--space-2xs); }
.admin-table__row {
  display: grid;
  grid-template-columns: 60px 1fr 60px 1fr;
  gap: var(--space-lg);
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
.admin-table__actions { display: flex; gap: var(--space-sm); align-items: center; }
.admin-table__pw {
  padding: 4px 8px;
  background: var(--color-bg-base);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  font-size: var(--text-meta);
}
.admin-table__pw:focus { outline: none; border-color: var(--color-accent); }
.admin-btn {
  display: inline-flex; align-items: center; justify-content: center;
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius-pill);
  font-size: var(--text-caption); font-weight: 500;
  letter-spacing: var(--letter-spacing-wide);
  border: 1px solid var(--color-hairline-strong);
  background: var(--color-bg-base); color: var(--color-text-secondary);
  cursor: pointer; transition: all var(--duration-fast);
  white-space: nowrap;
}
.admin-btn--small { padding: var(--space-xs) var(--space-md); font-size: var(--text-micro); }
.admin-btn:hover { background: var(--color-bg-overlay); color: var(--color-text-primary); }
.admin-btn--danger:hover { background: var(--color-accent-soft); color: var(--color-accent); border-color: var(--color-accent); }
</style>
