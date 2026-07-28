<template>
  <div class="login-page">
    <div class="login-bg" aria-hidden="true">
      <div class="orb o1"></div>
      <div class="orb o2"></div>
    </div>
    <GlassCard class="login-card">
      <div class="login-header">
        <div class="logo-icon">
          <el-icon :size="28"><Monitor /></el-icon>
        </div>
        <h1>企业智能体工作台</h1>
        <p class="tag">登录模块 · 待开发</p>
      </div>

      <div class="stub-body">
        <p>正式登录 UI 由其他同事实现。当前可用下方<strong>测试登录</strong>或粘贴 Token 进入系统。</p>
        <p class="hint">测试账号：<code>test_regular</code> / <code>Test123456</code>（会员：<code>test_member</code>）</p>
      </div>

      <div class="dev-login">
        <label class="field-label">Token（可选，粘贴 Swagger 返回的 token）</label>
        <textarea
          v-model="tokenInput"
          class="token-input"
          rows="3"
          placeholder="留空则使用 localStorage 中已有的 auth_token"
        />

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <button
          type="button"
          class="ui-btn-primary login-btn"
          :disabled="loading"
          @click="goHome"
        >
          {{ loading ? '验证中…' : '我已设置 Token，进入工作台' }}
        </button>

        <button
          type="button"
          class="ui-btn-ghost quick-btn"
          :disabled="loading"
          @click="quickLogin('test_regular')"
        >
          测试账号快速登录（普通用户）
        </button>
        <button
          type="button"
          class="ui-btn-ghost quick-btn"
          :disabled="loading"
          @click="quickLogin('test_member')"
        >
          测试账号快速登录（会员用户）
        </button>
      </div>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Monitor } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import GlassCard from '../components/ui/GlassCard.vue'

const router = useRouter()
const auth = useAuthStore()
const tokenInput = ref('')
const loading = ref(false)
const errorMsg = ref('')

onMounted(() => {
  auth.syncTokenFromStorage()
  tokenInput.value = auth.token
})

async function enterWorkspace() {
  errorMsg.value = ''
  loading.value = true
  try {
    if (tokenInput.value.trim()) {
      auth.setToken(tokenInput.value.trim())
    } else {
      auth.syncTokenFromStorage()
    }

    const ok = await auth.checkAuth()
    if (!ok) {
      errorMsg.value = 'Token 无效或未设置。请粘贴有效 Token，或点击下方「测试账号快速登录」。'
      ElMessage.error(errorMsg.value)
      return
    }

    await router.push('/')
  } finally {
    loading.value = false
  }
}

async function goHome() {
  await enterWorkspace()
}

async function quickLogin(username: string) {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.login(username, 'Test123456')
    ElMessage.success(`已登录：${username}`)
    await router.push('/')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '登录失败，请确认后端已启动'
    errorMsg.value = msg
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: calc(100vh - 48px);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 24px;
}
.login-bg { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.35;
}
.o1 { width: 280px; height: 280px; background: #6366f1; top: 10%; left: 15%; }
.o2 { width: 220px; height: 220px; background: #22d3ee; bottom: 15%; right: 20%; }
.login-card {
  width: 100%;
  max-width: 440px;
  position: relative;
  z-index: 1;
  padding: 32px !important;
}
.login-header { text-align: center; margin-bottom: 20px; }
.logo-icon {
  width: 56px; height: 56px; margin: 0 auto 12px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(34,211,238,0.15));
  color: var(--accent-indigo, #6366f1);
}
.login-header h1 { font-size: 1.35rem; margin: 0 0 6px; }
.tag {
  color: var(--accent-cyan, #22d3ee);
  font-size: 0.85rem;
  font-weight: 600;
}
.stub-body {
  font-size: 0.9rem;
  line-height: 1.65;
  color: var(--text-secondary, #64748b);
  margin-bottom: 16px;
}
.stub-body code {
  font-size: 0.82rem;
  background: rgba(99,102,241,0.08);
  padding: 2px 6px;
  border-radius: 4px;
}
.hint {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(99,102,241,0.06);
  font-size: 0.82rem;
}
.dev-login { display: flex; flex-direction: column; gap: 10px; }
.field-label { font-size: 0.82rem; color: var(--text-secondary, #64748b); }
.token-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.82rem;
  font-family: ui-monospace, monospace;
  resize: vertical;
  background: rgba(255,255,255,0.7);
}
.token-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}
.error-msg {
  margin: 0;
  font-size: 0.82rem;
  color: #dc2626;
  line-height: 1.5;
}
.login-btn { width: 100%; margin-top: 4px; }
.quick-btn { width: 100%; justify-content: center; }
</style>
