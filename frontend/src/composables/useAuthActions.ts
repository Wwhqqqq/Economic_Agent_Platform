import { ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'

export function useAuthActions() {
  const auth = useAuthStore()
  const chat = useChatStore()
  const router = useRouter()

  async function performLogout(redirectTo = '/login') {
    auth.logout()
    chat.disconnect()
    await router.push(redirectTo)
  }

  async function confirmLogout() {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '退出登录', {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning',
      })
      await performLogout('/login')
    } catch {
      /* cancelled */
    }
  }

  async function confirmSwitchAccount() {
    try {
      await ElMessageBox.confirm(
        '切换账号将退出当前登录，是否继续？',
        '切换账号',
        {
          confirmButtonText: '继续',
          cancelButtonText: '取消',
          type: 'warning',
        },
      )
      await performLogout('/login?switch=1')
    } catch {
      /* cancelled */
    }
  }

  return {
    performLogout,
    confirmLogout,
    confirmSwitchAccount,
  }
}
