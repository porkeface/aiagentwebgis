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

      <!-- Error display -->
      <div v-if="errorMsg" class="chat-panel__error">
        <span class="error-text">{{ errorMsg }}</span>
        <button class="error-dismiss" @click="dismissError">✕</button>
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
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

/* ── Header ───────────────────────────────────────────────────────────────── */
.chat-panel__header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 14px 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.chat-panel__title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.chat-panel__subtitle {
  font-size: 12px;
  color: #909399;
}

/* ── Message List ─────────────────────────────────────────────────────────── */
.chat-panel__messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
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
  color: #909399;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-title {
  font-size: 16px;
  font-weight: 500;
  color: #606266;
  margin: 0 0 8px;
}

.empty-hint {
  font-size: 13px;
  color: #909399;
  margin: 0;
  max-width: 240px;
  line-height: 1.5;
}

/* ── Error ────────────────────────────────────────────────────────────────── */
.chat-panel__error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-top: 8px;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 6px;
  color: #f56c6c;
  font-size: 13px;
}

.error-text {
  flex: 1;
}

.error-dismiss {
  background: none;
  border: none;
  color: #f56c6c;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
  line-height: 1;
}

.error-dismiss:hover {
  color: #e6a23c;
}

/* ── Input Area ───────────────────────────────────────────────────────────── */
.chat-panel__input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  background: #fafafa;
}

.chat-panel__input :deep(.el-textarea__inner) {
  border-radius: 8px;
  box-shadow: none;
  border: 1px solid #dcdfe6;
  font-size: 14px;
  padding: 8px 12px;
}

.chat-panel__input :deep(.el-textarea__inner:focus) {
  border-color: #409eff;
}

.chat-panel__send-btn {
  flex-shrink: 0;
  height: 36px;
  border-radius: 8px;
}
</style>
