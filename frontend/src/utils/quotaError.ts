import axios from 'axios'

export interface QuotaErrorDetail {
  code?: string
  message: string
  quota?: string
}

export function parseApiErrorDetail(error: unknown): QuotaErrorDetail | null {
  if (!axios.isAxiosError(error)) {
    if (error instanceof Error) return { message: error.message }
    return null
  }
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') {
    return { message: detail }
  }
  if (detail && typeof detail === 'object') {
    return {
      code: detail.code,
      message: detail.message || '请求受限，请稍后重试',
      quota: detail.quota,
    }
  }
  if (error.response?.status === 429) {
    return { code: 'QUOTA_EXCEEDED', message: '请求过于频繁或已达使用上限' }
  }
  return { message: error.message || '请求失败' }
}

export function isQuotaExceeded(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false
  if (error.response?.status === 429) return true
  const detail = parseApiErrorDetail(error)
  return detail?.code === 'QUOTA_EXCEEDED'
}

export function quotaLimitMessage(quota: string | undefined, fallback?: string): string {
  switch (quota) {
    case 'max_sessions':
      return (
        fallback ||
        '有记录的对话数量已达上限。请右键删除不再需要的对话，或升级会员获得更高配额。'
      )
    case 'daily_messages':
      return fallback || '今日消息数已达上限，请明天再试或升级会员。'
    case 'max_documents':
      return fallback || '知识库文档数已达上限，请升级会员。'
    case 'max_file_mb':
      return fallback || '文件大小超过当前账号允许的上限。'
    default:
      return fallback || '已达使用上限，请升级会员或稍后再试。'
  }
}
