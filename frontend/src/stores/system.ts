import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchSystemStatus } from '../api/client'

export const useSystemStore = defineStore('system', () => {
  const status = ref<any>(null)
  const loading = ref(false)

  async function refresh() {
    loading.value = true
    try {
      status.value = await fetchSystemStatus()
    } catch (e) {
      status.value = { status: 'unknown', error: String(e) }
    } finally {
      loading.value = false
    }
  }

  return { status, loading, refresh }
})
