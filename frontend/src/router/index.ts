import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import AdminView from '../views/AdminView.vue'
import CalendarView from '../views/CalendarView.vue'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    { path: '/', name: 'overview', component: DashboardView },
    { path: '/calendar', name: 'calendar', component: CalendarView },
    { path: '/admin', redirect: { name: 'admin-servers' } },
    {
      path: '/admin/servers',
      name: 'admin-servers',
      component: AdminView,
      meta: { requiresAdmin: true, adminTab: 'servers' },
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: AdminView,
      meta: { requiresAdmin: true, adminTab: 'users' },
    },
    {
      path: '/admin/projects',
      name: 'admin-projects',
      component: AdminView,
      meta: { requiresAdmin: true, adminTab: 'projects' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.initialize()
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'overview' }
  if (to.name !== 'login' && !auth.isAuthenticated) return { name: 'login' }
  if (to.meta.requiresAdmin && !auth.isAdmin) return { name: 'overview' }
  return true
})
