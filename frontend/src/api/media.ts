/**
 * Media upload API for chat attachments
 */
import api from './client'

export interface ChatAttachmentMeta {
  asset_id: string
  filename: string
  mime_type: string
  kind?: 'image' | 'file'
  file_path?: string
  text_preview?: string
  image_class?: string
  ocr_text?: string
  ocr_quality?: number
  vlm_caption?: string
  vlm_structured?: Record<string, unknown>
  data_url?: string
  url?: string
  thumbnail_url?: string
}

function parseUploadError(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
  return '文件上传失败'
}

export async function uploadChatAttachment(file: File): Promise<ChatAttachmentMeta> {
  const form = new FormData()
  form.append('file', file)
  try {
    const { data } = await api.post<ChatAttachmentMeta>('/media/upload', form, {
      timeout: 120000,
    })
    return data
  } catch (err) {
    throw new Error(parseUploadError(err))
  }
}
