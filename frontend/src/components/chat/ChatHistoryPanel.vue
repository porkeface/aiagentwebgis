<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'

// ── Props & Emits ────────────────────────────────────────────────────────────
interface Props {
  visible: boolean
  isLoggedIn: boolean
  username: string | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'openAuth'): void
  (e: 'logout'): void
}>()

// ── Store ─────────────────────────────────────────────────────────────────────
const chatStore = useChatStore()

onMounted(() => {
  if (props.isLoggedIn) {
    chatStore.fetchHistory()
  }
})

// ── Session actions ──────────────────────────────────────────────────────────
async function openHistorySession(threadId: string): Promise<void> {
  emit('close')
  try {
    await chatStore.loadSession(threadId)
    ElMessage.success('已恢复对话')
  } catch {
    ElMessage.error('加载对话失败')
  }
}

async function removeHistorySession(threadId: string, event: Event): Promise<void> {
  event.stopPropagation()
  try {
    await chatStore.removeHistorySession(threadId)
    ElMessage.success('对话已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

function handleNewSession(): void {
  emit('close')
  chatStore.startNewSession()
}

function onBackdropClick(): void {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <transition name="panel-slide">
      <div v-if="visible" class="history-overlay" @click.self="onBackdropClick">
        <div class="history-panel">
          <!-- Head -->
          <div class="history-panel__head">
            <div class="history-panel__title-group">
              <span class="eyebrow">Archive</span>
              <h2 class="serif">Chat History</h2>
            </div>
            <button class="history-panel__close" @click="emit('close')">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M6 6l12 12M18 6L6 18" stroke-linecap="round" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="history-panel__body">
            <!-- Not logged in -->
            <div v-if="!isLoggedIn" class="history-panel__empty history-panel__empty--login">
              <div class="history-panel__empty-icon">
                <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1">
                  <rect x="3" y="11" width="18" height="11" rx="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </div>
              <h3 class="serif history-panel__empty-title">Sign in to save chats</h3>
              <p class="history-panel__empty-desc">Your conversations are saved so you can pick up where you left off.</p>
              <button class="history-panel__cta" @click="emit('openAuth')">
                <span>Enter</span>
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M5 12h14M13 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>
            </div>

            <!-- Loading -->
            <div v-else-if="chatStore.historyLoading" class="history-panel__empty">
              <p>Loading…</p>
            </div>

            <!-- Empty -->
            <div v-else-if="chatStore.historySessions.length === 0" class="history-panel__empty">
              <p class="serif">No conversations yet.</p>
              <p class="history-panel__hint">Send a message and it will be saved here.</p>
            </div>

            <!-- List -->
            <div v-else>
              <ul class="history-panel__list">
                <li
                  v-for="session in chatStore.historySessions"
                  :key="session.thread_id"
                  class="history-panel__item"
                  @click="openHistorySession(session.thread_id)"
                >
                  <div class="history-panel__item-main">
                    <div class="history-panel__item-meta">
                      <span class="numeric">{{ session.message_count }} 消息</span>
                    </div>
                    <div class="history-panel__item-title serif">{{ session.title || '未命名对话' }}</div>
                    <div class="history-panel__item-sub">
                      {{ new Date(session.updated_at).toLocaleDateString() }}
                    </div>
                  </div>
                  <button
                    class="history-panel__item-del"
                    title="删除对话"
                    @click="removeHistorySession(session.thread_id, $event)"
                  >
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
                      <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                    </svg>
                  </button>
                </li>
              </ul>
              <button class="history-panel__new-btn" @click="handleNewSession">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M12 5v14M5 12h14" stroke-linecap="round" />
                </svg>
                <span>新对话</span>
              </button>
            </div>
          </div>

          <!-- User footer -->
          <div v-if="isLoggedIn" class="history-panel__footer">
            <div class="history-panel__user">
              <span class="history-panel__avatar">{{ (username || 'U').charAt(0).toUpperCase() }}</span>
              <span class="history-panel__username">{{ username }}</span>
            </div>
            <button class="history-panel__logout" @click="emit('logout')">退出登录</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
/* ── Overlay ─────────────────────────────────────────────────────────────── */
.history-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: flex-end;
}

/* ── Panel ───────────────────────────────────────────────────────────────── */
.history-panel {
  width: 380px;
  height: 100vh;
  background: var(--color-bg-base);
  border-left: 1px solid var(--color-hairline);
  box-shadow: -32px 0 64px -16px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Slide transition ────────────────────────────────────────────────────── */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all var(--duration-slow) var(--ease-out-expo);
}
.panel-slide-enter-active .history-panel,
.panel-slide-leave-active .history-panel {
  transition: transform var(--duration-slow) var(--ease-out-expo);
}
.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
}
.panel-slide-enter-from .history-panel,
.panel-slide-leave-to .history-panel {
  transform: translateX(100%);
}

/* ── Head ────────────────────────────────────────────────────────────────── */
.history-panel__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: var(--space-lg) var(--space-xl);
  border-bottom: 1px solid var(--color-hairline);
  flex-shrink: 0;
}

.history-panel__title-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.history-panel__title-group h2 {
  font-family: var(--font-serif);
  font-size: var(--text-title);
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--letter-spacing-tight);
}

.history-panel__close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: var(--radius-circle);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.history-panel__close:hover {
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
}

/* ── Body ────────────────────────────────────────────────────────────────── */
.history-panel__body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-md) var(--space-xl) var(--space-xl);
}

.history-panel__empty {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-secondary);
  font-family: var(--font-serif);
  font-size: var(--text-body);
  font-style: italic;
}

.history-panel__empty--login {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}

.history-panel__empty-icon {
  color: var(--color-text-muted);
  margin-bottom: var(--space-sm);
}

.history-panel__empty-title {
  font-family: var(--font-serif);
  font-size: var(--text-subtitle);
  font-weight: 500;
  font-style: normal;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--letter-spacing-tight);
}

.history-panel__empty-desc {
  font-family: var(--font-serif);
  font-size: var(--text-meta);
  font-style: italic;
  color: var(--color-text-secondary);
  max-width: 240px;
  line-height: var(--line-height-relaxed);
  margin: 0;
}

.history-panel__cta {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-xl);
  margin-top: var(--space-sm);
  background: var(--color-accent);
  color: var(--color-bg-deep);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  font-weight: 500;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.history-panel__cta:hover {
  background: var(--color-accent-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent);
}

.history-panel__hint {
  font-size: var(--text-meta);
  color: var(--color-text-muted);
  margin-top: var(--space-xs);
  font-style: normal;
  font-family: var(--font-sans);
}

/* ── List ────────────────────────────────────────────────────────────────── */
.history-panel__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.history-panel__item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  position: relative;
}

.history-panel__item:hover {
  border-color: var(--color-accent);
  background: var(--color-bg-overlay);
  transform: translateX(2px);
}

.history-panel__item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.history-panel__item-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  color: var(--color-text-secondary);
}

.history-panel__item-meta .numeric {
  font-weight: 600;
  color: var(--color-accent);
  letter-spacing: 0.05em;
}

.history-panel__item-title {
  font-family: var(--font-serif);
  font-size: var(--text-subtitle);
  font-weight: 500;
  color: var(--color-text-primary);
  letter-spacing: var(--letter-spacing-tight);
  line-height: 1.2;
}

.history-panel__item-sub {
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  letter-spacing: var(--letter-spacing-wide);
}

.history-panel__item-del {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--color-text-muted);
  border-radius: var(--radius-circle);
  opacity: 0;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.history-panel__item:hover .history-panel__item-del {
  opacity: 1;
}

.history-panel__item-del:hover {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}

/* ── New session button ──────────────────────────────────────────────────── */
.history-panel__new-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  width: 100%;
  margin-top: var(--space-md);
  padding: var(--space-md);
  background: transparent;
  color: var(--color-accent);
  border: 1px dashed var(--color-accent);
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  font-weight: 500;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.history-panel__new-btn:hover {
  background: var(--color-accent-soft);
}

/* ── Footer ──────────────────────────────────────────────────────────────── */
.history-panel__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-xl);
  border-top: 1px solid var(--color-hairline);
  flex-shrink: 0;
}

.history-panel__user {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.history-panel__avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-accent-soft);
  color: var(--color-accent);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-circle);
  font-family: var(--font-serif);
  font-size: var(--text-body);
  font-weight: 500;
}

.history-panel__username {
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  color: var(--color-text-primary);
  font-weight: 500;
}

.history-panel__logout {
  padding: var(--space-xs) var(--space-md);
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.history-panel__logout:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
</style>
