<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { ElInput, ElButton } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import MessageBubble from './MessageBubble.vue'

// ── Store ────────────────────────────────────────────────────────────────────
const chatStore = useChatStore()

// ── Reactive State ───────────────────────────────────────────────────────────
const inputText = ref('')
const messageListRef = ref<HTMLElement | null>(null)

// ── Computed ─────────────────────────────────────────────────────────────────
const messages = computed(() => chatStore.messages)
const isLoading = computed(() => chatStore.loading)
const errorMsg = computed(() => chatStore.error)
const isEmpty = computed(() => messages.value.length === 0)

// ── Auto-scroll to bottom on new messages ────────────────────────────────────
watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

// Also scroll when loading state changes (typing indicator appears/disappears)
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

// ── Send Message ─────────────────────────────────────────────────────────────
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

// ── Clear Error ──────────────────────────────────────────────────────────────
function dismissError(): void {
  chatStore.clearError()
}

// ── Retry Last Message ──────────────────────────────────────────────────────
async function handleRetry(): Promise<void> {
  await chatStore.retryLastMessage()
}
</script>

<template>
  <div class="chat-panel">
    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <div class="chat-panel__header">
      <span class="chat-panel__title">AI 旅行助手</span>
      <span class="chat-panel__subtitle">智能行程规划</span>
    </div>

    <!-- ── Message List ───────────────────────────────────────────────────── -->
    <div ref="messageListRef" class="chat-panel__messages">
      <!-- Empty state -->
      <div v-if="isEmpty && !isLoading" class="chat-panel__empty">
        <div class="empty-icon">💬</div>
        <p class="empty-title">开始对话</p>
        <p class="empty-hint">
          告诉我你想去的城市和天数，我来帮你规划行程！
        </p>
      </div>

      <!-- Messages -->
      <MessageBubble
        v-for="(msg, index) in messages"
        :key="index"
        :message="msg"
      />

      <!-- Thinking indicator while loading -->
      <MessageBubble
        v-if="isLoading"
        :message="{ role: 'assistant', content: '', timestamp: new Date().toISOString() }"
        :is-thinking="true"
      />

      <!-- Error display with retry button -->
      <div v-if="errorMsg" class="chat-panel__error">
        <span class="chat-panel__error-icon">⚠️</span>
        <span class="chat-panel__error-text">{{ errorMsg }}</span>
        <div class="chat-panel__error-actions">
          <button
            v-if="chatStore.lastUserMessage"
            class="chat-panel__retry-btn"
            @click="handleRetry"
          >
            重试
          </button>
          <button class="chat-panel__dismiss-btn" @click="dismissError">
            关闭
          </button>
        </div>
      </div>
    </div>

    <!-- ── Input Area ─────────────────────────────────────────────────────── -->
    <div class="chat-panel__input">
      <ElInput
        v-model="inputText"
        placeholder="输入你的旅行需求..."
        :disabled="isLoading"
        :autosize="{ minRows: 1, maxRows: 4 }"
        type="textarea"
        resize="none"
        @keydown="handleKeydown"
      />
      <ElButton
        type="primary"
        :disabled="!inputText.trim() || isLoading"
        :loading="isLoading"
        class="chat-panel__send-btn"
        @click="handleSend"
      >
        发送
      </ElButton>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-overlay);
  overflow: hidden;
}

/* ── Header ───────────────────────────────────────────────────────────────── */
.chat-panel__header {
  display: flex;
  align-items: baseline;
  gap: var(--space-sm);
  padding: var(--space-lg) var(--space-lg);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-muted);
}

.chat-panel__title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.chat-panel__subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* ── Message List ─────────────────────────────────────────────────────────── */
.chat-panel__messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-lg);
  scroll-behavior: smooth;
}

/* ── Empty State ──────────────────────────────────────────────────────────── */
.chat-panel__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: var(--space-md);
  animation: empty-float 3s ease-in-out infinite;
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: 500;
  color: var(--color-text-regular);
  margin: 0 0 var(--space-sm);
}

.empty-hint {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
  max-width: 240px;
  line-height: var(--line-height-normal);
}

@keyframes empty-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

/* ── Error ────────────────────────────────────────────────────────────────── */
.chat-panel__error {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 10px var(--space-md);
  margin-top: var(--space-sm);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  border-radius: var(--radius-md);
  color: var(--color-error);
  font-size: 13px;
  animation: error-shake 0.4s ease;
}

@keyframes error-shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-4px); }
  40% { transform: translateX(4px); }
  60% { transform: translateX(-2px); }
  80% { transform: translateX(2px); }
}

.chat-panel__error-icon {
  font-size: var(--font-size-lg);
  flex-shrink: 0;
}

.chat-panel__error-text {
  flex: 1;
  line-height: var(--line-height-normal);
}

.chat-panel__error-actions {
  display: flex;
  gap: var(--space-sm);
  flex-shrink: 0;
}

.chat-panel__retry-btn,
.chat-panel__dismiss-btn {
  background: none;
  border: 1px solid currentColor;
  border-radius: var(--radius-sm);
  padding: var(--space-xs) var(--space-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
}

.chat-panel__retry-btn {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.chat-panel__retry-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

.chat-panel__dismiss-btn {
  color: var(--color-text-secondary);
  border-color: var(--color-divider);
}

.chat-panel__dismiss-btn:hover {
  color: var(--color-text-regular);
  border-color: var(--color-border);
}

/* ── Input Area ───────────────────────────────────────────────────────────── */
.chat-panel__input {
  display: flex;
  align-items: flex-end;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-muted);
}

.chat-panel__input :deep(.el-textarea__inner) {
  border-radius: var(--radius-md);
  box-shadow: none;
  border: 1px solid var(--color-divider);
  font-size: var(--font-size-base);
  padding: var(--space-sm) var(--space-md);
  transition: border-color var(--transition-fast);
}

.chat-panel__input :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary);
}

.chat-panel__send-btn {
  flex-shrink: 0;
  height: 36px;
  border-radius: var(--radius-md);
}

/* ── Responsive ───────────────────────────────────────────────────────────── */
@media (max-width: 767px) {
  .chat-panel__header {
    padding: var(--space-md);
  }

  .chat-panel__messages {
    padding: var(--space-md);
  }

  .chat-panel__input {
    padding: var(--space-sm) var(--space-md);
  }
}
</style>
