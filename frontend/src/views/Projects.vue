<template>
  <div class="projects-page">
    <!-- Project Cards List -->
    <van-pull-refresh v-model="refreshing" @refresh="loadProjects">
      <div class="project-cards">
        <template v-for="group in groupedProjects" :key="group.parent?.id || 'orphan'">
          <!-- Main project (expandable if has children) -->
          <div
            v-if="group.parent"
            class="pc-card"
            :class="{ 'pc-expanded': isExpanded(group.parent.id) }"
            @click="openDetail(group.parent)"
          >
            <div class="pc-header">
              <span
                v-if="group.children.length > 0"
                class="pc-expand-icon"
                @click.stop="toggleExpand(group.parent.id)"
              >{{ isExpanded(group.parent.id) ? '▼' : '▶' }}</span>
              <span v-else class="pc-expand-icon" style="visibility:hidden">▶</span>
              <span class="pc-code" style="display:none">{{ group.parent.code }}</span>
              <span class="pc-name">{{ group.parent.name }}</span>
              <span v-if="group.children.length > 0" class="pc-tag" style="background:#07c160">{{ group.children.length }}子</span>
              <span v-if="group.parent.alert_count > 0" class="pc-alert-badge">🔴{{ group.parent.alert_count }}</span>
              <span v-if="group.parent.expansion_total > 0" class="pc-level-badge">L{{ group.parent.expansion_level }}/{{ group.parent.expansion_total }}</span>
            </div>
            <div class="pc-body">
              <div class="pc-net" :class="(group.parent.net_amount || 0) >= 0 ? 'green' : 'red'">
                ¥{{ fmt(group.parent.net_amount || 0) }}
              </div>
              <div class="pc-stats">
                <div class="pc-stat">
                  <div class="pc-bar-wrap">
                    <div
                      class="pc-bar"
                      :style="{ width: Math.min(group.parent.budget_usage || 0, 100) + '%' }"
                      :class="(group.parent.budget_usage || 0) >= 95 ? 'danger' : (group.parent.budget_usage || 0) >= 80 ? 'warn' : ''"
                    ></div>
                  </div>
                  <span class="pc-bar-label">预算 {{ Math.round(group.parent.budget_usage || 0) }}%</span>
                </div>
                <div v-if="group.parent.stop_loss_diff != null" class="pc-stat">
                  <span class="pc-sl" :class="group.parent.stop_loss_diff >= 0 ? 'green' : 'red'">
                    止损差 ¥{{ fmt(group.parent.stop_loss_diff) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Sub-projects (nested, collapsible) -->
          <div v-if="isExpanded(group.parent?.id)" class="pc-sub-list">
            <div
              v-for="sub in group.children"
              :key="sub.id"
              class="pc-card pc-sub-card"
              @click="openDetail(sub)"
            >
              <div class="pc-header">
                <span v-if="false" class="pc-code" style="background:#e8f5e9;color:#07c160">{{ sub.code }}</span>
                <span class="pc-name">{{ sub.name }}</span>
                <span v-if="sub.alert_count > 0" class="pc-alert-badge">🔴{{ sub.alert_count }}</span>
              </div>
              <div class="pc-body">
                <div class="pc-net" :class="(sub.net_amount || 0) >= 0 ? 'green' : 'red'">
                  ¥{{ fmt(sub.net_amount || 0) }}
                </div>
                <div class="pc-stats">
                  <div class="pc-stat">
                    <div class="pc-bar-wrap">
                      <div
                        class="pc-bar"
                        :style="{ width: Math.min(sub.budget_usage || 0, 100) + '%' }"
                        :class="(sub.budget_usage || 0) >= 95 ? 'danger' : (sub.budget_usage || 0) >= 80 ? 'warn' : ''"
                      ></div>
                    </div>
                    <span class="pc-bar-label">预算 {{ Math.round(sub.budget_usage || 0) }}%</span>
                  </div>
                  <div v-if="sub.stop_loss_diff != null" class="pc-stat">
                    <span class="pc-sl" :class="sub.stop_loss_diff >= 0 ? 'green' : 'red'">
                      止损差 ¥{{ fmt(sub.stop_loss_diff) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Orphan sub-projects (no parent exists) -->
        <template v-if="orphanSubs.length > 0">
          <div class="pc-section-label">未关联子项目</div>
          <div
            v-for="sub in orphanSubs"
            :key="sub.id"
            class="pc-card pc-sub-card"
            @click="openDetail(sub)"
          >
            <div class="pc-header">
              <span v-if="false" class="pc-code" style="background:#e8f5e9;color:#07c160">{{ sub.code }}</span>
              <span class="pc-name">{{ sub.name }}</span>
              <span class="pc-tag">子</span>
            </div>
          </div>
        </template>

        <div v-if="!loading && projects.length === 0" class="pc-empty">
          暂无项目，点击下方按钮添加
        </div>
      </div>
    </van-pull-refresh>

    <!-- Add Project Button -->
    <div class="add-section">
      <van-button type="primary" block round @click="openAddDialog">+ 添加项目</van-button>
    </div>

    <!-- ============ Detail Popup ============ -->
    <van-popup
      v-model:show="showDetail"
      position="bottom"
      round
      :style="{ height: '88%' }"
      @closed="onDetailClosed"
    >
      <template v-if="currentProject">
        <div class="detail-container">
          <div class="detail-header">
            <div class="dh-left">
              <span class="dh-title">{{ currentProject.name }}</span>
              <span class="dh-code">{{ currentProject.code }}</span>
            </div>
            <van-icon name="cross" size="20" @click="showDetail = false" />
          </div>

          <van-tabs v-model:active="activeTab" sticky>
            <!-- 基本信息 Tab -->
            <van-tab title="基本信息">
              <div class="tab-content">
                <van-cell-group inset title="项目配置">
                  <van-field
                    v-model="editForm.budget"
                    label="预算(元)"
                    type="number"
                    placeholder="输入预算金额"
                  />
                  <van-field
                    v-model="editForm.stop_loss"
                    label="止损线(元)"
                    type="number"
                    placeholder="输入止损线"
                  />
                  <van-field
                    v-model="editForm.risk_ratio"
                    label="风险比率(%)"
                    type="number"
                    placeholder="输入风险比率"
                  />
                </van-cell-group>

                <div class="tab-actions">
                  <van-button
                    type="primary"
                    block
                    round
                    :loading="saving"
                    @click="saveProject"
                  >
                    保存设置
                  </van-button>
                  <van-button
                    type="danger"
                    block
                    round
                    style="margin-top: 8px"
                    @click="confirmDelete"
                  >
                    删除项目
                  </van-button>
                </div>

                <!-- 子项目入口 — 仅顶层主项目可见 -->
                <div
                  v-if="currentProject.category === 'main' && !currentProject.parent_id"
                  class="sub-project-section"
                >
                  <van-button type="default" block round @click="openAddSubProject">
                    + 子项目
                  </van-button>
                </div>
              </div>
            </van-tab>

            <!-- 递进拓展 Tab -->
            <van-tab title="递进拓展">
              <div class="tab-content">
                <div v-if="levelLoading" class="levels-empty">加载中…</div>
                <div v-else-if="levels.length === 0" class="levels-empty">
                  暂无递进层级，点击下方添加
                </div>
                <div
                  v-for="(lvl, idx) in levels"
                  :key="lvl.id || idx"
                  class="level-card"
                  :class="{ 'lc-met': lvl.met, 'lc-drawdown': lvl.drawdown }"
                  @click="openEditLevel(lvl)"
                >
                  <div class="lc-top">
                    <span class="lc-index">L{{ lvl.level || idx + 1 }}</span>
                    <span class="lc-name">{{ lvl.name }}</span>
                    <span class="lc-status" :class="lvl.drawdown ? 'drawdown' : (lvl.met ? 'met' : 'not-met')">
                      {{ lvl.drawdown ? '⚠️ 已回撤' : (lvl.met ? '✓ 达标' : '✗ 未达标') }}
                    </span>
                  </div>
                  <div v-if="lvl.unlocked" class="lc-unlocked-tag">🔓 已解锁</div>
                  <div class="lc-info">
                    <span v-for="(v, k) in lvl.detail" :key="k" class="lc-condition" :class="v === '✓' ? 'ok' : 'fail'">
                      {{ k }} {{ v }}
                    </span>
                  </div>
                  <div v-if="lvl.conditions?.desc" class="lc-desc-toggle" @click.stop="showLevelDesc(lvl)">
                    📖 说明
                  </div>
                  <van-icon name="delete-o" class="lc-delete" size="16" @click.stop="promptDeleteLevel(lvl, idx)" />
                </div>
                <div class="tab-actions">
                  <van-button type="primary" block round @click="openAddLevel">
                    + 添加层级
                  </van-button>
                </div>
              </div>
            </van-tab>
          </van-tabs>
        </div>
      </template>
    </van-popup>

    <!-- ============ Add Project Popup ============ -->
    <van-popup
      v-model:show="showAddDialog"
      position="bottom"
      round
      :style="{ height: 'auto', maxHeight: '85%' }"
    >
      <div class="add-form">
        <h3 class="af-title">{{ isAddingSub ? '添加子项目' : '添加项目' }}</h3>
        <van-cell-group inset>
          <van-field
            v-model="addForm.name"
            label="项目名称"
            placeholder="输入项目名称"
          />
          <van-field
            v-model="addForm.code"
            label="项目代码"
            placeholder="输入项目代码"
          />
          <van-field
            v-model="addForm.category_label"
            label="项目类别"
            readonly
            is-link
            placeholder="选择类别"
            @click="showCategoryPicker = true"
          />
          <van-field
            v-if="addForm.category === 'sub'"
            v-model="addForm.parent_label"
            label="父项目"
            readonly
            is-link
            placeholder="选择父项目"
            @click="showParentPicker = true"
          />
        </van-cell-group>
        <div class="af-actions">
          <van-button block round @click="showAddDialog = false">取消</van-button>
          <van-button
            type="primary"
            block
            round
            :loading="adding"
            @click="addProject"
          >
            确认添加
          </van-button>
        </div>
      </div>
    </van-popup>

    <!-- Category Picker -->
    <van-popup v-model:show="showCategoryPicker" position="bottom" round>
      <van-picker
        :columns="categoryColumns"
        :default-index="0"
        @confirm="onCategoryConfirm"
        @cancel="showCategoryPicker = false"
      />
    </van-popup>

    <!-- Parent Project Picker -->
    <van-popup v-model:show="showParentPicker" position="bottom" round>
      <van-picker
        :columns="parentColumns"
        :default-index="0"
        @confirm="onParentConfirm"
        @cancel="showParentPicker = false"
      />
    </van-popup>

    <!-- Add/Edit Level Popup -->
    <van-popup
      v-model:show="showAddLevel"
      position="bottom"
      round
      :style="{ height: 'auto' }"
    >
      <div class="add-form">
        <h3 class="af-title">{{ editingLevelId ? '编辑递进层级' : '添加递进层级' }}</h3>
        <van-cell-group inset>
          <van-field
            v-model="levelForm.name"
            label="名称"
            placeholder="如：第1级"
          />
          <van-field
            v-model="levelForm.net_min"
            label="净值下限"
            type="number"
            placeholder="净值达到此值进入本级"
          />
          <van-field
            v-model="levelForm.budget_max"
            label="预算上限(%)"
            type="number"
            placeholder="预算使用率不超过"
          />
        </van-cell-group>
        <div class="af-actions">
          <van-button block round @click="showAddLevel = false">取消</van-button>
          <van-button
            type="primary"
            block
            round
            :loading="levelSaving"
            @click="saveLevel"
          >
            确认
          </van-button>
        </div>
      </div>
    </van-popup>

    <van-dialog v-model:show="showDescPopup" title="📖 递进说明" :message="descText" message-align="left" confirm-button-text="知道了" />

  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { showDialog, showToast } from 'vant'
import api from '../api.js'

// ============ State ============
const projects = ref([])
const loading = ref(false)
const refreshing = ref(false)
const saving = ref(false)
const adding = ref(false)
const levelSaving = ref(false)
const levelLoading = ref(false)

const showDetail = ref(false)
const currentProject = ref(null)
const activeTab = ref(0)

const showAddDialog = ref(false)
const isAddingSub = ref(false)
const showCategoryPicker = ref(false)
const showParentPicker = ref(false)

const showAddLevel = ref(false)
const editingLevelId = ref(null)
const levels = ref([])
const showDescPopup = ref(false)
const descText = ref('')

// ============ Collapse state ============
const expandedParents = ref(new Set())

function isExpanded(id) {
  return expandedParents.value.has(id)
}
function toggleExpand(id) {
  const s = new Set(expandedParents.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  expandedParents.value = s
}

// ============ Grouped projects ============
const groupedProjects = computed(() => {
  const groups = {}
  const orphanSubs = []
  
  for (const p of projects.value) {
    if (p.category === 'main') {
      if (!groups[p.id]) groups[p.id] = { parent: p, children: [] }
      else groups[p.id].parent = p
    } else if (p.category === 'sub') {
      if (p.parent_id && groups[p.parent_id]) {
        groups[p.parent_id].children.push(p)
      } else {
        orphanSubs.push(p)
      }
    } else {
      // 'other' category treated as top-level
      if (!groups[p.id]) groups[p.id] = { parent: p, children: [] }
      else groups[p.id].parent = p
    }
  }
  return Object.values(groups)
})

// Expose orphan sub-projects separately
const orphanSubs = computed(() => {
  const result = []
  for (const p of projects.value) {
    if (p.category === 'sub') {
      const parent = projects.value.find(x => x.id === p.parent_id)
      if (!parent) result.push(p)
    }
  }
  return result
})

// ============ Forms ============
const editForm = reactive({
  budget: '',
  stop_loss: '',
  risk_ratio: ''
})

const addForm = reactive({
  name: '',
  code: '',
  category: '',
  category_label: '',
  parent_id: null,
  parent_label: ''
})

const levelForm = reactive({
  name: '',
  net_min: '',
  budget_max: ''
})

// ============ Picker Columns ============
const categoryColumns = [
  { text: '主项目', value: 'main' },
  { text: '子项目', value: 'sub' }
]

const parentColumns = ref([])

// ============ Helpers ============
function fmt(v) {
  return Number(v || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })
}

function parentName(p) {
  if (!p.parent_id) return ''
  const parent = projects.value.find(x => x.id === p.parent_id)
  return parent ? parent.name : ''
}

// ============ API ============
async function loadProjects() {
  loading.value = true
  try {
    const { data } = await api.get('/projects')
    projects.value = Array.isArray(data) ? data : (data.projects || [])
  } catch (e) {
    console.error('加载项目失败', e)
    showToast('加载失败')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function loadLevels(projectId) {
  levelLoading.value = true
  levels.value = []
  try {
    const { data } = await api.get(`/expansion/${projectId}`)
    levels.value = Array.isArray(data) ? data : (data.levels || [])
  } catch (e) {
    console.error('加载层级失败', e)
  } finally {
    levelLoading.value = false
  }
}

// ============ Detail ============
function openDetail(p) {
  currentProject.value = { ...p }
  editForm.budget = p.budget ?? ''
  editForm.stop_loss = p.stop_loss ?? ''
  editForm.risk_ratio = p.risk_ratio ?? ''
  activeTab.value = 0
  showDetail.value = true
  loadLevels(p.id)
}

function onDetailClosed() {
  currentProject.value = null
  levels.value = []
}

async function saveProject() {
  saving.value = true
  try {
    await api.put(`/projects/${currentProject.value.id}`, {
      budget: Number(editForm.budget) || 0,
      stop_loss: Number(editForm.stop_loss) || 0,
      risk_ratio: Number(editForm.risk_ratio) || 0
    })
    showToast('保存成功')
    currentProject.value.budget = Number(editForm.budget) || 0
    currentProject.value.stop_loss = Number(editForm.stop_loss) || 0
    currentProject.value.risk_ratio = Number(editForm.risk_ratio) || 0
    loadProjects()
  } catch (e) {
    console.error('保存失败', e)
    showToast('保存失败')
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  showDialog({
    title: '确认删除',
    message: `确定要删除项目「${currentProject.value.name}」吗？此操作不可撤销。`,
    confirmButtonText: '确认删除',
    confirmButtonColor: '#ee0a24'
  }).then(async () => {
    try {
      await api.delete(`/projects/${currentProject.value.id}`)
      showToast('已删除')
      showDetail.value = false
      loadProjects()
    } catch (e) {
      console.error('删除失败', e)
      showToast('删除失败')
    }
  }).catch(() => {})
}

// ============ Add Project ============
function openAddDialog() {
  resetAddForm()
  isAddingSub.value = false
  addForm.code = generateCode()
  showAddDialog.value = true
}

function openAddSubProject() {
  resetAddForm()
  isAddingSub.value = true
  addForm.category = 'sub'
  addForm.category_label = '子项目'
  addForm.parent_id = currentProject.value.id
  addForm.parent_label = currentProject.value.name
  addForm.code = generateCode()
  showAddDialog.value = true
}

function generateCode() {
  const now = new Date()
  const y = String(now.getFullYear()).slice(-2)
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const dateStr = `${y}${m}${d}`
  
  // 统计已有主项目数（排除"其他"），用作序号
  const mainCount = projects.value.filter(p => p.category === 'main').length
  const num = String(mainCount + 1).padStart(3, '0')
  
  // 当日已有项目数
  const todayPattern = `-${dateStr}-`
  const todayCount = projects.value.filter(p => (p.code || '').includes(todayPattern)).length
  const seq = String(todayCount + 1).padStart(3, '0')
  
  return `A${num}-${dateStr}-${seq}`
}

function resetAddForm() {
  addForm.name = ''
  addForm.code = ''
  addForm.category = ''
  addForm.category_label = ''
  addForm.parent_id = null
  addForm.parent_label = ''
}

function onCategoryConfirm({ selectedOptions }) {
  const opt = selectedOptions[0]
  addForm.category = opt.value
  addForm.category_label = opt.text
  if (addForm.category !== 'sub') {
    addForm.parent_id = null
    addForm.parent_label = ''
  }
  showCategoryPicker.value = false
}

function onParentConfirm({ selectedOptions }) {
  const opt = selectedOptions[0]
  addForm.parent_id = opt.value
  addForm.parent_label = opt.text
  showParentPicker.value = false
}

// Rebuild parent picker columns from main projects
function buildParentColumns() {
  parentColumns.value = projects.value
    .filter(p => p.category === 'main' && !p.parent_id)
    .map(p => ({ text: `${p.code} ${p.name}`, value: p.id }))
}

async function addProject() {
  if (!addForm.name.trim() || !addForm.code.trim()) {
    showToast('请填写名称和代码')
    return
  }
  if (!addForm.category) {
    showToast('请选择类别')
    return
  }
  if (addForm.category === 'sub' && !addForm.parent_id) {
    showToast('请选择父项目')
    return
  }

  adding.value = true
  try {
    const payload = {
      name: addForm.name.trim(),
      code: addForm.code.trim(),
      category: addForm.category
    }
    if (addForm.category === 'sub') {
      payload.parent_id = addForm.parent_id
    }
    await api.post('/projects', payload)
    showToast('项目已添加')
    showAddDialog.value = false
    loadProjects()
  } catch (e) {
    console.error('添加失败', e)
    showToast('添加失败')
  } finally {
    adding.value = false
  }
}

// ============ Levels ============
function openAddLevel() {
  editingLevelId.value = null
  levelForm.name = ''
  levelForm.net_min = ''
  levelForm.budget_max = ''
  showAddLevel.value = true
}

function openEditLevel(lvl) {
  editingLevelId.value = lvl.id
  levelForm.name = lvl.name || ''
  levelForm.net_min = lvl.conditions?.net_min ?? ''
  levelForm.budget_max = lvl.conditions?.budget_max ?? ''
  showAddLevel.value = true
}

function showLevelDesc(lvl) {
  descText.value = lvl.conditions?.desc || '暂无说明'
  showDescPopup.value = true
}

async function saveLevel() {
  if (!levelForm.name || levelForm.net_min === '' || levelForm.budget_max === '') {
    showToast('请填写完整')
    return
  }
  levelSaving.value = true
  try {
    const payload = {
      project_id: currentProject.value.id,
      level: levels.value.length + 1,
      name: levelForm.name,
      conditions: JSON.stringify({ net_min: Number(levelForm.net_min), budget_max: Number(levelForm.budget_max) })
    }
    if (editingLevelId.value) {
      await api.put(`/expansion/${editingLevelId.value}`, payload)
      showToast('已更新')
    } else {
      await api.post('/expansion', payload)
      showToast('已添加')
    }
    showAddLevel.value = false
    editingLevelId.value = null
    loadLevels(currentProject.value.id)
  } catch (e) {
    console.error('保存层级失败', e)
    showToast('保存失败')
  } finally {
    levelSaving.value = false
  }
}

function promptDeleteLevel(lvl, idx) {
  const name = lvl.name || `L${lvl.level || idx + 1}`
  showDialog({
    title: '删除层级',
    message: `确定删除「${name}」？`,
    confirmButtonText: '删除',
    confirmButtonColor: '#ee0a24'
  }).then(() => deleteLevel(lvl))
    .catch(() => {})
}

async function deleteLevel(lvl) {
  try {
    await api.delete(`/expansion/${lvl.id}`)
    showToast('已删除')
    loadLevels(currentProject.value.id)
  } catch (e) {
    console.error('删除层级失败', e)
    showToast('删除失败')
  }
}

// ============ Lifecycle ============
onMounted(() => {
  loadProjects()
})

watch(projects, () => buildParentColumns(), { immediate: true })
</script>

<style scoped>
.projects-page {
  padding-bottom: 80px;
}

/* ── Expand/Collapse ── */
.pc-expand-icon {
  font-size: 11px;
  color: var(--nn-lightink);
  cursor: pointer;
  width: 16px;
  flex-shrink: 0;
  user-select: none;
}
.pc-expanded {
  border-bottom-left-radius: 4px;
  border-bottom-right-radius: 4px;
}

/* ── Sub-project list ── */
.pc-sub-list {
  margin-left: 24px;
  margin-top: 4px;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pc-sub-card {
  border-left: 3px solid #2d6a4f;
  padding: 10px 14px;
}

/* ── Section label ── */
.pc-section-label {
  font-size: 12px;
  color: var(--nn-lightink);
  padding: 8px 0 4px 4px;
  font-weight: 600;
}

.pc-card {
  background: var(--nn-paper);
  border-radius: var(--nn-radius);
  padding: 14px 16px;
  box-shadow: var(--nn-shadow-seal);
  cursor: pointer;
  transition: box-shadow .2s var(--nn-ease);
}
.pc-card:active {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.pc-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.pc-code {
  background: rgba(139,90,43,0.12);
  color: var(--nn-ink);
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.pc-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--nn-ink);
  flex: 1;
}
.pc-tag {
  background: var(--nn-accent);
  color: var(--nn-paper);
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 600;
}
.pc-parent {
  font-size: 11px;
  color: var(--nn-lightink);
  white-space: nowrap;
}
.pc-alert-badge {
  font-size: 12px;
}
.pc-level-badge {
  background: linear-gradient(135deg, var(--nn-accent), #7c4dff);
  color: var(--nn-paper);
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 700;
  margin-left: 4px;
}

.pc-body {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.pc-net {
  font-size: 20px;
  font-weight: 800;
}
.pc-net.green {
  color: #2d6a4f;
}
.pc-net.red {
  color: var(--nn-seal);
}

.pc-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.pc-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.pc-bar-wrap {
  width: 60px;
  height: 6px;
  background: rgba(139,90,43,0.12);
  border-radius: 3px;
  overflow: hidden;
}
.pc-bar {
  height: 100%;
  background: var(--nn-accent);
  border-radius: 3px;
  transition: width .3s var(--nn-ease);
}
.pc-bar.warn {
  background: #ff976a;
}
.pc-bar.danger {
  background: var(--nn-seal);
}
.pc-bar-label {
  font-size: 11px;
  color: var(--nn-lightink);
  margin-top: 2px;
}
.pc-sl {
  font-size: 12px;
  font-weight: 600;
}
.pc-sl.green {
  color: #2d6a4f;
}
.pc-sl.red {
  color: var(--nn-seal);
}

.pc-empty {
  text-align: center;
  padding: 40px 0;
  color: var(--nn-lightink);
  font-size: 14px;
}

/* ── Add Section ── */
.add-section {
  position: fixed;
  bottom: 60px;
  left: 0;
  right: 0;
  padding: 10px 16px;
  background: linear-gradient(transparent, rgba(139,90,43,0.06) 40%);
}

/* ── Detail Popup ── */
.detail-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 16px 8px;
  flex-shrink: 0;
}
.dh-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.dh-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--nn-ink);
}
.dh-code {
  font-size: 12px;
  color: var(--nn-lightink);
}

/* ── Tabs ── */
.tab-content {
  padding: 12px 0 24px;
}

.tab-actions {
  padding: 16px 16px 0;
}

.sub-project-section {
  margin-top: 16px;
  padding: 0 16px;
}

/* ── Level Cards ── */
.levels-empty {
  text-align: center;
  padding: 36px 16px;
  color: var(--nn-lightink);
  font-size: 14px;
}

.level-card {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  background: var(--nn-paper);
  margin: 6px 16px;
  padding: 12px 14px;
  border-radius: var(--nn-radius);
  box-shadow: var(--nn-shadow-seal);
  cursor: pointer;
  transition: all .2s var(--nn-ease);
  border-left: 3px solid rgba(139,90,43,0.12);
  position: relative;
}
.level-card:active { background: rgba(139,90,43,0.06); }
.level-card.lc-met { border-left-color: #2d6a4f; }
.level-card.lc-drawdown { border-left-color: #ff976a; background: rgba(139,90,43,0.04); }

.lc-top {
  display: flex; align-items: center; gap: 8px; flex: none;
  padding-right: 30px;
}
.lc-index {
  width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg, var(--nn-accent), #0a5fd8);
  color: var(--nn-paper); font-weight: 800; font-size: 12px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.lc-name {
  font-size: 14px; font-weight: 600; color: var(--nn-ink); flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.lc-status {
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; flex-shrink: 0;
}
.lc-status.met { background: rgba(45,106,79,0.10); color: #2d6a4f; }
.lc-status.not-met { background: #fff3e0; color: #ff976a; }
.lc-status.drawdown { background: #fef3e7; color: #ff6b00; }

.lc-unlocked-tag {
  font-size: 11px; color: var(--nn-accent); padding: 1px 6px;
  background: rgba(139,90,43,0.06); border-radius: 4px; flex-shrink: 0;
  align-self: flex-start;
}

.lc-info {
  flex: 1;
  display: flex; flex-direction: column; gap: 2px;
  padding-left: 40px;
}
.lc-condition {
  font-size: 12px; color: var(--nn-ink); font-weight: 500;
}
.lc-condition.ok { color: #2d6a4f; }
.lc-condition.fail { color: var(--nn-seal); }

.lc-delete {
  position: absolute; top: 10px; right: 10px;
  color: var(--nn-seal); padding: 6px; cursor: pointer; flex-shrink: 0;
}

.lc-desc-toggle {
  font-size: 12px; color: var(--nn-accent); cursor: pointer;
  padding: 4px 0; user-select: none;
}
.lc-desc-toggle:active { opacity: 0.7; }

/* ── Add Form Popup ── */
.add-form {
  padding: 16px 0 24px;
}
.af-title {
  text-align: center;
  font-size: 17px;
  font-weight: 700;
  color: var(--nn-ink);
  margin-bottom: 12px;
}
.af-actions {
  display: flex;
  gap: 10px;
  padding: 16px 16px 0;
}

/* ── Level form inside dialog ── */
.level-form {
  padding: 12px 0;
}
</style>
