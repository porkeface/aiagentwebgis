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
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
  max-width: 85%;
  animation: bubble-fade-in 0.3s ease-out;
}

@keyframes bubble-fade-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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
  border-radius: var(--radius-round);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: var(--color-bg-muted);
  box-shadow: var(--shadow-sm);
}

.message-bubble__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.message-bubble--user .message-bubble__body {
  align-items: flex-end;
}

.message-bubble--assistant .message-bubble__body {
  align-items: flex-start;
}

.message-bubble__content {
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
  word-break: break-word;
  white-space: pre-wrap;
}

.message-bubble--user .message-bubble__content {
  background: var(--color-primary);
  color: #fff;
  border-top-right-radius: var(--radius-sm);
}

.message-bubble--assistant .message-bubble__content {
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
  border-top-left-radius: var(--radius-sm);
}

.message-bubble__time {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  padding: 0 var(--space-xs);
}

/* ── Typing Indicator ────────────────────────────────────────────────────── */
.message-bubble__typing {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) 0;
}

.typing-dot {
  width: 7px;
  height: 7px;
  border-radius: var(--radius-round);
  background: var(--color-text-secondary);
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

/* ── Responsive ───────────────────────────────────────────────────────────── */
@media (max-width: 767px) {
  .message-bubble {
    max-width: 92%;
  }

  .message-bubble__avatar {
    width: 30px;
    height: 30px;
    font-size: 15px;
  }
}
</style>
