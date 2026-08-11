import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { login as apiLogin, fetchMe, register as apiRegister, updateProfile as apiUpdateProfile } from '../api/client'
import { resolveIsMember, userTypeLabel, type UserType } from '../utils/membership'
import { loadAvatarUrl, saveAvatarUrl } from '../utils/avatar'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('auth_token') || '')
  const userId = ref<number | null>(null)
  const username = ref('')
  const email = ref<string | null>(null)
  const userType = ref<UserType>('regular')
  const membershipExpiresAt = ref<string | null>(null)
  const createdAt = ref<string | null>(null)
  const lastLoginAt = ref<string | null>(null)
  const avatarUrl = ref<string | null>(null)
  const authEnabled = ref(false)
  const checked = ref(false)

  const isMember = computed(() =>
    resolveIsMember(userType.value, membershipExpiresAt.value),
  )

  const userTypeDisplay = computed(() => userTypeLabel(isMember.value))

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

  function applyUserProfile(data: {
    user_id?: number
    username?: string
    email?: string | null
    user_type?: string
    membership_expires_at?: string | null
    created_at?: string | null
    last_login_at?: string | null
  }) {
    userId.value = data.user_id ?? null
    username.value = data.username ?? ''
    email.value = data.email ?? null
    userType.value = (String(data.user_type || 'regular').trim().toLowerCase() === 'member'
      ? 'member'
      : 'regular') as UserType
    membershipExpiresAt.value = data.membership_expires_at ?? null
    createdAt.value = data.created_at ?? null
    lastLoginAt.value = data.last_login_at ?? null
    if (data.user_id) {
      avatarUrl.value = loadAvatarUrl(data.user_id)
    }
  }

  function setAvatarUrl(value: string | null) {
    avatarUrl.value = value
    saveAvatarUrl(userId.value, value)
  }

  async function updateProfile(payload: {
    username?: string
    email?: string
    verification_code?: string
  }) {
    const data = await apiUpdateProfile(payload)
    if (!data.success) {
      const err = new Error(data.message || '更新失败') as Error & {
        code?: string
        field?: string
      }
      err.code = data.code
      err.field = data.field
      throw err
    }
    applyUserProfile(data)
    if (data.token) {
      setToken(data.token)
    }
    return data
  }

  async function refreshProfile() {
    if (!token.value) return
    try {
      const data = await fetchMe()
      applyUserProfile(data)
    } catch {
      /* keep existing profile on transient errors */
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
      applyUserProfile(data)
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
    applyUserProfile(data)
    localStorage.setItem('auth_token', data.token)
    checked.value = true
    return data
  }

  async function register(payload: {
    username: string
    email: string
    password: string
    verification_code: string
  }) {
    const data = await apiRegister(payload)
    if (!data.success) {
      const err = new Error(data.message || '注册失败') as Error & {
        code?: string
        field?: string
      }
      err.code = data.code
      err.field = data.field
      throw err
    }
    token.value = data.token
    applyUserProfile(data)
    localStorage.setItem('auth_token', data.token)
    checked.value = true
    return data
  }

  function logout() {
    token.value = ''
    username.value = ''
    email.value = null
    userId.value = null
    userType.value = 'regular'
    membershipExpiresAt.value = null
    createdAt.value = null
    lastLoginAt.value = null
    avatarUrl.value = null
    localStorage.removeItem('auth_token')
  }

  return {
    token,
    userId,
    username,
    email,
    userType,
    membershipExpiresAt,
    createdAt,
    lastLoginAt,
    avatarUrl,
    isMember,
    userTypeDisplay,
    authEnabled,
    checked,
    checkAuth,
    refreshProfile,
    syncTokenFromStorage,
    setToken,
    login,
    register,
    updateProfile,
    setAvatarUrl,
    logout,
    applyUserProfile,
  }
})
