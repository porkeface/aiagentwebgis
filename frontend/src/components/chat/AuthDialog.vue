<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { login, register } from '@/api/auth'

// ── Props & Emits ────────────────────────────────────────────────────────────
interface Props {
  visible: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'success', username: string): void
}>()

// ── Local state ──────────────────────────────────────────────────────────────
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const email = ref('')
const passwordVisible = ref(false)
const submitting = ref(false)

const title = computed(() => (mode.value === 'login' ? '登录' : '注册'))
const submitLabel = computed(() =>
  mode.value === 'login' ? '登 录' : '注 册',
)
const canSubmit = computed(
  () =>
    !submitting.value &&
    username.value.trim().length >= 2 &&
    password.value.length >= 4,
)

// Reset fields when dialog opens
watch(
  () => props.visible,
  (v) => {
    if (v) {
      username.value = ''
      password.value = ''
      email.value = ''
      passwordVisible.value = false
    }
  },
)

function switchMode(newMode: 'login' | 'register'): void {
  mode.value = newMode
}

function close(): void {
  emit('update:visible', false)
}

async function handleSubmit(): Promise<void> {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    if (mode.value === 'login') {
      await login(username.value.trim(), password.value)
      ElMessage.success(`欢迎回来，${username.value.trim()}`)
    } else {
      await register(
        username.value.trim(),
        password.value,
        email.value.trim() || `${username.value.trim()}@travel.local`,
      )
      ElMessage.success(`注册成功，欢迎 ${username.value.trim()}`)
    }
    emit('success', username.value.trim())
    close()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '认证失败'
    // Translate common backend errors. Use exact phrase matches so we don't
    // accidentally match unrelated messages like "invalid date".
    let friendly = msg
    const lower = msg.toLowerCase()
    if (msg.includes('409') || lower.includes('already registered')) {
      friendly = '该用户名已被注册，换一个试试'
    } else if (
      msg.includes('401') ||
      lower.includes('invalid credentials') ||
      lower.includes('invalid username or password')
    ) {
      friendly = '用户名或密码错误'
    }
    ElMessage.error(friendly)
  } finally {
    submitting.value = false
  }
}

function handleKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter') {
    e.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <Teleport to="body">
    <transition name="auth-fade">
      <div v-if="visible" class="auth-overlay" @click.self="close">
        <div class="auth-dialog">
          <header class="auth-dialog__head">
            <h2 class="auth-dialog__title">{{ title }}</h2>
            <button class="auth-dialog__close" @click="close" title="关闭">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/>
              </svg>
            </button>
          </header>

          <nav class="auth-dialog__tabs">
            <button
              class="auth-dialog__tab"
              :class="{ 'auth-dialog__tab--active': mode === 'login' }"
              @click="switchMode('login')"
            >
              登录
            </button>
            <button
              class="auth-dialog__tab"
              :class="{ 'auth-dialog__tab--active': mode === 'register' }"
              @click="switchMode('register')"
            >
              注册
            </button>
          </nav>

          <form class="auth-dialog__form" @submit.prevent="handleSubmit">
            <label class="auth-dialog__field">
              <span class="auth-dialog__label">用户名</span>
              <input
                v-model="username"
                type="text"
                autocomplete="username"
                placeholder="起个名字吧"
                class="auth-dialog__input"
                @keydown="handleKeydown"
              />
            </label>

            <label class="auth-dialog__field">
              <span class="auth-dialog__label">密码</span>
              <div class="auth-dialog__input-wrap">
                <input
                  v-model="password"
                  :type="passwordVisible ? 'text' : 'password'"
                  autocomplete="current-password"
                  placeholder="至少 4 位"
                  class="auth-dialog__input"
                  @keydown="handleKeydown"
                />
                <button
                  type="button"
                  class="auth-dialog__eye"
                  @click="passwordVisible = !passwordVisible"
                  :title="passwordVisible ? '隐藏密码' : '显示密码'"
                >
                  <svg v-if="passwordVisible" viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style="display: block;">
                    <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.82l2.92 2.92c1.51-1.39 2.7-3.14 3.44-5.12-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 2.2 0 4.27-.61 6.04-1.66l.46.46 2.28 2.28 1.27-1.27L3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.17c0-1.66-1.34-3-3-3l-.17.02z"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style="display: block;">
                    <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
                  </svg>
                </button>
              </div>
            </label>

            <label v-if="mode === 'register'" class="auth-dialog__field">
              <span class="auth-dialog__label">邮箱 <span class="auth-dialog__label-hint">(可选)</span></span>
              <input
                v-model="email"
                type="email"
                autocomplete="email"
                placeholder="your@email.com"
                class="auth-dialog__input"
                @keydown="handleKeydown"
              />
            </label>

            <button
              type="submit"
              class="auth-dialog__submit"
              :disabled="!canSubmit"
            >
              {{ submitting ? '处理中…' : submitLabel }}
            </button>

            <p class="auth-dialog__hint">
              {{ mode === 'login' ? '还没有账号？点上方「注册」' : '已有账号？点上方「登录」' }}
            </p>
          </form>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.auth-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 20, 30, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: var(--space-lg);
}

.auth-dialog {
  width: min(380px, 100%);
  background: var(--color-bg-overlay);
  border-radius: var(--radius-xl);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  animation: auth-pop 0.25s ease-out;
}

@keyframes auth-pop {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.auth-dialog__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-xl) var(--space-xl) var(--space-md);
}

.auth-dialog__title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.auth-dialog__close {
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-round);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-base);
  transition: all var(--transition-fast);
}

.auth-dialog__close:hover {
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
}

.auth-dialog__tabs {
  display: flex;
  gap: var(--space-xs);
  padding: 0 var(--space-xl);
  border-bottom: 1px solid var(--color-border-light);
  margin-bottom: var(--space-lg);
}

.auth-dialog__tab {
  flex: 1;
  background: transparent;
  border: none;
  padding: var(--space-md) 0;
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all var(--transition-fast);
}

.auth-dialog__tab:hover {
  color: var(--color-text-primary);
}

.auth-dialog__tab--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}

.auth-dialog__form {
  padding: 0 var(--space-xl) var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.auth-dialog__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.auth-dialog__label {
  font-size: var(--font-size-sm);
  color: var(--color-text-regular);
  font-weight: 500;
}

.auth-dialog__label-hint {
  color: var(--color-text-placeholder);
  font-weight: 400;
  margin-left: 4px;
}

.auth-dialog__input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  background: var(--color-bg-overlay);
  transition: all var(--transition-fast);
  font-family: inherit;
}

.auth-dialog__input::placeholder {
  color: var(--color-text-placeholder);
}

.auth-dialog__input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.15);
}

.auth-dialog__input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.auth-dialog__input-wrap .auth-dialog__input {
  padding-right: 40px;
}

.auth-dialog__eye {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 15px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  opacity: 0.6;
  transition: opacity var(--transition-fast);
}

.auth-dialog__eye:hover {
  opacity: 1;
}

.auth-dialog__submit {
  margin-top: var(--space-sm);
  padding: 11px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: inherit;
}

.auth-dialog__submit:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.auth-dialog__submit:active:not(:disabled) {
  background: var(--color-primary-active);
}

.auth-dialog__submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.auth-dialog__hint {
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin: var(--space-xs) 0 0;
}

/* ── Fade transition ─────────────────────────────────────────────────────── */
.auth-fade-enter-active,
.auth-fade-leave-active {
  transition: opacity 0.2s ease;
}
.auth-fade-enter-from,
.auth-fade-leave-to {
  opacity: 0;
}
</style>
