<template>
  <header class="page-header">
    <div class="header-accent" aria-hidden="true"></div>
    <div class="breadcrumb" v-if="breadcrumb">
      <el-icon><Location /></el-icon>
      {{ breadcrumb }}
    </div>
    <div class="header-main">
      <div class="title-block">
        <h1 class="section-title page-title">{{ title }}</h1>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>
      <div class="header-extra" v-if="$slots.extra">
        <slot name="extra" />
      </div>
    </div>
    <div class="stats-row" v-if="stats && stats.length">
      <StatChip
        v-for="(s, i) in stats"
        :key="i"
        :label="s.label"
        :value="s.value"
        :icon="s.icon"
        :variant="i % 3"
      />
    </div>
  </header>
</template>

<script setup lang="ts">
import { Location } from '@element-plus/icons-vue'
import StatChip from '../ui/StatChip.vue'

defineProps<{
  title: string
  subtitle?: string
  breadcrumb?: string
  stats?: { label: string; value: string | number; icon?: import('vue').Component }[]
}>()
</script>

<style scoped>
.page-header {
  position: relative;
  padding: 18px 24px 14px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(199, 210, 254, 0.4);
  overflow: hidden;
}

.header-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-accent);
  opacity: 0.7;
}

.breadcrumb {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-violet);
  margin-bottom: 8px;
  padding: 4px 12px;
  background: rgba(245, 243, 255, 0.85);
  border: 1px solid rgba(199, 210, 254, 0.45);
  border-radius: 20px;
}

.header-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-title {
  margin-bottom: 6px;
  font-size: 20px;
  background: linear-gradient(135deg, #1E1B4B 0%, #4F46E5 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-block p {
  font-size: 14px;
  color: var(--ui-text-regular);
  max-width: 640px;
  line-height: 1.6;
  padding-left: 14px;
}

.stats-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}
</style>
