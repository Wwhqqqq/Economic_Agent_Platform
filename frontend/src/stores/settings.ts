import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  const selectedProvider = ref('deepseek')
  const selectedModel = ref('')
  const selectedMode = ref('adaptive')
  const activeSkill = ref<string | null>(null)

  function setProvider(provider: string) {
    selectedProvider.value = provider
  }

  function setModel(model: string) {
    selectedModel.value = model
  }

  function setMode(mode: string) {
    selectedMode.value = mode
  }

  function setActiveSkill(skill: string | null) {
    activeSkill.value = skill
  }

  return {
    selectedProvider,
    selectedModel,
    selectedMode,
    activeSkill,
    setProvider,
    setModel,
    setMode,
    setActiveSkill,
  }
})
