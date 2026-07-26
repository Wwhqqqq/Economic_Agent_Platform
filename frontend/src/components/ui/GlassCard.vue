<template>
  <div
    :class="['glass-card', { hoverable, tinted, active }]"
    @click="$emit('click', $event)"
  >
    <div class="card-shine" aria-hidden="true"></div>
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
  background: var(--gradient-card-shine);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(199, 210, 254, 0.55);
  border-radius: var(--ui-radius-card);
  box-shadow: var(--ui-shadow-md);
  padding: 18px 22px;
  transition: all 0.28s ease;
  font-family: var(--ui-font);
}

.card-shine {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-accent);
  opacity: 0.55;
  border-radius: var(--ui-radius-card) var(--ui-radius-card) 0 0;
}

.glass-card.tinted {
  background: linear-gradient(145deg, rgba(255,255,255,0.92) 0%, rgba(238,242,255,0.85) 60%, rgba(236,254,255,0.7) 100%);
}

.glass-card.active {
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: var(--ui-shadow-glow);
}

.glass-card.active .card-shine {
  opacity: 1;
}

.glass-card.hoverable:hover {
  transform: translateY(-3px);
  box-shadow: var(--ui-shadow-glow);
  border-color: rgba(129, 140, 248, 0.55);
}

.glass-card.hoverable:hover .card-shine {
  opacity: 0.85;
}
</style>
