<template>
  <div class="gradient-divider" :style="{ margin: spacing }"></div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ spacing?: string }>(), {
  spacing: '12px 0',
})
</script>

<style scoped>
.gradient-divider {
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    var(--ui-primary) 50%,
    transparent 100%
  );
  opacity: 0.4;
}
</style>
