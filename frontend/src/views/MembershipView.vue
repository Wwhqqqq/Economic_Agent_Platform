<template>
  <div class="page-shell">
    <PageHeader
      title="会员中心"
      subtitle="查看会员权益、到期时间与升级方案"
      breadcrumb="系统 / 会员中心"
    />
    <div class="page-body">
      <GlassCard class="membership-card">
        <MembershipBadge
          :is-member="auth.isMember"
          :membership-expires-at="auth.membershipExpiresAt"
          size="md"
          :show-expiry="auth.isMember"
        />
        <h3>{{ auth.isMember ? '感谢您的会员支持' : '升级会员，解锁高级能力' }}</h3>
        <p v-if="auth.isMember">
          会员有效期至 {{ formatDate(auth.membershipExpiresAt) }}
        </p>
        <p v-else>
          开通会员后可使用 Plan-Execute、Multi-Agent、个人模型配置、会员专享技能与知识库。
        </p>
        <ul class="benefits">
          <li>Plan-Execute 与 Multi-Agent 协同</li>
          <li>财务审计等会员专享技能</li>
          <li>个人 LLM API Key 配置</li>
          <li>会员专享知识库只读访问</li>
        </ul>
        <button type="button" class="ui-btn-primary" disabled>
          {{ auth.isMember ? '续费（即将推出）' : '立即升级（即将推出）' }}
        </button>
        <router-link to="/settings/account" class="back-link">返回账号设置</router-link>
      </GlassCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
import PageHeader from '../components/layout/PageHeader.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import MembershipBadge from '../components/ui/MembershipBadge.vue'

const auth = useAuthStore()

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.membership-card {
  max-width: 560px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.membership-card h3 {
  margin: 8px 0 0;
  font-size: 18px;
}

.membership-card p {
  margin: 0;
  font-size: 14px;
  color: var(--ui-text-secondary);
  line-height: 1.6;
}

.benefits {
  margin: 8px 0 16px;
  padding-left: 18px;
  line-height: 1.8;
  color: var(--ui-text-regular);
}

.back-link {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
}
</style>
