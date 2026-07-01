<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useMapStore } from '@/stores/map'
import { getToken, getUsername, logout, setAuthChangeListener } from '@/api/auth'
import MessageBubble from './MessageBubble.vue'
import AuthDialog from './AuthDialog.vue'

// ── Store ────────────────────────────────────────────────────────────────────
const chatStore = useChatStore()
const mapStore = useMapStore()

// ── Progress bar ─────────────────────────────────────────────────────────────
const progressPercent = computed(() => {
  const p = chatStore.progress
  if (!p || p.total === 0) return 0
  return Math.round((p.step / p.total) * 100)
})

// ── Reactive State ───────────────────────────────────────────────────────────
const inputText = ref('')
const messageListRef = ref<HTMLElement | null>(null)
const historyOpen = ref(false)
const authOpen = ref(false)

const username = ref<string | null>(getUsername())
const isLoggedIn = ref(!!getToken())

function refreshAuthState(): void {
  username.value = getUsername()
  isLoggedIn.value = !!getToken()
}

const unsubscribeAuth = setAuthChangeListener(refreshAuthState)

function onStorage(event: StorageEvent): void {
  if (event.key === 'token' || event.key === 'username') {
    refreshAuthState()
  }
}
window.addEventListener('storage', onStorage)

onBeforeUnmount(() => {
  unsubscribeAuth()
  window.removeEventListener('storage', onStorage)
})

function openAuth(): void {
  authOpen.value = true
}

async function handleLogout(): Promise<void> {
  try {
    await logout()
  } catch { /* ignore */ }
  refreshAuthState()
  historyOpen.value = false
  chatStore.historySessions = []
  ElMessage.info('已退出登录')
}

function onAuthSuccess(): void {
  refreshAuthState()
  historyOpen.value = true
  chatStore.fetchHistory()
}

onMounted(() => {
  if (isLoggedIn.value) {
    chatStore.fetchHistory()
  }
})

// ── Computed ─────────────────────────────────────────────────────────────────
const messages = computed(() => chatStore.messages)
const isLoading = computed(() => chatStore.loading)
const errorMsg = computed(() => chatStore.error)
const isEmpty = computed(() => messages.value.length === 0)

// ── Suggestions (cover page) ─────────────────────────────────────────────────
const suggestions: string[] = [
  '杭州三日游，慢节奏',
  '成都两日，美食主题',
  '北京五日，深度文化',
]

function handleSuggestion(text: string): void {
  inputText.value = text
  handleSend()
}

watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    scrollToBottom()
  },
)

watch(isLoading, async () => {
  await nextTick()
  scrollToBottom()
})

function scrollToBottom(): void {
  const el = messageListRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

function handleSend(): void {
  const text = inputText.value.trim()
  if (!text || isLoading.value) return

  chatStore.sendMessage(text)
  inputText.value = ''
}

function handleKeydown(event: Event | KeyboardEvent): void {
  const e = event as KeyboardEvent
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function dismissError(): void {
  chatStore.clearError()
}

async function handleRetry(): Promise<void> {
  await chatStore.retryLastMessage()
}

// ── Chat history drawer ──────────────────────────────────────────────────────
async function toggleHistoryDrawer(): Promise<void> {
  historyOpen.value = !historyOpen.value
  if (historyOpen.value && isLoggedIn.value) {
    await chatStore.fetchHistory()
  }
}

async function openHistorySession(threadId: string): Promise<void> {
  historyOpen.value = false
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
  historyOpen.value = false
  chatStore.startNewSession()
}
</script>

<template>
  <div class="chat-panel">
    <!-- ── Editorial Header ──────────────────────────────────────────── -->
    <header class="chat-panel__header">
      <div class="chat-panel__brand">
        <div class="chat-panel__brand-mark">
          <span class="chat-panel__brand-rule"></span>
          <span class="chat-panel__brand-eyebrow">ATELIER · 2026</span>
        </div>
        <h1 class="chat-panel__brand-title">
          Travel <em>Atlas</em>
        </h1>
        <p class="chat-panel__brand-tagline">
          <span class="serif italic">A concierge for the curious traveler</span>
        </p>
      </div>

      <div class="chat-panel__actions">
        <button
          class="chat-panel__icon-btn"
          :class="{ 'is-active': historyOpen }"
          title="对话历史"
          @click="toggleHistoryDrawer"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.4">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" stroke-linecap="round" />
          </svg>
          <span v-if="chatStore.historySessions.length > 0" class="chat-panel__badge numeric">
            {{ chatStore.historySessions.length }}
          </span>
        </button>
        <button
          v-if="isLoggedIn"
          class="chat-panel__avatar"
          :title="`已登录：${username || '用户'}（点击退出）`"
          @click="handleLogout"
        >
          <span>{{ (username || 'U').charAt(0).toUpperCase() }}</span>
        </button>
        <button
          v-else
          class="chat-panel__signin"
          title="登录 / 注册"
          @click="openAuth"
        >
          <span class="chat-panel__signin-label">登录</span>
        </button>
      </div>
    </header>

    <!-- ── Chat History Drawer ──────────────────────────────────────────── -->
    <transition name="drawer">
      <div v-if="historyOpen" class="chat-panel__drawer">
        <div class="drawer-head">
          <div class="drawer-head__title">
            <span class="eyebrow">Archive</span>
            <h2 class="serif">Chat History</h2>
          </div>
          <button class="drawer-close" @click="historyOpen = false">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M6 6l12 12M18 6L6 18" stroke-linecap="round" />
            </svg>
          </button>
        </div>
        <div class="drawer-body">
          <div v-if="!isLoggedIn" class="drawer-empty drawer-empty--login">
            <div class="drawer-empty__icon">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1">
                <rect x="3" y="11" width="18" height="11" rx="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <h3 class="serif drawer-empty__title">Sign in to save chats</h3>
            <p class="drawer-empty__desc">Your conversations are saved so you can pick up where you left off.</p>
            <button class="drawer-cta" @click="openAuth">
              <span>Enter</span>
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M5 12h14M13 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
          </div>
          <div v-else-if="chatStore.historyLoading" class="drawer-empty">
            <p>Loading…</p>
          </div>
          <div v-else-if="chatStore.historySessions.length === 0" class="drawer-empty">
            <p class="serif">No conversations yet.</p>
            <p class="drawer-hint">Send a message and it will be saved here.</p>
          </div>
          <div v-else>
            <ul class="drawer-list">
              <li
                v-for="session in chatStore.historySessions"
                :key="session.thread_id"
                class="drawer-item"
                @click="openHistorySession(session.thread_id)"
              >
                <div class="drawer-item-main">
                  <div class="drawer-item-meta">
                    <span class="numeric">{{ session.message_count }} 消息</span>
                  </div>
                  <div class="drawer-item-title serif">{{ session.title || '未命名对话' }}</div>
                  <div class="drawer-item-sub">
                    {{ new Date(session.updated_at).toLocaleDateString() }}
                  </div>
                </div>
                <button
                  class="drawer-item-del"
                  title="删除对话"
                  @click="removeHistorySession(session.thread_id, $event)"
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  </svg>
                </button>
              </li>
            </ul>
            <button class="new-session-btn" @click="handleNewSession">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 5v14M5 12h14" stroke-linecap="round" />
              </svg>
              <span>新对话</span>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- ── Message List ────────────────────────────────────────────────── -->
    <div ref="messageListRef" class="chat-panel__messages">
      <!-- Empty state — editorial cover -->
      <div v-if="isEmpty && !isLoading" class="chat-panel__cover">
        <div class="cover-eyebrow">
          <span class="cover-rule"></span>
          <span>Chapter 01</span>
        </div>
        <h2 class="cover-title serif">
          Where shall <em>we</em> wander?
        </h2>
        <p class="cover-subtitle serif italic">
          Tell me a city, a number of days, and a dream — I will plot the route.
        </p>
        <div class="cover-suggestions">
          <button
            v-for="(s, i) in suggestions"
            :key="i"
            class="cover-suggestion"
            @click="handleSuggestion(s)"
          >
            <span class="cover-suggestion__index numeric">{{ (i + 1).toString().padStart(2, '0') }}</span>
            <span class="cover-suggestion__text">{{ s }}</span>
          </button>
        </div>
      </div>

      <MessageBubble
        v-for="(msg, index) in messages"
        :key="index"
        :message="msg"
      />

      <MessageBubble
        v-if="isLoading"
        :message="{ role: 'assistant', content: '', timestamp: new Date().toISOString() }"
        :is-thinking="true"
      />

      <div v-if="errorMsg" class="chat-panel__error">
        <span class="chat-panel__error-icon">⚠</span>
        <span class="chat-panel__error-text">{{ errorMsg }}</span>
        <div class="chat-panel__error-actions">
          <button
            v-if="chatStore.lastUserMessage"
            class="chat-panel__retry-btn"
            @click="handleRetry"
          >
            重试
          </button>
          <button class="chat-panel__dismiss-btn" @click="dismissError">关闭</button>
        </div>
      </div>
    </div>

    <!-- ── Tool Status Bar ─────────────────────────────────────────────── -->
    <div v-if="chatStore.toolStatus" class="chat-panel__status">
      <span class="status-indicator" />
      <span>{{ chatStore.toolStatus }}</span>
    </div>

    <!-- ── Progress Bar ─────────────────────────────────────────────────── -->
    <div v-if="chatStore.progress" class="chat-panel__progress">
      <div
        class="chat-panel__progress-fill"
        :style="{ width: progressPercent + '%' }"
      />
    </div>

    <!-- ── Input Area ─────────────────────────────────────────────────── -->
    <div class="chat-panel__input">
      <div class="chat-panel__input-field">
        <textarea
          v-model="inputText"
          placeholder="Begin a new journey…"
          :disabled="isLoading"
          rows="1"
          @keydown="handleKeydown"
        />
        <button
          class="chat-panel__send-btn"
          :disabled="!inputText.trim() || isLoading"
          :class="{ 'is-ready': inputText.trim() && !isLoading }"
          title="发送"
          @click="handleSend"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6">
            <path d="M5 12h14M13 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </div>
      <div class="chat-panel__input-meta">
        <span class="eyebrow">Press Enter to send · Shift+Enter for newline</span>
      </div>
    </div>

    <AuthDialog
      v-model:visible="authOpen"
      @success="onAuthSuccess"
    />
  </div>
</template>

<style scoped>
/* ── New session button ────────────────────────────────────────────────── */
.new-session-btn {
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

.new-session-btn:hover {
  background: var(--color-accent-soft);
}

/* ── Keep all existing styles below ───────────────────────────────────── */
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-base);
  overflow: hidden;
  color: var(--color-text-regular);
  font-family: var(--font-sans);
}

/* ── Header ──────────────────────────────────────────────────────────────── */
.chat-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--space-xl) var(--space-2xl) var(--space-lg);
  border-bottom: 1px solid var(--color-hairline);
  background: var(--color-bg-base);
  gap: var(--space-lg);
}

.chat-panel__brand {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  min-width: 0;
}

.chat-panel__brand-mark {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-text-secondary);
}

.chat-panel__brand-rule {
  width: 18px;
  height: 1px;
  background: currentColor;
}

.chat-panel__brand-eyebrow {
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  font-weight: 500;
  letter-spacing: var(--letter-spacing-eyebrow);
  text-transform: uppercase;
}

.chat-panel__brand-title {
  font-family: var(--font-serif);
  font-size: var(--text-headline);
  font-weight: 500;
  line-height: 1;
  color: var(--color-text-primary);
  letter-spacing: var(--letter-spacing-tight);
  margin: var(--space-2xs) 0 0;
}

.chat-panel__brand-title em {
  font-style: italic;
  color: var(--color-accent);
  font-weight: 400;
}

.chat-panel__brand-tagline {
  font-family: var(--font-serif);
  font-size: var(--text-meta);
  color: var(--color-text-secondary);
  font-style: italic;
  margin: var(--space-2xs) 0 0;
  letter-spacing: 0.01em;
}

.chat-panel__actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
}

.chat-panel__icon-btn {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-circle);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.chat-panel__icon-btn:hover {
  color: var(--color-text-primary);
  border-color: var(--color-text-primary);
}

.chat-panel__icon-btn.is-active {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.chat-panel__badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: var(--color-accent);
  color: var(--color-bg-deep);
  font-family: var(--font-sans);
  font-size: var(--text-micro);
  font-weight: 600;
  border-radius: var(--radius-pill);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1.5px solid var(--color-bg-base);
}

.chat-panel__avatar {
  width: 36px;
  height: 36px;
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
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.chat-panel__avatar:hover {
  background: var(--color-accent);
  color: var(--color-bg-deep);
}

.chat-panel__signin {
  padding: var(--space-sm) var(--space-md);
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  font-weight: 500;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.chat-panel__signin:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

/* ── Chat History Drawer ─────────────────────────────────────────────────── */
.drawer-enter-active, .drawer-leave-active {
  transition: max-height var(--duration-slow) var(--ease-out-expo), opacity var(--duration-normal);
}
.drawer-enter-from, .drawer-leave-to {
  max-height: 0;
  opacity: 0;
}
.drawer-enter-to, .drawer-leave-from {
  max-height: 50vh;
  opacity: 1;
}

.chat-panel__drawer {
  border-bottom: 1px solid var(--color-hairline);
  background: var(--color-bg-elevated);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.drawer-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: var(--space-lg) var(--space-2xl);
  border-bottom: 1px solid var(--color-hairline);
}

.drawer-head__title {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.drawer-head h2 {
  font-family: var(--font-serif);
  font-size: var(--text-title);
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--letter-spacing-tight);
}

.drawer-close {
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

.drawer-close:hover {
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
}

.drawer-body {
  overflow-y: auto;
  padding: var(--space-md) var(--space-2xl) var(--space-xl);
}

.drawer-empty {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-secondary);
  font-family: var(--font-serif);
  font-size: var(--text-body);
  font-style: italic;
}

.drawer-empty--login {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}

.drawer-empty__icon {
  color: var(--color-text-muted);
  margin-bottom: var(--space-sm);
}

.drawer-empty__title {
  font-family: var(--font-serif);
  font-size: var(--text-subtitle);
  font-weight: 500;
  font-style: normal;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: var(--letter-spacing-tight);
}

.drawer-empty__desc {
  font-family: var(--font-serif);
  font-size: var(--text-meta);
  font-style: italic;
  color: var(--color-text-secondary);
  max-width: 240px;
  line-height: var(--line-height-relaxed);
  margin: 0;
}

.drawer-cta {
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

.drawer-cta:hover {
  background: var(--color-accent-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent);
}

.drawer-hint {
  font-size: var(--text-meta);
  color: var(--color-text-muted);
  margin-top: var(--space-xs);
  font-style: normal;
  font-family: var(--font-sans);
}

.drawer-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.drawer-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-base);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  position: relative;
}

.drawer-item:hover {
  border-color: var(--color-accent);
  background: var(--color-bg-overlay);
  transform: translateX(2px);
}

.drawer-item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.drawer-item-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  color: var(--color-text-secondary);
}

.drawer-item-meta .numeric {
  font-weight: 600;
  color: var(--color-accent);
  letter-spacing: 0.05em;
}

.drawer-item-status {
  padding: 1px var(--space-sm);
  border-radius: var(--radius-pill);
  background: var(--color-bg-muted);
  font-size: var(--text-micro);
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  color: var(--color-text-secondary);
}

.drawer-item-status.is-planned {
  color: var(--color-sage);
  background: var(--color-sage-soft);
}

.drawer-item-status.is-draft {
  color: var(--color-amber);
  background: var(--color-amber-soft);
}

.drawer-item-title {
  font-family: var(--font-serif);
  font-size: var(--text-subtitle);
  font-weight: 500;
  color: var(--color-text-primary);
  letter-spacing: var(--letter-spacing-tight);
  line-height: 1.2;
}

.drawer-item-sub {
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  letter-spacing: var(--letter-spacing-wide);
}

.drawer-item-del {
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

.drawer-item:hover .drawer-item-del {
  opacity: 1;
}

.drawer-item-del:hover {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}

/* ── Message List ─────────────────────────────────────────────────────── */
.chat-panel__messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2xl);
  scroll-behavior: smooth;
}

/* ── Cover (empty state) ──────────────────────────────────────────────── */
.chat-panel__cover {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-lg);
  padding: var(--space-3xl) 0;
  animation: cover-fade-in var(--duration-slower) var(--ease-out-expo);
}

@keyframes cover-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.cover-eyebrow {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-text-secondary);
}

.cover-rule {
  width: 32px;
  height: 1px;
  background: var(--color-accent);
}

.cover-eyebrow span:last-child {
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  font-weight: 500;
  letter-spacing: var(--letter-spacing-eyebrow);
  text-transform: uppercase;
}

.cover-title {
  font-family: var(--font-serif);
  font-size: var(--text-display);
  font-weight: 500;
  line-height: 0.95;
  color: var(--color-text-primary);
  letter-spacing: -0.04em;
  margin: 0;
}

.cover-title em {
  font-style: italic;
  color: var(--color-accent);
  font-weight: 400;
}

.cover-subtitle {
  font-family: var(--font-serif);
  font-size: var(--text-body);
  font-style: italic;
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  max-width: 320px;
  margin: 0;
}

.cover-suggestions {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  width: 100%;
  margin-top: var(--space-md);
}

.cover-suggestion {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-md);
  text-align: left;
  font-family: var(--font-sans);
  font-size: var(--text-meta);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.cover-suggestion:hover {
  border-color: var(--color-accent);
  background: var(--color-accent-soft);
  transform: translateX(4px);
}

.cover-suggestion__index {
  font-family: var(--font-serif);
  font-size: var(--text-meta);
  font-style: italic;
  font-weight: 500;
  color: var(--color-accent);
  opacity: 0.7;
  width: 22px;
  text-align: right;
}

.cover-suggestion__text {
  font-family: var(--font-serif);
  font-size: var(--text-body);
  color: var(--color-text-primary);
  letter-spacing: 0.01em;
}

/* ── Error ────────────────────────────────────────────────────────────── */
.chat-panel__error {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md);
  margin-top: var(--space-md);
  background: var(--color-accent-soft);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  color: var(--color-accent);
  font-size: var(--text-meta);
  animation: error-shake var(--duration-slow) var(--ease-spring);
}

@keyframes error-shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-3px); }
  40% { transform: translateX(3px); }
  60% { transform: translateX(-2px); }
  80% { transform: translateX(2px); }
}

.chat-panel__error-icon {
  font-size: var(--text-body);
  flex-shrink: 0;
}

.chat-panel__error-text {
  flex: 1;
  line-height: var(--line-height-normal);
  color: var(--color-text-primary);
}

.chat-panel__error-actions {
  display: flex;
  gap: var(--space-xs);
  flex-shrink: 0;
}

.chat-panel__retry-btn,
.chat-panel__dismiss-btn {
  padding: var(--space-xs) var(--space-md);
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--text-caption);
  font-weight: 500;
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.chat-panel__retry-btn {
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.chat-panel__retry-btn:hover {
  background: var(--color-accent);
  color: var(--color-bg-deep);
}

.chat-panel__dismiss-btn:hover {
  border-color: var(--color-text-primary);
}

/* ── Input Area ───────────────────────────────────────────────────────── */
.chat-panel__input {
  padding: var(--space-lg) var(--space-2xl) var(--space-xl);
  border-top: 1px solid var(--color-hairline);
  background: var(--color-bg-base);
}

/* ── Tool Status Bar ────────────────────────────────────────────────── */
.chat-panel__status {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-2xl);
  border-top: 1px solid var(--color-hairline);
  background: var(--color-bg-subtle);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-circle);
  background: var(--color-accent);
  animation: pulse-status 1.2s ease-in-out infinite;
}
@keyframes pulse-status {
  0%, 100% { opacity: 0.35; }
  50% { opacity: 1; }
}

/* ── Progress bar ─────────────────────────────────────────────────────── */
.chat-panel__progress {
  height: 3px;
  background: var(--color-hairline);
}
.chat-panel__progress-fill {
  height: 100%;
  background: var(--color-accent);
  transition: width 0.3s ease;
}

.chat-panel__input-field {
  display: flex;
  align-items: flex-end;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-md) var(--space-md) var(--space-lg);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-lg);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.chat-panel__input-field:focus-within {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-soft);
}

.chat-panel__input-field textarea {
  flex: 1;
  background: transparent;
  color: var(--color-text-primary);
  border: none;
  outline: none;
  resize: none;
  font-family: var(--font-sans);
  font-size: var(--text-body);
  line-height: var(--line-height-normal);
  padding: var(--space-sm) 0;
  min-height: 24px;
  max-height: 120px;
}

.chat-panel__input-field textarea::placeholder {
  color: var(--color-text-placeholder);
  font-family: var(--font-serif);
  font-style: italic;
}

.chat-panel__send-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-muted);
  color: var(--color-text-muted);
  border-radius: var(--radius-circle);
  flex-shrink: 0;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.chat-panel__send-btn.is-ready {
  background: var(--color-accent);
  color: var(--color-bg-deep);
}

.chat-panel__send-btn.is-ready:hover {
  background: var(--color-accent-hover);
  transform: rotate(-12deg) scale(1.08);
}

.chat-panel__send-btn:disabled {
  cursor: not-allowed;
}

.chat-panel__input-meta {
  margin-top: var(--space-sm);
  text-align: center;
}

.chat-panel__input-meta .eyebrow {
  font-size: var(--text-micro);
  color: var(--color-text-muted);
}

/* ── Responsive ──────────────────────────────────────────────────────── */
@media (max-width: 767px) {
  .chat-panel__header {
    padding: var(--space-md) var(--space-lg) var(--space-md);
  }
  .chat-panel__brand-title {
    font-size: var(--text-title);
  }
  .chat-panel__messages {
    padding: var(--space-lg);
  }
  .chat-panel__input {
    padding: var(--space-md) var(--space-lg) var(--space-lg);
  }
  .cover-title {
    font-size: 2.4rem;
  }
}
</style>
