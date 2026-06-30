<template>
  <div class="transactions">
    <!-- 统计条 -->
    <div class="stats-bar">
      <div class="st-item income">
        <span class="st-val">¥{{ fmt(stats.total_income) }}</span>
        <span class="st-lbl">收入</span>
      </div>
      <div class="st-item expense">
        <span class="st-val">¥{{ fmt(stats.total_expense) }}</span>
        <span class="st-lbl">支出</span>
      </div>
      <div class="st-item" :class="stats.net >= 0 ? 'income' : 'expense'">
        <span class="st-val">{{ stats.net >= 0 ? '+' : '' }}¥{{ fmt(Math.abs(stats.net)) }}</span>
        <span class="st-lbl">净额</span>
      </div>
    </div>

    <!-- 峰值日 -->
    <div v-if="peaks.positive || peaks.negative" class="peak-bar">
      <div v-if="peaks.positive" class="pk-item pos">
        <span class="pk-lbl">📈 最赚</span>
        <span class="pk-date">{{ peaks.positive.date }}</span>
        <span class="pk-val">+¥{{ fmt(peaks.positive.amount) }}</span>
        <span class="pk-proj">{{ peaks.positive.project_name }}</span>
      </div>
      <div v-if="peaks.negative" class="pk-item neg">
        <span class="pk-lbl">📉 最亏</span>
        <span class="pk-date">{{ peaks.negative.date }}</span>
        <span class="pk-val">¥{{ fmt(peaks.negative.amount) }}</span>
        <span class="pk-proj">{{ peaks.negative.project_name }}</span>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <van-field v-model="filters.start_date" type="date" label="起始" class="fl-item" />
      <van-field v-model="filters.end_date" type="date" label="截止" class="fl-item" />
      <van-field
        v-model="filters.project_name"
        readonly
        is-link
        label="项目"
        placeholder="全部"
        class="fl-item"
        @click="showProjectFilter = true"
      />
      <van-button type="primary" size="small" class="fl-btn" @click="search">查询</van-button>
    </div>

    <!-- 项目筛选弹窗 -->
    <van-popup v-model:show="showProjectFilter" position="bottom" round>
      <van-picker
        :columns="projectColumns"
        @confirm="onProjectConfirm"
        @cancel="showProjectFilter = false"
      />
    </van-popup>

    <!-- 录入按钮 -->
    <div class="add-bar">
      <van-button type="primary" icon="plus" block @click="openAdd">录入</van-button>
    </div>

    <!-- 流水列表 -->
    <div v-if="items.length" class="tx-list">
      <div class="tx-header">
        <span class="th-date">日期</span>
        <span class="th-seq">#</span>
        <span class="th-amount">金额</span>
        <span class="th-project">项目</span>
        <span class="th-remark">备注</span>
        <span class="th-actions">操作</span>
      </div>
      <div v-for="tx in items" :key="tx.id" class="tx-row">
        <span class="td-date">{{ tx.date }}</span>
        <span class="td-seq">{{ tx.day_seq }}</span>
        <span class="td-amount" :class="tx.amount >= 0 ? 'green' : 'red'">
          {{ tx.amount >= 0 ? '+' : '' }}{{ fmt(tx.amount) }}
        </span>
        <span class="td-project">{{ tx.project_name }}</span>
        <span class="td-remark">{{ tx.remark || '-' }}</span>
        <span class="td-actions">
          <van-icon name="edit" class="act-icon" @click="openEdit(tx)" />
          <van-icon name="delete-o" class="act-icon del" @click="delTx(tx)" />
        </span>
      </div>
    </div>
    <van-empty v-else description="暂无流水记录" />

    <!-- 分页 -->
    <div class="pg-wrap" v-if="total > pageSize">
      <van-pagination
        v-model="page"
        :total-items="total"
        :items-per-page="pageSize"
        :show-page-size="3"
        @change="onPageChange"
      />
    </div>

    <!-- 录入/编辑弹窗 -->
    <van-popup v-model:show="showForm" position="center" round :style="{ width: '88%', padding: '20px 16px' }">
      <div class="form-wrap">
        <h3 class="form-title">{{ isEdit ? '编辑流水' : '录入流水' }}</h3>
        <van-field v-model="form.date" type="date" label="日期" />
        <van-field
          v-model="form.amount"
          type="number"
          label="金额"
          placeholder="收入为正，支出为负"
        >
          <template #extra>
            <span class="calc-trigger" @click.stop="openCalc">🧮</span>
          </template>
        </van-field>
        <van-field
          v-model="form.project_name"
          readonly
          is-link
          label="项目"
          placeholder="请选择项目"
          @click="showProjectPicker = true"
        />
        <van-field v-model="form.remark" label="备注" placeholder="选填" />
        <div class="form-btns">
          <van-button round block type="primary" @click="saveTx">保存</van-button>
          <van-button round block plain @click="showForm = false">取消</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 项目选择器(表单用) -->
    <van-popup v-model:show="showProjectPicker" position="bottom" round>
      <van-picker
        :columns="formProjectColumns"
        @confirm="onFormProjectConfirm"
        @cancel="showProjectPicker = false"
      />
    </van-popup>

    <!-- 计算器浮框 -->
    <div v-if="showCalc" class="calc-float" ref="calcRef" :style="calcStyle">
      <div class="calc-dragbar" ref="calcDragbar">
        <span class="calc-title">🧮 计算器</span>
        <span class="calc-close" @click="showCalc = false">✕</span>
      </div>
      <div class="calc-display">
        <div class="calc-expr">{{ calcExpr || '0' }}</div>
        <div class="calc-result">= {{ fmt(calcResult) }}</div>
      </div>
      <div class="calc-keys">
        <button class="calc-key fn" @click="calcClear">C</button>
        <button class="calc-key fn" @click="calcBackspace">⌫</button>
        <button class="calc-key fn" @click="calcToggleSign">±</button>
        <button class="calc-key op" @click="calcOp('/')">÷</button>
        <button class="calc-key num" @click="calcDigit('7')">7</button>
        <button class="calc-key num" @click="calcDigit('8')">8</button>
        <button class="calc-key num" @click="calcDigit('9')">9</button>
        <button class="calc-key op" @click="calcOp('*')">×</button>
        <button class="calc-key num" @click="calcDigit('4')">4</button>
        <button class="calc-key num" @click="calcDigit('5')">5</button>
        <button class="calc-key num" @click="calcDigit('6')">6</button>
        <button class="calc-key op" @click="calcOp('-')">−</button>
        <button class="calc-key num" @click="calcDigit('1')">1</button>
        <button class="calc-key num" @click="calcDigit('2')">2</button>
        <button class="calc-key num" @click="calcDigit('3')">3</button>
        <button class="calc-key op" @click="calcOp('+')">+</button>
        <button class="calc-key num zero" @click="calcDigit('0')">0</button>
        <button class="calc-key num" @click="calcDigit('.')">.</button>
        <button class="calc-key confirm" @click="calcConfirm">✓</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import api from '../api.js'

const route = useRoute()

// ── 数据 ──
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const stats = reactive({ total_income: 0, total_expense: 0, net: 0 })
const peaks = reactive({ positive: null, negative: null })
const projects = ref([])

// ── 筛选 ──
const filters = reactive({
  start_date: '',
  end_date: '',
  project_id: null,
  project_name: '',
})
const showProjectFilter = ref(false)

// 项目列
const projectColumns = computed(() => {
  const cols = [{ text: '全部项目', value: null }]
  for (const p of projects.value) {
    if (p.category === 'sub') continue
    cols.push({ text: p.name, value: p.id })
    const subs = projects.value.filter(s => s.parent_id === p.id && s.category === 'sub')
    for (const s of subs) {
      cols.push({ text: `  └ ${s.name}`, value: s.id })
    }
  }
  return cols
})

// 表单项目列
const formProjectColumns = computed(() => {
  const cols = []
  for (const p of projects.value) {
    if (p.category === 'sub') continue
    cols.push({ text: p.name, value: p.id })
    const subs = projects.value.filter(s => s.parent_id === p.id && s.category === 'sub')
    for (const s of subs) {
      cols.push({ text: `  └ ${s.name}`, value: s.id })
    }
  }
  return cols
})

// ── 表单 ──
const showForm = ref(false)
const showProjectPicker = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = reactive({
  date: '',
  amount: '',
  project_id: null,
  project_name: '',
  remark: '',
})

// ── 计算器 ──
const showCalc = ref(false)
const calcRef = ref(null)
const calcDragbar = ref(null)
const calcPos = reactive({ left: 0, top: 0 })
const calcStyle = computed(() => ({
  left: calcPos.left + 'px',
  top: calcPos.top + 'px',
}))

function initCalcPosition() {
  const w = window.innerWidth
  const h = window.innerHeight
  calcPos.left = Math.max(8, (w - 320) / 2)
  calcPos.top = Math.max(80, (h - 440) / 2)
}

// 拖动逻辑
function setupCalcDrag() {
  if (!calcRef.value || !calcDragbar.value) return
  const el = calcRef.value
  const bar = calcDragbar.value
  let dragging = false, ox = 0, oy = 0
  bar.style.cursor = 'grab'
  bar.addEventListener('pointerdown', (e) => {
    dragging = true
    ox = e.clientX - calcPos.left
    oy = e.clientY - calcPos.top
    bar.setPointerCapture(e.pointerId)
    bar.style.cursor = 'grabbing'
    el.style.transition = 'none'
  })
  bar.addEventListener('pointermove', (e) => {
    if (!dragging) return
    calcPos.left = e.clientX - ox
    calcPos.top = e.clientY - oy
  })
  bar.addEventListener('pointerup', () => {
    dragging = false
    bar.style.cursor = 'grab'
    el.style.transition = 'box-shadow .2s'
  })
}

watch(showCalc, (v) => {
  if (v) {
    initCalcPosition()
    nextTick(setupCalcDrag)
  }
})
const calcExpr = ref('')       // 显示的表达式
const calcCurrent = ref('0')   // 当前输入的数字
const calcOpPending = ref('')  // 待执行的运算符
const calcAccumulator = ref(0) // 累加结果
const calcLastWasOp = ref(false)

const calcResult = computed(() => {
  if (!calcExpr.value) return 0
  // 安全求值：用 Function 计算当前表达式
  try {
    const expr = calcExpr.value.replace(/×/g, '*').replace(/÷/g, '/').replace(/−/g, '-')
    const val = new Function(`return (${expr})`)()
    return isNaN(val) || !isFinite(val) ? 0 : val
  } catch {
    return 0
  }
})

function openCalc() {
  // 如果金额字段已有值，带入计算器
  if (form.amount !== '' && form.amount !== null) {
    calcExpr.value = String(form.amount)
    calcCurrent.value = String(form.amount)
    calcAccumulator.value = Number(form.amount)
    calcOpPending.value = ''
    calcLastWasOp.value = false
  } else {
    calcClear()
  }
  showCalc.value = true
}

function calcDigit(d) {
  if (calcLastWasOp.value) {
    // 运算符后开始新数字
    if (d === '.') {
      calcCurrent.value = '0.'
    } else {
      calcCurrent.value = d
    }
    calcExpr.value += d
    calcLastWasOp.value = false
  } else {
    // 继续输入当前数字
    if (d === '.' && calcCurrent.value.includes('.')) return
    if (calcCurrent.value === '0' && d !== '.') {
      calcCurrent.value = d
      // 替换表达式中最后一个 0
      calcExpr.value = calcExpr.value.slice(0, -1) + d
    } else {
      calcCurrent.value += d
      calcExpr.value += d
    }
  }
}

function calcOp(op) {
  if (calcLastWasOp.value) {
    // 替换上一个运算符
    calcExpr.value = calcExpr.value.slice(0, -1) + op
  } else {
    calcExpr.value += op
    calcLastWasOp.value = true
  }
  calcOpPending.value = op
}

function calcClear() {
  calcExpr.value = ''
  calcCurrent.value = '0'
  calcOpPending.value = ''
  calcAccumulator.value = 0
  calcLastWasOp.value = false
}

function calcBackspace() {
  if (calcExpr.value.length === 0) return
  const last = calcExpr.value.slice(-1)
  calcExpr.value = calcExpr.value.slice(0, -1)
  if ('+−×÷'.includes(last)) {
    calcLastWasOp.value = false
    calcCurrent.value = calcExpr.value.split(/[+−×÷]/).pop() || '0'
  } else {
    calcCurrent.value = calcCurrent.value.slice(0, -1) || '0'
    calcLastWasOp.value = false
  }
}

function calcToggleSign() {
  // 翻转计算结果的正负
  const result = calcResult.value
  if (result === 0) return
  const negated = -result
  calcExpr.value = String(negated)
  calcCurrent.value = String(negated)
  calcLastWasOp.value = false
}

function calcConfirm() {
  form.amount = String(calcResult.value)
  showCalc.value = false
}

// ── 工具函数 ──
function fmt(v) {
  return Number(v || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })
}

// ── 加载项目 ──
async function loadProjects() {
  try {
    const res = await api.get('/projects')
    projects.value = Array.isArray(res.data) ? res.data : (res.data.data || [])
  } catch (e) {
    console.error('加载项目失败:', e)
  }
}

// ── 加载流水 ──
async function loadTx() {
  try {
    const params = {
      page: page.value,
      per_page: pageSize.value,
    }
    if (filters.start_date) params.start_date = filters.start_date
    if (filters.end_date) params.end_date = filters.end_date
    if (filters.project_id) params.project_id = filters.project_id

    const res = await api.get('/transactions', { params })
    const data = res.data

    items.value = data.items || data.data || []
    total.value = data.total || 0

    peaks.positive = data.peak_positive || null
    peaks.negative = data.peak_negative || null

    if (data.total_income !== undefined) {
      stats.total_income = data.total_income
      stats.total_expense = data.total_expense
      stats.net = data.net
    } else {
      stats.total_income = items.value
        .filter(t => Number(t.amount) > 0)
        .reduce((s, t) => s + Number(t.amount), 0)
      stats.total_expense = items.value
        .filter(t => Number(t.amount) < 0)
        .reduce((s, t) => s + Math.abs(Number(t.amount)), 0)
      stats.net = stats.total_income - stats.total_expense
    }
  } catch (e) {
    console.error('加载流水失败:', e)
  }
}

// ── 搜索 / 分页 ──
function search() {
  page.value = 1
  loadTx()
}

function onPageChange(p) {
  page.value = p
  loadTx()
}

// ── 项目筛选确认 ──
function onProjectConfirm({ selectedOptions }) {
  const opt = selectedOptions[0]
  if (opt && opt.value !== null) {
    filters.project_id = opt.value
    filters.project_name = opt.text
  } else {
    filters.project_id = null
    filters.project_name = ''
  }
  showProjectFilter.value = false
  search()
}

// ── 表单操作 ──
function resetForm() {
  form.date = new Date().toISOString().slice(0, 10)
  form.amount = ''
  form.project_id = null
  form.project_name = ''
  form.remark = ''
  isEdit.value = false
  editId.value = null
}

function openAdd() {
  resetForm()
  showForm.value = true
}

function openEdit(tx) {
  isEdit.value = true
  editId.value = tx.id
  form.date = tx.date
  form.amount = String(tx.amount)
  form.project_id = tx.project_id
  form.project_name = tx.project_name
  form.remark = tx.remark || ''
  showForm.value = true
}

function onFormProjectConfirm({ selectedOptions }) {
  const opt = selectedOptions[0]
  if (opt) {
    form.project_id = opt.value
    form.project_name = opt.text
  }
  showProjectPicker.value = false
}

async function saveTx() {
  if (!form.date) {
    showToast('请选择日期')
    return
  }
  if (form.amount === '' || form.amount === null) {
    showToast('请输入金额')
    return
  }
  if (!form.project_id) {
    showToast('请选择项目')
    return
  }

  try {
    const payload = {
      date: form.date,
      amount: Number(form.amount),
      project_id: form.project_id,
      remark: form.remark,
    }
    if (isEdit.value) {
      await api.put(`/transactions/${editId.value}`, payload)
      showToast('修改成功')
    } else {
      await api.post('/transactions', payload)
      showToast('录入成功')
    }
    showForm.value = false
    loadTx()
  } catch (e) {
    console.error('保存失败:', e)
    showToast('保存失败，请重试')
  }
}

async function delTx(tx) {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: `确定删除 ${tx.date} 的这笔流水吗？`,
    })
    await api.delete(`/transactions/${tx.id}`)
    showToast('已删除')
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    loadTx()
  } catch (e) {
    if (e !== 'cancel') console.error('删除失败:', e)
  }
}

// ── 监听路由 query pid ──
watch(
  () => route.query.pid,
  (pid) => {
    if (pid && projects.value.length) {
      const p = projects.value.find(p => p.id === Number(pid))
      if (p) {
        filters.project_id = p.id
        filters.project_name = p.name
      }
    }
  },
)

// ── 初始化 ──
onMounted(async () => {
  await loadProjects()
  if (route.query.pid) {
    const pid = Number(route.query.pid)
    const p = projects.value.find(p => p.id === pid)
    if (p) {
      filters.project_id = p.id
      filters.project_name = p.name
    }
  }
  loadTx()
})
</script>

<style scoped>
.transactions {
  padding-bottom: 20px;
}

/* ── 统计条 ── */
.stats-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}
.st-item {
  flex: 1;
  background: var(--nn-paper);
  border-radius: var(--nn-radius);
  padding: 10px 8px;
  text-align: center;
  box-shadow: var(--nn-shadow-seal);
}
.st-item.income .st-val {
  color: #2d6a4f;
}
.st-item.expense .st-val {
  color: var(--nn-seal);
}
.st-val {
  font-size: 16px;
  font-weight: 800;
  display: block;
  color: var(--nn-ink);
}
.st-lbl {
  font-size: 11px;
  color: var(--nn-lightink);
  margin-top: 2px;
}

/* ── 峰值日 ── */
.peak-bar {
  display: flex; gap: 8px; margin-bottom: 10px;
}
.pk-item {
  flex: 1; background: var(--nn-paper); border-radius: var(--nn-radius);
  padding: 8px 10px; box-shadow: var(--nn-shadow-seal);
  display: flex; align-items: center; gap: 4px; flex-wrap: wrap;
}
.pk-lbl { font-size: 11px; font-weight: 700; flex-shrink: 0; }
.pk-item.pos .pk-lbl { color: #2d6a4f; }
.pk-item.neg .pk-lbl { color: var(--nn-seal); }
.pk-date { font-size: 11px; color: var(--nn-lightink); }
.pk-val { font-size: 14px; font-weight: 800; }
.pk-item.pos .pk-val { color: #2d6a4f; }
.pk-item.neg .pk-val { color: var(--nn-seal); }
.pk-proj {
  font-size: 10px; color: var(--nn-lightink);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  min-width: 0;
}

/* ── 筛选栏 ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 10px;
  background: var(--nn-paper);
  border-radius: var(--nn-radius);
  padding: 4px;
  box-shadow: var(--nn-shadow-seal);
  flex-wrap: wrap;
}
.fl-item {
  flex: 1 1 0;
  min-width: 0;
  padding: 0;
  font-size: 12px;
}
.fl-item :deep(.van-field__label) {
  width: auto;
  margin-right: 2px;
  font-size: 11px;
  color: var(--nn-lightink);
}
.fl-item :deep(.van-field__control) {
  font-size: 12px;
}
.fl-btn {
  flex-shrink: 0;
  margin: 4px;
  height: 32px;
  font-size: 13px;
  padding: 0 14px;
}

/* ── 录入按钮 ── */
.add-bar {
  margin-bottom: 10px;
}

/* ── 流水列表 ── */
.tx-list {
  background: var(--nn-paper);
  border-radius: var(--nn-radius);
  overflow: hidden;
  box-shadow: var(--nn-shadow-seal);
}
.tx-header {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  background: rgba(139,90,43,0.04);
  font-size: 11px;
  color: var(--nn-lightink);
  font-weight: 600;
  border-bottom: 1px solid rgba(139,90,43,0.10);
}
.tx-row {
  display: flex;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid rgba(139,90,43,0.10);
  font-size: 12px;
}
.tx-row:last-child {
  border-bottom: none;
}

/* 列宽分配 */
.th-date,
.td-date {
  width: 80px;
  flex-shrink: 0;
}
.th-seq,
.td-seq {
  width: 28px;
  flex-shrink: 0;
  text-align: center;
  color: var(--nn-lightink);
  font-size: 11px;
}
.th-amount,
.td-amount {
  width: 70px;
  flex-shrink: 0;
  text-align: right;
  font-weight: 700;
}
.th-project,
.td-project {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 4px;
}
.th-remark,
.td-remark {
  width: 56px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--nn-lightink);
  font-size: 11px;
}
.th-actions,
.td-actions {
  width: 44px;
  flex-shrink: 0;
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.td-amount.green {
  color: #2d6a4f;
}
.td-amount.red {
  color: var(--nn-seal);
}

.act-icon {
  font-size: 16px;
  color: var(--nn-accent);
  cursor: pointer;
  padding: 2px;
}
.act-icon.del {
  color: var(--nn-seal);
}

/* ── 分页 ── */
.pg-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: center;
}

/* ── 表单弹窗 ── */
.form-wrap {
  padding: 20px 16px 32px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}
.form-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--nn-ink);
  text-align: center;
  margin-bottom: 16px;
}
.form-btns {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 20px;
}

/* ── 计算器按钮 ── */
.calc-trigger {
  font-size: 22px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  background: #f0f2f5;
  user-select: none;
}
.calc-trigger:active {
  background: #e0e6ed;
}

/* ── 计算器浮框 ── */
.calc-float {
  position: fixed;
  z-index: 3000;
  width: 320px;
  max-width: calc(100vw - 16px);
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  padding: 0 14px 14px;
  transition: box-shadow 0.2s;
  touch-action: none;
}
.calc-dragbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 2px 10px;
  cursor: grab;
  user-select: none;
}
.calc-dragbar:active {
  cursor: grabbing;
}
.calc-title {
  font-size: 15px;
  font-weight: 700;
  color: #0a1628;
}
.calc-close {
  font-size: 18px;
  color: #bbb;
  cursor: pointer;
  padding: 4px 8px;
}
.calc-display {
  background: #f7f8fa;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  text-align: right;
  min-height: 80px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
.calc-expr {
  font-size: 18px;
  color: #0a1628;
  word-break: break-all;
  line-height: 1.4;
  min-height: 25px;
}
.calc-result {
  font-size: 28px;
  font-weight: 800;
  color: #4da6ff;
  margin-top: 8px;
}
.calc-keys {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.calc-key {
  height: 56px;
  border: none;
  border-radius: 28px;
  font-size: 20px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  transition: transform 0.1s, opacity 0.1s;
}
.calc-key:active {
  transform: scale(0.95);
  opacity: 0.8;
}
.calc-key.num {
  background: #fff;
  color: #0a1628;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.calc-key.op {
  background: #e8f0fe;
  color: #4da6ff;
}
.calc-key.fn {
  background: #f0f2f5;
  color: #8899bb;
  font-size: 16px;
}
.calc-key.confirm {
  background: linear-gradient(135deg, #4da6ff, #0a1628);
  color: #fff;
  font-size: 22px;
}
.calc-key.zero {
  grid-column: span 1;
}
</style>
