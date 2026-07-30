import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
    { path: '/register', name: 'register', component: () => import('../views/RegisterView.vue') },
    { path: '/', name: 'chat', component: () => import('../views/ChatView.vue') },
    { path: '/tools', name: 'tools', component: () => import('../views/ToolsView.vue') },
    { path: '/skills', name: 'skills', component: () => import('../views/SkillsView.vue') },
    { path: '/experts', name: 'experts', component: () => import('../views/ExpertsView.vue') },
    { path: '/agents', redirect: '/experts' },
    { path: '/knowledge', name: 'knowledge', component: () => import('../views/KnowledgeView.vue') },
    { path: '/membership', name: 'membership', component: () => import('../views/MembershipView.vue') },
    {
      path: '/settings',
      component: () => import('../views/SettingsView.vue'),
      redirect: '/settings',
      children: [
        {
          path: '',
          name: 'settings-index',
          component: () => import('../views/settings/SettingsIndex.vue'),
        },
        {
          path: 'account',
          name: 'settings-account',
          component: () => import('../views/settings/AccountSettings.vue'),
        },
        {
          path: 'appearance',
          name: 'settings-appearance',
          component: () => import('../views/settings/AppearanceSettings.vue'),
        },
        {
          path: 'model',
          name: 'settings-model',
          component: () => import('../views/settings/ModelSettings.vue'),
        },
        {
          path: 'privacy',
          name: 'settings-privacy',
          component: () => import('../views/settings/PrivacySettings.vue'),
        },
        {
          path: 'about',
          name: 'settings-about',
          component: () => import('../views/settings/AboutSettings.vue'),
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  auth.syncTokenFromStorage()
  if (!auth.checked) await auth.checkAuth()

  const isPublic = to.name === 'login' || to.name === 'register'
  if (auth.authEnabled && !auth.token && !isPublic) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (isPublic && auth.token) {
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : '/'
    return redirect
  }
})

export default router
