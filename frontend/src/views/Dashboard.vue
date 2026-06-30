<template>
  <div class="dashboard">
    <!-- 四宫格豆腐块 -->
    <div class="summary-grid">
      <!-- 日总 -->
      <div class="sg-block" :class="{ active: activeModal === 'today' }" @click="openModal('today')">
        <div class="sg-title">📅 今日 <span class="sg-date">{{ summary.today.label }}</span></div>
        <div class="sg-val-row">合计 <span :class="summary.today.net >= 0 ? 'green' : 'red'">¥{{ fmt(summary.today.net) }}</span></div>
        <div class="sg-val-row sub">收入 ¥{{ fmt(summary.today.income) }}  支出 ¥{{ fmt(summary.today.expense) }}</div>
        <div class="sg-compare" @click.stop="openModal('yesterday')">
          <div class="sg-cmp-row main">昨日 合计 <span :class="summary.yesterday.net >= 0 ? 'green' : 'red'">¥{{ fmt(summary.yesterday.net) }}</span></div>
          <div class="sg-cmp-row">收入 ¥{{ fmt(summary.yesterday.income) }}  支出 ¥{{ fmt(summary.yesterday.expense) }}</div>
        </div>
      </div>

      <!-- 周总 -->
      <div class="sg-block" :class="{ active: activeModal === 'week' }" @click="openModal('week')">
        <div class="sg-title">📆 本周 <span class="sg-date">{{ summary.week.label }}</span></div>
        <div class="sg-val-row">合计 <span :class="summary.week.net >= 0 ? 'green' : 'red'">¥{{ fmt(summary.week.net) }}</span></div>
        <div class="sg-val-row sub">收入 ¥{{ fmt(summary.week.income) }}  支出 ¥{{ fmt(summary.week.expense) }}</div>
        <div class="sg-compare" @click.stop="openModal('last_week')">
          <div class="sg-cmp-row main">上周 合计 <span :class="summary.last_week.net >= 0 ? 'green' : 'red'">¥{{ fmt(summary.last_week.net) }}</span></div>
          <div class="sg-cmp-row">收入 ¥{{ fmt(summary.last_week.income) }}  支出 ¥{{ fmt(summary.last_week.expense) }}</div>
        </div>
      </div>

      <!-- 月总 -->
      <div class="sg-block" :class="{ active: activeModal === 'month' }" @click="openModal('month')">
        <div class="sg-title">📊 本月 <span class="sg-date">{{ summary.month.label }}</span></div>
        <div class="sg-val-row">合计 <span :class="summary.month.net >= 0 ? 'green' : 'red'">¥{{ fmt(summary.month.net) }}</span></div>
        <div class="sg-val-row sub">收入 ¥{{ fmt(summary.month.income) }}  支出 ¥{{ fmt(summary.month.expense) }}</div>
        <div class="sg-compare" @click.stop="openModal('last_month')">
          <div class="sg-cmp-row main">上月 合计 <span :class="summary.last_month.net >= 0 ? 'green' : 'red'">¥{{ fmt(summary.last_month.net) }}</span></div>
          <div class="sg-cmp-row">收入 ¥{{ fmt(summary.last_month.income) }}  支出 ¥{{ fmt(summary.last_month.expense) }}</div>
        </div>
      </div>

      <!-- 年总 -->
      <div class="sg-block" :class="{ active: activeModal === 'year' }" @click="openModal('year')">
        <div class="sg-title">🏦 本年 <span class="sg-date">{{ summary.year.label }}</span></div>
        <div class="sg-val-row">合计 <span :class="summary.year.net >= 0 ? 'green' : 'red'">¥{{ fmt(summary.year.net) }}</span></div>
        <div class="sg-val-row sub">收入 ¥{{ fmt(summary.year.income) }}  支出 ¥{{ fmt(summary.year.expense) }}</div>
        <div class="sg-compare" @click.stop="openModal('last_year')">
          <div class="sg-cmp-row main">上年 合计 <span :class="summary.last_year.net >= 0 ? 'green' : 'red'">¥{{ fmt(summary.last_year.net) }}</span></div>
          <div class="sg-cmp-row">收入 ¥{{ fmt(summary.last_year.income) }}  支出 ¥{{ fmt(summary.last_year.expense) }}</div>
        </div>
      </div>
    </div>

    <!-- 预警提示 -->
    <div v-if="alertCount > 0" class="alert-banner" @click="$router.push('/alerts')">
      ⚠️ {{ alertCount }} 条活跃预警
    </div>

    <!-- 走势图 -->
    <div class="trend-section">
      <div class="trend-header">
        <span class="trend-title">📈 走势</span>
      </div>

      <!-- 项目选择 -->
      <div class="trend-projects">
        <span
          v-for="p in projects"
          :key="p.id"
          class="tp-pill"
          :class="{ on: selectedIds.has(p.id), sub: p.parent_id }"
          @click="toggleProject(p.id)"
        ><span v-if="p.parent_id" class="tp-indent">╰</span><span v-if="p.parent_id" class="tp-bar"></span>{{ p.name }}</span>
      </div>

      <!-- 周期切换 -->
      <div class="trend-tabs">
        <span v-for="t in periods" :key="t.value" class="tt-tab" :class="{ on: trendPeriod === t.value }" @click="switchPeriod(t.value)">{{ t.label }}</span>
      </div>

      <!-- Canvas -->
      <div class="trend-canvas-wrap">
        <canvas ref="chartCanvas" class="trend-canvas"></canvas>
      </div>
    </div>

    <!-- 明细弹框 -->
    <van-popup v-model:show="showModal" position="center" round :style="{ width: '90%', maxHeight: '70vh', borderRadius: '16px' }">
      <div class="modal-wrap">
        <div class="modal-header">
          <span class="modal-title">{{ modalTitle }}·明细</span>
          <span class="modal-close" @click="showModal = false">✕</span>
        </div>
        <div class="modal-body">
          <van-loading v-if="modalLoading" class="modal-loading" />
          
          <template v-else-if="modalProjects.length">
            <div class="modal-summary">
              合计：收 <b class="income">¥{{ fmt(modalTotal.income) }}</b>
              支 <b class="expense">¥{{ fmt(modalTotal.expense) }}</b>
              净 <b :class="modalTotal.net >= 0 ? 'green' : 'red'">¥{{ fmt(modalTotal.net) }}</b>
            </div>

            <div v-for="(p, idx) in modalProjects" :key="p.id" class="modal-proj">
              <div class="mp-main">
                <span class="mp-num">{{ idx + 1 }}</span>
                <span class="mp-name">{{ p.name }}</span>
                <span class="mp-total" :class="p.net >= 0 ? 'green' : 'red'">合计 ¥{{ fmt(p.net) }}</span>
              </div>
              <div v-for="sub in p.sub_projects" :key="sub.id" class="mp-sub">
                <span class="mp-sub-name">{{ sub.name }}</span>
                <span class="mp-sub-total-val" :class="sub.net >= 0 ? 'green' : 'red'">合计 ¥{{ fmt(sub.net) }}</span>
              </div>
            </div>
          </template>
          
          <div v-else class="modal-empty">暂无数据</div>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api.js'

const router = useRouter()
const summary = reactive({
  today: { income: 0, expense: 0, net: 0, label: '' },
  yesterday: { income: 0, expense: 0, net: 0 },
  week: { income: 0, expense: 0, net: 0, label: '' },
  last_week: { income: 0, expense: 0, net: 0 },
  month: { income: 0, expense: 0, net: 0, label: '' },
  last_month: { income: 0, expense: 0, net: 0 },
  year: { income: 0, expense: 0, net: 0, label: '' },
  last_year: { income: 0, expense: 0, net: 0 },
})
const alertCount = ref(0)
const showModal = ref(false)
const activeModal = ref('')
const modalLoading = ref(false)
const modalProjects = ref([])

const periodNames = {
  today: '今日', yesterday: '昨日',
  week: '本周', last_week: '上周',
  month: '本月', last_month: '上月',
  year: '本年', last_year: '上年',
}
const modalTitle = computed(() => periodNames[activeModal.value] || '')

const modalTotal = computed(() => {
  let income = 0, expense = 0, net = 0
  modalProjects.value.forEach(p => {
    income += p.income
    expense += p.expense
    net += p.net
    if (p.sub_projects) {
      p.sub_projects.forEach(s => {
        income += s.income
        expense += s.expense
        net += s.net
      })
    }
  })
  return { income, expense, net }
})

const mainTotal = computed(() => {
  let income = 0, expense = 0, net = 0
  modalProjects.value.forEach(p => {
    income += p.income
    expense += p.expense
    net += p.net
  })
  return { income, expense, net }
})

function fmt(v) { return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }
function subSum(p) { return (p.sub_projects || []).reduce((s, sp) => s + (sp.net || 0), 0) }

// 走势图
const projects = ref([])
const selectedIds = ref(new Set())
const trendPeriod = ref('day')
const trendData = ref({ dates: [], labels: [], series: [] })
const trendLoading = ref(false)
const chartCanvas = ref(null)
const periods = [
  { label: '日', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '年', value: 'year' },
]

function toggleProject(id) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) {
    s.delete(id)
  } else {
    s.add(id)
  }
  selectedIds.value = s
  loadTrend()
}

function switchPeriod(p) {
  trendPeriod.value = p
  loadTrend()
}

async function loadTrend() {
  if (selectedIds.value.size === 0) {
    trendData.value = { dates: [], labels: [], series: [] }
    nextTick(() => drawChart())
    return
  }
  trendLoading.value = true
  try {
    const ids = [...selectedIds.value].join(',')
    const data = await api.get('/dashboard/trend', { params: { project_ids: ids, period: trendPeriod.value } })
    trendData.value = data.data
  } catch (e) { console.error(e) }
  finally { trendLoading.value = false }
  nextTick(() => drawChart())
}

function drawChart() {
  const canvas = chartCanvas.value
  if (!canvas) return
  const dpr = window.devicePixelRatio || 1
  const rect = canvas.parentElement.getBoundingClientRect()
  const w = rect.width
  const ctx_init = canvas.getContext('2d')

  const { dates, labels, series } = trendData.value

  // 计算图例行数（支持换行）
  let legendRows = 0
  if (series.length) {
    ctx_init.font = '10px sans-serif'
    let lx = 0
    series.forEach((s, i) => {
      const tw = ctx_init.measureText(s.name).width + 16
      if (lx > 0 && lx + tw > w - 100) { lx = 0; legendRows++ }
      lx += tw + (lx > 0 || i > 0 ? 4 : 0)
    })
    if (lx > 0) legendRows++
  }
  const legendH = legendRows * 20
  const chartH = 240
  const h = legendH + chartH
  canvas.width = w * dpr
  canvas.height = h * dpr
  canvas.style.width = w + 'px'
  canvas.style.height = h + 'px'
  const ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)

  const pad = { top: 12, right: 28, bottom: 32, left: 44 }
  const pw = w - pad.left - pad.right
  const ph = chartH - pad.top - pad.bottom

  ctx.clearRect(0, 0, w, h)
  // 图表背景 + 边框
  ctx.fillStyle = '#f0f3f8'
  ctx.fillRect(pad.left, pad.top, pw, ph)
  ctx.strokeStyle = '#dde3ea'
  ctx.lineWidth = 1
  ctx.strokeRect(pad.left, pad.top, pw, ph)

  // 加载中
  if (trendLoading.value) {
    ctx.fillStyle = '#b0bec5'
    ctx.font = '13px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('加载中…', w / 2, legendH + chartH / 2)
    return
  }

  // 图例（支持换行，不跳过）
  if (series.length) {
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'left'
    let row = 0, lx = pad.left
    series.forEach((s, i) => {
      const txt = s.name
      const tw = ctx.measureText(txt).width + 16
      if (lx > pad.left && lx + tw > w - pad.right) { row++; lx = pad.left }
      const ly = 6 + row * 20 + 4
      ctx.beginPath()
      ctx.arc(lx + 5, ly, 4, 0, Math.PI * 2)
      ctx.fillStyle = s.color
      ctx.fill()
      ctx.fillStyle = '#334155'
      ctx.fillText(txt, lx + 12, ly + 4)
      lx += tw + 4
    })
  }

  if (!dates.length) {
    ctx.fillStyle = '#b0bec5'
    ctx.font = '13px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('选择项目查看走势', w / 2, legendH + chartH / 2)
    return
  }

  const allVals = series.flatMap(s => s.data)
  let max = Math.max(...allVals, 1)
  let min = Math.min(...allVals, 0)
  if (max === min) { max = min + 1 }
  const range = max - min
  const yo = legendH
  const zeroY = yo + pad.top + ph - (0 - min) / range * ph

  function x(i) { return pad.left + (i + 0.5) * (pw / dates.length) }
  function y(v) { return yo + pad.top + ph - (v - min) / range * ph }

  ctx.strokeStyle = '#dde3ea'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(pad.left, zeroY)
  ctx.lineTo(w - pad.right, zeroY)
  ctx.stroke()

  // 中轴线 + 标签
  const midY = yo + pad.top + ph / 2
  ctx.strokeStyle = '#ee0a24'
  ctx.lineWidth = 1
  ctx.setLineDash([5, 4])
  ctx.beginPath()
  ctx.moveTo(pad.left, midY)
  ctx.lineTo(w - pad.right, midY)
  ctx.stroke()
  ctx.setLineDash([])
  ctx.fillStyle = '#ee0a24'
  ctx.font = '9px sans-serif'
  ctx.textAlign = 'right'
  ctx.fillText('中线', w - pad.right - 4, midY - 5)

  ctx.strokeStyle = '#e8ecf1'
  ctx.lineWidth = 0.5
  const nGrid = 4
  for (let i = 0; i <= nGrid; i++) {
    const gy = yo + pad.top + (ph / nGrid) * i
    ctx.beginPath()
    ctx.moveTo(pad.left, gy)
    ctx.lineTo(w - pad.right, gy)
    ctx.stroke()
    const lv = max - (range / nGrid) * i
    ctx.fillStyle = '#8899bb'
    ctx.font = '9px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText(Math.round(lv), pad.left - 4, gy + 3)
  }

  series.forEach(s => {
    ctx.strokeStyle = s.color
    ctx.lineWidth = 2
    ctx.setLineDash([])
    ctx.beginPath()
    s.data.forEach((v, i) => {
      const px = x(i), py = y(v)
      if (i === 0) ctx.moveTo(px, py)
      else ctx.lineTo(px, py)
    })
    ctx.stroke()

    // 所有数据点都画圆点
    s.data.forEach((v, i) => {
      ctx.beginPath()
      ctx.arc(x(i), y(v), 3, 0, Math.PI * 2)
      ctx.fillStyle = s.color
      ctx.fill()
    })
  })

  ctx.fillStyle = '#64748b'
  ctx.font = '9px sans-serif'
  ctx.textAlign = 'center'
  const step = Math.max(1, Math.floor(dates.length / 7))
  labels.forEach((lb, i) => {
    if (i % step === 0 || i === dates.length - 1) {
      ctx.fillText(lb, x(i), yo + chartH - pad.bottom + 14)
    }
  })
}

async function openModal(period) {
  activeModal.value = period
  showModal.value = true
  modalLoading.value = true
  modalProjects.value = []
  try {
    const data = await api.get('/stats', { params: { period } })
    modalProjects.value = data.data.projects || []
  } catch (e) {
    console.error(e)
  } finally {
    modalLoading.value = false
  }
}

onMounted(async () => {
  try {
    const [s, a, p] = await Promise.all([
      api.get('/stats/summary'),
      api.get('/alerts', { params: { status: 'active' } }),
      api.get('/dashboard/projects'),
    ])
    Object.assign(summary, s.data)
    alertCount.value = a.data.length
    projects.value = p.data.projects || []
    projects.value.sort((a, b) => {
      const aid = a.parent_id || a.id
      const bid = b.parent_id || b.id
      if (aid !== bid) return aid - bid
      return (a.parent_id ? 1 : 0) - (b.parent_id ? 1 : 0)
    })
    const all = new Set(projects.value.map(p => p.id))
    if (all.size > 0) {
      selectedIds.value = all
      loadTrend()
    }
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.dashboard { padding-bottom: 20px; }

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 8px;
}
.sg-block {
  background: #fff;
  border-radius: 14px;
  padding: 12px 10px 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,.05);
  cursor: pointer;
  transition: transform .15s;
  position: relative;
}
.sg-block:active { transform: scale(.97); }
.sg-block.active { box-shadow: 0 0 0 2px #1989fa inset; }

.sg-title { font-size: 12px; font-weight: 700; color: #0a1628; margin-bottom: 6px; }
.sg-date { font-weight: 400; font-size: 10px; color: #8899bb; margin-left: 2px; }

.sg-val-row { font-size: 16px; font-weight: 600; margin-bottom: 1px; color: #334155; }
.sg-val-row span { font-weight: 700; }
.sg-val-row.sub { font-size: 11px; font-weight: 500; color: #64748b; margin-top: 0; }
.sg-val-row .green { color: #07c160; }
.sg-val-row .red { color: #ee0a24; }

.sg-compare {
  border-top: 1px solid #f0f2f5;
  padding-top: 4px;
  margin-top: 2px;
  cursor: pointer;
  border-radius: 0 0 10px 10px;
}
.sg-compare:hover { background: #f8fafd; }
.sg-compare:active { background: #edf2f7; }
.sg-cmp-row { font-size: 9px; color: #b0bec5; line-height: 1.3; }
.sg-cmp-row.main { font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 1px; }
.sg-cmp-row span { color: #64748b; font-weight: 500; }
.sg-cmp-row.main span { font-weight: 700; }
.sg-cmp-row .green { color: #07c160; }
.sg-cmp-row .red { color: #ee0a24; }

.alert-banner {
  margin: 0 8px 8px;
  background: #fff3e0;
  color: #e65100;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.modal-wrap { display: flex; flex-direction: column; max-height: 70vh; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid #f0f2f5; flex-shrink: 0; }
.modal-title { font-size: 16px; font-weight: 700; color: #0a1628; }
.modal-close { font-size: 18px; color: #8899bb; cursor: pointer; padding: 4px; }
.modal-body { flex: 1; overflow-y: auto; padding: 12px 14px; }
.modal-loading { display: flex; justify-content: center; padding: 32px 0; }
.modal-empty { text-align: center; color: #8899bb; padding: 32px 0; font-size: 14px; }

.modal-summary {
  text-align: center; padding: 10px 12px; margin-bottom: 12px;
  background: #f0f4f8; border-radius: 10px; font-size: 13px; color: #334155;
}
.modal-summary b { margin: 0 4px; }
.modal-summary .income { color: #07c160; }
.modal-summary .expense { color: #ee0a24; }
.modal-summary .green { color: #07c160; }
.modal-summary .red { color: #ee0a24; }
.modal-summary.main-only {
  background: #fffbe6; border: 1px solid #ffe58f; font-size: 12px; padding: 8px 12px;
}
.ms-note {
  margin-left: 6px; font-size: 10px; color: #b0a060; font-weight: 400;
}

.modal-proj { margin-bottom: 10px; border: 1px solid #e8ecf1; border-radius: 10px; overflow: hidden; }
.mp-main { padding: 10px 12px; background: #fafbfc; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.mp-num { background: #e8ecf1; color: #4a5a7a; font-weight: 700; min-width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0; }
.mp-name { font-size: 14px; font-weight: 600; color: #0a1628; flex: 1; }
.mp-total { font-size: 15px; font-weight: 700; flex-shrink: 0; }
.mp-total.green { color: #07c160; }
.mp-total.red { color: #ee0a24; }
.mp-sub-total-val { font-size: 13px; font-weight: 600; flex-shrink: 0; }
.mp-sub-total-val.green { color: #07c160; }
.mp-sub-total-val.red { color: #ee0a24; }
.mp-stats { display: flex; align-items: center; gap: 8px; margin-left: auto; flex-wrap: wrap; }
.mps { font-size: 12px; font-variant-numeric: tabular-nums; font-weight: 500; color: #334155; }
.mps.income { color: #07c160; }
.mps.expense { color: #ee0a24; }
.mps.green { color: #07c160; }
.mps.red { color: #ee0a24; }
.mps.budget { display: flex; align-items: center; gap: 4px; color: #1989fa; font-size: 11px; }
.mp-bar { display: inline-block; width: 32px; height: 3px; background: #e8ecf1; border-radius: 2px; overflow: hidden; vertical-align: middle; }
.mp-bar-fill { height: 100%; background: #1989fa; border-radius: 2px; }
.mp-bar-fill.warn { background: #ff976a; }
.mp-bar-fill.danger { background: #ee0a24; }

.mp-sub { padding: 6px 12px 6px 36px; border-top: 1px solid #f0f2f5; display: flex; align-items: center; justify-content: space-between; background: #fff; }
.mp-sub-icon { color: #b0bec5; font-size: 12px; }
.mp-sub-name { font-size: 13px; color: #64748b; }
.mp-sub .mp-stats { margin-left: auto; }

.trend-section {
  margin: 8px;
  background: #fff;
  border-radius: 14px;
  padding: 12px 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.trend-header { margin-bottom: 10px; }
.trend-title { font-size: 13px; font-weight: 700; color: #0a1628; }

.trend-projects {
  display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px;
}
.tp-pill {
  font-size: 11px; padding: 3px 10px; border-radius: 12px;
  background: #f0f2f5; color: #8899bb; cursor: pointer;
  font-weight: 500; transition: all .15s;
}
.tp-pill.on {
  background: #1989fa; color: #fff; font-weight: 600;
}
.tp-pill.sub {
  font-size: 10px; padding-left: 4px; color: #8a9bb5;
  background: #edf2f7; border-left: 2px solid #8a9bb5;
  border-radius: 4px 12px 12px 4px;
}
.tp-pill.sub.on {
  background: #1661ab; color: #fff;
  border-left-color: #fff;
}
.tp-indent { font-size: 11px; color: #8a9bb5; margin: 0 1px 0 2px; }
.tp-bar { display: none; }

.trend-tabs {
  display: flex; gap: 4px; margin-bottom: 8px;
}
.tt-tab {
  font-size: 12px; padding: 3px 14px; border-radius: 14px;
  background: #f0f2f5; color: #64748b; cursor: pointer;
  font-weight: 500; transition: all .15s;
}
.tt-tab.on {
  background: #0a1628; color: #fff;
}

.trend-canvas-wrap {
  width: 100%; overflow: hidden;
}
.trend-canvas {
  display: block; width: 100%;
}
</style>
