<template>
  <div class="app">
    <div class="top-bar">
      <span class="tb-title">💰 资金跟踪</span>
      <div class="tb-right">
        <span class="user-badge" v-if="isLoggedIn" @click="showLogout = true">📱 {{ phone }}</span>
        <span class="user-badge guest" v-else @click="goLogin">登录</span>
        <span class="tb-time">{{ now }}</span>
      </div>
    </div>
    <div class="content">
      <router-view />
    </div>
    <van-tabbar v-model="active" route>
      <van-tabbar-item icon="chart-trending-o" to="/">总览</van-tabbar-item>
      <van-tabbar-item icon="bill-o" to="/transactions" :badge="isLoggedIn ? '' : '🔒'">流水</van-tabbar-item>
      <van-tabbar-item icon="setting-o" to="/projects">项目</van-tabbar-item>
      <van-tabbar-item icon="bar-chart-o" to="/reports">报表</van-tabbar-item>
      <van-tabbar-item icon="warning-o" to="/alerts">预警</van-tabbar-item>
    </van-tabbar>
    <div class="app-version">v1.0.2</div>

    <!-- 退出确认 -->
    <van-dialog v-model:show="showLogout" title="退出登录" message="确定要退出吗？"
      show-cancel-button @confirm="doLogout" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const active = ref(0)
const now = ref('')
const isLoggedIn = ref(false)
const phone = ref('')
const showLogout = ref(false)

onMounted(() => {
  const tabs = ['/', '/transactions', '/projects', '/reports', '/alerts']
  const idx = tabs.indexOf(route.path)
  if (idx >= 0) active.value = idx
  checkLogin()
  setInterval(() => {
    now.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }, 1000)
})

function checkLogin() {
  const token = localStorage.getItem('token')
  const storedPhone = localStorage.getItem('phone')
  if (token && storedPhone) {
    isLoggedIn.value = true
    phone.value = storedPhone
  }
}

function goLogin() {
  router.push('/login')
}

function doLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('phone')
  isLoggedIn.value = false
  phone.value = ''
  showLogout.value = false
  router.push('/')
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f7fa; }
.app { min-height: 100vh; padding-bottom: 60px; }
.top-bar {
  position: sticky; top: 0; z-index: 10;
  background: linear-gradient(135deg, #0a1628, #1a2a4a);
  color: #fff; padding: 12px 16px; display: flex;
  justify-content: space-between; align-items: center;
}
.tb-title { font-size: 17px; font-weight: 700; }
.tb-right { display: flex; align-items: center; gap: 10px; }
.user-badge {
  font-size: 12px; color: #4da6ff; cursor: pointer;
  background: rgba(77,166,255,.15); padding: 4px 10px;
  border-radius: 12px;
}
.user-badge.guest { color: #8899bb; background: rgba(255,255,255,.1); }
.tb-time { font-size: 12px; color: #8899bb; }
.content { padding: 12px 12px 0; }
.van-tabbar { border-top: 1px solid #eee; }
.app-version {
  text-align: center;
  font-size: 10px;
  color: #ccc;
  padding: 2px 0 8px;
}
</style>
