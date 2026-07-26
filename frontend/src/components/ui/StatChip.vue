<template>
  <div class="stat-chip" :class="`variant-${variant ?? 0}`">
    <div class="stat-icon" v-if="icon">
      <el-icon><component :is="icon" /></el-icon>
    </div>
    <div class="stat-body">
      <div class="stat-value">{{ value }}</div>
      <div class="stat-label">{{ label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  label: string
  value: string | number
  icon?: Component
  variant?: number
}>()
</script>

<style scoped>
.stat-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(199, 210, 254, 0.45);
  border-radius: 12px;
  padding: 10px 16px;
  min-width: 110px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-chip:hover {
  transform: translateY(-2px);
  box-shadow: var(--ui-shadow-md);
}

.stat-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
  color: #fff;
}

.variant-0 .stat-icon { background: linear-gradient(135deg, #818CF8, #6366F1); }
.variant-1 .stat-icon { background: linear-gradient(135deg, #A78BFA, #8B5CF6); }
.variant-2 .stat-icon { background: linear-gradient(135deg, #22D3EE, #06B6D4); }

.stat-value {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.2;
}

.variant-0 .stat-value { color: #4F46E5; }
.variant-1 .stat-value { color: #7C3AED; }
.variant-2 .stat-value { color: #0891B2; }

.stat-label {
  font-size: 11px;
  color: var(--ui-text-secondary);
  margin-top: 2px;
}
</style>
