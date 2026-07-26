import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as apiLogin, fetchMe } from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('auth_token') || '')
  const username = ref('')
  const authEnabled = ref(false)
  const checked = ref(false)

  async function checkAuth() {
    try {
      const data = await fetchMe()
      authEnabled.value = data.auth_enabled
      username.value = data.username
      checked.value = true
      return true
    } catch {
      checked.value = true
      return false
    }
  }

  async function login(user: string, password: string) {
    const data = await apiLogin(user, password)
    if (!data.success) throw new Error(data.message || '登录失败')
    token.value = data.token
    username.value = data.username
    localStorage.setItem('auth_token', data.token)
    return data
  }

  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem('auth_token')
  }

  return { token, username, authEnabled, checked, checkAuth, login, logout }
})
