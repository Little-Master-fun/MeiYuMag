import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/login' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
    },
    {
      path: '/applications/new',
      name: 'venue-application-placeholder',
      component: () => import('@/views/VenueApplicationPlaceholder.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: '/login' },
  ],
})

export default router
