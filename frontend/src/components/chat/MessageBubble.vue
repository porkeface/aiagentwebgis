<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/types'

// ── Props ───────────────────────────────────────────────────────────────────
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
  const ts = props.message.timestamp
  if (!ts) return ''
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ''
  try {
    return date.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
})
</script>

<template>
  <article class="message" :class="{ 'message--user': isUser, 'message--assistant': !isUser }">
    <div v-if="!isUser" class="message__index eyebrow">
      <span class="message__rule"></span>
      <span>CONCIERGE</span>
    </div>
    <div v-else class="message__index eyebrow message__index--user">
      <span>YOU</span>
      <span class="message__rule message__rule--user"></span>
    </div>

    <div class="message__body">
      <div v-if="isThinking && !isUser" class="message__thinking">
        <span class="thinking-dot"></span>
        <span class="thinking-dot"></span>
        <span class="thinking-dot"></span>
        <span class="message__thinking-text serif italic">Composing your itinerary…</span>
      </div>
      <p v-else class="message__content">{{ message.content }}</p>

      <div class="message__meta">
        <span class="message__time numeric">{{ formattedTime }}</span>
      </div>
    </div>
  </article>
</template>

<style scoped>
.message {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-lg) 0;
  animation: msg-fade-in var(--duration-slow) var(--ease-out-expo);
}

@keyframes msg-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.message--user {
  align-items: flex-end;
  text-align: right;
}

.message__index {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-text-muted);
}

.message__index--user {
  color: var(--color-text-secondary);
}

.message__rule {
  width: 18px;
  height: 1px;
  background: currentColor;
  opacity: 0.5;
}

.message__rule--user {
  opacity: 0.5;
}

.message__body {
  max-width: 92%;
}

.message--user .message__body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-xs);
}

.message__content {
  font-family: var(--font-serif);
  font-size: var(--text-subtitle);
  font-weight: 400;
  line-height: var(--line-height-relaxed);
  color: var(--color-text-primary);
  letter-spacing: -0.005em;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.message--user .message__content {
  font-family: var(--font-sans);
  font-size: var(--text-body);
  font-weight: 400;
  line-height: var(--line-height-normal);
  color: var(--color-text-primary);
  background: var(--color-bg-elevated);
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-hairline);
  letter-spacing: 0;
}

.message__meta {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
}

.message--user .message__meta {
  justify-content: flex-end;
}

.message__time {
  font-family: var(--font-sans);
  font-size: var(--text-micro);
  color: var(--color-text-muted);
  letter-spacing: var(--letter-spacing-wide);
  text-transform: uppercase;
}

.message__thinking {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) 0;
}

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-circle);
  background: var(--color-accent);
  animation: thinking-pulse 1.4s ease-in-out infinite both;
}

.thinking-dot:nth-child(1) { animation-delay: 0s; }
.thinking-dot:nth-child(2) { animation-delay: 0.18s; }
.thinking-dot:nth-child(3) { animation-delay: 0.36s; }

@keyframes thinking-pulse {
  0%, 80%, 100% { transform: scale(0.4); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

.message__thinking-text {
  font-family: var(--font-serif);
  font-size: var(--text-body);
  font-style: italic;
  color: var(--color-text-secondary);
  margin-left: var(--space-sm);
}
</style>