<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/types'

// ── Props ────────────────────────────────────────────────────────────────────
interface Props {
  message: ChatMessage
  isThinking?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isThinking: false,
})

// ── Computed ─────────────────────────────────────────────────────────────────
const isUser = computed(() => props.message.role === 'user')

const formattedTime = computed(() => {
  try {
    const date = new Date(props.message.timestamp)
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
})
</script>

<template>
  <div class="message-bubble" :class="{ 'message-bubble--user': isUser, 'message-bubble--assistant': !isUser }">
    <div class="message-bubble__avatar">
      {{ isUser ? '🧑' : '🤖' }}
    </div>
    <div class="message-bubble__body">
      <div class="message-bubble__content">
        <template v-if="isThinking && !isUser">
          <div class="message-bubble__typing">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </template>
        <template v-else>
          {{ message.content }}
        </template>
      </div>
      <div class="message-bubble__time">
        {{ formattedTime }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-bubble {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  max-width: 85%;
}

.message-bubble--user {
  flex-direction: row-reverse;
  margin-left: auto;
}

.message-bubble--assistant {
  flex-direction: row;
  margin-right: auto;
}

.message-bubble__avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: #f0f2f5;
}

.message-bubble__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-bubble--user .message-bubble__body {
  align-items: flex-end;
}

.message-bubble--assistant .message-bubble__body {
  align-items: flex-start;
}

.message-bubble__content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
}

.message-bubble--user .message-bubble__content {
  background: #409eff;
  color: #fff;
  border-top-right-radius: 4px;
}

.message-bubble--assistant .message-bubble__content {
  background: #f4f4f5;
  color: #303133;
  border-top-left-radius: 4px;
}

.message-bubble__time {
  font-size: 11px;
  color: #909399;
  padding: 0 4px;
}

/* ── Typing Indicator ────────────────────────────────────────────────────── */
.message-bubble__typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #909399;
  animation: typing-bounce 1.4s infinite ease-in-out both;
}

.typing-dot:nth-child(1) {
  animation-delay: 0s;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing-bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
