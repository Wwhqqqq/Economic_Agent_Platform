<template>
  <div :class="['app-container', { 'auth-layout': isAuthRoute }]">
    <aside v-if="!isAuthRoute" class="sidebar">
      <div class="sidebar-header">
        <div class="logo-wrap">
          <div class="logo-icon">
            <el-icon :size="22"><Monitor /></el-icon>
          </div>
          <div>
            <span class="logo">{{ platformStore.platformName }}</span>
            <span class="logo-sub">会计通用工作台</span>
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
          <el-dropdown
            v-for="s in chatStore.sessions"
            :key="s.session_id"
            trigger="contextmenu"
            placement="bottom-start"
            @command="(cmd: string) => handleSessionMenu(cmd, s.session_id)"
          >
            <div
              :class="['session-item', { active: s.session_id === chatStore.sessionId && isChatRoute }]"
              @click="selectSession(s.session_id)"
            >
              <el-icon class="session-icon"><ChatLineRound /></el-icon>
              <div class="session-body">
                <div class="session-title">{{ s.title || '新对话' }}</div>
                <div class="session-meta">{{ s.message_count }} 条消息</div>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="export">
                  <el-icon><Download /></el-icon>
                  导出对话
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <el-icon><Delete /></el-icon>
                  删除对话
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div v-if="chatStore.sessions.length === 0" class="session-empty">暂无历史对话</div>
        </div>

        <div class="nav-section-label">能力中心</div>
        <router-link to="/tools" class="nav-item" active-class="active">
          <el-icon class="nav-icon-el"><Tools /></el-icon>
          <span>工具能力库</span>
        </router-link>
        <router-link to="/skills" class="nav-item" active-class="active">
          <el-icon class="nav-icon-el"><Aim /></el-icon>
          <span>技能库</span>
        </router-link>
        <router-link to="/experts" class="nav-item" active-class="active">
          <el-icon class="nav-icon-el"><User /></el-icon>
          <span>专家中心</span>
        </router-link>
        <router-link to="/knowledge" class="nav-item" active-class="active">
          <el-icon class="nav-icon-el"><Collection /></el-icon>
          <span>知识资产</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div v-if="authStore.username" class="user-card" :class="{ member: authStore.isMember }">
          <div class="user-identity">
            <div class="user-avatar" :class="{ member: authStore.isMember }">
              <img v-if="authStore.avatarUrl" :src="authStore.avatarUrl" alt="" class="user-avatar-img" />
              <span v-else>{{ userInitial }}</span>
            </div>
            <div class="user-info">
              <span class="user-name">{{ authStore.username }}</span>
              <MembershipBadge
                :is-member="authStore.isMember"
                :membership-expires-at="authStore.membershipExpiresAt"
                size="sm"
                :show-expiry="authStore.isMember"
              />
            </div>
          </div>
        </div>
        <router-link
          to="/settings"
          class="settings-entry-btn"
          :class="{ active: isSettingsRoute }"
        >
          <el-icon class="settings-icon"><Setting /></el-icon>
          <div class="settings-entry-text">
            <span class="settings-label">设置</span>
            <span class="settings-version">{{ versionLabel }}</span>
          </div>
          <el-icon class="settings-arrow"><ArrowRight /></el-icon>
        </router-link>
      </div>
    </aside>

    <main :class="['main-content', { 'auth-main': isAuthRoute }]">
      <DecorativeBg v-if="!isAuthRoute" />
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
import { computed, onMounted, watch } from 'vue'
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
  ArrowRight,
  WarningFilled,
  Download,
  Delete,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePlatformStore } from './stores/platform'
import { useSystemStore } from './stores/system'
import { useChatStore } from './stores/chat'
import { useAuthStore } from './stores/auth'
import { formatVersionLabel } from './utils/appVersion'
import DecorativeBg from './components/ui/DecorativeBg.vue'
import MembershipBadge from './components/ui/MembershipBadge.vue'

const route = useRoute()
const router = useRouter()
const platformStore = usePlatformStore()
const systemStore = useSystemStore()
const chatStore = useChatStore()
const authStore = useAuthStore()

const isChatRoute = computed(() => route.path === '/')
const isAuthRoute = computed(() => route.path === '/login' || route.path === '/register')
const isSettingsRoute = computed(() => route.path.startsWith('/settings'))
const versionLabel = formatVersionLabel()

const userInitial = computed(() => {
  const name = authStore.username
  return name ? name.charAt(0).toUpperCase() : '?'
})

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

async function handleSessionMenu(command: string, sessionId: string) {
  if (command === 'export') {
    try {
      await chatStore.exportSession(sessionId)
      ElMessage.success('对话已导出')
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : '导出失败')
    }
    return
  }
  if (command === 'delete') {
    const target = chatStore.sessions.find(s => s.session_id === sessionId)
    try {
      await ElMessageBox.confirm(
        `确定删除「${target?.title || '新对话'}」？删除后无法恢复。`,
        '删除对话',
        { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
      )
      await chatStore.deleteSession(sessionId)
      ElMessage.success('对话已删除')
    } catch (e) {
      if (e !== 'cancel' && e !== 'close') {
        ElMessage.error(e instanceof Error ? e.message : '删除失败')
      }
    }
  }
}

onMounted(async () => {
  await platformStore.load()
  if (!isAuthRoute.value) {
    systemStore.refresh()
  }
  if (!authStore.checked) await authStore.checkAuth()
  if (isAuthRoute.value) return
  if (authStore.authEnabled && authStore.token) {
    await authStore.refreshProfile()
    await chatStore.newSession()
  }
  chatStore.loadSessions()
})

watch(isAuthRoute, async (onAuthPage) => {
  if (onAuthPage || !authStore.token) return
  await authStore.refreshProfile()
  systemStore.refresh()
  try {
    await chatStore.newSession()
  } catch (e) {
    console.error('[chat] failed to init session after login', e)
  }
  chatStore.loadSessions()
})
</script>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  background: var(--color-background);
}

.sidebar {
  width: 260px;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  z-index: 10;
  box-shadow: none;
}

.sidebar-header {
  padding: 20px 16px 14px;
  border-bottom: 1px solid var(--sidebar-divider);
  background: #ffffff;
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
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
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
  background: var(--ui-bg-muted);
  border: 1px solid var(--color-border);
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
  border: 1px solid var(--color-primary-hover);
  background: var(--btn-primary-bg);
  color: var(--btn-primary-color);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
  font-family: var(--ui-font);
}

.new-chat-btn:hover {
  background: var(--color-primary-hover);
}

.session-list {
  max-height: 220px;
  overflow-y: auto;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--sidebar-divider);
}

.session-list :deep(.el-dropdown) {
  display: block;
  width: 100%;
}

.session-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
  transition: background 0.15s ease;
  margin-bottom: 3px;
  border: 1px solid transparent;
}

.session-item:hover {
  background: var(--sidebar-item-hover-bg);
  border-color: var(--sidebar-item-hover-border);
}

.session-item.active {
  background: var(--sidebar-item-active-bg);
  border-color: var(--sidebar-item-active-border);
  box-shadow: var(--sidebar-item-active-shadow);
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
  color: var(--ui-text-regular);
  text-decoration: none;
  transition: background 0.15s ease, border-color 0.15s ease;
  font-size: 14px;
  margin-bottom: 3px;
  border: 1px solid transparent;
  position: relative;
}

.nav-item:hover {
  background: var(--nav-item-hover-bg);
  color: var(--ui-text-primary);
  border-color: var(--nav-item-hover-border);
}

.nav-item.active {
  background: var(--nav-item-active-bg);
  color: var(--color-primary);
  font-weight: 600;
  border-color: var(--nav-item-active-border);
  box-shadow: var(--nav-item-active-shadow);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--color-primary);
}

.user-card {
  margin-bottom: 10px;
  padding: 10px 12px;
  background: var(--user-card-bg);
  border: 1px solid var(--user-card-border);
}

.user-card .user-identity {
  margin-bottom: 0;
}

.user-card.member {
  background: var(--user-card-member-bg);
  border: 1px solid var(--user-card-member-border);
}

.user-identity {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.user-avatar {
  width: 36px;
  height: 36px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.user-avatar.member {
  background: var(--color-primary);
}

.user-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--ui-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  border-top: 1px solid var(--sidebar-divider);
}

.settings-icon {
  font-size: 18px;
  color: var(--color-primary);
  flex-shrink: 0;
}

.settings-entry-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.settings-label {
  font-size: 13px;
  font-weight: 600;
}

.settings-version {
  font-size: 11px;
  color: var(--ui-text-secondary);
}

.settings-arrow {
  font-size: 14px;
  color: var(--ui-text-secondary);
  flex-shrink: 0;
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
  background: #fff8e1;
  color: #e65100;
  font-size: 12px;
  border-bottom: 1px solid #ffcc80;
  flex-shrink: 0;
}

.settings-entry-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--settings-entry-border);
  background: var(--settings-entry-bg);
  color: var(--ui-text-primary);
  text-decoration: none;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.settings-entry-btn:hover {
  border-color: var(--settings-entry-hover-border);
  background: var(--settings-entry-hover-bg);
  box-shadow: none;
}

.settings-entry-btn.active {
  border-color: var(--settings-entry-active-border);
  background: var(--settings-entry-active-bg);
  box-shadow: inset 3px 0 0 var(--color-primary);
}

.auth-layout {
  background: var(--color-background);
}

.auth-main {
  background: transparent;
}

.auth-main .main-inner {
  overflow: auto;
}
</style>
