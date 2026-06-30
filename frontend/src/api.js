import axios from 'axios'

// Dev: Vite proxies /api → 8006. Prod: served at /fund/, API must route through /fund/api proxy
const baseURL = window.location.pathname.startsWith('/fund/') ? '/fund/api' : '/api'

const api = axios.create({
  baseURL,
  timeout: 10000,
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api
