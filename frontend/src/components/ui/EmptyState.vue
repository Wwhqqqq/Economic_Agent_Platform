<template>
  <div class="empty-state">
    <div class="empty-icon-wrap">
      <div class="icon-ring" aria-hidden="true"></div>
      <slot name="icon">
        <el-icon :size="28" color="#6366F1"><Star /></el-icon>
      </slot>
    </div>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.actions" class="empty-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Star } from '@element-plus/icons-vue'

defineProps<{
  title: string
  description?: string
}>()
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 24px;
  gap: 10px;
}

.empty-icon-wrap {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(238,242,255,0.8));
  border: 1px solid rgba(199, 210, 254, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
  box-shadow: 0 8px 28px rgba(99, 102, 241, 0.15);
}

.icon-ring {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid transparent;
  background: linear-gradient(135deg, #818CF8, #06B6D4, #F472B6) border-box;
  -webkit-mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.6;
  animation: ring-spin 8s linear infinite;
}

@keyframes ring-spin {
  to { transform: rotate(360deg); }
}

.empty-state h3 {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #1E1B4B, #6366F1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.empty-state p {
  font-size: 14px;
  color: var(--ui-text-secondary);
  max-width: 420px;
  line-height: 1.6;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 12px;
}
</style>
