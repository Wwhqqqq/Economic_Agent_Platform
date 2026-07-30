<template>
  <div v-if="visible && filtered.length" class="slash-menu" @mousedown.prevent>
    <div class="slash-search">
      <el-icon><Search /></el-icon>
      <span class="slash-hint">搜索技能…</span>
    </div>
    <button
      v-for="(skill, idx) in filtered"
      :key="skill.name"
      type="button"
      :class="['slash-item', { active: idx === activeIndex }]"
      @click="emit('select', skill)"
    >
      <span class="slash-cmd">{{ skill.slash_command }}</span>
      <span class="slash-name">{{ skill.display_name }}</span>
      <span class="slash-desc">{{ skill.description }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'

export interface InvocableSkill {
  name: string
  display_name: string
  slash_command: string
  description: string
  category_label?: string
}

const props = defineProps<{
  visible: boolean
  query: string
  skills: InvocableSkill[]
}>()

const emit = defineEmits<{
  select: [skill: InvocableSkill]
  close: []
}>()

const activeIndex = ref(0)

const filtered = computed(() => {
  const q = props.query.toLowerCase()
  if (!q) return props.skills
  return props.skills.filter(s =>
    s.name.includes(q) ||
    s.display_name.toLowerCase().includes(q) ||
    (s.description || '').toLowerCase().includes(q)
  )
})

watch(() => props.query, () => { activeIndex.value = 0 })
watch(filtered, () => { activeIndex.value = 0 })

function move(delta: number) {
  if (!filtered.value.length) return
  activeIndex.value = (activeIndex.value + delta + filtered.value.length) % filtered.value.length
}

function confirm() {
  const item = filtered.value[activeIndex.value]
  if (item) emit('select', item)
}

defineExpose({ move, confirm, filtered })
</script>

<style scoped>
.slash-menu {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 8px);
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(199, 210, 254, 0.55);
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(99, 102, 241, 0.15);
  max-height: 240px;
  overflow-y: auto;
  z-index: 20;
  padding: 6px;
}

.slash-search {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--ui-text-secondary);
  border-bottom: 1px solid rgba(199, 210, 254, 0.35);
  margin-bottom: 4px;
}

.slash-item {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  gap: 2px 10px;
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
}

.slash-item:hover,
.slash-item.active {
  background: rgba(238, 242, 255, 0.9);
}

.slash-cmd {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  grid-row: span 2;
  align-self: center;
}

.slash-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ui-text-primary);
}

.slash-desc {
  font-size: 11px;
  color: var(--ui-text-secondary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
