<template>
  <div
    :class="['glass-card', { hoverable, tinted, active }]"
    @click="$emit('click', $event)"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
defineEmits<{ click: [event: MouseEvent] }>()

defineProps<{
  hoverable?: boolean
  tinted?: boolean
  active?: boolean
}>()
</script>

<style scoped>
.glass-card {
  position: relative;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid var(--color-border);
  box-shadow: var(--ui-shadow-sm);
  padding: 18px 22px;
  transition: border-color 0.15s ease;
  font-family: var(--ui-font);
}

.glass-card.tinted {
  background: var(--ui-bg-muted);
}

.glass-card.active {
  border-color: var(--color-primary);
  box-shadow: var(--ui-shadow-glow);
}

.glass-card.hoverable:hover {
  border-color: var(--color-primary);
}
</style>
