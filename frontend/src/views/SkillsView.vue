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
        <GlassCard
          v-for="skill in skills"
          :key="skill.name"
          hoverable
          class="skill-card"
          :class="{ locked: skill.membership_required && !auth.isMember }"
          @click="onSkillClick(skill)"
        >
          <div class="skill-top">
            <div class="skill-icon-wrap">
              <el-icon :size="18"><Aim /></el-icon>
            </div>
            <div class="skill-head">
              <div class="name-row">
                <h3>{{ skill.display_name }}</h3>
                <code class="slash-chip" @click.stop="copySlash(skill.name)">/{{ skill.name }}</code>
              </div>
              <div class="tag-row">
                <el-tag size="small" type="primary" effect="plain">{{ skill.category_label }}</el-tag>
                <el-tag v-if="skill.membership_required" size="small" type="warning" effect="plain">会员专享</el-tag>
              </div>
            </div>
          </div>
          <p class="skill-desc">{{ skill.description }}</p>
        </GlassCard>
      </div>
    </div>

    <UpgradePrompt ref="upgradePromptRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim } from '@element-plus/icons-vue'
import { fetchSkills } from '../api/client'
import { useAuthStore } from '../stores/auth'
import PageHeader from '../components/layout/PageHeader.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import UpgradePrompt from '../components/ui/UpgradePrompt.vue'

const auth = useAuthStore()
const skills = ref<any[]>([])
const upgradePromptRef = ref<InstanceType<typeof UpgradePrompt> | null>(null)

onMounted(async () => { await loadSkills() })

async function loadSkills() {
  try {
    const data = await fetchSkills()
    skills.value = data.skills || []
  } catch (e) { console.error(e) }
}

function onSkillClick(skill: { name: string; membership_required?: boolean }) {
  if (skill.membership_required && !auth.isMember) {
    upgradePromptRef.value?.open('该技能需开通会员')
    return
  }
  copySlash(skill.name)
}

function copySlash(name: string) {
  navigator.clipboard.writeText(`/${name} `).then(() => {
    ElMessage.success('已复制，请在聊天框粘贴使用')
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

.skill-card.locked {
  opacity: 0.85;
}

.tag-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
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
  cursor: pointer;
}

.skill-top {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}

.skill-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(79, 70, 229, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  flex-shrink: 0;
}

.skill-head { flex: 1; min-width: 0; }

.name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.name-row h3 {
  margin: 0;
  font-size: 15px;
}

.slash-chip {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary);
  cursor: pointer;
}

.skill-desc {
  margin: 0;
  font-size: 13px;
  color: var(--ui-text-secondary);
  line-height: 1.5;
}
</style>
