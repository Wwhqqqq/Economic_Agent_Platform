/**
 * Media upload API for chat attachments
 */

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export interface ChatAttachmentMeta {
  asset_id: string
  filename: string
  mime_type: string
  image_class?: string
  ocr_text?: string
  ocr_quality?: number
  vlm_caption?: string
  vlm_structured?: Record<string, unknown>
  data_url?: string
  url?: string
  thumbnail_url?: string
}

export async function uploadChatAttachment(file: File): Promise<ChatAttachmentMeta> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/media/upload', {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '图片上传失败')
  }
  return res.json()
}
