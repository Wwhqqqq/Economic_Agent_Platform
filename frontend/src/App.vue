<template>
  <div class="app-container">
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo-wrap">
          <div class="logo-icon">
            <el-icon :size="22"><Monitor /></el-icon>
          </div>
          <div>
            <span class="logo">{{ platformStore.platformName }}</span>
            <span class="logo-sub">企业智能体平台</span>
          </div>
        </div>
        <div class="status-pill">
          <span class="status-dot" :class="serviceStatusClass"></span>
          {{ serviceStatusText }}
        </div>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section-label">工作台</div>
        <button class="new-chat-btn" @click="createSession">
          <el-icon><Plus /></el-icon>
          <span>新建对话</span>
        </button>
        <div class="session-list">
          <div
            v-for="s in chatStore.sessions"
            :key="s.session_id"
            :class="['session-item', { active: s.session_id === chatStore.sessionId && isChatRoute }]"
            @click="selectSession(s.session_id)"
          >
            <el-icon class="session-icon"><ChatLineRound /></el-icon>
            <div class="session-body">
              <div class="session-title">{{ s.title || '新对话' }}</div>
              <div class="session-meta">{{ s.message_count }} 条消息</div>
            </div>
          </div>
          <div v-if="chatStore.sessions.length === 0" class="session-empty">暂无历史对话</div>
        </div>

        <div class="nav-section-label">能力中心</div>
        <router-link to="/tools" class="nav-item" active-class="active">
          <el-icon class="nav-icon-el"><Tools /></el-icon>
          <span>工具能力库</span>
        </router-link>
        <router-link to="/skills" class="nav-item" active-class="active">
          <el-icon class="nav-icon-el"><Aim /></el-icon>
          <span>技能编排</span>
        </router-link>
        <router-link to="/agents" class="nav-item" active-class="active">
          <el-icon class="nav-icon-el"><User /></el-icon>
          <span>智能体档案</span>
        </router-link>
        <router-link to="/knowledge" class="nav-item" active-class="active">
          <el-icon class="nav-icon-el"><Collection /></el-icon>
          <span>知识资产</span>
        </router-link>

        <div class="nav-section-label">系统</div>
        <router-link to="/settings" class="nav-item" active-class="active">
          <el-icon class="nav-icon-el"><Setting /></el-icon>
          <span>模型与接入</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="footer-card">
          <div class="footer-title">企业版</div>
          <div class="version">v1.0.0</div>
        </div>
      </div>
    </aside>

    <main class="main-content">
      <DecorativeBg />
      <div v-if="showStatusBanner" class="status-banner">
        <el-icon><WarningFilled /></el-icon>
        <span>部分服务暂不可用，核心对话功能仍可正常使用</span>
      </div>
      <div class="main-inner">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Monitor,
  Plus,
  ChatLineRound,
  Tools,
  Aim,
  User,
  Collection,
  Setting,
  WarningFilled,
} from '@element-plus/icons-vue'
import { usePlatformStore } from './stores/platform'
import { useSystemStore } from './stores/system'
import { useChatStore } from './stores/chat'
import DecorativeBg from './components/ui/DecorativeBg.vue'

const route = useRoute()
const router = useRouter()
const platformStore = usePlatformStore()
const systemStore = useSystemStore()
const chatStore = useChatStore()

const isChatRoute = computed(() => route.path === '/')

const serviceStatusText = computed(() => {
  const s = systemStore.status?.status
  if (s === 'healthy') return '服务就绪'
  if (s === 'degraded') return '部分受限'
  if (s === 'unknown') return '检测中'
  return '服务异常'
})

const serviceStatusClass = computed(() => {
  const s = systemStore.status?.status
  if (s === 'healthy') return 'ok'
  if (s === 'degraded') return 'warn'
  return 'err'
})

const showStatusBanner = computed(() => {
  const s = systemStore.status?.status
  return s && s !== 'healthy'
})

async function createSession() {
  if (route.path !== '/') await router.push('/')
  chatStore.newSession()
}

async function selectSession(id: string) {
  if (route.path !== '/') await router.push('/')
  if (id !== chatStore.sessionId) chatStore.switchSession(id)
}

onMounted(async () => {
  await platformStore.load()
  systemStore.refresh()
  chatStore.connect()
  chatStore.loadSessions()
})
</script>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  background: var(--gradient-page);
}

.sidebar {
  width: 260px;
  background: var(--gradient-sidebar);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(199, 210, 254, 0.45);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  z-index: 10;
  box-shadow: 4px 0 24px rgba(99, 102, 241, 0.06);
}

.sidebar-header {
  padding: 20px 16px 14px;
  border-bottom: 1px solid rgba(199, 210, 254, 0.35);
  background: linear-gradient(180deg, rgba(255,255,255,0.5) 0%, transparent 100%);
}

.logo-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.logo-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: var(--gradient-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
}

.logo {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: var(--ui-text-primary);
  line-height: 1.3;
}

.logo-sub {
  display: block;
  font-size: 11px;
  color: var(--ui-text-secondary);
  margin-top: 1px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: linear-gradient(135deg, rgba(238,242,255,0.9), rgba(236,254,255,0.7));
  border: 1px solid rgba(199, 210, 254, 0.5);
  border-radius: 20px;
  font-size: 11px;
  color: var(--ui-text-regular);
  font-weight: 500;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ui-text-secondary);
  box-shadow: 0 0 6px currentColor;
}

.status-dot.ok {
  background: var(--ui-success);
  box-shadow: 0 0 8px rgba(5, 150, 105, 0.5);
  animation: pulse-dot 2s ease-in-out infinite;
}
.status-dot.warn { background: var(--ui-warning); }
.status-dot.err { background: var(--ui-danger); }

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(0.85); }
}

.sidebar-nav {
  flex: 1;
  padding: 8px 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.nav-section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-violet);
  letter-spacing: 0.08em;
  padding: 12px 8px 6px;
  opacity: 0.85;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 40px;
  margin-bottom: 10px;
  border: none;
  border-radius: 12px;
  background: var(--gradient-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  font-family: var(--ui-font);
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
}

.new-chat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
  filter: brightness(1.05);
}

.session-list {
  max-height: 220px;
  overflow-y: auto;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(199, 210, 254, 0.35);
}

.session-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 3px;
  border: 1px solid transparent;
}

.session-item:hover {
  background: rgba(238, 242, 255, 0.7);
  border-color: rgba(199, 210, 254, 0.4);
}

.session-item.active {
  background: linear-gradient(135deg, rgba(238,242,255,0.95), rgba(236,254,255,0.6));
  border-color: rgba(129, 140, 248, 0.45);
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.1);
}

.session-item.active .session-title {
  color: var(--color-primary);
  font-weight: 600;
}

.session-icon {
  font-size: 14px;
  color: var(--ui-text-secondary);
  margin-top: 2px;
  flex-shrink: 0;
}

.session-body {
  min-width: 0;
  flex: 1;
}

.session-title {
  font-size: 13px;
  color: var(--ui-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-meta {
  font-size: 11px;
  color: var(--ui-text-secondary);
  margin-top: 1px;
}

.session-empty {
  font-size: 12px;
  color: var(--ui-text-secondary);
  padding: 12px 8px;
  text-align: center;
}

.session-item.active .session-icon {
  color: var(--color-primary);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 10px;
  color: var(--ui-text-regular);
  text-decoration: none;
  transition: all 0.2s ease;
  font-size: 14px;
  margin-bottom: 3px;
  border: 1px solid transparent;
  position: relative;
}

.nav-item:hover {
  background: rgba(238, 242, 255, 0.65);
  color: var(--ui-text-primary);
  border-color: rgba(199, 210, 254, 0.35);
}

.nav-item.active {
  background: linear-gradient(135deg, rgba(238,242,255,0.95), rgba(245,243,255,0.8));
  color: var(--color-primary);
  font-weight: 600;
  border-color: rgba(129, 140, 248, 0.4);
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.08);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--gradient-accent);
  border-radius: 0 3px 3px 0;
}

.nav-item.active .nav-icon-el {
  color: var(--color-primary);
}

.nav-icon-el {
  font-size: 17px;
  color: var(--ui-text-secondary);
}

.sidebar-footer {
  padding: 12px 16px 16px;
  border-top: 1px solid rgba(199, 210, 254, 0.35);
}

.footer-card {
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(238,242,255,0.9), rgba(236,254,255,0.6));
  border: 1px solid rgba(199, 210, 254, 0.45);
}

.footer-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--ui-text-primary);
}

.version {
  font-size: 11px;
  color: var(--ui-text-secondary);
  margin-top: 2px;
}

.main-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

.main-inner {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

.status-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 16px;
  background: #FFFBEB;
  color: #B45309;
  font-size: 12px;
  border-bottom: 1px solid #FDE68A;
  flex-shrink: 0;
}
</style>
