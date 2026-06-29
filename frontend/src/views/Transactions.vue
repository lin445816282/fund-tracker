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

    <!-- 录入/编辑弹窗 — 居中弹框 -->
    <van-popup v-model:show="showForm" position="center" round :style="{ width: '88%', padding: '20px 16px' }">
      <div class="form-wrap">
        <h3 class="form-title">{{ isEdit ? '编辑流水' : '录入流水' }}</h3>
        <van-field v-model="form.date" type="date" label="日期" />
        <van-field
          v-model="form.amount"
          type="number"
          label="金额"
          placeholder="收入为正，支出为负"
        />
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
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

// 项目列: 始终包含"全部"选项，子项目缩进显示
const projectColumns = computed(() => {
  const cols = [{ text: '全部项目', value: null }]
  for (const p of projects.value) {
    if (p.category === 'sub') continue // 子项目稍后追加到父项目下
    cols.push({ text: p.name, value: p.id })
    // 添加该主项目的子项目
    const subs = projects.value.filter(s => s.parent_id === p.id && s.category === 'sub')
    for (const s of subs) {
      cols.push({ text: `  └ ${s.name}`, value: s.id })
    }
  }
  return cols
})

// 表单项目列: 不含"全部"，子项目缩进
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
    // api.js 默认返回 axios response，data 在 res.data
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

    // 峰值日
    peaks.positive = data.peak_positive || null
    peaks.negative = data.peak_negative || null

    // 优先使用后端返回的统计
    if (data.total_income !== undefined) {
      stats.total_income = data.total_income
      stats.total_expense = data.total_expense
      stats.net = data.net
    } else {
      // fallback: 客户端计算
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
    // 如果删除后当前页没数据了且不是第1页，回退一页
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    loadTx()
  } catch (e) {
    // 用户取消删除或其他错误
    if (e !== 'cancel') console.error('删除失败:', e)
  }
}

// ── 监听路由 query pid，自动预填项目筛选 ──
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
  // 如果从 Dashboard 带 pid 进来
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
  background: #fff;
  border-radius: 10px;
  padding: 10px 8px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.st-item.income .st-val {
  color: #07c160;
}
.st-item.expense .st-val {
  color: #ee0a24;
}
.st-val {
  font-size: 16px;
  font-weight: 800;
  display: block;
  color: #0a1628;
}
.st-lbl {
  font-size: 11px;
  color: #8899bb;
  margin-top: 2px;
}

/* ── 峰值日 ── */
.peak-bar {
  display: flex; gap: 8px; margin-bottom: 10px;
}
.pk-item {
  flex: 1; background: #fff; border-radius: 10px;
  padding: 8px 10px; box-shadow: 0 1px 3px rgba(0,0,0,.05);
  display: flex; align-items: center; gap: 4px; flex-wrap: wrap;
}
.pk-lbl { font-size: 11px; font-weight: 700; flex-shrink: 0; }
.pk-item.pos .pk-lbl { color: #07c160; }
.pk-item.neg .pk-lbl { color: #ee0a24; }
.pk-date { font-size: 11px; color: #8899bb; }
.pk-val { font-size: 14px; font-weight: 800; }
.pk-item.pos .pk-val { color: #07c160; }
.pk-item.neg .pk-val { color: #ee0a24; }
.pk-proj {
  font-size: 10px; color: #8899bb;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  min-width: 0;
}

/* ── 筛选栏 ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 10px;
  background: #fff;
  border-radius: 10px;
  padding: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
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
  color: #8899bb;
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
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.tx-header {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  background: #f8f9fb;
  font-size: 11px;
  color: #8899bb;
  font-weight: 600;
  border-bottom: 1px solid #f0f2f5;
}
.tx-row {
  display: flex;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #f5f6f8;
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
  color: #8899bb;
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
  color: #8899bb;
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
  color: #07c160;
}
.td-amount.red {
  color: #ee0a24;
}

.act-icon {
  font-size: 16px;
  color: #1989fa;
  cursor: pointer;
  padding: 2px;
}
.act-icon.del {
  color: #ee0a24;
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
  color: #0a1628;
  text-align: center;
  margin-bottom: 16px;
}
.form-btns {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 20px;
}
</style>
