<template>
  <div class="login-page">
    <div class="login-bg" aria-hidden="true">
      <div class="bg-grid"></div>
      <svg class="bg-chart bg-chart--left" viewBox="0 0 200 120" fill="none">
        <polyline points="10,90 40,70 70,75 100,45 130,55 160,25 190,35" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        <circle cx="160" cy="25" r="4" fill="currentColor" />
      </svg>
      <svg class="bg-chart bg-chart--right" viewBox="0 0 120 120" fill="none">
        <rect x="20" y="60" width="16" height="40" rx="2" fill="currentColor" opacity="0.5" />
        <rect x="44" y="40" width="16" height="60" rx="2" fill="currentColor" opacity="0.7" />
        <rect x="68" y="25" width="16" height="75" rx="2" fill="currentColor" />
        <rect x="92" y="50" width="16" height="50" rx="2" fill="currentColor" opacity="0.6" />
      </svg>
      <div class="bg-panel bg-panel--tl"></div>
      <div class="bg-panel bg-panel--br"></div>
      <div class="orb o1"></div>
      <div class="orb o2"></div>
      <div class="orb o3"></div>
    </div>

    <GlassCard class="login-card" tinted>
      <div class="login-header">
        <div class="logo-icon">
          <el-icon :size="28"><Monitor /></el-icon>
        </div>
        <h1>企业智能体工作台</h1>
        <p class="subtitle">登录您的账号，进入多用户智能体协作空间</p>
        <p v-if="isSwitchMode" class="switch-hint">请登录其他账号</p>
      </div>

      <GradientDivider spacing="0 0 24px" />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <label class="field-label">用户名</label>
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            clearable
            :prefix-icon="User"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item prop="password">
          <label class="field-label">密码</label>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            :prefix-icon="Lock"
            autocomplete="current-password"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <p v-if="errorMsg" class="error-msg" role="alert">{{ errorMsg }}</p>

        <button
          type="submit"
          class="ui-btn-primary login-btn"
          :disabled="loading"
        >
          {{ loading ? '登录中…' : '登录' }}
        </button>
      </el-form>

      <p class="register-hint">
        还没有账号？
        <router-link to="/register" class="register-link">去注册</router-link>
      </p>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { Monitor, User, Lock } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import GlassCard from '../components/ui/GlassCard.vue'
import GradientDivider from '../components/ui/GradientDivider.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isSwitchMode = computed(() => route.query.switch === '1')

const formRef = ref<FormInstance>()
const loading = ref(false)
const errorMsg = ref('')

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 64, message: '用户名长度为 3–64 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  errorMsg.value = ''
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const data = await auth.login(form.username.trim(), form.password)
    ElMessage.success(`欢迎回来，${data.username}（${auth.userTypeDisplay}）`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '登录失败，请稍后重试'
    errorMsg.value = msg
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 24px;
  background-color: var(--color-background);
  background-image: url('/images/login-bg-mint-rich.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.login-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(46, 125, 50, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(46, 125, 50, 0.04) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 70% 60% at 50% 50%, transparent 30%, black 85%);
}

.bg-chart {
  position: absolute;
  color: rgba(46, 125, 50, 0.12);
}

.bg-chart--left {
  width: 220px;
  height: 132px;
  top: 12%;
  left: 4%;
  animation: float-slow 18s ease-in-out infinite;
}

.bg-chart--right {
  width: 140px;
  height: 140px;
  bottom: 10%;
  right: 5%;
  animation: float-slow 22s ease-in-out infinite reverse;
}

.bg-panel {
  position: absolute;
  border: 1px solid rgba(46, 125, 50, 0.1);
  background: rgba(255, 255, 255, 0.35);
}

.bg-panel--tl {
  width: 180px;
  height: 100px;
  top: 8%;
  right: 8%;
  transform: rotate(-6deg);
}

.bg-panel--br {
  width: 160px;
  height: 90px;
  bottom: 14%;
  left: 6%;
  transform: rotate(4deg);
}

.orb {
  position: absolute;
  border-radius: 50%;
  background: rgba(200, 230, 201, 0.35);
  filter: blur(40px);
}

.o1 {
  width: 280px;
  height: 280px;
  top: -60px;
  right: 10%;
}

.o2 {
  width: 220px;
  height: 220px;
  bottom: 8%;
  left: 12%;
}

.o3 {
  width: 160px;
  height: 160px;
  top: 40%;
  left: -40px;
  background: rgba(46, 125, 50, 0.08);
}

@keyframes float-slow {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.login-card {
  width: 100%;
  max-width: 420px;
  position: relative;
  z-index: 1;
  padding: 36px 32px !important;
}

.login-header {
  text-align: center;
  margin-bottom: 4px;
}

.logo-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #fff;
}

.login-header h1 {
  font-size: 1.35rem;
  font-weight: 700;
  margin: 0 0 8px;
  color: var(--ui-text-primary);
}

.subtitle {
  margin: 0;
  font-size: 0.875rem;
  color: var(--ui-text-secondary);
  line-height: 1.5;
}

.switch-hint {
  margin: 10px 0 0;
  font-size: 0.8125rem;
  color: var(--color-primary);
  font-weight: 600;
}

.login-form {
  display: flex;
  flex-direction: column;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.login-form :deep(.el-form-item__content) {
  flex-direction: column;
  align-items: stretch;
}

.field-label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--ui-text-regular);
  margin-bottom: 8px;
}

.error-msg {
  margin: 0 0 14px;
  padding: 10px 12px;
  font-size: 0.8125rem;
  color: var(--ui-danger);
  line-height: 1.5;
  background: rgba(220, 38, 38, 0.06);
  border: 1px solid rgba(220, 38, 38, 0.15);
  border-radius: 10px;
}

.login-btn {
  width: 100%;
  height: 44px;
  margin-top: 4px;
}

.register-hint {
  margin: 22px 0 0;
  text-align: center;
  font-size: 0.875rem;
  color: var(--ui-text-secondary);
}

.register-link {
  color: var(--color-primary);
  font-weight: 600;
  text-decoration: none;
  transition: color 0.2s ease;
}

.register-link:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}
</style>
