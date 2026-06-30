<template>
  <div class="alerts-page">
    <van-tabs v-model:active="filter" @change="loadAlerts" sticky>
      <van-tab title="活跃" name="active" />
      <van-tab title="全部" name="all" />
      <van-tab title="已处理" name="resolved" />
    </van-tabs>

    <van-cell-group inset v-for="a in list" :key="a.id" style="margin-bottom:8px">
      <div class="alert-card" :class="'level-' + a.level">
        <div class="ac-header">
          <span class="ac-icon">{{ a.level === 'danger' ? '🔴' : a.level === 'warning' ? '🟡' : '🔵' }}</span>
          <span class="ac-project">{{ a.project_name }}</span>
          <span class="ac-type">{{ a.alert_type === 'budget' ? '预算预警' : '止损预警' }}</span>
          <span class="ac-status" v-if="a.status !== 'active'">{{ a.status }}</span>
        </div>
        <div class="ac-msg">{{ a.message }}</div>
        <div class="ac-time">{{ a.created_at }}</div>
        <div class="ac-actions" v-if="a.status === 'active'">
          <van-button size="small" plain type="success" @click="doResolve(a.id, 'resolved')">✓ 已处理</van-button>
          <van-button size="small" plain type="default" @click="doResolve(a.id, 'ignored')">忽略</van-button>
        </div>
        <div class="ac-note" v-if="a.resolve_note">备注: {{ a.resolve_note }}</div>
      </div>
    </van-cell-group>

    <van-empty v-if="!list.length" description="暂无预警记录" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showToast } from 'vant'
import api from '../api.js'

const filter = ref('active')
const list = ref([])

async function loadAlerts() {
  try {
    const { data } = await api.get('/alerts', { params: { status: filter.value } })
    list.value = data
  } catch (e) { console.error(e) }
}

async function doResolve(id, status) {
  try {
    await api.put(`/alerts/${id}`, { status, resolve_note: status === 'resolved' ? '已处理' : '已忽略' })
    showToast('已更新')
    loadAlerts()
  } catch (e) { showToast('操作失败') }
}

onMounted(loadAlerts)
</script>

<style scoped>
.alert-card {
  padding: 12px 16px;
  background: var(--nn-paper);
  border-radius: var(--nn-radius-sm);
  box-shadow: var(--nn-shadow-seal);
}
.alert-card.level-danger { border-left: 3px solid var(--nn-seal); }
.alert-card.level-warning { border-left: 3px solid var(--nn-gold); }
.ac-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.ac-icon { font-size: 14px; }
.ac-project { font-weight: 700; font-size: 14px; color: var(--nn-ink); }
.ac-type {
  font-size: 11px;
  background: rgba(139, 90, 43, 0.08);
  padding: 2px 8px;
  border-radius: var(--nn-radius-sm);
  color: var(--nn-lightink);
}
.ac-status { font-size: 11px; color: var(--nn-lightink); margin-left: auto; }
.ac-msg { font-size: 13px; color: var(--nn-lightink); margin-bottom: 4px; }
.ac-time { font-size: 11px; color: var(--nn-lightink); margin-bottom: 8px; }
.ac-actions { display: flex; gap: 8px; }
.ac-note { font-size: 11px; color: #2d6a4f; margin-top: 4px; }
</style>
