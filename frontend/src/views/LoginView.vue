<template>
  <div class="login-page">
    <div class="login-bg" aria-hidden="true">
      <div class="orb o1"></div>
      <div class="orb o2"></div>
      <div class="orb o3"></div>
    </div>
    <GlassCard class="login-card">
      <div class="login-header">
        <div class="logo-icon">
          <el-icon :size="28"><Monitor /></el-icon>
        </div>
        <h1>企业智能体工作台</h1>
        <p>请登录以继续</p>
      </div>
      <el-form @submit.prevent="handleLogin">
        <el-input v-model="username" placeholder="用户名" size="large" class="login-input" />
        <el-input v-model="password" type="password" placeholder="密码" size="large" class="login-input" show-password />
        <button type="submit" class="ui-btn-primary login-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
      </el-form>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Monitor } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import GlassCard from '../components/ui/GlassCard.vue'

const router = useRouter()
const auth = useAuthStore()
const username = ref('admin')
const password = ref('admin123')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.message || '登录失败'
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
  background: var(--gradient-page);
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
}

.o1 {
  width: 400px;
  height: 400px;
  background: rgba(167, 139, 250, 0.4);
  top: -100px;
  right: 10%;
}

.o2 {
  width: 350px;
  height: 350px;
  background: rgba(99, 102, 241, 0.3);
  bottom: -80px;
  left: 5%;
}

.o3 {
  width: 250px;
  height: 250px;
  background: rgba(6, 182, 212, 0.25);
  top: 40%;
  left: 40%;
}

.login-card {
  width: 400px;
  padding: 36px !important;
  position: relative;
  z-index: 1;
  box-shadow: var(--ui-shadow-lg) !important;
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 14px;
  border-radius: 14px;
  background: var(--gradient-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
}

.login-header h1 {
  font-size: 22px;
  margin-bottom: 6px;
  background: linear-gradient(135deg, #1E1B4B, #6366F1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-header p { color: var(--ui-text-secondary); font-size: 13px; }
.login-input { margin-bottom: 14px; }
.login-btn { width: 100%; margin-top: 8px; }
.error { color: var(--ui-danger); font-size: 13px; margin-top: 10px; text-align: center; }
</style>
