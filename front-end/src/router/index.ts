import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { nativeApp } from '@/platform/native'

const router = createRouter({
  history: nativeApp ? createWebHashHistory() : createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/login' },
    {
      path: '/signatures',
      component: () => import('@/views/SignatureDesk.vue'),
      meta: { secondary: true },
    },
    {
      path: '/admin',
      alias: '/admin/applications',
      component: () => import('@/views/ReviewDesk.vue'),
      meta: { admin: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
    },
    {
      path: '/applications/new',
      name: 'venue-application',
      redirect: to => ({path: '/login', query: {...to.query, action: 'apply'}}),
    },
    {
      path: '/applications/:id(\\d+)',
      redirect: to => ({path: '/login', query: {application: String(to.params.id)}}),
    },
    { path: '/:pathMatch(.*)*', redirect: '/login' },
  ],
})

router.beforeEach(async to => {
  if (!to.meta.admin && !to.meta.secondary) return true
  const auth = useAuthStore()
  if (!auth.user) await auth.fetchMe()
  return (to.meta.secondary ? auth.isSecondaryAdmin : auth.isAdmin) ? true : '/login'
})

export default router
