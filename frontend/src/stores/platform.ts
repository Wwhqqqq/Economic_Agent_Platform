import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchCatalog } from '../api/client'
import { setCatalogLabels } from '../utils/displayLabels'

export interface ExecutionMode {
  key: string
  name: string
  short_name: string
  tagline: string
  description: string
  适用场景?: string[]
}

export const usePlatformStore = defineStore('platform', () => {
  const loaded = ref(false)
  const platformName = ref('企业智能体工作台')
  const productCode = ref('AgentWorkbench')
  const description = ref('')
  const executionModes = ref<ExecutionMode[]>([])

  async function load() {
    if (loaded.value) return
    try {
      const data = await fetchCatalog()
      platformName.value = data.platform?.name || platformName.value
      productCode.value = data.platform?.product_code || productCode.value
      description.value = data.platform?.description || ''
      executionModes.value = data.execution_modes || []
      setCatalogLabels({
        tool_labels: data.tool_labels,
        skill_labels: data.skill_labels,
        provider_labels: data.provider_labels,
      })
      loaded.value = true
    } catch (e) {
      console.error('Failed to load platform catalog', e)
      executionModes.value = [
        { key: 'adaptive', name: '智能路由模式', short_name: '智能路由', tagline: '自动选择引擎', description: '' },
        { key: 'reasoning_action', name: '推理-行动闭环引擎', short_name: '推理闭环', tagline: '工具调用迭代', description: '' },
        { key: 'task_orchestration', name: '任务编排引擎', short_name: '任务编排', tagline: '多步规划执行', description: '' },
        { key: 'collaborative_decision', name: '协同决策引擎', short_name: '协同决策', tagline: '多角色辩论', description: '' },
      ]
    }
  }

  function getModeLabel(key: string): string {
    const m = executionModes.value.find(x => x.key === key)
    return m?.name || key
  }

  return { loaded, platformName, productCode, description, executionModes, load, getModeLabel }
})
