<template>
  <div class="page-shell">
    <PageHeader
      title="技能编排"
      subtitle="技能 = 工具组合 + 领域 Prompt + 上下文策略，面向业务场景的一键能力包。"
      breadcrumb="能力中心 / 技能编排"
      :stats="[
        { label: '可用技能', value: skills.length, icon: Aim },
        { label: '当前启用', value: activeCount, icon: CircleCheck },
      ]"
    />

    <div class="page-body">
      <div class="skills-list">
        <GlassCard
          v-for="skill in skills"
          :key="skill.name"
          :active="skill.active"
          :tinted="skill.active"
          class="skill-card"
        >
          <div class="skill-header">
            <div class="skill-icon-wrap">
              <el-icon :size="20"><Aim /></el-icon>
            </div>
            <div class="skill-title">
              <h3>{{ skill.display_name }}</h3>
              <div class="meta">
                <el-tag size="small" type="primary" effect="plain">{{ skill.category_label }}</el-tag>
              </div>
            </div>
            <button v-if="!skill.active" class="ui-btn-ghost activate-btn" @click="activate(skill.name)">
              启用技能
            </button>
            <button v-else class="ui-btn-primary active-btn" @click="deactivate()">
              运行中 ✓
            </button>
          </div>
          <p class="skill-desc">{{ skill.description }}</p>

          <div class="workflow" v-if="skill.workflow?.length">
            <span class="wf-label">执行流程</span>
            <div class="wf-steps">
              <span v-for="(step, i) in skill.workflow" :key="i" class="wf-step">
                <span class="step-num">{{ i + 1 }}</span>{{ step }}
                <span v-if="i < skill.workflow.length - 1" class="arrow">→</span>
              </span>
            </div>
          </div>

          <div class="skill-tools">
            <span class="tools-label">依赖能力</span>
            <el-tag v-for="t in skill.required_tools" :key="t" size="small" effect="plain" round>
              {{ toolLabel(t) }}
            </el-tag>
          </div>

          <GradientDivider spacing="12px 0" />
          <div class="trial-panel">
            <span class="tools-label">技能试跑</span>
            <el-input v-model="trialInputs[skill.name]" type="textarea" :rows="2" placeholder="输入试跑内容..." />
            <button class="ui-btn-primary trial-btn" @click="trialRun(skill.name)">执行试跑</button>
            <pre v-if="trialResults[skill.name]" class="trial-result">{{ trialResults[skill.name] }}</pre>
          </div>
        </GlassCard>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, CircleCheck } from '@element-plus/icons-vue'
import { fetchSkills, activateSkill, deactivateSkill, executeSkill } from '../api/client'
import { useSettingsStore } from '../stores/settings'
import { toolLabel } from '../utils/displayLabels'
import PageHeader from '../components/layout/PageHeader.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import GradientDivider from '../components/ui/GradientDivider.vue'

const settingsStore = useSettingsStore()
const skills = ref<any[]>([])
const trialInputs = reactive<Record<string, string>>({})
const trialResults = reactive<Record<string, string>>({})
const activeCount = computed(() => skills.value.filter(s => s.active).length)

onMounted(async () => { await loadSkills() })

async function loadSkills() {
  try { const data = await fetchSkills(); skills.value = data.skills || [] } catch (e) { console.error(e) }
}
async function activate(name: string) { await activateSkill(name); await loadSkills() }
async function deactivate() { await deactivateSkill(); await loadSkills() }

async function trialRun(name: string) {
  const input = trialInputs[name]
  if (!input?.trim()) return
  try {
    const result = await executeSkill(name, input, {
      provider: settingsStore.selectedProvider,
      model: settingsStore.selectedModel || undefined,
    })
    trialResults[name] = result.output || result.error || '无输出'
    ElMessage.success('试跑完成')
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}
</script>

<style scoped>
.skills-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.skill-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 10px;
}

.skill-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--ui-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--ui-border);
}

.skill-title {
  flex: 1;
}

.skill-title h3 {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 6px;
}

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta code {
  font-size: 10px;
  color: var(--ui-text-secondary);
  background: var(--ui-bg-muted);
  padding: 2px 8px;
  border-radius: 4px;
}

.activate-btn,
.active-btn {
  margin-left: auto;
  white-space: nowrap;
}

.skill-desc {
  font-size: 13px;
  color: var(--ui-text-regular);
  line-height: 1.6;
  margin-bottom: 14px;
}

.wf-label,
.tools-label {
  font-size: 11px;
  color: var(--ui-text-secondary);
  font-weight: 600;
  display: block;
  margin-bottom: 8px;
}

.wf-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 14px;
}

.wf-step {
  font-size: 12px;
  color: var(--ui-text-regular);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.step-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--ui-primary);
  color: #fff;
  font-size: 10px;
  font-weight: bold;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.arrow {
  color: var(--ui-text-secondary);
  margin: 0 4px;
}

.skill-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.skill-tools .tools-label {
  width: 100%;
}

.trial-panel { margin-top: 4px; }
.trial-btn { margin-top: 8px; }
.trial-result {
  margin-top: 10px;
  padding: 10px;
  background: var(--ui-bg-muted);
  border-radius: 8px;
  font-size: 12px;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}
</style>
