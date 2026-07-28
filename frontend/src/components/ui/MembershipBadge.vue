<template>
  <span :class="['membership-badge', variant, size]">
    <el-icon v-if="isMember" class="badge-icon"><Medal /></el-icon>
    <el-icon v-else class="badge-icon"><User /></el-icon>
    <span class="badge-text">{{ label }}</span>
    <span v-if="isMember && expiryText" class="badge-expiry">{{ expiryText }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Medal, User } from '@element-plus/icons-vue'
import { formatMembershipExpiry, userTypeShortLabel } from '../../utils/membership'

const props = withDefaults(
  defineProps<{
    isMember: boolean
    membershipExpiresAt?: string | null
    size?: 'sm' | 'md'
    showExpiry?: boolean
  }>(),
  {
    membershipExpiresAt: null,
    size: 'md',
    showExpiry: false,
  },
)

const label = computed(() => userTypeShortLabel(props.isMember))

const variant = computed(() => (props.isMember ? 'member' : 'regular'))

const expiryText = computed(() => {
  if (!props.showExpiry || !props.isMember) return null
  const formatted = formatMembershipExpiry(props.membershipExpiresAt)
  return formatted ? `至 ${formatted}` : null
})
</script>

<style scoped>
.membership-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: var(--ui-radius-pill);
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}

.membership-badge.sm {
  font-size: 11px;
  padding: 3px 9px;
}

.membership-badge.md {
  font-size: 12px;
  padding: 4px 11px;
}

/* 普通用户：浅蓝靛色系 */
.membership-badge.regular {
  background: linear-gradient(135deg, rgba(224, 242, 254, 0.95), rgba(238, 242, 255, 0.9));
  color: #2563eb;
  border: 1px solid rgba(96, 165, 250, 0.45);
}

/* 会员用户：紫色系，与普通用户浅蓝区分 */
.membership-badge.member {
  background: linear-gradient(135deg, rgba(237, 233, 254, 0.95), rgba(221, 214, 254, 0.88));
  color: #7c3aed;
  border: 1px solid rgba(139, 92, 246, 0.5);
  box-shadow: 0 2px 10px rgba(139, 92, 246, 0.18);
}

.badge-icon {
  font-size: 1.05em;
}

.badge-expiry {
  font-weight: 500;
  opacity: 0.88;
  margin-left: 2px;
  font-size: 0.92em;
}

.membership-badge.sm .badge-expiry {
  display: none;
}
</style>
