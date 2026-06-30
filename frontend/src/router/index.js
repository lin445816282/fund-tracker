import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/transactions', name: 'Transactions', component: () => import('../views/Transactions.vue') },
  { path: '/projects', name: 'Projects', component: () => import('../views/Projects.vue') },
  { path: '/reports', name: 'Reports', component: () => import('../views/Reports.vue') },
  { path: '/alerts', name: 'Alerts', component: () => import('../views/Alerts.vue') },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 全局守卫：非登录页且无token → 跳登录
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (!token && to.path !== '/login') {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
