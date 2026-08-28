<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import axios from 'axios'
import {
  FileText, Clock, CheckCircle, XCircle, PlusCircle,
  TrendingUp, Calendar, ArrowRight, Building2, Key,
  Sparkles, Bell
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const auth   = useAuthStore()
const router = useRouter()

const applications = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/v1/applications')
    applications.value = data
  } catch { /* ignore */ } finally {
    loading.value = false
  }
})

const stats = computed(() => {
  const all     = applications.value
  const pending = all.filter(a => ['draft','ai_reviewing','ai_passed','pending_signed','pending_admin'].includes(a.status))
  const approved = all.filter(a => ['admin_submitted','completed'].includes(a.status))
  const rejected = all.filter(a => ['ai_rejected','cancelled'].includes(a.status))
  return [
    { label: '全部申请', value: all.length,       icon: FileText,     color: 'teal',  sub: '总提交数量' },
    { label: '处理中',   value: pending.length,    icon: Clock,        color: 'amber', sub: '等待审核' },
    { label: '已通过',   value: approved.length,   icon: CheckCircle,  color: 'green', sub: '申请成功' },
    { label: '已拒绝',   value: rejected.length,   icon: XCircle,      color: 'red',   sub: '需要修改' },
  ]
})

const recentApps = computed(() => applications.value.slice(0, 5))

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

const typeConfig: Record<string, { label: string; icon: any }> = {
  meiyu:   { label: '美育场地', icon: Building2 },
  yueyuan: { label: '月苑三楼', icon: Building2 },
  key:     { label: '钥匙借用', icon: Key },
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6)  return '夜深了'
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const colorMap: Record<string, string> = {
  teal:  'card-teal',
  amber: 'card-amber',
  green: 'card-green',
  red:   'card-red',
}
</script>

<template>
  <AppLayout>
    <div class="dashboard">

      <!-- Welcome banner -->
      <div class="welcome-banner">
        <div class="welcome-text">
          <h1>{{ greeting }}，{{ auth.user?.email?.split('@')[0] ?? '同学' }} 👋</h1>
          <p>欢迎使用山东大学美育场地管理系统，以下是您的申请概况</p>
        </div>
        <button class="new-app-btn" @click="router.push('/applications/new')">
          <PlusCircle :size="17" />
          新建申请
        </button>
      </div>

      <!-- Stats row -->
      <div class="stats-row">
        <div
          v-for="(s, i) in stats"
          :key="i"
          class="stat-card"
          :class="colorMap[s.color]"
          :style="{ animationDelay: `${i * 0.08}s` }"
        >
          <div class="stat-top">
            <component :is="s.icon" :size="22" class="stat-icon" />
            <TrendingUp :size="13" class="stat-trend" />
          </div>
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
          <div class="stat-sub">{{ s.sub }}</div>
        </div>
      </div>

      <!-- Content grid -->
      <div class="content-grid">
        <!-- Recent applications -->
        <div class="section-card">
          <div class="section-head">
            <h3>最近申请</h3>
            <button class="see-all-btn" @click="router.push('/applications')">
              全部申请 <ArrowRight :size="14" />
            </button>
          </div>

          <!-- Loading skeleton -->
          <div v-if="loading" class="skeleton-list">
            <div v-for="i in 4" :key="i" class="skeleton-item">
              <div class="skeleton-line w-2/3" />
              <div class="skeleton-line w-1/3" />
            </div>
          </div>

          <!-- Application list -->
          <div v-else-if="recentApps.length" class="app-list">
            <div
              v-for="app in recentApps"
              :key="app.id"
              class="app-row"
              @click="router.push(`/applications/${app.id}`)"
            >
              <div class="app-row-icon" :class="app.app_type === 'key' ? 'icon-key' : 'icon-venue'">
                <component :is="typeConfig[app.app_type]?.icon ?? Building2" :size="16" />
              </div>
              <div class="app-row-info">
                <p class="app-row-title">{{ typeConfig[app.app_type]?.label ?? app.app_type }}</p>
                <p class="app-row-date">{{ formatDate(app.created_at) }}</p>
              </div>
              <span class="status-badge" :class="statusConfig[app.status]?.cls ?? 'status-gray'">
                {{ statusConfig[app.status]?.label ?? app.status }}
              </span>
            </div>
          </div>

          <div v-else class="empty-state">
            <Sparkles :size="32" class="empty-icon" />
            <p>暂无申请记录</p>
            <button class="empty-btn" @click="router.push('/applications/new')">立即发起申请</button>
          </div>
        </div>

        <!-- Quick actions + info -->
        <div class="side-panel">

          <!-- Quick actions -->
          <div class="section-card">
            <div class="section-head"><h3>快速操作</h3></div>
            <div class="quick-actions">
              <button class="qa-btn" @click="router.push('/applications/new')">
                <div class="qa-icon qa-teal"><PlusCircle :size="20" /></div>
                <span>发起申请</span>
              </button>
              <button class="qa-btn" @click="router.push('/venues')">
                <div class="qa-icon qa-amber"><Calendar :size="20" /></div>
                <span>查看日历</span>
              </button>
              <button class="qa-btn" @click="router.push('/applications')">
                <div class="qa-icon qa-blue"><FileText :size="20" /></div>
                <span>我的申请</span>
              </button>
              <button v-if="auth.isAdmin" class="qa-btn" @click="router.push('/admin')">
                <div class="qa-icon qa-purple"><Bell :size="20" /></div>
                <span>管理后台</span>
              </button>
            </div>
          </div>

          <!-- Notice -->
          <div class="notice-card">
            <div class="notice-icon"><Bell :size="18" /></div>
            <div>
              <p class="notice-title">温馨提示</p>
              <p class="notice-text">
                申请提交后将经过AI预审核，通过后请在规定时间内上传签字材料，逾期将自动取消预约。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Welcome banner */
.welcome-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 26px 28px;
  background: linear-gradient(120deg, rgba(61,217,172,0.08), rgba(247,202,117,0.06));
  border: 1px solid rgba(61,217,172,0.15);
  border-radius: 16px;
  animation: float-up 0.5s ease both;
}

.welcome-text h1 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 700;
  color: #e8f5f0;
}

.welcome-text p {
  margin: 0;
  font-size: 14px;
  color: rgba(232,245,240,0.54);
}

.new-app-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 22px;
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

.new-app-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(61,217,172,0.25);
}

/* Stats */
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
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: default;
}

.stat-card:hover {
  transform: translateY(-3px);
}

.card-teal  { background: linear-gradient(135deg, rgba(61,217,172,0.12), rgba(61,217,172,0.04)); border-color: rgba(61,217,172,0.2); }
.card-amber { background: linear-gradient(135deg, rgba(247,202,117,0.12), rgba(247,202,117,0.04)); border-color: rgba(247,202,117,0.2); }
.card-green { background: linear-gradient(135deg, rgba(110,231,183,0.12), rgba(110,231,183,0.04)); border-color: rgba(110,231,183,0.2); }
.card-red   { background: linear-gradient(135deg, rgba(248,113,113,0.12), rgba(248,113,113,0.04)); border-color: rgba(248,113,113,0.2); }

.stat-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.card-teal  .stat-icon { color: #3DD9AC; }
.card-amber .stat-icon { color: #F7CA75; }
.card-green .stat-icon { color: #6EE7B7; }
.card-red   .stat-icon { color: #F87171; }

.stat-trend { color: rgba(232,245,240,0.25); }

.stat-value {
  font-size: 32px;
  font-weight: 800;
  color: #e8f5f0;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  font-weight: 600;
  color: rgba(232,245,240,0.75);
}

.stat-sub {
  font-size: 12px;
  color: rgba(232,245,240,0.4);
  margin-top: 2px;
}

/* Content grid */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  align-items: start;
}

/* Section cards */
.section-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 20px;
  animation: float-up 0.5s ease both;
  animation-delay: 0.2s;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.section-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: rgba(232,245,240,0.88);
}

.see-all-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: 0;
  color: #3DD9AC;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.see-all-btn:hover { opacity: 0.7; }

/* Skeleton */
.skeleton-list { display: flex; flex-direction: column; gap: 14px; }
.skeleton-item { display: flex; flex-direction: column; gap: 8px; padding: 14px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
.skeleton-line { height: 12px; background: rgba(255,255,255,0.06); border-radius: 6px; animation: shimmer 1.5s ease infinite; background-size: 200% 100%; background-image: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.04) 75%); }
.w-2\/3 { width: 66%; }
.w-1\/3 { width: 33%; }

/* App list */
.app-list { display: flex; flex-direction: column; gap: 4px; }

.app-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.18s;
}

.app-row:hover { background: rgba(255,255,255,0.05); }

.app-row-icon {
  width: 36px; height: 36px;
  display: grid; place-items: center;
  border-radius: 9px;
  flex-shrink: 0;
}

.icon-venue { background: rgba(61,217,172,0.12); color: #3DD9AC; }
.icon-key   { background: rgba(247,202,117,0.12); color: #F7CA75; }

.app-row-info { flex: 1; min-width: 0; }

.app-row-title {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(232,245,240,0.85);
}

.app-row-date {
  margin: 0;
  font-size: 12px;
  color: rgba(232,245,240,0.4);
}

/* Status badges */
.status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 99px;
  flex-shrink: 0;
}

.status-gray   { background: rgba(148,163,184,0.12); color: #94a3b8; border: 1px solid rgba(148,163,184,0.2); }
.status-purple { background: rgba(167,139,250,0.12); color: #a78bfa; border: 1px solid rgba(167,139,250,0.2); animation: status-pulse 2s ease infinite; }
.status-teal   { background: rgba(61,217,172,0.12);  color: #3DD9AC; border: 1px solid rgba(61,217,172,0.2); }
.status-red    { background: rgba(248,113,113,0.12); color: #f87171; border: 1px solid rgba(248,113,113,0.2); }
.status-amber  { background: rgba(247,202,117,0.12); color: #F7CA75; border: 1px solid rgba(247,202,117,0.2); }
.status-blue   { background: rgba(96,165,250,0.12);  color: #60a5fa; border: 1px solid rgba(96,165,250,0.2); }
.status-orange { background: rgba(251,146,60,0.12);  color: #fb923c; border: 1px solid rgba(251,146,60,0.2); }
.status-green  { background: rgba(74,222,128,0.12);  color: #4ade80; border: 1px solid rgba(74,222,128,0.2); }

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 20px;
  color: rgba(232,245,240,0.4);
}

.empty-icon { opacity: 0.4; }

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.empty-btn {
  padding: 9px 18px;
  background: rgba(61,217,172,0.1);
  border: 1px solid rgba(61,217,172,0.25);
  border-radius: 8px;
  color: #3DD9AC;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.empty-btn:hover { background: rgba(61,217,172,0.18); }

/* Side panel */
.side-panel { display: flex; flex-direction: column; gap: 16px; }

/* Quick actions */
.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.qa-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 12px;
  cursor: pointer;
  color: rgba(232,245,240,0.7);
  font-size: 12px;
  font-weight: 600;
  transition: background 0.2s, transform 0.2s;
}

.qa-btn:hover {
  background: rgba(255,255,255,0.07);
  transform: translateY(-2px);
}

.qa-icon {
  width: 40px; height: 40px;
  border-radius: 10px;
  display: grid; place-items: center;
}

.qa-teal   { background: rgba(61,217,172,0.15);  color: #3DD9AC; }
.qa-amber  { background: rgba(247,202,117,0.15); color: #F7CA75; }
.qa-blue   { background: rgba(96,165,250,0.15);  color: #60a5fa; }
.qa-purple { background: rgba(167,139,250,0.15); color: #a78bfa; }

/* Notice card */
.notice-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: rgba(247,202,117,0.06);
  border: 1px solid rgba(247,202,117,0.18);
  border-radius: 12px;
}

.notice-icon {
  flex-shrink: 0;
  color: #F7CA75;
  margin-top: 1px;
}

.notice-title {
  margin: 0 0 5px;
  font-size: 13px;
  font-weight: 700;
  color: #F7CA75;
}

.notice-text {
  margin: 0;
  font-size: 12px;
  color: rgba(232,245,240,0.56);
  line-height: 1.7;
}

@media (max-width: 1024px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .content-grid { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .welcome-banner { flex-direction: column; align-items: flex-start; }
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}
</style>
