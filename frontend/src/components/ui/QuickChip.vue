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
  background: var(--chip-bg);
  backdrop-filter: blur(8px);
  border: 1px solid var(--chip-border);
  border-radius: 20px;
  color: var(--btn-ghost-color);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.22s ease;
  font-family: var(--ui-font);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.quick-chip:hover {
  background: var(--chip-hover-bg);
  border-color: var(--chip-hover-border);
  color: var(--chip-hover-color);
  transform: translateY(-2px);
  box-shadow: var(--chip-hover-shadow);
}

.chip-icon-wrap {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: var(--btn-primary-bg);
  color: var(--btn-primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
}

.chip-icon {
  font-size: 13px;
}
</style>
