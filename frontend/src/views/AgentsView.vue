<template>
  <div class="page-shell">
    <PageHeader
      title="智能体档案"
      subtitle="平台内置的执行单元与协同决策团队，每种智能体绑定特定的执行引擎与能力边界。"
      breadcrumb="能力中心 / 智能体档案"
      :stats="[
        { label: '智能体单元', value: agents.length, icon: User },
        { label: '执行引擎', value: executionModes.length, icon: Lightning },
      ]"
    />

    <div class="page-body">
      <section class="section">
        <h3 class="section-title">执行引擎</h3>
        <div class="modes-grid">
          <GlassCard v-for="mode in executionModes" :key="mode.key" hoverable tinted class="mode-card">
            <div class="mode-name">{{ mode.name }}</div>
            <div class="mode-tagline">{{ mode.tagline }}</div>
            <p>{{ mode.description }}</p>
            <div class="scenarios" v-if="mode.适用场景?.length">
              <el-tag v-for="s in mode.适用场景" :key="s" size="small" effect="plain" round>{{ s }}</el-tag>
            </div>
          </GlassCard>
        </div>
      </section>

      <GradientDivider spacing="8px 0 20px" />

      <section class="section">
        <h3 class="section-title">智能体单元</h3>
        <div class="agents-grid">
          <GlassCard v-for="agent in agents" :key="agent.key" hoverable class="agent-card">
            <el-tag size="small" type="primary" effect="dark" round class="agent-badge">
              {{ getModeName(agent.execution_mode) }}
            </el-tag>
            <h3>{{ agent.name }}</h3>
            <div class="role">{{ agent.role }}</div>
            <p>{{ agent.description }}</p>
            <div class="capabilities">
              <el-tag v-for="c in agent.capabilities" :key="c" size="small" type="primary" effect="plain" round>
                {{ c }}
              </el-tag>
            </div>
            <div v-if="agent.members" class="members">
              <div class="members-title">委员会成员</div>
              <div v-for="m in agent.members" :key="m.role" class="member">
                <strong>{{ m.role }}</strong> — {{ m.职责 }}
              </div>
            </div>
          </GlassCard>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { User, Lightning } from '@element-plus/icons-vue'
import { fetchAgents } from '../api/client'
import PageHeader from '../components/layout/PageHeader.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import GradientDivider from '../components/ui/GradientDivider.vue'

const agents = ref<any[]>([])
const executionModes = ref<any[]>([])

function getModeName(key: string) {
  return executionModes.value.find(m => m.key === key)?.short_name || key
}

onMounted(async () => {
  try {
    const data = await fetchAgents()
    agents.value = data.agents || []
    executionModes.value = data.execution_modes || []
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.section {
  margin-bottom: 8px;
}

.modes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.mode-card .mode-name {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 4px;
}

.mode-tagline {
  font-size: 12px;
  color: var(--ui-primary);
  margin-bottom: 8px;
  font-weight: 500;
}

.mode-card p {
  font-size: 12px;
  color: var(--ui-text-regular);
  line-height: 1.55;
  margin-bottom: 10px;
}

.scenarios {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}

.agent-badge {
  margin-bottom: 10px;
}

.agent-card h3 {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 4px;
}

.role {
  font-size: 12px;
  color: var(--ui-text-secondary);
  margin-bottom: 10px;
}

.agent-card p {
  font-size: 13px;
  color: var(--ui-text-regular);
  line-height: 1.6;
  margin-bottom: 12px;
}

.capabilities {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.members {
  border-top: 1px solid var(--ui-border);
  padding-top: 12px;
  margin-top: 4px;
}

.members-title {
  font-size: 11px;
  color: var(--ui-text-secondary);
  font-weight: 600;
  margin-bottom: 6px;
}

.member {
  font-size: 12px;
  color: var(--ui-text-regular);
  margin-bottom: 4px;
}

.member strong {
  color: var(--ui-text-primary);
}
</style>
