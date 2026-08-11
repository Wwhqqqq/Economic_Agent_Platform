<template>
  <Teleport to="body">
    <div v-if="visible" class="upgrade-overlay" @click.self="close">
      <div class="upgrade-dialog">
        <h3>{{ title }}</h3>
        <p class="upgrade-message">{{ message }}</p>
        <ul class="upgrade-benefits">
          <li v-for="item in benefits" :key="item">{{ item }}</li>
        </ul>
        <div class="upgrade-actions">
          <button type="button" class="ui-btn-primary" @click="goUpgrade">立即升级</button>
          <button type="button" class="ui-btn-ghost" @click="close">稍后再说</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const visible = ref(false)
const title = ref('该功能需要会员')
const message = ref('Plan 任务编排、Multi-Agent 协同、财务审计技能等专业能力需开通会员。')

const benefits = [
  'Plan 任务编排与 Multi-Agent 协同',
  '财务审计 / 数据可视化技能',
  '会员专享知识库检索',
  '个人 LLM 配置与更高配额',
]

function open(customMessage?: string) {
  if (customMessage) message.value = customMessage
  visible.value = true
}

function close() {
  visible.value = false
}

function goUpgrade() {
  visible.value = false
  router.push('/membership')
}

defineExpose({ open, close })
</script>

<style scoped>
.upgrade-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.upgrade-dialog {
  width: min(440px, 100%);
  background: var(--ui-card-bg, #fff);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
}

.upgrade-dialog h3 {
  margin: 0 0 8px;
  font-size: 18px;
}

.upgrade-message {
  margin: 0 0 12px;
  color: var(--ui-text-secondary);
  line-height: 1.6;
  font-size: 14px;
}

.upgrade-benefits {
  margin: 0 0 20px;
  padding-left: 18px;
  line-height: 1.8;
  font-size: 14px;
}

.upgrade-actions {
  display: flex;
  gap: 10px;
}
</style>
