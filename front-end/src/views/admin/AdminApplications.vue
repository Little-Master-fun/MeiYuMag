<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import { useNotificationsStore } from '@/stores/notifications'
import axios from 'axios'
import {
  Search, Building2, Key, ChevronRight, CheckCircle,
  XCircle, AlertCircle, MessageSquare, Loader2, X, Check,
  SlidersHorizontal, MoreHorizontal
} from 'lucide-vue-next'

const notify = useNotificationsStore()
const applications = ref<any[]>([])
const loading = ref(true)
const searchText = ref('')
const filterStatus = ref('')
const filterType = ref('')

// Review modal
const reviewModal = ref(false)
const selectedApp = ref<any>(null)
const reviewDecision = ref<'approved' | 'rejected' | 'supplement'>('approved')
const reviewNote = ref('')
const reviewSubmitting = ref(false)

onMounted(async () => {
  await loadApps()
})

async function loadApps() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/v1/admin/applications')
    applications.value = data
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  return applications.value.filter(a => {
    const search  = !searchText.value || (a.organization ?? '').includes(searchText.value) || String(a.id).includes(searchText.value)
    const status  = !filterStatus.value || a.status === filterStatus.value
    const type    = !filterType.value   || a.app_type === filterType.value
    return search && status && type
  })
})

function openReview(app: any) {
  selectedApp.value = app
  reviewDecision.value = 'approved'
  reviewNote.value = ''
  reviewModal.value = true
}

async function submitReview() {
  if (!selectedApp.value) return
  reviewSubmitting.value = true
  try {
    if (reviewDecision.value === 'supplement') {
      await axios.post(`/api/v1/admin/applications/${selectedApp.value.id}/supplement`, {
        note: reviewNote.value,
      })
      notify.success('已请求补充材料')
    } else {
      await axios.patch(`/api/v1/admin/applications/${selectedApp.value.id}/status`, {
        status: reviewDecision.value === 'approved' ? 'admin_submitted' : 'cancelled',
      })
      notify.success(reviewDecision.value === 'approved' ? '申请已通过' : '申请已拒绝')
    }
    reviewModal.value = false
    await loadApps()
  } catch (e: any) {
    notify.error('操作失败', e.response?.data?.detail)
  } finally {
    reviewSubmitting.value = false
  }
}

const statusConfig: Record<string, { label: string; cls: string }> = {
  draft:               { label: '草稿',     cls: 'status-gray' },
  ai_reviewing:        { label: 'AI审核中', cls: 'status-purple' },
  ai_passed:           { label: 'AI通过',   cls: 'status-teal' },
  ai_rejected:         { label: 'AI拒绝',   cls: 'status-red' },
  pending_signed:      { label: '待签字',   cls: 'status-amber' },
  pending_admin:       { label: '待管理员', cls: 'status-blue' },
  supplement_required: { label: '需补充',   cls: 'status-orange' },
  admin_submitted:     { label: '已提交',   cls: 'status-teal' },
  completed:           { label: '已完成',   cls: 'status-green' },
  cancelled:           { label: '已取消',   cls: 'status-gray' },
}

const typeConfig: Record<string, { label: string; icon: any }> = {
  meiyu:   { label: '美育场地', icon: Building2 },
  yueyuan: { label: '月苑三楼', icon: Building2 },
  key:     { label: '钥匙借用', icon: Key },
}

const statusOptions = [
  { value: '',              label: '全部状态' },
  { value: 'pending_admin', label: '待管理员' },
  { value: 'supplement_required', label: '需补充' },
  { value: 'ai_reviewing',  label: 'AI审核中' },
  { value: 'completed',     label: '已完成' },
  { value: 'cancelled',     label: '已取消' },
]

const typeOptions = [
  { value: '',        label: '全部类型' },
  { value: 'meiyu',   label: '美育场地' },
  { value: 'yueyuan', label: '月苑三楼' },
  { value: 'key',     label: '钥匙借用' },
]

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const canReview = (app: any) => ['pending_admin', 'supplement_required'].includes(app.status)
</script>

<template>
  <AppLayout>
    <div class="admin-apps">

      <!-- Header -->
      <div class="page-header">
        <div>
          <h1>申请管理</h1>
          <p>共 <span class="accent">{{ applications.length }}</span> 条申请</p>
        </div>
      </div>

      <!-- Filter bar -->
      <div class="filter-bar">
        <div class="search-wrap">
          <Search :size="15" class="search-icon" />
          <input v-model="searchText" placeholder="搜索申请ID、组织名称..." class="search-input" />
        </div>
        <select v-model="filterType"   class="filter-select">
          <option v-for="o in typeOptions"   :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <select v-model="filterStatus" class="filter-select">
          <option v-for="o in statusOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </div>

      <!-- Table -->
      <div class="table-wrap">
        <div class="table-header">
          <span>申请信息</span>
          <span>申请人</span>
          <span>时间</span>
          <span>状态</span>
          <span>操作</span>
        </div>

        <div v-if="loading" class="skeleton-list">
          <div v-for="i in 6" :key="i" class="skeleton-row-full">
            <div class="skeleton-line w-1/3" />
            <div class="skeleton-line w-1/4" />
            <div class="skeleton-line w-1/5" />
            <div class="skeleton-line w-1/6" />
          </div>
        </div>

        <TransitionGroup v-else name="row-list" tag="div">
          <div
            v-for="app in filtered"
            :key="app.id"
            class="table-row"
            :class="{ 'row-needs-action': canReview(app) }"
          >
            <!-- App info -->
            <div class="row-info">
              <div class="row-icon" :class="app.app_type === 'key' ? 'icon-amber' : 'icon-teal'">
                <component :is="typeConfig[app.app_type]?.icon ?? Building2" :size="15" />
              </div>
              <div>
                <p class="row-title">{{ typeConfig[app.app_type]?.label ?? app.app_type }} #{{ app.id }}</p>
                <p class="row-org">{{ app.organization || '—' }}</p>
              </div>
            </div>

            <!-- User -->
            <div class="row-user">{{ app.user_email || '—' }}</div>

            <!-- Date -->
            <div class="row-date">{{ formatDate(app.created_at) }}</div>

            <!-- Status -->
            <span class="status-badge" :class="statusConfig[app.status]?.cls ?? 'status-gray'">
              {{ statusConfig[app.status]?.label ?? app.status }}
            </span>

            <!-- Actions -->
            <div class="row-actions">
              <button
                v-if="canReview(app)"
                class="action-btn action-review"
                @click="openReview(app)"
              >
                <CheckCircle :size="14" /> 审核
              </button>
              <button class="action-btn action-view" @click="$router.push(`/applications/${app.id}`)">
                <ChevronRight :size="14" />
              </button>
            </div>
          </div>
        </TransitionGroup>

        <div v-if="!loading && filtered.length === 0" class="empty-state">
          <Search :size="28" class="opacity-30" />
          <p>没有匹配的申请</p>
        </div>
      </div>
    </div>

    <!-- Review Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="reviewModal" class="modal-overlay" @click.self="reviewModal = false">
          <div class="modal">
            <div class="modal-head">
              <h3>审核申请 #{{ selectedApp?.id }}</h3>
              <button class="modal-close" @click="reviewModal = false"><X :size="18" /></button>
            </div>

            <div class="modal-body">
              <p class="modal-label">选择审核结果</p>
              <div class="decision-grid">
                <button
                  v-for="d in [
                    { value: 'approved',   label: '通过申请',   icon: CheckCircle,  cls: 'dec-pass' },
                    { value: 'supplement', label: '请求补充',   icon: AlertCircle, cls: 'dec-warn' },
                    { value: 'rejected',   label: '拒绝申请',   icon: XCircle,      cls: 'dec-fail' },
                  ]"
                  :key="d.value"
                  class="dec-btn"
                  :class="[d.cls, { selected: reviewDecision === d.value }]"
                  @click="reviewDecision = d.value as any"
                >
                  <component :is="d.icon" :size="18" />
                  {{ d.label }}
                </button>
              </div>

              <div v-if="reviewDecision !== 'approved'" class="note-field">
                <label class="modal-label">
                  {{ reviewDecision === 'supplement' ? '补充要求说明' : '拒绝原因' }}
                </label>
                <textarea
                  v-model="reviewNote"
                  rows="3"
                  :placeholder="reviewDecision === 'supplement' ? '请说明需要补充的材料...' : '请说明拒绝原因...'"
                  class="modal-textarea"
                />
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-cancel" @click="reviewModal = false">取消</button>
              <button
                class="btn-confirm"
                :class="{
                  'btn-pass': reviewDecision === 'approved',
                  'btn-warn': reviewDecision === 'supplement',
                  'btn-fail': reviewDecision === 'rejected',
                }"
                :disabled="reviewSubmitting"
                @click="submitReview"
              >
                <Loader2 v-if="reviewSubmitting" :size="15" class="animate-spin" />
                <span v-else>确认提交</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </AppLayout>
</template>

<style scoped>
.admin-apps { display: flex; flex-direction: column; gap: 20px; }

.page-header h1 {
  margin: 0 0 4px; font-size: 22px; font-weight: 800; color: #e8f5f0;
  animation: float-up 0.4s ease both;
}
.page-header p { margin: 0; font-size: 13px; color: rgba(232,245,240,0.5); }
.accent { color: #3DD9AC; font-weight: 700; }

/* Filter bar */
.filter-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 12px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07); border-radius: 12px;
  animation: float-up 0.4s ease both 0.05s;
}

.search-wrap { flex: 1; min-width: 200px; position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 11px; color: rgba(232,245,240,0.35); }
.search-input {
  width: 100%; padding: 9px 12px 9px 34px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px; color: #e8f5f0; font-size: 13px; transition: border-color 0.2s;
}
.search-input::placeholder { color: rgba(232,245,240,0.3); }
.search-input:focus { outline: none; border-color: rgba(61,217,172,0.4); }

.filter-select {
  padding: 8px 12px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px; color: rgba(232,245,240,0.8); font-size: 13px; cursor: pointer;
}
.filter-select:focus { outline: none; }
.filter-select option { background: #0d1f1c; }

/* Table */
.table-wrap {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px; overflow: hidden;
  animation: float-up 0.4s ease both 0.1s;
}

.table-header {
  display: grid;
  grid-template-columns: 1fr 180px 140px 120px 100px;
  padding: 11px 18px;
  background: rgba(255,255,255,0.03);
  border-bottom: 1px solid rgba(255,255,255,0.07);
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  color: rgba(232,245,240,0.35);
}

.table-row {
  display: grid;
  grid-template-columns: 1fr 180px 140px 120px 100px;
  align-items: center;
  padding: 13px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  font-size: 13px;
  color: rgba(232,245,240,0.7);
  transition: background 0.18s;
  cursor: default;
}

.table-row:last-child { border-bottom: none; }
.table-row:hover { background: rgba(255,255,255,0.04); }
.table-row.row-needs-action { border-left: 3px solid rgba(247,202,117,0.5); }

.row-info { display: flex; align-items: center; gap: 10px; }
.row-icon { width: 30px; height: 30px; border-radius: 7px; display: grid; place-items: center; flex-shrink: 0; }
.icon-teal  { background: rgba(61,217,172,0.12);  color: #3DD9AC; }
.icon-amber { background: rgba(247,202,117,0.12); color: #F7CA75; }

.row-title { margin: 0 0 1px; font-size: 13px; font-weight: 600; color: rgba(232,245,240,0.85); }
.row-org   { margin: 0; font-size: 11px; color: rgba(232,245,240,0.4); }
.row-user  { font-size: 12px; color: rgba(232,245,240,0.55); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row-date  { font-size: 12px; color: rgba(232,245,240,0.4); }

.row-actions { display: flex; align-items: center; gap: 6px; }
.action-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 6px 11px; border-radius: 7px;
  font-size: 12px; font-weight: 600; cursor: pointer; border: 0;
  transition: all 0.2s;
}
.action-review {
  background: rgba(247,202,117,0.12); color: #F7CA75; border: 1px solid rgba(247,202,117,0.25);
}
.action-review:hover { background: rgba(247,202,117,0.22); }
.action-view {
  width: 28px; height: 28px; padding: 0;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  color: rgba(232,245,240,0.5); border-radius: 7px; display: grid; place-items: center;
}
.action-view:hover { background: rgba(61,217,172,0.12); color: #3DD9AC; border-color: rgba(61,217,172,0.25); }

/* Status badges */
.status-badge {
  font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 99px; white-space: nowrap;
  width: fit-content;
}
.status-gray   { background: rgba(148,163,184,0.1); color: #94a3b8; border: 1px solid rgba(148,163,184,0.2); }
.status-purple { background: rgba(167,139,250,0.1); color: #a78bfa; border: 1px solid rgba(167,139,250,0.2); }
.status-teal   { background: rgba(61,217,172,0.1);  color: #3DD9AC; border: 1px solid rgba(61,217,172,0.2); }
.status-red    { background: rgba(248,113,113,0.1); color: #f87171; border: 1px solid rgba(248,113,113,0.2); }
.status-amber  { background: rgba(247,202,117,0.1); color: #F7CA75; border: 1px solid rgba(247,202,117,0.2); }
.status-blue   { background: rgba(96,165,250,0.1);  color: #60a5fa; border: 1px solid rgba(96,165,250,0.2); }
.status-orange { background: rgba(251,146,60,0.1);  color: #fb923c; border: 1px solid rgba(251,146,60,0.2); }
.status-green  { background: rgba(74,222,128,0.1);  color: #4ade80; border: 1px solid rgba(74,222,128,0.2); }

/* Skeleton */
.skeleton-list { padding: 8px 0; }
.skeleton-row-full {
  display: flex; align-items: center; gap: 16px; padding: 14px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.skeleton-line { height: 13px; border-radius: 6px; background-image: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.04) 75%); background-size: 200% 100%; animation: shimmer 1.5s ease infinite; }
.w-1\/3 { width: 33%; } .w-1\/4 { width: 25%; } .w-1\/5 { width: 20%; } .w-1\/6 { width: 16%; }

/* Empty */
.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 40px; color: rgba(232,245,240,0.4); font-size: 13px;
}

/* Row transitions */
.row-list-enter-active { transition: all 0.3s ease; }
.row-list-leave-active { transition: all 0.2s ease; }
.row-list-enter-from   { opacity: 0; transform: translateY(8px); }
.row-list-leave-to     { opacity: 0; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; padding: 20px;
}

.modal {
  width: min(500px, 100%);
  background: #0d1f1c;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 30px 80px rgba(0,0,0,0.5);
  animation: bounce-in 0.3s ease both;
}

.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.modal-head h3 { margin: 0; font-size: 16px; font-weight: 700; color: #e8f5f0; }
.modal-close {
  background: transparent; border: 0; color: rgba(232,245,240,0.5); cursor: pointer;
  padding: 4px; border-radius: 6px; transition: color 0.2s;
}
.modal-close:hover { color: #e8f5f0; }

.modal-body { padding: 20px 22px; display: flex; flex-direction: column; gap: 16px; }
.modal-label { font-size: 13px; font-weight: 600; color: rgba(232,245,240,0.65); margin-bottom: 8px; display: block; }

.decision-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.dec-btn {
  display: flex; flex-direction: column; align-items: center; gap: 7px;
  padding: 14px 8px; border-radius: 10px; font-size: 12px; font-weight: 600;
  cursor: pointer; border: 1.5px solid transparent; transition: all 0.2s;
}
.dec-pass { background: rgba(61,217,172,0.08);  color: #3DD9AC; border-color: rgba(61,217,172,0.15); }
.dec-pass.selected { background: rgba(61,217,172,0.2); border-color: rgba(61,217,172,0.5); }
.dec-warn { background: rgba(247,202,117,0.08); color: #F7CA75; border-color: rgba(247,202,117,0.15); }
.dec-warn.selected { background: rgba(247,202,117,0.2); border-color: rgba(247,202,117,0.5); }
.dec-fail { background: rgba(248,113,113,0.08); color: #f87171; border-color: rgba(248,113,113,0.15); }
.dec-fail.selected { background: rgba(248,113,113,0.2); border-color: rgba(248,113,113,0.5); }

.note-field { display: flex; flex-direction: column; gap: 7px; }
.modal-textarea {
  width: 100%; padding: 11px 14px; background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1); border-radius: 9px;
  color: #e8f5f0; font-size: 13px; resize: vertical; transition: border-color 0.2s;
}
.modal-textarea::placeholder { color: rgba(232,245,240,0.28); }
.modal-textarea:focus { outline: none; border-color: rgba(61,217,172,0.4); }

.modal-footer {
  display: flex; justify-content: flex-end; gap: 10px;
  padding: 16px 22px;
  border-top: 1px solid rgba(255,255,255,0.07);
}

.btn-cancel {
  padding: 10px 20px; background: transparent; border: 1px solid rgba(255,255,255,0.12);
  border-radius: 9px; color: rgba(232,245,240,0.6); font-size: 13px; font-weight: 600; cursor: pointer;
  transition: background 0.2s;
}
.btn-cancel:hover { background: rgba(255,255,255,0.06); }

.btn-confirm {
  padding: 10px 24px; border: 0; border-radius: 9px;
  font-size: 13px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; gap: 6px;
  transition: opacity 0.2s, transform 0.2s;
}
.btn-confirm:disabled { opacity: 0.5; pointer-events: none; }
.btn-confirm:hover { transform: translateY(-1px); }
.btn-pass { background: linear-gradient(90deg, #3DD9AC, #5FCBB8); color: #060e0c; }
.btn-warn { background: linear-gradient(90deg, #F7CA75, #fbbf24); color: #060e0c; }
.btn-fail { background: linear-gradient(90deg, #f87171, #ef4444); color: #fff; }

@media (max-width: 900px) {
  .table-header,
  .table-row { grid-template-columns: 1fr 100px 80px; }
  .table-header span:nth-child(2),
  .table-row .row-user,
  .table-header span:nth-child(3),
  .table-row .row-date { display: none; }
}
</style>
