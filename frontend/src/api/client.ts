import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('auth_token')
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default api

export async function sendVerificationCode(email: string, purpose = 'register') {
  const { data } = await api.post('/auth/send-verification-code', { email, purpose })
  return data
}

export async function register(payload: {
  username: string
  email: string
  password: string
  verification_code: string
}) {
  const { data } = await api.post('/auth/register', payload)
  return data
}

export async function createSession(
  title = '新对话',
  options: { force_new?: boolean; exclude_session_id?: string } = {},
) {
  const { data } = await api.post('/sessions', {
    title,
    force_new: options.force_new ?? false,
    exclude_session_id: options.exclude_session_id ?? null,
  })
  return data
}

export async function login(username: string, password: string) {
  const { data } = await api.post('/auth/login', { username, password })
  return data
}

export async function changePassword(currentPassword: string, newPassword: string) {
  const { data } = await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
  return data
}

export async function sendBindEmailCode(email: string) {
  const { data } = await api.post('/auth/send-bind-email-code', { email })
  return data
}

export async function updateProfile(payload: {
  username?: string
  email?: string
  verification_code?: string
}) {
  const { data } = await api.patch('/auth/profile', payload)
  return data
}

export async function fetchMe() {
  const { data } = await api.get('/auth/me')
  return data
}

export async function fetchSystemStatus() {
  const { data } = await axios.get('/health', { timeout: 10000 })
  return data
}

export async function fetchCatalog() {
  const { data } = await api.get('/catalog')
  return data
}

export async function fetchTools() {
  const { data } = await api.get('/tools')
  return data
}

export async function fetchSkills() {
  const { data } = await api.get('/skills')
  return data
}

export async function fetchInvocableSkills() {
  const { data } = await api.get('/skills/invocable')
  return data
}

export async function fetchExperts() {
  const { data } = await api.get('/experts')
  return data
}

export async function fetchAgents() {
  const { data } = await api.get('/agents')
  return data
}

export async function fetchModels() {
  const { data } = await api.get('/agents/models')
  return data
}

export async function fetchLLMConfig() {
  const { data } = await api.get('/settings/llm')
  return data
}

export async function updateLLMConfig(provider: string, config: Record<string, unknown>) {
  const { data } = await api.put('/settings/llm', { provider, ...config })
  return data
}

export async function setDefaultProvider(provider: string) {
  const { data } = await api.put('/settings/llm/default', { provider })
  return data
}

export async function uploadKnowledge(content: string, metadata?: Record<string, unknown>) {
  const { data } = await api.post('/knowledge/upload', { content, metadata })
  return data
}

export async function uploadKnowledgeMedia(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/knowledge/upload/media', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function uploadKnowledgeFile(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/knowledge/upload/file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function fetchKnowledgeDocuments(limit = 100, offset = 0) {
  const { data } = await api.get('/knowledge/documents', { params: { limit, offset } })
  return data
}

export async function deleteKnowledgeDocument(docId: string) {
  const { data } = await api.delete(`/knowledge/${docId}`)
  return data
}

export async function searchKnowledge(query: string, topK = 5, mode = 'hybrid') {
  const { data } = await api.post('/knowledge/search', { query, top_k: topK, mode })
  return data
}

export async function fetchSessionContext(sessionId: string) {
  const { data } = await api.get(`/sessions/${sessionId}/context`)
  return data
}

export async function summonExpertSession(sessionId: string, expertId: string) {
  const { data } = await api.post(`/sessions/${sessionId}/summon`, { expert_id: expertId })
  return data
}

export async function clearExpertSession(sessionId: string) {
  const { data } = await api.delete(`/sessions/${sessionId}/summon`)
  return data
}

export async function clearSkillSession(sessionId: string) {
  const { data } = await api.delete(`/sessions/${sessionId}/skill`)
  return data
}

export async function clearSessionMessages(sessionId: string) {
  const { data } = await api.post(`/sessions/${sessionId}/clear`)
  return data
}

export async function deleteSession(sessionId: string) {
  const { data } = await api.delete(`/sessions/${sessionId}`)
  return data
}

/** @deprecated 使用 clearSessionMessages 或 deleteSession */
export async function clearSession(sessionId: string) {
  return clearSessionMessages(sessionId)
}

export async function fetchSessions() {
  const { data } = await api.get('/sessions')
  return data
}

export async function renameSession(sessionId: string, title: string) {
  const { data } = await api.patch(`/sessions/${sessionId}`, { title })
  return data
}

export async function fetchSessionMessages(sessionId: string) {
  const { data } = await api.get(`/sessions/${sessionId}/messages`)
  return data
}

export async function executeSkill(
  name: string,
  input: string,
  options: { sessionId?: string; provider?: string; model?: string; temperature?: number } = {}
) {
  const { data } = await api.post(`/skills/${name}/execute`, {
    input,
    session_id: options.sessionId || 'default',
    provider: options.provider,
    model: options.model,
    temperature: options.temperature ?? 0.7,
  })
  return data
}

export async function fetchKnowledgeDocStatus(docId: string) {
  const { data } = await api.get(`/knowledge/documents/${docId}/status`)
  return data
}

export async function fetchKnowledgeStats() {
  const { data } = await api.get('/knowledge/stats')
  return data
}

export async function fetchAuditLogs(limit = 50) {
  const { data } = await api.get('/audit/logs', { params: { limit } })
  return data
}

export async function fetchMembershipStatus() {
  const { data } = await api.get('/membership/status')
  return data
}

export async function fetchMembershipQuota() {
  const { data } = await api.get('/membership/quota')
  return data
}

export async function redeemMembershipCode(code: string) {
  const { data } = await api.post('/membership/redeem', { code })
  return data
}

export async function fetchMemberKnowledgeDocuments(limit = 100, offset = 0) {
  const { data } = await api.get('/knowledge/documents/member', { params: { limit, offset } })
  return data
}

export async function fetchMembershipOrders() {
  const { data } = await api.get('/membership/orders')
  return data
}
