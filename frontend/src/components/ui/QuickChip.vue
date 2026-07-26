<template>
  <button type="button" class="quick-chip" @click="$emit('click')">
    <span v-if="icon" class="chip-icon-wrap">
      <el-icon class="chip-icon"><component :is="icon" /></el-icon>
    </span>
    <span>{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  label: string
  icon?: Component
}>()

defineEmits<{ click: [] }>()
</script>

<style scoped>
.quick-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(199, 210, 254, 0.5);
  border-radius: 20px;
  color: var(--ui-text-regular);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.22s ease;
  font-family: var(--ui-font);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.06);
}

.quick-chip:hover {
  background: linear-gradient(135deg, rgba(238,242,255,0.95), rgba(236,254,255,0.8));
  border-color: rgba(129, 140, 248, 0.55);
  color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.15);
}

.chip-icon-wrap {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: var(--gradient-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chip-icon {
  font-size: 13px;
}
</style>
