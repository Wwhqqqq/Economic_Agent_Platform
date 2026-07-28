/**
 * 会员身份判断 — 与后端 UserContext.is_member 逻辑一致
 * @see backend/app/schemas/user_context.py
 * @see docs/多用户/03-身份认证与会话/README.md
 */

export type UserType = 'regular' | 'member'

export function resolveIsMember(
  userType: UserType | string,
  membershipExpiresAt: string | null | undefined,
): boolean {
  const normalized = String(userType || '').trim().toLowerCase()
  if (normalized !== 'member') return false
  if (!membershipExpiresAt) return true
  const expires = new Date(membershipExpiresAt)
  if (Number.isNaN(expires.getTime())) return true
  return expires.getTime() > Date.now()
}

export function userTypeLabel(isMember: boolean): string {
  return isMember ? '会员用户' : '普通用户'
}

export function userTypeShortLabel(isMember: boolean): string {
  return isMember ? '会员' : '普通用户'
}

export function formatMembershipExpiry(iso: string | null | undefined): string | null {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}
