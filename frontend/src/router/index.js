import { createRouter, createWebHashHistory } from 'vue-router'

function requireAuth(to, from, next) {
  const token = localStorage.getItem('token')
  if (!token) next({ path: '/login', query: { redirect: to.fullPath } })
  else next()
}

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/transactions', name: 'Transactions', component: () => import('../views/Transactions.vue'), beforeEnter: requireAuth },
  { path: '/projects', name: 'Projects', component: () => import('../views/Projects.vue') },
  { path: '/reports', name: 'Reports', component: () => import('../views/Reports.vue') },
  { path: '/alerts', name: 'Alerts', component: () => import('../views/Alerts.vue') },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
