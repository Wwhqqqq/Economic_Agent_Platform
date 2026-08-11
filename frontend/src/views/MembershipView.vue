<template>
  <div class="page-shell">
    <PageHeader
      title="会员中心"
      subtitle="查看会员权益、到期时间与升级方案"
      breadcrumb="系统 / 会员中心"
    />
    <div class="page-body membership-layout">
      <GlassCard class="membership-card">
        <MembershipBadge
          :is-member="auth.isMember"
          :membership-expires-at="auth.membershipExpiresAt"
          size="md"
          :show-expiry="auth.isMember"
        />
        <h3>{{ auth.isMember ? '感谢您的会员支持' : '升级会员，解锁专业财务智能体能力' }}</h3>
        <p v-if="membership.isTrial" class="trial-tag">体验会员 · 剩余 {{ membership.daysRemaining ?? 0 }} 天</p>
        <p v-else-if="auth.isMember">
          会员有效期至 {{ formatDate(auth.membershipExpiresAt) }}
        </p>
        <p v-else>
          开通会员后可使用 Plan 任务编排、Multi-Agent、个人模型配置、会员专享技能与知识库。
        </p>

        <div v-if="membership.quota" class="quota-grid">
          <div class="quota-item">
            <span class="quota-label">会话</span>
            <span class="quota-value">{{ membership.quotaSessionsLabel }}</span>
          </div>
          <div class="quota-item">
            <span class="quota-label">文档</span>
            <span class="quota-value">{{ membership.quotaDocumentsLabel }}</span>
          </div>
          <div class="quota-item">
            <span class="quota-label">今日消息</span>
            <span class="quota-value">
              {{ membership.quota.daily_messages?.used ?? 0 }} /
              {{ membership.quota.daily_messages?.limit ?? '—' }}
            </span>
          </div>
        </div>

        <table class="perm-table">
          <thead>
            <tr><th>能力</th><th>普通</th><th>会员</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in compareRows" :key="row.name">
              <td>{{ row.name }}</td>
              <td>{{ row.regular ? '✓' : '—' }}</td>
              <td>{{ row.member ? '✓' : '—' }}</td>
            </tr>
          </tbody>
        </table>

        <div v-if="!auth.isMember" class="plan-cards">
          <div
            v-for="plan in membership.plans"
            :key="plan.id"
            class="plan-card"
            :class="{ recommended: plan.recommended }"
          >
            <h4>{{ plan.name }}</h4>
            <p class="plan-price">¥{{ (plan.price_cents / 100).toFixed(0) }}</p>
            <p class="plan-duration">{{ plan.duration_days }} 天</p>
          </div>
        </div>

        <button
          v-if="!auth.isMember"
          type="button"
          class="ui-btn-primary"
          :disabled="!membership.upgradeUrl"
          @click="openUpgrade"
        >
          {{ membership.upgradeUrl ? '立即升级' : '立即升级（即将推出）' }}
        </button>
        <button v-else type="button" class="ui-btn-primary" :disabled="!membership.upgradeUrl" @click="openUpgrade">
          {{ membership.upgradeUrl ? '续费' : '续费（即将推出）' }}
        </button>

        <div class="redeem-section">
          <h4>兑换码</h4>
          <div class="redeem-row">
            <input v-model="redeemCode" type="text" class="redeem-input" placeholder="输入兑换码" />
            <button type="button" class="ui-btn-ghost" :disabled="redeeming" @click="handleRedeem">
              {{ redeeming ? '兑换中…' : '兑换' }}
            </button>
          </div>
        </div>

        <router-link to="/settings/account" class="back-link">返回账号设置</router-link>
      </GlassCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { useMembershipStore } from '../stores/membership'
import PageHeader from '../components/layout/PageHeader.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import MembershipBadge from '../components/ui/MembershipBadge.vue'

const auth = useAuthStore()
const membership = useMembershipStore()
const redeemCode = ref('')
const redeeming = ref(false)

const compareRows = [
  { name: 'Auto 智能对话', regular: true, member: true },
  { name: 'Plan 任务编排', regular: false, member: true },
  { name: 'Multi-Agent 协同', regular: false, member: true },
  { name: '财务审计 / 数据可视化', regular: false, member: true },
  { name: '会员专享知识库', regular: false, member: true },
  { name: '个人 LLM 配置', regular: false, member: true },
]

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('zh-CN')
}

function openUpgrade() {
  if (membership.upgradeUrl) {
    window.open(membership.upgradeUrl, '_blank', 'noopener,noreferrer')
  }
}

async function handleRedeem() {
  const code = redeemCode.value.trim()
  if (!code) {
    ElMessage.warning('请输入兑换码')
    return
  }
  redeeming.value = true
  try {
    const data = await membership.redeem(code)
    ElMessage.success(data.message || '兑换成功')
    redeemCode.value = ''
  } catch (e: any) {
    const msg = e.response?.data?.detail?.message || e.message || '兑换失败'
    ElMessage.error(msg)
  } finally {
    redeeming.value = false
  }
}

onMounted(() => membership.refresh())
</script>

<style scoped>
.membership-layout {
  max-width: 720px;
}

.membership-card {
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

.trial-tag {
  color: #d97706 !important;
  font-weight: 600;
}

.quota-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 8px 0;
}

.quota-item {
  background: rgba(79, 70, 229, 0.06);
  border-radius: 10px;
  padding: 10px 12px;
}

.quota-label {
  display: block;
  font-size: 12px;
  color: var(--ui-text-secondary);
}

.quota-value {
  font-size: 16px;
  font-weight: 700;
}

.perm-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin: 8px 0;
}

.perm-table th,
.perm-table td {
  border-bottom: 1px solid rgba(199, 210, 254, 0.35);
  padding: 8px 6px;
  text-align: left;
}

.plan-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.plan-card {
  border: 1px solid rgba(199, 210, 254, 0.5);
  border-radius: 12px;
  padding: 12px;
}

.plan-card.recommended {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.05);
}

.plan-price {
  font-size: 22px;
  font-weight: 700;
  margin: 4px 0;
}

.plan-duration {
  margin: 0;
  font-size: 12px;
  color: var(--ui-text-secondary);
}

.redeem-section h4 {
  margin: 12px 0 8px;
  font-size: 14px;
}

.redeem-row {
  display: flex;
  gap: 8px;
}

.redeem-input {
  flex: 1;
  border: 1px solid rgba(199, 210, 254, 0.6);
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 14px;
}

.back-link {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
}
</style>
