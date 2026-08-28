<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import {
  FileText, Users, CheckCircle, Clock, AlertCircle,
  TrendingUp, ChevronRight, ArrowRight, Shield,
  XCircle, RefreshCw, Building2, Key
} from 'lucide-vue-next'

const router = useRouter()
const applications = ref<any[]>([])
const users = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [appsRes, usersRes] = await Promise.all([
      axios.get('/api/v1/admin/applications'),
      axios.get('/api/v1/admin/users'),
    ])
    applications.value = appsRes.data
    users.value = usersRes.data
  } catch { /* ignore */ } finally {
    loading.value = false
  }
})

const stats = computed(() => {
  const all = applications.value
  return [
    { label: '全部申请', value: all.length,                                                          color: 'teal',   icon: FileText,   sub: '历史总量' },
    { label: '待处理',   value: all.filter(a => ['pending_admin','supplement_required'].includes(a.status)).length, color: 'amber', icon: Clock, sub: '需要操作' },
    { label: 'AI审核中', value: all.filter(a => a.status === 'ai_reviewing').length,                 color: 'purple', icon: RefreshCw,  sub: '系统处理' },
    { label: '用户总数', value: users.value.length,                                                  color: 'blue',   icon: Users,      sub: '注册账号' },
  ]
})

const pendingApps = computed(() =>
  applications.value
    .filter(a => ['pending_admin', 'supplement_required'].includes(a.status))
    .slice(0, 8)
)

const statusConfig: Record<string, { label: string; cls: string }> = {
  pending_admin:       { label: '待管理员审核', cls: 'status-blue' },
  supplement_required: { label: '需补充材料',   cls: 'status-orange' },
  ai_reviewing:        { label: 'AI审核中',     cls: 'status-purple' },
  ai_rejected:         { label: 'AI拒绝',       cls: 'status-red' },
  completed:           { label: '已完成',        cls: 'status-green' },
}

const typeConfig: Record<string, { label: string; icon: any }> = {
  meiyu:   { label: '美育场地', icon: Building2 },
  yueyuan: { label: '月苑三楼', icon: Building2 },
  key:     { label: '钥匙借用', icon: Key },
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

// Type distribution
const typeDist = computed(() => {
  const map: Record<string, number> = {}
  applications.value.forEach(a => {
    map[a.app_type] = (map[a.app_type] || 0) + 1
  })
  const total = applications.value.length || 1
  return Object.entries(map).map(([type, count]) => ({
    type,
    label: typeConfig[type]?.label ?? type,
    count,
    pct: Math.round(count / total * 100),
  }))
})

const colorMap: Record<string, string> = {
  teal: 'card-teal', amber: 'card-amber', blue: 'card-blue', purple: 'card-purple',
}
</script>

<template>
  <AppLayout>
    <div class="admin-dash">

      <!-- Header -->
      <div class="page-header">
        <div>
          <div class="admin-badge">
            <Shield :size="14" /> 管理员后台
          </div>
          <h1>管理概览</h1>
          <p>申请管理 · 用户管理 · 数据统计</p>
        </div>
      </div>

      <!-- Stats -->
      <div class="stats-row">
        <div
          v-for="(s, i) in stats"
          :key="i"
          class="stat-card"
          :class="colorMap[s.color]"
          :style="{ animationDelay: `${i * 0.07}s` }"
        >
          <div class="stat-top">
            <component :is="s.icon" :size="20" class="stat-icon" />
          </div>
          <div class="stat-value">{{ loading ? '—' : s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
          <div class="stat-sub">{{ s.sub }}</div>
        </div>
      </div>

      <!-- Content grid -->
      <div class="content-grid">

        <!-- Pending applications -->
        <div class="section-card">
          <div class="section-head">
            <h3>待处理申请</h3>
            <button class="see-all" @click="router.push('/admin/applications')">
              全部申请 <ArrowRight :size="14" />
            </button>
          </div>

          <div v-if="loading" class="skeleton-list">
            <div v-for="i in 5" :key="i" class="skeleton-row">
              <div class="skeleton-line w-2/3" />
              <div class="skeleton-line w-1/4" />
            </div>
          </div>

          <div v-else-if="pendingApps.length" class="app-list">
            <div
              v-for="app in pendingApps"
              :key="app.id"
              class="app-row"
              @click="router.push(`/applications/${app.id}`)"
            >
              <div class="app-icon" :class="app.app_type === 'key' ? 'icon-amber' : 'icon-teal'">
                <component :is="typeConfig[app.app_type]?.icon ?? Building2" :size="15" />
              </div>
              <div class="app-info">
                <p class="app-title">{{ typeConfig[app.app_type]?.label }} · #{{ app.id }}</p>
                <p class="app-org">{{ app.organization || app.user_email || '未知' }}</p>
              </div>
              <span class="status-badge" :class="statusConfig[app.status]?.cls ?? 'status-blue'">
                {{ statusConfig[app.status]?.label ?? app.status }}
              </span>
              <span class="app-date">{{ formatDate(app.created_at) }}</span>
              <ChevronRight :size="14" class="row-arrow" />
            </div>
          </div>

          <div v-else class="empty-state">
            <CheckCircle :size="28" class="opacity-40 text-jade-400" />
            <p>暂无待处理申请</p>
          </div>
        </div>

        <!-- Side panel -->
        <div class="side-panel">

          <!-- Type distribution -->
          <div class="section-card">
            <div class="section-head"><h3>申请类型分布</h3></div>
            <div v-if="typeDist.length" class="dist-list">
              <div v-for="t in typeDist" :key="t.type" class="dist-item">
                <div class="dist-label-row">
                  <span class="dist-name">{{ t.label }}</span>
                  <span class="dist-count">{{ t.count }}</span>
                </div>
                <div class="dist-bar-bg">
                  <div
                    class="dist-bar"
                    :style="{ width: t.pct + '%' }"
                    :class="t.type === 'key' ? 'bar-amber' : t.type === 'yueyuan' ? 'bar-blue' : 'bar-teal'"
                  />
                </div>
                <span class="dist-pct">{{ t.pct }}%</span>
              </div>
            </div>
            <div v-else class="empty-small">暂无数据</div>
          </div>

          <!-- Quick admin actions -->
          <div class="section-card">
            <div class="section-head"><h3>快速操作</h3></div>
            <div class="quick-actions">
              <button class="qa-btn" @click="router.push('/admin/applications')">
                <div class="qa-icon qa-amber"><AlertCircle :size="18" /></div>
                <span>审核申请</span>
              </button>
              <button class="qa-btn" @click="router.push('/admin/users')">
                <div class="qa-icon qa-blue"><Users :size="18" /></div>
                <span>用户管理</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.admin-dash { display: flex; flex-direction: column; gap: 22px; }

.page-header h1 {
  margin: 4px 0 4px;
  font-size: 22px; font-weight: 800; color: #e8f5f0;
  animation: float-up 0.4s ease both;
}
.page-header p {
  margin: 0;
  font-size: 13px; color: rgba(232,245,240,0.5);
  animation: float-up 0.4s ease both 0.05s;
}

.admin-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: rgba(167,139,250,0.12);
  border: 1px solid rgba(167,139,250,0.25);
  border-radius: 99px;
  color: #a78bfa;
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 6px;
  animation: float-up 0.4s ease both;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  padding: 20px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.08);
  animation: float-up 0.5s ease both;
  transition: transform 0.2s;
}
.stat-card:hover { transform: translateY(-2px); }

.card-teal   { background: linear-gradient(135deg, rgba(61,217,172,0.12), rgba(61,217,172,0.04));   border-color: rgba(61,217,172,0.2); }
.card-amber  { background: linear-gradient(135deg, rgba(247,202,117,0.12), rgba(247,202,117,0.04)); border-color: rgba(247,202,117,0.2); }
.card-blue   { background: linear-gradient(135deg, rgba(96,165,250,0.12), rgba(96,165,250,0.04));   border-color: rgba(96,165,250,0.2); }
.card-purple { background: linear-gradient(135deg, rgba(167,139,250,0.12), rgba(167,139,250,0.04)); border-color: rgba(167,139,250,0.2); }

.stat-top { margin-bottom: 12px; }
.card-teal   .stat-icon { color: #3DD9AC; }
.card-amber  .stat-icon { color: #F7CA75; }
.card-blue   .stat-icon { color: #60a5fa; }
.card-purple .stat-icon { color: #a78bfa; }

.stat-value { font-size: 30px; font-weight: 800; color: #e8f5f0; line-height: 1; margin-bottom: 4px; }
.stat-label { font-size: 14px; font-weight: 600; color: rgba(232,245,240,0.75); }
.stat-sub   { font-size: 12px; color: rgba(232,245,240,0.38); margin-top: 2px; }

.content-grid {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
  align-items: start;
}

.section-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 20px;
  animation: float-up 0.4s ease both 0.12s;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-head h3 {
  margin: 0;
  font-size: 15px; font-weight: 700; color: rgba(232,245,240,0.85);
}

.see-all {
  display: flex; align-items: center; gap: 4px;
  background: transparent; border: 0;
  color: #3DD9AC; font-size: 12px; font-weight: 600; cursor: pointer;
  transition: opacity 0.2s;
}
.see-all:hover { opacity: 0.7; }

/* App list */
.app-list { display: flex; flex-direction: column; gap: 4px; }
.app-row {
  display: flex; align-items: center; gap: 10px;
  padding: 11px 10px; border-radius: 9px; cursor: pointer;
  transition: background 0.18s;
}
.app-row:hover { background: rgba(255,255,255,0.05); }

.app-icon {
  width: 32px; height: 32px;
  border-radius: 8px; display: grid; place-items: center; flex-shrink: 0;
}
.icon-teal  { background: rgba(61,217,172,0.12);  color: #3DD9AC; }
.icon-amber { background: rgba(247,202,117,0.12); color: #F7CA75; }

.app-info { flex: 1; min-width: 0; }
.app-title { margin: 0 0 1px; font-size: 13px; font-weight: 600; color: rgba(232,245,240,0.85); }
.app-org   { margin: 0; font-size: 11px; color: rgba(232,245,240,0.4); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.app-date  { font-size: 11px; color: rgba(232,245,240,0.35); white-space: nowrap; }
.row-arrow { color: rgba(232,245,240,0.25); }
.app-row:hover .row-arrow { color: #3DD9AC; }

/* Skeleton */
.skeleton-list { display: flex; flex-direction: column; gap: 10px; }
.skeleton-row  { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.skeleton-line { height: 13px; border-radius: 6px; background-image: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.04) 75%); background-size: 200% 100%; animation: shimmer 1.5s ease infinite; }
.w-2\/3 { width: 65%; }
.w-1\/4 { width: 25%; }

/* Empty */
.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 30px 20px; color: rgba(232,245,240,0.4); font-size: 13px;
}
.empty-small { font-size: 13px; color: rgba(232,245,240,0.35); padding: 10px 0; }

/* Side panel */
.side-panel { display: flex; flex-direction: column; gap: 16px; }

/* Distribution */
.dist-list { display: flex; flex-direction: column; gap: 14px; }
.dist-item { display: flex; flex-direction: column; gap: 6px; }
.dist-label-row { display: flex; justify-content: space-between; }
.dist-name  { font-size: 13px; font-weight: 600; color: rgba(232,245,240,0.75); }
.dist-count { font-size: 13px; font-weight: 700; color: rgba(232,245,240,0.5); }
.dist-bar-bg { height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
.dist-bar    { height: 100%; border-radius: 3px; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
.bar-teal  { background: linear-gradient(90deg, #3DD9AC, #5FCBB8); }
.bar-blue  { background: linear-gradient(90deg, #60a5fa, #818cf8); }
.bar-amber { background: linear-gradient(90deg, #F7CA75, #fbbf24); }
.dist-pct  { font-size: 11px; color: rgba(232,245,240,0.35); text-align: right; }

/* Quick actions */
.quick-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.qa-btn {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 14px 10px; background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07); border-radius: 11px;
  cursor: pointer; color: rgba(232,245,240,0.7); font-size: 12px; font-weight: 600;
  transition: background 0.2s, transform 0.2s;
}
.qa-btn:hover { background: rgba(255,255,255,0.07); transform: translateY(-2px); }
.qa-icon { width: 38px; height: 38px; border-radius: 9px; display: grid; place-items: center; }
.qa-amber  { background: rgba(247,202,117,0.15); color: #F7CA75; }
.qa-blue   { background: rgba(96,165,250,0.15);  color: #60a5fa; }

/* Status badges */
.status-badge {
  font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 99px; white-space: nowrap;
}
.status-blue   { background: rgba(96,165,250,0.12);  color: #60a5fa; border: 1px solid rgba(96,165,250,0.2); }
.status-orange { background: rgba(251,146,60,0.12);  color: #fb923c; border: 1px solid rgba(251,146,60,0.2); }
.status-red    { background: rgba(248,113,113,0.12); color: #f87171; border: 1px solid rgba(248,113,113,0.2); }
.status-purple { background: rgba(167,139,250,0.12); color: #a78bfa; border: 1px solid rgba(167,139,250,0.2); }
.status-green  { background: rgba(74,222,128,0.12);  color: #4ade80; border: 1px solid rgba(74,222,128,0.2); }

@media (max-width: 1024px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .content-grid { grid-template-columns: 1fr; }
}
</style>
