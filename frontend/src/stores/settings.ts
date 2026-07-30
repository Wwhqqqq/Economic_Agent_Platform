import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchSessionContext,
  summonExpertSession,
  clearExpertSession,
  clearSkillSession,
} from '../api/client'

export const useSettingsStore = defineStore('settings', () => {
  const selectedProvider = ref('deepseek')
  const selectedModel = ref('')
  const selectedMode = ref('adaptive')
  const activeSkill = ref<string | null>(null)
  const activeSkillLabel = ref<string | null>(null)
  const activeExpertId = ref<string | null>(null)
  const activeExpertName = ref<string | null>(null)
  const expertDefaultSkill = ref<string | null>(null)
  const expertDefaultSkillLabel = ref<string | null>(null)
  const skillInvocationSource = ref<'slash' | 'expert' | 'explicit' | null>(null)

  function setProvider(provider: string) {
    selectedProvider.value = provider
  }

  function setModel(model: string) {
    selectedModel.value = model
  }

  function setMode(mode: string) {
    selectedMode.value = mode
  }

  function setActiveSkill(
    skill: string | null,
    label?: string | null,
    source?: 'slash' | 'expert' | 'explicit' | null,
  ) {
    activeSkill.value = skill
    activeSkillLabel.value = label ?? skill
    if (source !== undefined) skillInvocationSource.value = source
  }

  function applyContext(ctx: any) {
    activeExpertId.value = ctx.expert_id ?? null
    activeExpertName.value = ctx.expert_name ?? null
    activeSkill.value = ctx.active_skill ?? null
    activeSkillLabel.value = ctx.active_skill_label ?? ctx.active_skill ?? null
    skillInvocationSource.value = ctx.skill_invocation ?? null
    const defaultSkill = ctx.expert_default_skill
    expertDefaultSkill.value = defaultSkill?.name ?? null
    expertDefaultSkillLabel.value = defaultSkill?.display_name ?? null
    if (ctx.mode) selectedMode.value = ctx.mode
  }

  async function syncFromBackend(sessionId: string) {
    try {
      const ctx = await fetchSessionContext(sessionId)
      applyContext(ctx)
    } catch (e) {
      console.error('[Settings] sync context failed', e)
    }
  }

  function summonExpertLocal(expert: {
    id: string
    name: string
    equipped_skills?: { name: string; display_name: string }[]
  }) {
    activeExpertId.value = expert.id
    activeExpertName.value = expert.name
    const defaultSkill = expert.equipped_skills?.[0]
    expertDefaultSkill.value = defaultSkill?.name ?? null
    expertDefaultSkillLabel.value = defaultSkill?.display_name ?? null
    if (defaultSkill) {
      activeSkill.value = defaultSkill.name
      activeSkillLabel.value = defaultSkill.display_name
      skillInvocationSource.value = 'expert'
    }
  }

  async function summonExpert(
    expert: {
      id: string
      name: string
      equipped_skills?: { name: string; display_name: string }[]
    },
    sessionId?: string,
  ) {
    summonExpertLocal(expert)
    if (sessionId) {
      try {
        const ctx = await summonExpertSession(sessionId, expert.id)
        applyContext(ctx)
      } catch (e) {
        console.error('[Settings] summon API failed', e)
      }
    }
  }

  async function clearExpert(sessionId?: string) {
    if (sessionId) {
      try {
        const ctx = await clearExpertSession(sessionId)
        applyContext(ctx)
        return
      } catch (e) {
        console.error('[Settings] clear expert API failed', e)
      }
    }
    activeExpertId.value = null
    activeExpertName.value = null
    expertDefaultSkill.value = null
    expertDefaultSkillLabel.value = null
    if (skillInvocationSource.value === 'expert') {
      activeSkill.value = null
      activeSkillLabel.value = null
      skillInvocationSource.value = null
    }
  }

  async function clearSkill(sessionId?: string) {
    if (sessionId) {
      try {
        const ctx = await clearSkillSession(sessionId)
        applyContext(ctx)
        return
      } catch (e) {
        console.error('[Settings] clear skill API failed', e)
      }
    }
    if (activeExpertId.value && expertDefaultSkill.value) {
      activeSkill.value = expertDefaultSkill.value
      activeSkillLabel.value = expertDefaultSkillLabel.value
      skillInvocationSource.value = 'expert'
    } else {
      activeSkill.value = null
      activeSkillLabel.value = null
      skillInvocationSource.value = null
    }
  }

  function resetSessionContext() {
    activeExpertId.value = null
    activeExpertName.value = null
    expertDefaultSkill.value = null
    expertDefaultSkillLabel.value = null
    activeSkill.value = null
    activeSkillLabel.value = null
    skillInvocationSource.value = null
    selectedMode.value = 'adaptive'
  }

  return {
    selectedProvider,
    selectedModel,
    selectedMode,
    activeSkill,
    activeSkillLabel,
    activeExpertId,
    activeExpertName,
    skillInvocationSource,
    setProvider,
    setModel,
    setMode,
    setActiveSkill,
    applyContext,
    syncFromBackend,
    summonExpert,
    clearExpert,
    clearSkill,
    resetSessionContext,
  }
})
