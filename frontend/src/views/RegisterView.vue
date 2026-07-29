<template>
  <div class="register-page">
    <div class="register-bg" aria-hidden="true">
      <div class="orb o1"></div>
      <div class="orb o2"></div>
      <div class="orb o3"></div>
    </div>

    <GlassCard class="register-card" tinted>
      <div class="register-header">
        <div class="logo-icon">
          <el-icon :size="28"><UserFilled /></el-icon>
        </div>
        <h1>创建账号</h1>
        <p class="subtitle">注册成为普通用户，开启智能体协作</p>
      </div>

      <GradientDivider spacing="0 0 20px" />

      <form class="register-form" @submit.prevent="handleRegister">
        <!-- 用户名 -->
        <div class="form-field" :class="{ 'field-error': errors.username }">
          <label class="field-label">用户名</label>
          <div class="input-shell" :class="{ 'field-error-shake': shake.username }">
            <el-input
            v-model="form.username"
            placeholder="请输入用户名（字母、数字、下划线）"
            size="large"
            clearable
            :prefix-icon="User"
            autocomplete="username"
            @input="onFieldInput('username')"
          />
          </div>
          <p v-if="errors.username" class="field-error-text">{{ errors.username }}</p>
        </div>

        <!-- 邮箱 -->
        <div class="form-field" :class="{ 'field-error': errors.email }">
          <label class="field-label">邮箱</label>
          <div class="input-shell" :class="{ 'field-error-shake': shake.email }">
          <el-input
            v-model="form.email"
            placeholder="请输入邮箱地址"
            size="large"
            clearable
            :prefix-icon="Message"
            autocomplete="email"
            @input="onFieldInput('email')"
          />
          </div>
          <p v-if="errors.email" class="field-error-text">{{ errors.email }}</p>
        </div>

        <!-- 密码 -->
        <div class="form-field" :class="{ 'field-error': errors.password }">
          <label class="field-label">密码</label>
          <div class="input-shell" :class="{ 'field-error-shake': shake.password }">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="至少 6 位，仅字母、数字、下划线"
            size="large"
            show-password
            :prefix-icon="Lock"
            autocomplete="new-password"
            @input="onFieldInput('password')"
          />
          </div>
          <p v-if="errors.password" class="field-error-text">{{ errors.password }}</p>
        </div>

        <!-- 确认密码 -->
        <div class="form-field" :class="{ 'field-error': errors.confirm_password }">
          <label class="field-label">确认密码</label>
          <div class="input-shell" :class="{ 'field-error-shake': shake.confirm_password }">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            size="large"
            show-password
            :prefix-icon="Lock"
            autocomplete="new-password"
            @input="onFieldInput('confirm_password')"
          />
          </div>
          <p v-if="errors.confirm_password" class="field-error-text">{{ errors.confirm_password }}</p>
        </div>

        <!-- 验证码 -->
        <div class="form-field" :class="{ 'field-error': errors.verification_code }">
          <label class="field-label">验证码</label>
          <div class="code-row">
            <div class="input-shell code-input" :class="{ 'field-error-shake': shake.verification_code }">
            <el-input
              v-model="form.verificationCode"
              placeholder="请输入 4 位验证码"
              size="large"
              maxlength="4"
              :prefix-icon="Key"
              class="code-input-inner"
              @input="onCodeInput"
            />
            </div>
            <button
              type="button"
              class="ui-btn-ghost send-code-btn"
              :disabled="!canSendCode || sendingCode"
              @mousedown.prevent
              @click="handleSendCode"
            >
              {{ sendCodeLabel }}
            </button>
          </div>
          <p v-if="errors.verification_code" class="field-error-text">
            {{ errors.verification_code }}
          </p>
        </div>

        <button type="submit" class="ui-btn-primary submit-btn" :disabled="submitting">
          {{ submitting ? '注册中…' : '注册' }}
        </button>
      </form>

      <p class="login-hint">
        已有账号？
        <router-link to="/login" class="login-link">去登录</router-link>
      </p>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, reactive, ref } from 'vue'
import { UserFilled, User, Lock, Message, Key } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { sendVerificationCode } from '../api/client'
import { useAuthStore } from '../stores/auth'
import GlassCard from '../components/ui/GlassCard.vue'
import GradientDivider from '../components/ui/GradientDivider.vue'
import {
  mapServerField,
  mapServerMessage,
  validateConfirmPassword,
  validateEmail,
  validatePassword,
  validateUsername,
  validateVerificationCode,
  type RegisterField,
} from '../utils/validation'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  verificationCode: '',
})

const errors = reactive<Record<RegisterField, string>>({
  username: '',
  email: '',
  password: '',
  confirm_password: '',
  verification_code: '',
})

const shake = reactive<Record<RegisterField, boolean>>({
  username: false,
  email: false,
  password: false,
  confirm_password: false,
  verification_code: false,
})

const sendingCode = ref(false)
const submitting = ref(false)
const attemptedSubmit = ref(false)
const cooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const canSendCode = computed(() => {
  if (sendingCode.value || cooldown.value > 0) return false
  return !validateEmail(form.email)
})

const sendCodeLabel = computed(() => {
  if (sendingCode.value) return '发送中…'
  if (cooldown.value > 0) return `${cooldown.value}s 后重发`
  return '发送验证码'
})

function triggerShake(field: RegisterField) {
  shake[field] = false
  requestAnimationFrame(() => {
    shake[field] = true
    setTimeout(() => {
      shake[field] = false
    }, 400)
  })
}

function setError(field: RegisterField, message: string, opts?: { shake?: boolean }) {
  errors[field] = message
  if (opts?.shake !== false) {
    triggerShake(field)
  }
}

function clearError(field: RegisterField) {
  errors[field] = ''
}

function onFieldInput(field: RegisterField) {
  if (attemptedSubmit.value && errors[field]) {
    clearError(field)
  }
}

function startCooldown(seconds: number) {
  cooldown.value = seconds
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    if (cooldown.value <= 1) {
      cooldown.value = 0
      if (cooldownTimer) clearInterval(cooldownTimer)
      cooldownTimer = null
    } else {
      cooldown.value -= 1
    }
  }, 1000)
}

function validateField(field: RegisterField): boolean {
  let msg: string | null = null
  switch (field) {
    case 'username':
      msg = validateUsername(form.username)
      break
    case 'email':
      msg = validateEmail(form.email)
      break
    case 'password':
      msg = validatePassword(form.password)
      break
    case 'verification_code':
      msg = validateVerificationCode(form.verificationCode)
      break
    default:
      break
  }
  if (msg) {
    setError(field, msg)
    return false
  }
  clearError(field)
  return true
}

function validateConfirmPasswordField(): boolean {
  const msg = validateConfirmPassword(form.password, form.confirmPassword)
  if (msg) {
    setError('confirm_password', msg)
    return false
  }
  clearError('confirm_password')
  return true
}

function onCodeInput() {
  form.verificationCode = form.verificationCode.replace(/\D/g, '').slice(0, 4)
  if (errors.verification_code) {
    clearError('verification_code')
  }
}

function validateAll(): boolean {
  const results = [
    validateField('username'),
    validateField('email'),
    validateField('password'),
    validateConfirmPasswordField(),
    validateField('verification_code'),
  ]
  return results.every(Boolean)
}

async function handleSendCode() {
  const emailMsg = validateEmail(form.email)
  if (emailMsg) {
    ElMessage.warning(emailMsg)
    return
  }

  sendingCode.value = true
  try {
    const data = await sendVerificationCode(form.email.trim())
    if (!data.success) {
      const isTooFrequent = data.code === 'SEND_TOO_FREQUENT'
      const msg = isTooFrequent
        ? '获取过于频繁，请稍后再试'
        : mapServerMessage(data.code, data.message)
      if (isTooFrequent) {
        setError('verification_code', msg)
      } else {
        ElMessage.error(msg)
      }
      if (data.retry_after_seconds) startCooldown(data.retry_after_seconds)
      return
    }
    clearError('verification_code')
    ElMessage.success('验证码已发送，请查收邮件')
    startCooldown(data.retry_after_seconds ?? 60)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '发送失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    sendingCode.value = false
  }
}

async function handleRegister() {
  attemptedSubmit.value = true
  if (!validateAll()) return

  if (form.password !== form.confirmPassword) {
    setError('confirm_password', '密码不一致')
    return
  }

  submitting.value = true
  try {
    const data = await auth.register({
      username: form.username.trim(),
      email: form.email.trim(),
      password: form.password,
      verification_code: form.verificationCode.trim(),
    })
    ElMessage.success(`注册成功，欢迎 ${data.username}`)
    await router.push('/')
  } catch (e: unknown) {
    const err = e as Error & { code?: string; field?: string }
    const field = mapServerField(err.field)
    const msg = mapServerMessage(err.code, err.message)
    if (field) {
      setError(field, msg)
    } else {
      ElMessage.error(msg)
    }
  } finally {
    submitting.value = false
  }
}

onUnmounted(() => {
  if (cooldownTimer) clearInterval(cooldownTimer)
})
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 24px;
  background: var(--gradient-page);
}

.register-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(72px);
  opacity: 0.32;
}

.o1 {
  width: 320px;
  height: 320px;
  background: #6366f1;
  top: 8%;
  left: 10%;
}

.o2 {
  width: 260px;
  height: 260px;
  background: #06b6d4;
  bottom: 10%;
  right: 12%;
}

.o3 {
  width: 200px;
  height: 200px;
  background: #8b5cf6;
  top: 50%;
  left: 58%;
  opacity: 0.22;
}

.register-card {
  width: 100%;
  max-width: 440px;
  position: relative;
  z-index: 1;
  padding: 32px 32px 28px !important;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
}

.register-header {
  text-align: center;
  margin-bottom: 4px;
}

.logo-icon {
  width: 52px;
  height: 52px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: var(--gradient-primary);
  color: #fff;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
}

.register-header h1 {
  font-size: 1.3rem;
  font-weight: 700;
  margin: 0 0 6px;
  color: var(--ui-text-primary);
}

.subtitle {
  margin: 0;
  font-size: 0.875rem;
  color: var(--ui-text-secondary);
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.field-label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--ui-text-regular);
  margin-bottom: 8px;
}

.field-error-text {
  margin: 6px 0 0;
  font-size: 0.8125rem;
  color: var(--ui-danger);
  line-height: 1.4;
}

.form-field.field-error :deep(.el-input__wrapper) {
  border-color: #dc2626 !important;
  background: rgba(220, 38, 38, 0.06) !important;
  box-shadow: none !important;
}

.register-form :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.85) !important;
  border: 1px solid var(--ui-border) !important;
  box-shadow: none !important;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.register-form :deep(.el-input__wrapper:hover) {
  border-color: #a5b4fc !important;
  background: rgba(255, 255, 255, 0.85) !important;
}

.register-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary) !important;
  background: rgba(255, 255, 255, 0.92) !important;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12) !important;
}

.form-field.field-error :deep(.el-input__wrapper.is-focus) {
  border-color: #dc2626 !important;
  background: rgba(220, 38, 38, 0.06) !important;
  box-shadow: none !important;
}

.form-field.field-error :deep(.el-input__inner:-webkit-autofill),
.form-field.field-error :deep(.el-input__inner:-webkit-autofill:focus),
.form-field.field-error :deep(.el-input__inner:autofill) {
  -webkit-box-shadow: 0 0 0 1000px rgba(255, 245, 245, 0.95) inset !important;
  box-shadow: 0 0 0 1000px rgba(255, 245, 245, 0.95) inset !important;
  -webkit-text-fill-color: var(--ui-text-primary) !important;
}

.input-shell.field-error-shake {
  animation: field-shake 0.4s ease;
}

@keyframes field-shake {
  0%,
  100% {
    transform: translateX(0);
  }
  20% {
    transform: translateX(-6px);
  }
  40% {
    transform: translateX(6px);
  }
  60% {
    transform: translateX(-4px);
  }
  80% {
    transform: translateX(4px);
  }
}

.code-row {
  display: flex;
  gap: 10px;
  align-items: stretch;
}

.code-input {
  flex: 1;
  min-width: 0;
}

.code-input-inner {
  width: 100%;
}

.send-code-btn {
  flex-shrink: 0;
  height: 40px;
  padding: 0 12px;
  white-space: nowrap;
  font-size: 12px;
}

.send-code-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.submit-btn {
  width: 100%;
  height: 44px;
  margin-top: 6px;
}

.login-hint {
  margin: 20px 0 0;
  text-align: center;
  font-size: 0.875rem;
  color: var(--ui-text-secondary);
}

.login-link {
  color: var(--color-primary);
  font-weight: 600;
  text-decoration: none;
}

.login-link:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}
</style>
