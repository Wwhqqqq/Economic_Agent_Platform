import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ChatWebSocket } from '../api/websocket'
import { clearSession, fetchSessions, fetchSessionMessages, renameSession, createSession as apiCreateSession } from '../api/client'

export interface Citation {
  doc_id: string
  title: string
  score: number
  snippet: string
  source: string
}

export interface StepItem {
  title: string
  content: string
  status?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  tool_calls?: { tool: string; result: string }[]
  citations?: Citation[]
  steps?: StepItem[]
  tokens_used?: number
  timestamp: number
  isStreaming?: boolean
  thinking?: boolean
}

export interface SessionItem {
  session_id: string
  title: string
  message_count: number
  updated_at: string
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const sessions = ref<SessionItem[]>([])
  const isLoading = ref(false)
  const ws = ref<ChatWebSocket | null>(null)
  const sessionId = ref('session_' + Date.now())
  const membershipRequiredMessage = ref<string | null>(null)

  function connect() {
    if (ws.value) ws.value.disconnect()
    ws.value = new ChatWebSocket(sessionId.value)
    ws.value.connect()

    ws.value.on('start', () => { isLoading.value = true })

    ws.value.on('thinking', () => {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant') last.thinking = true
    })

    ws.value.on('citation', (data: any) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant') {
        last.citations = data.citations || []
      }
    })

    ws.value.on('step', (data: any) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant') {
        if (!last.steps) last.steps = []
        last.steps.push({
          title: data.title || data.step || '步骤',
          content: data.content || data.message || '',
          status: data.status,
        })
      }
    })

    ws.value.on('reasoning', (data: any) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant' && last.isStreaming) {
        last.thinking = false
        if (data.accumulated) last.content = data.accumulated
        else if (data.content) last.content = data.content
        else if (data.token) last.content += data.token
      }
    })

    ws.value.on('intermediate', (data: any) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant' && last.isStreaming) {
        if (!last.steps) last.steps = []
        last.steps.push({
          title: data.phase || data.step || '中间步骤',
          content: data.message || data.content || '',
          status: data.status || 'info',
        })
      }
    })

    ws.value.on('tool_call', (data) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant') {
        last.thinking = false
        if (!last.tool_calls) last.tool_calls = []
        last.tool_calls.push({ tool: data.tool, result: '...' })
      }
    })

    ws.value.on('tool_result', (data) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant' && last.tool_calls) {
        const tc = last.tool_calls.find(t => t.tool === data.tool)
        if (tc) tc.result = data.result
      }
    })

    ws.value.on('final', (data) => {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant') {
        if (data.output && data.output !== last.content) {
          last.content = data.output
        }
        last.isStreaming = false
        last.thinking = false
        last.tool_calls = data.tool_calls || []
        last.tokens_used = data.tokens_used
      }
    })

    ws.value.on('done', () => {
      isLoading.value = false
      loadSessions()
    })

    ws.value.on('error', (data) => {
      isLoading.value = false
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant' && last.isStreaming) {
        messages.value.pop()
      }
      if (data.code === 'MEMBERSHIP_REQUIRED') {
        membershipRequiredMessage.value = data.message || '该功能需开通会员'
        return
      }
      messages.value.push({
        id: 'err_' + Date.now(),
        role: 'system',
        content: data.message || '请求处理失败，请稍后重试',
        timestamp: Date.now(),
      })
    })

    ws.value.on('disconnected', () => { isLoading.value = false })
  }

  async function loadSessions() {
    try {
      const data = await fetchSessions()
      sessions.value = data.sessions || []
    } catch (e) { console.error(e) }
  }

  async function switchSession(id: string) {
    sessionId.value = id
    messages.value = []
    connect()
    try {
      const data = await fetchSessionMessages(id)
      for (const m of data.messages || []) {
        messages.value.push({
          id: `${m.role}_${Date.now()}_${Math.random()}`,
          role: m.role,
          content: m.content,
          timestamp: Date.now(),
        })
      }
    } catch (e) { console.error(e) }
    const { useSettingsStore } = await import('./settings')
    await useSettingsStore().syncFromBackend(id)
  }

  async function newSession() {
    try {
      const data = await apiCreateSession('新对话')
      sessionId.value = data.session_id
    } catch {
      sessionId.value = 'session_' + Date.now()
    }
    messages.value = []
    connect()
    await loadSessions()
  }

  async function renameCurrentSession(title: string) {
    await renameSession(sessionId.value, title)
    await loadSessions()
  }

  async function sendContextClear(options: { clear_skill?: boolean; clear_expert?: boolean }) {
    isLoading.value = false
    try {
      await ws.value?.send('', {
        mode: 'adaptive',
        clear_skill: options.clear_skill,
        clear_expert: options.clear_expert,
      })
    } catch (e) {
      console.error(e)
    }
  }

  async function sendMessage(
    content: string,
    options: {
      mode?: string
      skill?: string | null
      expert_id?: string | null
      skill_invocation?: 'slash' | 'expert' | 'explicit' | null
      provider?: string
      model?: string | null
      attachments?: Array<Record<string, unknown>>
    } = {}
  ) {
    if (!content.trim() && !(options.attachments?.length)) return

    messages.value.push({
      id: 'u_' + Date.now(),
      role: 'user',
      content,
      timestamp: Date.now(),
    })

    messages.value.push({
      id: 'a_' + Date.now(),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true,
      thinking: true,
      steps: [],
      citations: [],
    })

    isLoading.value = true
    try {
      await ws.value?.send(content, options)
    } catch (e) {
      isLoading.value = false
      messages.value.push({
        id: 'err_' + Date.now(),
        role: 'system',
        content: e instanceof Error ? e.message : '消息发送失败，请检查网络连接',
        timestamp: Date.now(),
      })
    }
  }

  async function clearChat() {
    messages.value = []
    try {
      await clearSession(sessionId.value)
      await loadSessions()
    } catch (e) { console.error(e) }
  }

  function exportMessage(msg: ChatMessage) {
    const blob = new Blob([msg.content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  function disconnect() {
    ws.value?.disconnect()
  }

  function clearMembershipRequiredMessage() {
    membershipRequiredMessage.value = null
  }

  return {
    messages,
    sessions,
    isLoading,
    sessionId,
    membershipRequiredMessage,
    clearMembershipRequiredMessage,
    connect,
    disconnect,
    loadSessions,
    switchSession,
    newSession,
    renameCurrentSession,
    sendMessage,
    sendContextClear,
    clearChat,
    exportMessage,
  }
})
