import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import { login as apiLogin, fetchMe } from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('auth_token') || '')
  const userId = ref<number | null>(null)
  const username = ref('')
  const userType = ref<'regular' | 'member'>('regular')
  const authEnabled = ref(false)
  const checked = ref(false)

  function syncTokenFromStorage() {
    token.value = localStorage.getItem('auth_token') || ''
  }

  function setToken(value: string) {
    const trimmed = value.trim()
    token.value = trimmed
    if (trimmed) {
      localStorage.setItem('auth_token', trimmed)
    } else {
      localStorage.removeItem('auth_token')
    }
  }

  async function loadAuthConfig() {
    try {
      const { data } = await axios.get('/api/auth/config', { timeout: 5000 })
      authEnabled.value = Boolean(data.auth_enabled)
    } catch {
      authEnabled.value = false
    }
  }

  async function checkAuth() {
    syncTokenFromStorage()
    await loadAuthConfig()
    if (!authEnabled.value) {
      checked.value = true
      return true
    }
    if (!token.value) {
      checked.value = true
      return false
    }
    try {
      const data = await fetchMe()
      userId.value = data.user_id ?? null
      username.value = data.username
      userType.value = data.user_type || 'regular'
      checked.value = true
      return true
    } catch {
      token.value = ''
      localStorage.removeItem('auth_token')
      checked.value = true
      return false
    }
  }

  async function login(user: string, password: string) {
    const data = await apiLogin(user, password)
    if (!data.success) throw new Error(data.message || '登录失败')
    token.value = data.token
    username.value = data.username
    userId.value = data.user_id
    userType.value = data.user_type || 'regular'
    localStorage.setItem('auth_token', data.token)
    return data
  }

  function logout() {
    token.value = ''
    username.value = ''
    userId.value = null
    userType.value = 'regular'
    localStorage.removeItem('auth_token')
  }

  return {
    token,
    userId,
    username,
    userType,
    authEnabled,
    checked,
    checkAuth,
    syncTokenFromStorage,
    setToken,
    login,
    logout,
  }
})
