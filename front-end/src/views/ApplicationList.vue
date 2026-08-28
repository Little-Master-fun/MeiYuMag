<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import {
  PlusCircle, Search, Filter, Building2, Key, ChevronRight,
  FileText, LayoutGrid, List, SlidersHorizontal, X
} from 'lucide-vue-next'

const router = useRouter()
const applications = ref<any[]>([])
const loading = ref(true)
const searchText = ref('')
const filterStatus = ref('')
const filterType = ref('')
const viewMode = ref<'grid' | 'list'>('grid')

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/v1/applications')
    applications.value = data
  } catch { /* ignore */ } finally {
    loading.value = false
  }
})

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'draft',               label: '草稿' },
  { value: 'ai_reviewing',        label: 'AI审核中' },
  { value: 'ai_passed',           label: 'AI通过' },
  { value: 'ai_rejected',         label: 'AI拒绝' },
  { value: 'pending_signed',      label: '待签字' },
  { value: 'pending_admin',       label: '待管理员' },
  { value: 'supplement_required', label: '需补充' },
  { value: 'admin_submitted',     label: '已提交' },
  { value: 'completed',           label: '已完成' },
  { value: 'cancelled',           label: '已取消' },
]

const typeOptions = [
  { value: '',        label: '全部类型' },
  { value: 'meiyu',   label: '美育场地' },
  { value: 'yueyuan', label: '月苑三楼' },
  { value: 'key',     label: '钥匙借用' },
]

const filtered = computed(() => {
  return applications.value.filter(a => {
    const matchSearch = !searchText.value ||
      (a.venue_name ?? '').includes(searchText.value) ||
      (a.app_type ?? '').includes(searchText.value)
    const matchStatus = !filterStatus.value || a.status === filterStatus.value
    const matchType   = !filterType.value   || a.app_type === filterType.value
    return matchSearch && matchStatus && matchType
  })
})

const hasFilters = computed(() => filterStatus.value || filterType.value || searchText.value)

function clearFilters() {
  searchText.value = ''
  filterStatus.value = ''
  filterType.value = ''
}

const statusConfig: Record<string, { label: string; cls: string }> = {
  draft:              { label: '草稿',     cls: 'status-gray' },
  ai_reviewing:       { label: 'AI审核中', cls: 'status-purple' },
  ai_passed:          { label: 'AI通过',   cls: 'status-teal' },
  ai_rejected:        { label: 'AI拒绝',   cls: 'status-red' },
  pending_signed:     { label: '待签字',   cls: 'status-amber' },
  pending_admin:      { label: '待管理员', cls: 'status-blue' },
  supplement_required:{ label: '需补充',   cls: 'status-orange' },
  admin_submitted:    { label: '已提交',   cls: 'status-teal' },
  completed:          { label: '已完成',   cls: 'status-green' },
  cancelled:          { label: '已取消',   cls: 'status-gray' },
}

const typeConfig: Record<string, { label: string; icon: any; color: string }> = {
  meiyu:   { label: '美育场地', icon: Building2, color: 'teal' },
  yueyuan: { label: '月苑三楼', icon: Building2, color: 'blue' },
  key:     { label: '钥匙借用', icon: Key,       color: 'amber' },
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}
</script>

<template>
  <AppLayout>
    <div class="app-list-page">

      <!-- Page header -->
      <div class="page-header">
        <div>
          <h1>我的申请</h1>
          <p>共 <span class="accent">{{ applications.length }}</span> 条申请记录</p>
        </div>
        <button class="create-btn" @click="router.push('/applications/new')">
          <PlusCircle :size="16" />
          新建申请
        </button>
      </div>

      <!-- Filter bar -->
      <div class="filter-bar">
        <div class="search-wrap">
          <Search :size="15" class="search-icon" />
          <input v-model="searchText" placeholder="搜索场地名称..." class="search-input" />
        </div>

        <div class="filter-selects">
          <select v-model="filterType" class="filter-select">
            <option v-for="o in typeOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
          <select v-model="filterStatus" class="filter-select">
            <option v-for="o in statusOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
          <button v-if="hasFilters" class="clear-filter-btn" @click="clearFilters">
            <X :size="14" /> 清除
          </button>
        </div>

        <div class="view-toggle">
          <button :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'">
            <LayoutGrid :size="16" />
          </button>
          <button :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">
            <List :size="16" />
          </button>
        </div>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="skeleton-grid">
        <div v-for="i in 6" :key="i" class="skeleton-card">
          <div class="skeleton-h" />
          <div class="skeleton-row">
            <div class="skeleton-line w-1/2" />
            <div class="skeleton-line w-1/4" />
          </div>
          <div class="skeleton-line w-3/4" />
        </div>
      </div>

      <!-- Grid view -->
      <div v-else-if="viewMode === 'grid'" class="cards-grid">
        <TransitionGroup name="card-list">
          <div
            v-for="app in filtered"
            :key="app.id"
            class="app-card"
            @click="router.push(`/applications/${app.id}`)"
          >
            <!-- Card header -->
            <div class="card-top">
              <div class="card-type-icon" :class="`type-${typeConfig[app.app_type]?.color ?? 'teal'}`">
                <component :is="typeConfig[app.app_type]?.icon ?? Building2" :size="18" />
              </div>
              <span class="status-badge" :class="statusConfig[app.status]?.cls ?? 'status-gray'">
                {{ statusConfig[app.status]?.label ?? app.status }}
              </span>
            </div>

            <!-- Card body -->
            <div class="card-body">
              <h3 class="card-title">
                {{ typeConfig[app.app_type]?.label ?? app.app_type }}
              </h3>
              <p v-if="app.venue_name" class="card-venue">{{ app.venue_name }}</p>
              <p class="card-date">{{ formatDate(app.created_at) }}</p>
            </div>

            <!-- Card footer -->
            <div class="card-footer">
              <span class="card-id">#{{ app.id }}</span>
              <ChevronRight :size="16" class="card-arrow" />
            </div>
          </div>
        </TransitionGroup>
      </div>

      <!-- List view -->
      <div v-else class="list-view">
        <div class="list-header">
          <span>申请类型</span>
          <span>场地名称</span>
          <span>申请时间</span>
          <span>状态</span>
          <span></span>
        </div>
        <TransitionGroup name="card-list">
          <div
            v-for="app in filtered"
            :key="app.id"
            class="list-row"
            @click="router.push(`/applications/${app.id}`)"
          >
            <div class="list-type">
              <div class="list-type-icon" :class="`type-${typeConfig[app.app_type]?.color ?? 'teal'}`">
                <component :is="typeConfig[app.app_type]?.icon ?? Building2" :size="15" />
              </div>
              {{ typeConfig[app.app_type]?.label ?? app.app_type }}
            </div>
            <span class="list-venue">{{ app.venue_name || '—' }}</span>
            <span class="list-date">{{ formatDate(app.created_at) }}</span>
            <span class="status-badge" :class="statusConfig[app.status]?.cls ?? 'status-gray'">
              {{ statusConfig[app.status]?.label ?? app.status }}
            </span>
            <ChevronRight :size="16" class="list-arrow" />
          </div>
        </TransitionGroup>
      </div>

      <!-- Empty state -->
      <div v-if="!loading && filtered.length === 0" class="empty-state">
        <FileText :size="40" class="empty-icon" />
        <p class="empty-title">{{ hasFilters ? '没有匹配的申请' : '暂无申请记录' }}</p>
        <p class="empty-sub">{{ hasFilters ? '尝试调整筛选条件' : '点击下方按钮发起您的第一个申请' }}</p>
        <button v-if="!hasFilters" class="empty-btn" @click="router.push('/applications/new')">
          <PlusCircle :size="15" /> 立即申请
        </button>
        <button v-else class="empty-btn" @click="clearFilters">
          清除筛选
        </button>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.app-list-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Page header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  animation: float-up 0.4s ease both;
}

.page-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 800;
  color: #e8f5f0;
}

.page-header p {
  margin: 0;
  font-size: 13px;
  color: rgba(232,245,240,0.5);
}

.accent { color: #3DD9AC; font-weight: 700; }

.create-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 20px;
  background: linear-gradient(90deg, #3DD9AC, #5FCBB8);
  border: 0;
  border-radius: 10px;
  color: #060e0c;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: transform 0.2s, box-shadow 0.2s;
}

.create-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(61,217,172,0.25);
}

/* Filter bar */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 12px;
  flex-wrap: wrap;
  animation: float-up 0.4s ease both;
  animation-delay: 0.05s;
}

.search-wrap {
  flex: 1;
  min-width: 200px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 11px;
  color: rgba(232,245,240,0.35);
}

.search-input {
  width: 100%;
  padding: 9px 12px 9px 34px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: #e8f5f0;
  font-size: 13px;
  transition: border-color 0.2s;
}

.search-input::placeholder { color: rgba(232,245,240,0.3); }
.search-input:focus { outline: none; border-color: rgba(61,217,172,0.4); }

.filter-selects {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-select {
  padding: 8px 12px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: rgba(232,245,240,0.8);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.filter-select:focus { outline: none; border-color: rgba(61,217,172,0.4); }
.filter-select option { background: #0d1f1c; }

.clear-filter-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  background: rgba(248,113,113,0.08);
  border: 1px solid rgba(248,113,113,0.2);
  border-radius: 8px;
  color: #f87171;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.clear-filter-btn:hover { background: rgba(248,113,113,0.15); }

.view-toggle {
  display: flex;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  overflow: hidden;
}

.view-toggle button {
  padding: 8px 10px;
  background: transparent;
  border: 0;
  color: rgba(232,245,240,0.4);
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.view-toggle button.active {
  background: rgba(61,217,172,0.15);
  color: #3DD9AC;
}

/* Grid */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.app-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, transform 0.2s, box-shadow 0.2s;
}

.app-card:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(61,217,172,0.2);
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.25);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-type-icon {
  width: 36px; height: 36px;
  border-radius: 9px;
  display: grid; place-items: center;
}

.type-teal  { background: rgba(61,217,172,0.12);  color: #3DD9AC; }
.type-blue  { background: rgba(96,165,250,0.12);  color: #60a5fa; }
.type-amber { background: rgba(247,202,117,0.12); color: #F7CA75; }

.card-body { flex: 1; }

.card-title {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 700;
  color: rgba(232,245,240,0.9);
}

.card-venue {
  margin: 0 0 4px;
  font-size: 12px;
  color: rgba(232,245,240,0.5);
}

.card-date {
  margin: 0;
  font-size: 11px;
  color: rgba(232,245,240,0.35);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.card-id {
  font-size: 11px;
  color: rgba(232,245,240,0.3);
  font-family: monospace;
}

.card-arrow {
  color: rgba(232,245,240,0.25);
  transition: transform 0.2s, color 0.2s;
}

.app-card:hover .card-arrow {
  color: #3DD9AC;
  transform: translateX(3px);
}

/* List view */
.list-view { display: flex; flex-direction: column; gap: 4px; }

.list-header {
  display: grid;
  grid-template-columns: 160px 1fr 140px 110px 40px;
  padding: 8px 16px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(232,245,240,0.35);
}

.list-row {
  display: grid;
  grid-template-columns: 160px 1fr 140px 110px 40px;
  align-items: center;
  padding: 13px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(232,245,240,0.75);
  transition: background 0.18s, border-color 0.18s;
}

.list-row:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(61,217,172,0.18);
}

.list-type {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: rgba(232,245,240,0.85);
}

.list-type-icon {
  width: 28px; height: 28px;
  border-radius: 6px;
  display: grid; place-items: center;
}

.list-venue { color: rgba(232,245,240,0.6); }
.list-date  { color: rgba(232,245,240,0.45); }
.list-arrow { color: rgba(232,245,240,0.25); justify-self: end; }
.list-row:hover .list-arrow { color: #3DD9AC; }

/* Status badges */
.status-badge {
  font-size: 11px; font-weight: 600;
  padding: 4px 10px; border-radius: 99px;
  white-space: nowrap;
}
.status-gray   { background: rgba(148,163,184,0.12); color: #94a3b8; border: 1px solid rgba(148,163,184,0.2); }
.status-purple { background: rgba(167,139,250,0.12); color: #a78bfa; border: 1px solid rgba(167,139,250,0.2); }
.status-teal   { background: rgba(61,217,172,0.12);  color: #3DD9AC; border: 1px solid rgba(61,217,172,0.2); }
.status-red    { background: rgba(248,113,113,0.12); color: #f87171; border: 1px solid rgba(248,113,113,0.2); }
.status-amber  { background: rgba(247,202,117,0.12); color: #F7CA75; border: 1px solid rgba(247,202,117,0.2); }
.status-blue   { background: rgba(96,165,250,0.12);  color: #60a5fa; border: 1px solid rgba(96,165,250,0.2); }
.status-orange { background: rgba(251,146,60,0.12);  color: #fb923c; border: 1px solid rgba(251,146,60,0.2); }
.status-green  { background: rgba(74,222,128,0.12);  color: #4ade80; border: 1px solid rgba(74,222,128,0.2); }

/* Skeleton */
.skeleton-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.skeleton-card { padding: 18px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; display: flex; flex-direction: column; gap: 10px; }
.skeleton-h    { height: 36px; width: 36px; border-radius: 9px; background: rgba(255,255,255,0.07); }
.skeleton-row  { display: flex; justify-content: space-between; gap: 10px; }
.skeleton-line { height: 12px; border-radius: 6px; background-image: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%); background-size: 200% 100%; animation: shimmer 1.5s ease infinite; }
.w-1\/2 { width: 50%; }
.w-1\/4 { width: 25%; }
.w-3\/4 { width: 75%; }

/* Empty state */
.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 60px 20px; color: rgba(232,245,240,0.4);
}
.empty-icon { opacity: 0.3; margin-bottom: 6px; }
.empty-title { margin: 0; font-size: 16px; font-weight: 600; color: rgba(232,245,240,0.6); }
.empty-sub { margin: 0; font-size: 13px; }
.empty-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 20px; margin-top: 8px;
  background: rgba(61,217,172,0.1); border: 1px solid rgba(61,217,172,0.25);
  border-radius: 9px; color: #3DD9AC; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: background 0.2s;
}
.empty-btn:hover { background: rgba(61,217,172,0.18); }

/* Transitions */
.card-list-enter-active { transition: all 0.3s ease; }
.card-list-leave-active { transition: all 0.2s ease; }
.card-list-enter-from  { opacity: 0; transform: scale(0.95) translateY(10px); }
.card-list-leave-to    { opacity: 0; transform: scale(0.95); }
.card-list-move        { transition: transform 0.3s ease; }
</style>
