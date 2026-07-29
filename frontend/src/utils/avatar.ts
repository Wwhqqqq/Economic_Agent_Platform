export function avatarStorageKey(userId: number | null | undefined) {
  return userId ? `user_avatar_${userId}` : 'user_avatar_guest'
}

export function loadAvatarUrl(userId: number | null | undefined): string | null {
  if (!userId) return null
  return localStorage.getItem(avatarStorageKey(userId))
}

export function saveAvatarUrl(userId: number | null | undefined, dataUrl: string | null) {
  if (!userId) return
  const key = avatarStorageKey(userId)
  if (dataUrl) {
    localStorage.setItem(key, dataUrl)
  } else {
    localStorage.removeItem(key)
  }
}

export function readImageFileAsAvatar(file: File, maxSize = 128): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith('image/')) {
      reject(new Error('请选择图片文件'))
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      reject(new Error('图片大小不能超过 2MB'))
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const size = maxSize
        canvas.width = size
        canvas.height = size
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('无法处理图片'))
          return
        }
        const scale = Math.max(size / img.width, size / img.height)
        const w = img.width * scale
        const h = img.height * scale
        ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h)
        resolve(canvas.toDataURL('image/jpeg', 0.85))
      }
      img.onerror = () => reject(new Error('图片读取失败'))
      img.src = reader.result as string
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}
