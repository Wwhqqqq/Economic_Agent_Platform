<template>
  <Teleport to="body">
    <div v-if="visible" class="quota-overlay" @click.self="close">
      <div class="quota-dialog">
        <div class="quota-icon-wrap">
          <el-icon :size="28"><WarningFilled /></el-icon>
        </div>
        <h3>{{ title }}</h3>
        <p class="quota-message">{{ message }}</p>
        <p v-if="usageHint" class="quota-usage">{{ usageHint }}</p>
        <ul v-if="tips.length" class="quota-tips">
          <li v-for="item in tips" :key="item">{{ item }}</li>
        </ul>
        <div class="quota-actions">
          <button
            v-if="showManageSessions"
            type="button"
            class="ui-btn-primary"
            @click="emitManage"
          >
            管理历史对话
          </button>
          <button
            v-if="showUpgrade"
            type="button"
            :class="showManageSessions ? 'ui-btn-ghost' : 'ui-btn-primary'"
            @click="goUpgrade"
          >
            升级会员
          </button>
          <button type="button" class="ui-btn-ghost" @click="close">知道了</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { WarningFilled } from '@element-plus/icons-vue'

const emit = defineEmits<{ manageSessions: [] }>()
const router = useRouter()

const visible = ref(false)
const title = ref('已达使用上限')
const message = ref('')
const usageHint = ref('')
const tips = ref<string[]>([])
const showManageSessions = ref(false)
const showUpgrade = ref(true)

function openSessionLimit(options: {
  message?: string
  usageLabel?: string
  reusedExisting?: boolean
}) {
  title.value = options.reusedExisting ? '无法新建对话' : '对话数量已达上限'
  message.value =
    options.message ||
    (options.reusedExisting
      ? '当前账号的对话额度已满，无法创建新的对话条目。您仍可继续在现有对话中交流，或删除旧对话后再试。'
      : '普通用户最多保留一定数量的有记录对话。请删除不再需要的对话，或升级会员提升配额。')
  usageHint.value = options.usageLabel || ''
  tips.value = [
    '在左侧历史对话上右键可删除或导出',
    '仅删除有记录的对话后才会释放额度',
    '会员享有更高对话与消息配额',
  ]
  showManageSessions.value = true
  showUpgrade.value = true
  visible.value = true
}

function openDailyMessageLimit(message?: string, usageLabel?: string) {
  title.value = '今日消息已达上限'
  message.value = message || '普通用户每日可发送的消息数有限，请明天再试或升级会员。'
  usageHint.value = usageLabel || ''
  tips.value = ['额度将在每日 0 点（UTC+8）重置', '会员享有更高每日消息配额']
  showManageSessions.value = false
  showUpgrade.value = true
  visible.value = true
}

function openGeneric(message: string, usageLabel?: string) {
  title.value = '已达使用上限'
  message.value = message
  usageHint.value = usageLabel || ''
  tips.value = []
  showManageSessions.value = false
  showUpgrade.value = true
  visible.value = true
}

function close() {
  visible.value = false
}

function goUpgrade() {
  visible.value = false
  router.push('/membership')
}

function emitManage() {
  visible.value = false
  emit('manageSessions')
}

defineExpose({ openSessionLimit, openDailyMessageLimit, openGeneric, close })
</script>

<style scoped>
.quota-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.quota-dialog {
  width: min(460px, 100%);
  background: var(--ui-card-bg, #fff);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
}

.quota-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #fef3c7;
  color: #d97706;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.quota-dialog h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: var(--ui-text-primary, #1a2e1a);
}

.quota-message {
  margin: 0 0 8px;
  color: var(--ui-text-secondary, #4b5563);
  line-height: 1.65;
  font-size: 14px;
}

.quota-usage {
  margin: 0 0 12px;
  padding: 8px 12px;
  background: #fef9c3;
  border: 1px solid #fde047;
  color: #854d0e;
  font-size: 13px;
  font-weight: 600;
}

.quota-tips {
  margin: 0 0 20px;
  padding-left: 18px;
  line-height: 1.75;
  font-size: 13px;
  color: var(--ui-text-secondary, #6b7280);
}

.quota-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
