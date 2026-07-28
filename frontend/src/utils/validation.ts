/** Registration form validators — aligned with PRD & backend validators */

export const USERNAME_RE = /^[A-Za-z0-9_]{3,64}$/
export const EMAIL_RE = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/
export const PASSWORD_RE = /^[A-Za-z0-9_]{6,128}$/
export const VERIFICATION_CODE_RE = /^[0-9]{4}$/

export type RegisterField =
  | 'username'
  | 'email'
  | 'password'
  | 'confirm_password'
  | 'verification_code'

export function validateUsername(value: string): string | null {
  const v = value.trim()
  if (!v) return '请输入用户名'
  if (!USERNAME_RE.test(v)) {
    if (v.length < 3 || v.length > 64) return '用户名长度为 3–64 个字符'
    return '用户名只能包含字母、数字和下划线'
  }
  return null
}

export function validateEmail(value: string): string | null {
  const v = value.trim()
  if (!v) return '请输入邮箱地址'
  if (!EMAIL_RE.test(v)) return '请输入有效的邮箱地址'
  return null
}

export function validatePassword(value: string): string | null {
  if (!value) return '请输入密码'
  if (!PASSWORD_RE.test(value)) {
    if (value.length < 6) return '密码至少 6 位'
    return '密码只能包含字母、数字和下划线'
  }
  return null
}

export function validateConfirmPassword(password: string, confirm: string): string | null {
  if (!confirm) return '请再次输入密码'
  if (!PASSWORD_RE.test(confirm)) {
    if (confirm.length < 6) return '密码至少 6 位'
    return '密码只能包含字母、数字和下划线'
  }
  if (confirm !== password) return '密码不一致'
  return null
}

export function validateVerificationCode(value: string): string | null {
  const v = value.trim()
  if (!v) return '请输入验证码'
  if (!VERIFICATION_CODE_RE.test(v)) return '请输入 4 位数字验证码'
  return null
}

export const SERVER_FIELD_MAP: Record<string, RegisterField> = {
  username: 'username',
  email: 'email',
  password: 'password',
  confirm_password: 'confirm_password',
  verification_code: 'verification_code',
}

export function mapServerField(field?: string): RegisterField | null {
  if (!field) return null
  return SERVER_FIELD_MAP[field] ?? null
}

export function mapServerMessage(code?: string, message?: string): string {
  const table: Record<string, string> = {
    USERNAME_INVALID: '用户名只能包含字母、数字和下划线',
    USERNAME_TAKEN: '用户名已被占用',
    EMAIL_INVALID: '请输入有效的邮箱地址',
    EMAIL_TAKEN: '该邮箱已被注册',
    EMAIL_ALREADY_REGISTERED: '该邮箱已被注册',
    PASSWORD_INVALID: '密码只能包含字母、数字和下划线，至少 6 位',
    VERIFICATION_CODE_INVALID: '验证码错误',
    VERIFICATION_CODE_EXPIRED: '验证码已过期，请重新获取',
    SEND_TOO_FREQUENT: '获取过于频繁，请稍后再试',
    MAIL_SEND_FAILED: '邮件发送失败，请稍后重试',
  }
  if (code && table[code]) return table[code]
  return message || '操作失败，请稍后重试'
}
