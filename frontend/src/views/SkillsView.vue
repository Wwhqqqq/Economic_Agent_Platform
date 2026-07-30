<template>
  <div class="page-shell">
    <PageHeader
      title="技能库"
      subtitle="在对话中输入 / 召唤技能"
      breadcrumb="能力中心 / 技能库"
      :stats="[{ label: '可用技能', value: skills.length, icon: Aim }]"
    />

    <div class="page-body">
      <div class="skills-grid">
        <GlassCard v-for="skill in skills" :key="skill.name" hoverable class="skill-card">
          <div class="skill-top">
            <div class="skill-icon-wrap">
              <el-icon :size="18"><Aim /></el-icon>
            </div>
            <div class="skill-head">
              <div class="name-row">
                <h3>{{ skill.display_name }}</h3>
                <code class="slash-chip" @click="copySlash(skill.name)">/{{ skill.name }}</code>
              </div>
              <el-tag size="small" type="primary" effect="plain">{{ skill.category_label }}</el-tag>
            </div>
          </div>
          <p class="skill-desc">{{ skill.description }}</p>
        </GlassCard>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim } from '@element-plus/icons-vue'
import { fetchSkills } from '../api/client'
import PageHeader from '../components/layout/PageHeader.vue'
import GlassCard from '../components/ui/GlassCard.vue'

const skills = ref<any[]>([])

onMounted(async () => { await loadSkills() })

async function loadSkills() {
  try {
    const data = await fetchSkills()
    skills.value = data.skills || []
  } catch (e) { console.error(e) }
}

function copySlash(name: string) {
  navigator.clipboard.writeText(`/${name} `).then(() => {
    ElMessage.success('已复制')
  }).catch(() => {
    ElMessage.info(`请在聊天框输入 /${name}`)
  })
}
</script>

<style scoped>
.skills-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

@media (max-width: 1100px) {
  .skills-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .skills-grid { grid-template-columns: 1fr; }
}

.skill-card {
  padding: 14px 16px !important;
  min-height: 120px;
}

.skill-top {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 8px;
}

.skill-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: var(--ui-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--ui-border);
}

.skill-head {
  flex: 1;
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.name-row h3 {
  font-size: 15px;
  font-weight: 700;
  margin: 0;
  color: var(--ui-text-primary);
}

.slash-chip {
  font-size: 11px;
  font-weight: 600;
  font-family: ui-monospace, monospace;
  color: var(--color-primary);
  background: rgba(238, 242, 255, 0.95);
  border: 1px solid rgba(199, 210, 254, 0.55);
  padding: 2px 8px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}

.slash-chip:hover {
  background: rgba(224, 231, 255, 0.95);
}

.skill-desc {
  font-size: 12px;
  color: var(--ui-text-regular);
  line-height: 1.55;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
