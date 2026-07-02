<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <div class="brand-icon">💰</div>
        <h2 class="brand-title">资金跟踪</h2>
        <p class="brand-desc">项目资金实时预警管理</p>
      </div>
      <div class="mode-switch">
        <span :class="{ active: mode === 0 }" @click="mode = 0">登录</span>
        <span :class="{ active: mode === 1 }" @click="mode = 1">注册</span>
      </div>
      <van-form @submit="onSubmit">
        <div class="form-group">
          <div class="field-wrap">
            <span class="field-icon">📱</span>
            <input v-model="phone" type="tel" maxlength="11" placeholder="请输入手机号" class="field-input" />
          </div>
          <div class="field-wrap">
            <span class="field-icon">🔑</span>
            <input v-model="password" type="password" maxlength="20"
              :placeholder="mode === 0 ? '请输入密码' : '设置密码（至少6位）'"
              class="field-input" />
          </div>
        </div>
        <van-button round block type="primary" native-type="submit" :loading="loading"
          class="submit-btn">
          {{ mode === 0 ? '登 录' : '注 册' }}
        </van-button>
      </van-form>
      <div class="login-bottom">
        <span>🔒 登录后可查看全部数据与操作</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast } from 'vant'
import api from '../api'

const router = useRouter()
const route = useRoute()
const mode = ref(0)
const phone = ref('')
const password = ref('')
const loading = ref(false)

function goBack() {
  const redirect = route.query.redirect
  if (redirect && redirect !== '/login') {
    router.replace(redirect)
  } else if (window.history.length > 1) {
    router.back()
  } else {
    router.replace('/')
  }
}

async function onSubmit() {
  const trimmedPhone = phone.value.trim()
  const trimmedPwd = password.value.trim()
  if (!/^1[3-9]\d{9}$/.test(trimmedPhone)) {
    showToast('请输入正确的手机号')
    return
  }
  if (trimmedPwd.length < 6) {
    showToast('密码至少6位')
    return
  }
  loading.value = true
  try {
    const endpoint = mode.value === 0 ? '/auth/login' : '/auth/register'
    const res = await api.post(endpoint, { phone: trimmedPhone, password: trimmedPwd })
    localStorage.setItem('token', res.data.token)
    localStorage.setItem('phone', res.data.phone)
    showToast(mode.value === 0 ? '登录成功' : '注册成功')
    const redirect = route.query.redirect
    setTimeout(() => {
      if (redirect && redirect !== '/login') {
        router.replace(redirect)
      } else {
        router.replace('/')
      }
    }, 400)
  } catch (e) {
    showToast(e.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #0a1628 0%, #1a2a4a 100%);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
  animation: fadeIn .3s ease;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.login-card {
  position: relative; background: #fff; border-radius: 20px;
  width: 100%; max-width: 360px; padding: 36px 24px 24px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
  animation: slideUp .3s ease;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.login-close {
  position: absolute; top: 14px; right: 14px;
  width: 30px; height: 30px; display: flex;
  align-items: center; justify-content: center;
  border-radius: 50%; font-size: 16px; color: var(--nn-lightink); cursor: pointer;
}
.login-close:active { background: rgba(139, 90, 43, 0.08); color: #666; }
.login-brand { text-align: center; margin-bottom: 24px; }
.brand-icon { font-size: 40px; margin-bottom: 8px; }
.brand-title { margin: 0; font-size: 20px; font-weight: 700; color: var(--nn-ink); }
.brand-desc { margin: 4px 0 0; font-size: 12px; color: var(--nn-lightink); }
.mode-switch {
  display: flex; background: rgba(139, 90, 43, 0.08); border-radius: 10px;
  padding: 4px; margin-bottom: 20px;
}
.mode-switch span {
  flex: 1; text-align: center; padding: 8px 0;
  font-size: 14px; font-weight: 500; color: var(--nn-lightink);
  border-radius: 8px; cursor: pointer; transition: all .2s;
}
.mode-switch span.active {
  background: #fff; color: var(--nn-accent); font-weight: 600;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.field-wrap {
  display: flex; align-items: center; gap: 10px;
  background: #f5f7fa; border-radius: 12px;
  padding: 0 14px; margin-bottom: 12px;
}
.field-wrap:focus-within { background: #eef2ff; }
.field-icon { font-size: 18px; flex-shrink: 0; }
.field-input {
  flex: 1; border: none; background: transparent;
  height: 48px; font-size: 15px; color: #333; outline: none;
}
.field-input::placeholder { color: #c0c4cc; }
.submit-btn {
  margin-top: 16px; height: 46px; font-size: 16px; font-weight: 600;
  letter-spacing: 4px;
  background: linear-gradient(135deg, var(--nn-accent), var(--nn-ink));
  border: none; border-radius: 23px;
}
.login-bottom {
  text-align: center; padding: 16px 0 0;
  font-size: 11px; color: var(--nn-lightink);
}
</style>
