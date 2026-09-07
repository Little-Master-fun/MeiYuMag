import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/login' },
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
  if (!to.meta.admin) return true
  const auth = useAuthStore()
  if (!auth.user) await auth.fetchMe()
  return auth.isAdmin ? true : '/login'
})

export default router
