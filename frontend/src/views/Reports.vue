<template>
  <div class="reports">
    <!-- 概览统计 -->
    <div v-if="projects.length" class="stat-strip">
      <div class="ss-item">
        <span class="ss-val">{{ globalStats.count }}</span>
        <span class="ss-label">笔流水</span>
      </div>
      <div class="ss-item">
        <span class="ss-val income">¥{{ fmt(globalStats.income) }}</span>
        <span class="ss-label">收入</span>
      </div>
      <div class="ss-item">
        <span class="ss-val expense">¥{{ fmt(globalStats.expense) }}</span>
        <span class="ss-label">支出</span>
      </div>
      <div class="ss-item">
        <span class="ss-val" :class="globalStats.net >= 0 ? 'green' : 'red'">¥{{ fmt(globalStats.net) }}</span>
        <span class="ss-label">净额</span>
      </div>
    </div>

    <!-- 周期选择 -->
    <van-tabs v-model:active="period" @change="onPeriodChange" sticky>
      <van-tab v-for="p in periods" :key="p" :title="periodLabels[p]" :name="p" />
    </van-tabs>

    <!-- 汇总表格 -->
    <van-cell-group title="项目报表" inset>
      <div class="report-table">
        <!-- 表头 -->
        <div class="rt-header">
          <span class="rth-name">项目</span>
          <span class="rth-val sortable" :class="{ active: sortKey === 'income' }" @click="doSort('income')">收入 {{ sortIcon('income') }}</span>
          <span class="rth-val sortable" :class="{ active: sortKey === 'expense' }" @click="doSort('expense')">支出 {{ sortIcon('expense') }}</span>
          <span class="rth-val sortable" :class="{ active: sortKey === 'net' }" @click="doSort('net')">净额 {{ sortIcon('net') }}</span>
          <span class="rth-val sortable" :class="{ active: sortKey === 'budget' }" @click="doSort('budget')">预算 {{ sortIcon('budget') }}</span>
          <span class="rth-val">止损差</span>
        </div>

        <!-- 数据行 -->
        <template v-for="p in sortedProjects" :key="p.id">
          <div
            class="rt-row"
            :class="{ 'has-children': p.sub_projects && p.sub_projects.length }"
            @click="p.sub_projects && p.sub_projects.length && toggleExpand(p.id)"
          >
            <span class="rth-name">
              <span v-if="p.sub_projects && p.sub_projects.length" class="expand-icon">
                {{ expanded[p.id] ? '▼' : '▶' }}
              </span>
              <span class="pr-code">{{ p.code }}</span>
              {{ p.name }}
            </span>
            <span class="rth-val income">¥{{ fmt(p.income) }}</span>
            <span class="rth-val expense">¥{{ fmt(p.expense) }}</span>
            <span class="rth-val" :class="p.net >= 0 ? 'green' : 'red'">¥{{ fmt(p.net) }}</span>
            <span class="rth-val budget-cell">
              <template v-if="p.budget > 0">
                <span>¥{{ fmt(p.budget) }}</span>
                <span class="usage-badge" :class="usageClass(p.budget_usage)">{{ p.budget_usage?.toFixed(1) }}%</span>
              </template>
              <span v-else class="na">—</span>
            </span>
            <span class="rth-val" :class="p.stop_loss_diff >= 0 ? 'green' : 'red'">
              {{ p.stop_loss_diff != null ? fmt(p.stop_loss_diff) : '—' }}
            </span>
          </div>

          <!-- 子项目展开 -->
          <template v-if="p.sub_projects && p.sub_projects.length && expanded[p.id]">
            <div
              v-for="sub in p.sub_projects"
              :key="sub.id"
              class="rt-row sub-row"
            >
              <span class="rth-name sub-name">└ {{ sub.name }}</span>
              <span class="rth-val income">¥{{ fmt(sub.income) }}</span>
              <span class="rth-val expense">¥{{ fmt(sub.expense) }}</span>
              <span class="rth-val" :class="sub.net >= 0 ? 'green' : 'red'">¥{{ fmt(sub.net) }}</span>
              <span class="rth-val budget-cell">
                <template v-if="sub.budget > 0">
                  <span>¥{{ fmt(sub.budget) }}</span>
                  <span class="usage-badge" :class="usageClass(sub.budget_usage)">{{ sub.budget_usage?.toFixed(1) }}%</span>
                </template>
                <span v-else class="na">—</span>
              </span>
              <span class="rth-val" :class="sub.stop_loss_diff >= 0 ? 'green' : 'red'">
                {{ sub.stop_loss_diff != null ? fmt(sub.stop_loss_diff) : '—' }}
              </span>
            </div>
          </template>
        </template>

        <!-- 空/加载 -->
        <div v-if="!projects.length && !loading" class="rt-empty">暂无数据</div>
        <van-loading v-if="loading" class="rt-loading" />

        <!-- 总计行 -->
        <div v-if="projects.length" class="rt-row totals">
          <span class="rth-name totals-label">合计</span>
          <span class="rth-val income">¥{{ fmt(totals.income) }}</span>
          <span class="rth-val expense">¥{{ fmt(totals.expense) }}</span>
          <span class="rth-val" :class="totals.net >= 0 ? 'green' : 'red'">¥{{ fmt(totals.net) }}</span>
          <span class="rth-val budget-cell">
            <template v-if="totals.budget > 0">
              <span>¥{{ fmt(totals.budget) }}</span>
              <span class="usage-badge" :class="usageClass(totals.budget_usage)">{{ totals.budget_usage?.toFixed(1) }}%</span>
            </template>
            <span v-else class="na">—</span>
          </span>
          <span class="rth-val">—</span>
        </div>
      </div>
    </van-cell-group>

    <!-- 项目对比图 -->
    <van-cell-group v-if="projects.length" title="项目对比" inset>
      <div class="chart-section">
        <template v-for="p in projects" :key="'chart-' + p.id">
          <div class="chart-row">
            <span class="chart-label">{{ p.name }}</span>
            <div class="chart-bars">
              <div class="chart-bar-wrap">
                <div class="chart-bar income-bar" :style="{ width: barWidth(p.income, chartMax.income) + '%' }"></div>
                <span class="chart-bar-val">收 ¥{{ fmt(p.income) }}</span>
              </div>
              <div class="chart-bar-wrap">
                <div class="chart-bar expense-bar" :style="{ width: barWidth(p.expense, chartMax.expense) + '%' }"></div>
                <span class="chart-bar-val">支 ¥{{ fmt(p.expense) }}</span>
              </div>
            </div>
          </div>
          <!-- 子项目对比条 -->
          <div v-for="sub in p.sub_projects" :key="'chart-sub-' + sub.id" class="chart-row sub-chart">
            <span class="chart-label sub-label">└ {{ sub.name }}</span>
            <div class="chart-bars">
              <div class="chart-bar-wrap">
                <div class="chart-bar income-bar sub-bar" :style="{ width: barWidth(sub.income, chartMax.income) + '%' }"></div>
                <span class="chart-bar-val">收 ¥{{ fmt(sub.income) }}</span>
              </div>
              <div class="chart-bar-wrap">
                <div class="chart-bar expense-bar sub-bar" :style="{ width: barWidth(sub.expense, chartMax.expense) + '%' }"></div>
                <span class="chart-bar-val">支 ¥{{ fmt(sub.expense) }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </van-cell-group>

    <!-- 导出按钮 -->
    <div class="export-area">
      <van-button type="primary" block :loading="exporting" @click="doExport" icon="down">
        导出 Excel / CSV
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { showToast } from 'vant'
import api from '../api.js'

const period = ref('all')
const periods = ['today', 'week', 'month', 'year', 'all']
const periodLabels = { today: '今日', week: '本周', month: '本月', year: '本年', all: '全部' }
const loading = ref(false)
const exporting = ref(false)
const projects = ref([])
const expanded = reactive({})
const sortKey = ref('net')
const sortDir = ref(1)  // 1=asc, -1=desc (net default desc: click first → asc)

function fmt(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function usageClass(v) {
  if (v >= 95) return 'danger'
  if (v >= 80) return 'warn'
  return ''
}

function toggleExpand(id) {
  expanded[id] = !expanded[id]
}

// 排序
function sortIcon(key) {
  if (sortKey.value !== key) return '▸'
  return sortDir.value === -1 ? '▾' : '▴'
}

function doSort(key) {
  if (sortKey.value === key) {
    sortDir.value *= -1
  } else {
    sortKey.value = key
    sortDir.value = key === 'net' ? 1 : -1  // net default asc (reverse later), others default desc
  }
}

const sortedProjects = computed(() => {
  const arr = [...projects.value]
  arr.sort((a, b) => {
    const va = Number(a[sortKey.value] || 0)
    const vb = Number(b[sortKey.value] || 0)
    return (va - vb) * sortDir.value
  })
  return arr
})

// 全局统计
const globalStats = computed(() => {
  let count = 0, income = 0, expense = 0, net = 0
  projects.value.forEach(p => {
    count += Number(p.count || 0)
    income += Number(p.income || 0)
    expense += Number(p.expense || 0)
    net += Number(p.net || 0)
    if (p.sub_projects) {
      p.sub_projects.forEach(s => {
        count += Number(s.count || 0)
        income += Number(s.income || 0)
        expense += Number(s.expense || 0)
        net += Number(s.net || 0)
      })
    }
  })
  return { count, income: round2(income), expense: round2(expense), net: round2(net) }
})

// 总计（含子项目）
const totals = computed(() => {
  const t = { income: 0, expense: 0, net: 0, budget: 0, budget_usage: 0 }
  projects.value.forEach(p => {
    t.income += Number(p.income || 0)
    t.expense += Number(p.expense || 0)
    t.net += Number(p.net || 0)
    t.budget += Number(p.budget || 0)
    if (p.sub_projects) {
      p.sub_projects.forEach(s => {
        t.income += Number(s.income || 0)
        t.expense += Number(s.expense || 0)
        t.net += Number(s.net || 0)
        t.budget += Number(s.budget || 0)
      })
    }
  })
  t.budget_usage = t.budget > 0 ? (t.expense / t.budget) * 100 : 0
  return t
})

// 图表最大值（含子项目）
const chartMax = computed(() => {
  let maxIncome = 1, maxExpense = 1
  projects.value.forEach(p => {
    maxIncome = Math.max(maxIncome, Number(p.income || 0))
    maxExpense = Math.max(maxExpense, Number(p.expense || 0))
    if (p.sub_projects) {
      p.sub_projects.forEach(s => {
        maxIncome = Math.max(maxIncome, Number(s.income || 0))
        maxExpense = Math.max(maxExpense, Number(s.expense || 0))
      })
    }
  })
  return { income: maxIncome, expense: maxExpense }
})

function barWidth(val, max) {
  return Math.max(3, (Number(val || 0) / max) * 100)
}

function round2(v) { return Math.round(v * 100) / 100 }

async function fetchReports() {
  loading.value = true
  try {
    const res = await api.get('/stats', { params: { period: period.value } })
    const data = res.data
    projects.value = data.projects || data || []
    // 默认按净额降序
    sortKey.value = 'net'
    sortDir.value = -1
  } catch (e) {
    console.error('加载报表失败:', e)
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

function onPeriodChange() {
  fetchReports()
}

async function doExport() {
  exporting.value = true
  try {
    const response = await api.get('/export', {
      params: { period: period.value },
      responseType: 'blob',
    })
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${period.value}_${Date.now()}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    showToast('导出成功')
  } catch (e) {
    console.error('导出失败:', e)
    try {
      const response = await api.get('/export', {
        params: { period: period.value, format: 'csv' },
        responseType: 'blob',
      })
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${period.value}_${Date.now()}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      showToast('导出成功 (CSV)')
    } catch (e2) {
      console.error('CSV导出也失败:', e2)
      showToast('导出失败')
    }
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  fetchReports()
})
</script>

<style scoped>
.reports { padding-bottom: 20px; }

/* 概览条 */
.stat-strip {
  display: flex; gap: 0; margin: 0 12px 8px;
  background: var(--nn-paper); border-radius: 12px; overflow: hidden;
  box-shadow: var(--nn-shadow-seal);
}
.ss-item {
  flex: 1; text-align: center; padding: 10px 4px;
  border-right: 1px solid rgba(139, 69, 19, 0.08);
}
.ss-item:last-child { border-right: none; }
.ss-val {
  display: block; font-size: 15px; font-weight: 700; color: var(--nn-ink);
}
.ss-val.income { color: var(--van-success-color); }
.ss-val.expense { color: var(--nn-seal); }
.ss-val.green { color: var(--van-success-color); }
.ss-val.red { color: var(--nn-seal); }
.ss-label { font-size: 10px; color: var(--nn-lightink); margin-top: 2px; }

/* 表格 */
.report-table { background: var(--nn-paper); border-radius: 12px; overflow: hidden; }

.rt-header {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 1.4fr 0.7fr;
  gap: 2px; padding: 10px 8px;
  background: var(--nn-bg);
  font-size: 11px; font-weight: 700; color: var(--nn-lightink); text-align: center;
}

.rt-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 1.4fr 0.7fr;
  gap: 2px; padding: 12px 8px;
  border-bottom: 1px solid rgba(139, 69, 19, 0.08);
  align-items: center; text-align: center; font-size: 13px;
  transition: background .15s;
}
.rt-row:last-child { border-bottom: none; }
.rt-row.has-children { cursor: pointer; }
.rt-row.has-children:active { background: rgba(59, 34, 16, 0.04); }
.rt-row.sub-row { background: var(--nn-paper); padding-left: 20px; }
.rt-row.sub-row .rth-name { padding-left: 12px; }
.rt-row.totals {
  background: var(--nn-bg); font-weight: 700; border-top: 2px solid var(--nn-accent);
}

.rth-name {
  text-align: left; font-weight: 500; color: var(--nn-ink);
  display: flex; align-items: center; gap: 4px;
  overflow: hidden; white-space: nowrap;
}
.rth-name.totals-label { justify-content: flex-start; }

.rth-val {
  color: var(--nn-ink); font-variant-numeric: tabular-nums;
  overflow: hidden; white-space: nowrap;
}
.rth-val.green { color: var(--van-success-color); }
.rth-val.red { color: var(--nn-seal); }
.rth-val.income { color: var(--van-success-color); }
.rth-val.expense { color: var(--nn-seal); }
.rth-val.na { color: var(--nn-lightink); }

.sortable { cursor: pointer; user-select: none; }
.sortable.active { color: var(--nn-accent); font-weight: 700; }

.budget-cell {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
}

.expand-icon {
  font-size: 10px; color: var(--nn-lightink); width: 14px;
  display: inline-block; text-align: center;
}
.pr-code {
  background: var(--nn-bg); color: var(--nn-ink); font-weight: 700;
  padding: 1px 6px; border-radius: 3px; font-size: 11px; flex-shrink: 0;
}
.sub-name { font-size: 12px; color: var(--nn-lightink); }

.usage-badge {
  display: inline-block; padding: 2px 6px; border-radius: 4px;
  font-size: 10px; font-weight: 600;
  background: var(--nn-bg); color: var(--nn-accent);
}
.usage-badge.warn { background: #fff3e0; color: var(--nn-gold); }
.usage-badge.danger { background: #fde8ec; color: var(--nn-seal); }

.rt-empty { padding: 32px 0; text-align: center; color: var(--nn-lightink); font-size: 14px; }
.rt-loading { display: flex; justify-content: center; padding: 32px 0; }

/* 图表区 */
.chart-section { padding: 12px 8px; }
.chart-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.chart-row:last-child { margin-bottom: 0; }
.chart-row.sub-chart { padding-left: 16px; }
.chart-label {
  width: 56px; font-size: 12px; font-weight: 600; color: var(--nn-ink);
  flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.chart-label.sub-label { font-size: 11px; color: var(--nn-lightink); font-weight: 500; }
.chart-bars { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.chart-bar-wrap {
  position: relative; height: 20px; background: var(--nn-bg);
  border-radius: 4px; overflow: hidden;
}
.chart-bar {
  height: 100%; border-radius: 4px; min-width: 4px; transition: width .4s ease;
}
.chart-bar.income-bar { background: linear-gradient(90deg, var(--van-success-color), #1b4332); }
.chart-bar.expense-bar { background: linear-gradient(90deg, var(--nn-seal), #9a1a1a); }
.chart-bar.sub-bar { opacity: .55; }
.chart-bar-val {
  position: absolute; top: 50%; left: 6px; transform: translateY(-50%);
  font-size: 10px; color: #fff; font-weight: 600; white-space: nowrap;
  text-shadow: 0 1px 2px rgba(0,0,0,.25);
}

.export-area { margin-top: 16px; padding: 0 12px; }
</style>
