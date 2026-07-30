/**
 * WebSocket 客户端
 * 管理与后端的实时通信
 */

type EventCallback = (data: any) => void

export class ChatWebSocket {
  private ws: WebSocket | null = null
  private sessionId: string
  private listeners: Map<string, EventCallback[]> = new Map()
  private connectPromise: Promise<void> | null = null

  constructor(sessionId: string) {
    this.sessionId = sessionId
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  connect(): Promise<void> {
    if (this.isConnected) {
      return Promise.resolve()
    }

    if (this.connectPromise) {
      return this.connectPromise
    }

    this.connectPromise = new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const token = localStorage.getItem('auth_token')
      const qs = token ? `?token=${encodeURIComponent(token)}` : ''
      const url = `${protocol}//${window.location.host}/ws/chat/${this.sessionId}${qs}`

      console.log('[WS] Connecting to', url)
      this.ws = new WebSocket(url)

      const timeout = window.setTimeout(() => {
        reject(new Error('WebSocket 连接超时'))
      }, 10000)

      this.ws.onopen = () => {
        window.clearTimeout(timeout)
        console.log('[WS] Connected')
        this.emit('connected', { session_id: this.sessionId })
        resolve()
      }

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          this.emit(msg.type, msg.data)
        } catch (e) {
          console.error('[WS] Parse error:', e)
        }
      }

      this.ws.onclose = () => {
        window.clearTimeout(timeout)
        console.log('[WS] Disconnected')
        this.connectPromise = null
        this.emit('disconnected', {})
      }

      this.ws.onerror = () => {
        window.clearTimeout(timeout)
        console.error('[WS] Connection error')
        this.connectPromise = null
        this.emit('error', { message: 'WebSocket 连接失败' })
        reject(new Error('WebSocket 连接失败'))
      }
    })

    return this.connectPromise
  }

  async send(
    input: string,
    options: {
      mode?: string
      skill?: string | null
      expert_id?: string | null
      skill_invocation?: 'slash' | 'expert' | null
      clear_skill?: boolean
      clear_expert?: boolean
      provider?: string
      model?: string | null
      temperature?: number
      attachments?: Array<Record<string, unknown>>
    } = {}
  ) {
    try {
      await this.connect()
    } catch (e) {
      console.error('[WS] Not connected', e)
      this.emit('error', { message: 'WebSocket 未连接，请刷新页面重试' })
      return
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.emit('error', { message: 'WebSocket 未就绪' })
      return
    }

    const payload: Record<string, unknown> = {
      type: 'message',
      input,
      mode: options.mode || 'adaptive',
      skill: options.skill,
      provider: options.provider || 'deepseek',
      temperature: options.temperature || 0.7,
    }
    if (options.expert_id) payload.expert_id = options.expert_id
    if (options.skill_invocation) payload.skill_invocation = options.skill_invocation
    if (options.clear_skill) payload.clear_skill = true
    if (options.clear_expert) payload.clear_expert = true
    if (options.model) payload.model = options.model
    if (options.attachments?.length) payload.attachments = options.attachments

    this.ws.send(JSON.stringify(payload))
  }

  on(event: string, callback: EventCallback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(callback)
  }

  off(event: string, callback: EventCallback) {
    const cbs = this.listeners.get(event)
    if (cbs) {
      const idx = cbs.indexOf(callback)
      if (idx >= 0) cbs.splice(idx, 1)
    }
  }

  private emit(event: string, data: any) {
    const cbs = this.listeners.get(event) || []
    cbs.forEach(cb => cb(data))
  }

  disconnect() {
    this.connectPromise = null
    this.ws?.close()
  }
}
