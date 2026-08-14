import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchMembershipStatus,
  fetchMembershipQuota,
  redeemMembershipCode,
} from '../api/client'
import { useAuthStore } from './auth'

export interface QuotaItem {
  used: number
  limit: number | null
  resets_at?: string
}

export interface MembershipPlan {
  id: string
  name: string
  price_cents: number
  duration_days: number
  recommended?: boolean
}

export const useMembershipStore = defineStore('membership', () => {
  const loaded = ref(false)
  const isTrial = ref(false)
  const daysRemaining = ref<number | null>(null)
  const upgradeUrl = ref<string | null>(null)
  const plans = ref<MembershipPlan[]>([])
  const benefits = ref<Record<string, unknown>>({})
  const quota = ref<{
    sessions?: QuotaItem
    documents?: QuotaItem
    daily_messages?: QuotaItem
    long_term_memories?: QuotaItem
    max_file_mb?: number
  } | null>(null)

  const authStore = useAuthStore()

  const quotaSessionsLabel = computed(() => {
    const q = quota.value?.sessions
    if (!q) return '—'
    return `${q.used} / ${q.limit ?? '∞'}`
  })

  const quotaDocumentsLabel = computed(() => {
    const q = quota.value?.documents
    if (!q) return '—'
    return `${q.used} / ${q.limit ?? '∞'}`
  })

  const sessionsQuota = computed(() => quota.value?.sessions ?? null)

  const sessionsAtLimit = computed(() => {
    const q = sessionsQuota.value
    if (!q || q.limit == null) return false
    return q.used >= q.limit
  })

  const sessionsNearLimit = computed(() => {
    const q = sessionsQuota.value
    if (!q || q.limit == null) return false
    return q.used >= Math.max(1, q.limit - 2)
  })

  const sessionsUsageLabel = computed(() => {
    const q = sessionsQuota.value
    if (!q || q.limit == null) return ''
    return `对话额度 ${q.used} / ${q.limit}`
  })

  const dailyMessagesUsageLabel = computed(() => {
    const q = quota.value?.daily_messages
    if (!q || q.limit == null) return ''
    return `今日消息 ${q.used} / ${q.limit}`
  })

  async function refresh() {
    if (!authStore.token) {
      loaded.value = true
      return
    }
    try {
      const [status, quotaData] = await Promise.all([
        fetchMembershipStatus(),
        fetchMembershipQuota(),
      ])
      authStore.applyUserProfile({
        user_type: status.user_type,
        membership_expires_at: status.membership_expires_at,
      })
      isTrial.value = Boolean(status.is_trial)
      daysRemaining.value = status.days_remaining ?? null
      upgradeUrl.value = status.upgrade_url ?? null
      plans.value = status.plans || []
      benefits.value = status.benefits || {}
      quota.value = quotaData
      loaded.value = true
    } catch (e) {
      console.error('[Membership] refresh failed', e)
      loaded.value = true
    }
  }

  async function redeem(code: string) {
    const data = await redeemMembershipCode(code)
    authStore.applyUserProfile({
      user_type: 'member',
      membership_expires_at: data.membership_expires_at,
    })
    await refresh()
    return data
  }

  return {
    loaded,
    isTrial,
    daysRemaining,
    upgradeUrl,
    plans,
    benefits,
    quota,
    quotaSessionsLabel,
    quotaDocumentsLabel,
    sessionsQuota,
    sessionsAtLimit,
    sessionsNearLimit,
    sessionsUsageLabel,
    dailyMessagesUsageLabel,
    refresh,
    redeem,
  }
})
