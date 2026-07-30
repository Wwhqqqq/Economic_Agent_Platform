import { defineStore } from 'pinia'
import { ref } from 'vue'

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
  const skillInvocationSource = ref<'slash' | 'expert' | null>(null)

  function setProvider(provider: string) {
    selectedProvider.value = provider
  }

  function setModel(model: string) {
    selectedModel.value = model
  }

  function setMode(mode: string) {
    selectedMode.value = mode
  }

  function setActiveSkill(skill: string | null, label?: string | null, source?: 'slash' | 'expert' | null) {
    activeSkill.value = skill
    activeSkillLabel.value = label ?? skill
    if (source !== undefined) skillInvocationSource.value = source
  }

  function summonExpert(expert: {
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

  function clearExpert() {
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

  function clearSkill() {
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
    clearExpert()
    clearSkill()
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
    summonExpert,
    clearExpert,
    clearSkill,
    resetSessionContext,
  }
})
