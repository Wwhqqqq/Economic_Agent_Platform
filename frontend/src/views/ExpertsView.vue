<template>
  <div class="page-shell">
    <PageHeader
      title="专家中心"
      subtitle="按领域挑选专家或专家团，一键召唤进入对话"
      breadcrumb="能力中心 / 专家中心"
      :stats="[
        { label: '领域专家', value: experts.length, icon: User },
        { label: '专家团', value: teams.length, icon: UserFilled },
      ]"
    />

    <div class="page-body">
      <div class="tab-row">
        <button :class="['tab-btn', { active: tab === 'experts' }]" @click="tab = 'experts'">专家</button>
        <button :class="['tab-btn', { active: tab === 'teams' }]" @click="tab = 'teams'">专家团</button>
      </div>

      <section v-if="tab === 'experts'" class="card-grid">
        <GlassCard v-for="expert in experts" :key="expert.id" hoverable class="expert-card">
          <div class="card-body">
            <div class="card-head">
              <div class="avatar">{{ expert.name.charAt(0) }}</div>
              <div>
                <h3>{{ expert.name }}</h3>
                <div class="title">{{ expert.title }}</div>
              </div>
            </div>
            <p class="tagline">{{ expert.tagline }}</p>
            <div class="tags">
              <el-tag v-for="d in expert.domains" :key="d" size="small" effect="plain" round>{{ d }}</el-tag>
            </div>
            <div v-if="expert.example_tasks?.length" class="examples">
              <span class="ex-label">任务示例</span>
              <button
                v-for="(ex, i) in expert.example_tasks"
                :key="i"
                class="example-btn"
                @click="summonWithPrompt(expert, ex.prompt)"
              >
                {{ ex.label }}
              </button>
            </div>
          </div>
          <button class="ui-btn-primary summon-btn" @click="summon(expert)">召唤专家</button>
        </GlassCard>
      </section>

      <section v-else class="card-grid">
        <GlassCard v-for="team in teams" :key="team.id" hoverable tinted class="team-card">
          <div class="card-body">
            <div class="card-head">
              <div class="avatar team">团</div>
              <div>
                <h3>{{ team.name }}</h3>
                <div class="title">多角色协作评审</div>
              </div>
            </div>
            <p class="tagline">{{ team.tagline }}</p>
            <div class="tags">
              <el-tag v-for="d in team.domains" :key="d" size="small" effect="plain" round>{{ d }}</el-tag>
            </div>
            <div v-if="team.members?.length" class="members">
              <div v-for="m in team.members" :key="m.role" class="member-row">
                <strong>{{ m.role }}</strong> — {{ m.stance }}
              </div>
            </div>
            <div v-if="team.example_tasks?.length" class="examples">
              <span class="ex-label">任务示例</span>
              <button
                v-for="(ex, i) in team.example_tasks"
                :key="i"
                class="example-btn"
                @click="summonWithPrompt(team, ex.prompt)"
              >
                {{ ex.label }}
              </button>
            </div>
            <p class="team-hint">多角色协作，耗时通常高于单专家</p>
          </div>
          <button class="ui-btn-primary summon-btn" @click="summon(team)">召唤专家团</button>
        </GlassCard>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { User, UserFilled } from '@element-plus/icons-vue'
import { fetchExperts } from '../api/client'
import { useSettingsStore } from '../stores/settings'
import PageHeader from '../components/layout/PageHeader.vue'
import GlassCard from '../components/ui/GlassCard.vue'

const router = useRouter()
const settingsStore = useSettingsStore()
const experts = ref<any[]>([])
const teams = ref<any[]>([])
const tab = ref<'experts' | 'teams'>('experts')

onMounted(async () => {
  try {
    const data = await fetchExperts()
    experts.value = data.experts || []
    teams.value = data.teams || []
  } catch (e) { console.error(e) }
})

function summon(profile: any) {
  settingsStore.summonExpert(profile)
  router.push({ path: '/', query: { summon: profile.id } })
}

function summonWithPrompt(profile: any, prompt: string) {
  settingsStore.summonExpert(profile)
  router.push({ path: '/', query: { summon: profile.id, prompt } })
}
</script>

<style scoped>
.tab-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab-btn {
  padding: 8px 18px;
  border-radius: 999px;
  border: 1px solid var(--ui-border);
  background: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  font-size: 13px;
  color: var(--ui-text-regular);
}

.tab-btn.active {
  background: var(--gradient-primary);
  color: #fff;
  border-color: transparent;
}

.expert-card,
.team-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
  align-items: stretch;
}

.card-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 10px;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--gradient-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}

.avatar.team {
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
}

.card-head h3 {
  margin: 0 0 4px;
  font-size: 16px;
}

.title {
  font-size: 12px;
  color: var(--ui-text-secondary);
}

.tagline {
  font-size: 13px;
  color: var(--ui-text-regular);
  line-height: 1.55;
  margin-bottom: 10px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.examples {
  margin-bottom: 0;
  flex: 1;
}

.members {
  border-top: 1px solid var(--ui-border);
  padding-top: 10px;
  margin-bottom: 10px;
}

.member-row {
  font-size: 12px;
  color: var(--ui-text-regular);
  margin-bottom: 4px;
}

.flow {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.flow-step {
  font-size: 12px;
  color: var(--ui-text-secondary);
}

.examples {
  margin-bottom: 12px;
}

.ex-label {
  display: block;
  font-size: 11px;
  color: var(--ui-text-secondary);
  font-weight: 600;
  margin-bottom: 6px;
}

.example-btn {
  display: block;
  width: 100%;
  text-align: left;
  padding: 6px 10px;
  margin-bottom: 4px;
  border-radius: 8px;
  border: 1px solid var(--ui-border);
  background: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  cursor: pointer;
  color: var(--ui-text-primary);
}

.example-btn:hover {
  border-color: rgba(99, 102, 241, 0.45);
  background: rgba(238, 242, 255, 0.8);
}

.team-hint {
  font-size: 11px;
  color: var(--ui-text-secondary);
  margin-bottom: 10px;
}

.summon-btn {
  width: 100%;
  margin-top: 14px;
  flex-shrink: 0;
}
</style>
