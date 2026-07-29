<template>
  <div class="login-page">
    <div class="login-bg" aria-hidden="true">
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
  background: var(--gradient-page);
}

.login-bg {
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
  left: 12%;
}

.o2 {
  width: 260px;
  height: 260px;
  background: #06b6d4;
  bottom: 12%;
  right: 15%;
}

.o3 {
  width: 200px;
  height: 200px;
  background: #8b5cf6;
  top: 55%;
  left: 55%;
  opacity: 0.22;
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
  border-radius: 16px;
  background: var(--gradient-primary);
  color: #fff;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
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
