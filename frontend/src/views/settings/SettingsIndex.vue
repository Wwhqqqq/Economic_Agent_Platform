<template>
  <div class="settings-index">
    <GlassCard class="settings-list-card">
      <router-link
        v-for="item in menuItems"
        :key="item.to"
        :to="item.to"
        class="settings-list-item"
      >
        <div class="item-leading">
          <span class="item-icon-wrap">
            <el-icon><component :is="item.icon" /></el-icon>
          </span>
          <div class="item-text">
            <span class="item-title">{{ item.label }}</span>
            <span class="item-desc">{{ item.desc }}</span>
          </div>
        </div>
        <el-icon class="item-arrow"><ArrowRight /></el-icon>
      </router-link>
    </GlassCard>

    <GlassCard class="settings-list-card danger-card">
      <button type="button" class="settings-list-item danger" @click="confirmLogout">
        <div class="item-leading">
          <span class="item-icon-wrap danger">
            <el-icon><SwitchButton /></el-icon>
          </span>
          <div class="item-text">
            <span class="item-title">退出登录</span>
            <span class="item-desc">退出当前账号</span>
          </div>
        </div>
        <el-icon class="item-arrow"><ArrowRight /></el-icon>
      </button>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import {
  User,
  Brush,
  Connection,
  Lock,
  InfoFilled,
  ArrowRight,
  SwitchButton,
} from '@element-plus/icons-vue'
import { useAuthActions } from '../../composables/useAuthActions'
import GlassCard from '../../components/ui/GlassCard.vue'

const { confirmLogout } = useAuthActions()

const menuItems = [
  {
    to: '/settings/account',
    label: '账号与资料',
    desc: '用户名、邮箱、头像与会员信息',
    icon: User,
  },
  {
    to: '/settings/appearance',
    label: '外观与显示',
    desc: '主题模式与界面偏好',
    icon: Brush,
  },
  {
    to: '/settings/model',
    label: '模型与接入',
    desc: 'LLM Provider 与 API 配置',
    icon: Connection,
  },
  {
    to: '/settings/privacy',
    label: '隐私与安全',
    desc: '密码、会话与数据说明',
    icon: Lock,
  },
  {
    to: '/settings/about',
    label: '关于',
    desc: '版本信息、权限说明与协议',
    icon: InfoFilled,
  },
]
</script>

<style scoped>
.settings-index {
  width: 100%;
  max-width: var(--settings-content-width, 720px);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.settings-list-card {
  padding: 0 !important;
  overflow: hidden;
}

.settings-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border: none;
  border-bottom: 1px solid var(--settings-list-divider, rgba(199, 210, 254, 0.35));
  background: transparent;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  transition: background 0.2s ease;
  font-family: var(--ui-font);
  text-align: left;
}

.settings-list-item:last-child {
  border-bottom: none;
}

.settings-list-item:hover {
  background: var(--settings-list-hover, rgba(238, 242, 255, 0.65));
}

.item-leading {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.item-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 18px;
}

.item-icon-wrap.danger {
  background: var(--settings-danger-icon-bg);
  color: var(--ui-danger);
}

.item-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ui-text-primary);
}

.item-desc {
  font-size: 12px;
  color: var(--ui-text-secondary);
}

.item-arrow {
  color: var(--ui-text-secondary);
  flex-shrink: 0;
}

.settings-list-item.danger .item-title {
  color: var(--ui-danger);
}
</style>
