<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import axios from 'axios'
import {
  Building2, Key, ChevronLeft, Upload, Download, CheckCircle,
  XCircle, Clock, FileText, AlertCircle, RefreshCw, Trash2,
  Loader2, ChevronRight
} from 'lucide-vue-next'

const route  = useRoute()
const router = useRouter()
const notify = useNotificationsStore()

const appId = computed(() => Number(route.params.id))
const app   = ref<any>(null)
const loading = ref(true)
const uploading = ref(false)

onMounted(async () => {
  await loadApp()
})

async function loadApp() {
  loading.value = true
  try {
    const { data } = await axios.get(`/api/v1/applications/${appId.value}`)
    app.value = data
  } catch {
    notify.error('加载失败', '无法获取申请详情')
    router.push('/applications')
  } finally {
    loading.value = false
  }
}

async function cancelApp() {
  if (!confirm('确认取消此申请？')) return
  try {
    await axios.post(`/api/v1/applications/${appId.value}/cancel`)
    notify.success('申请已取消')
    await loadApp()
  } catch (e: any) {
    notify.error('操作失败', e.response?.data?.detail)
  }
}

async function uploadSigned(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  const fd = new FormData()
  fd.append('file', file)
  try {
    await axios.post(`/api/v1/applications/${appId.value}/signed-files`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    notify.success('文件上传成功', '已上传签字材料')
    await loadApp()
  } catch (e: any) {
    notify.error('上传失败', e.response?.data?.detail)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function resubmit(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  const fd = new FormData()
  fd.append('file', file)
  try {
    await axios.post(`/api/v1/applications/${appId.value}/pre-review`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    notify.success('重新提交成功', '正在重新进行AI审核')
    await loadApp()
  } catch (e: any) {
    notify.error('提交失败', e.response?.data?.detail)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

const statusConfig: Record<string, { label: string; cls: string; icon: any }> = {
  draft:               { label: '草稿',     cls: 'status-gray',   icon: FileText },
  ai_reviewing:        { label: 'AI审核中', cls: 'status-purple', icon: RefreshCw },
  ai_passed:           { label: 'AI通过',   cls: 'status-teal',   icon: CheckCircle },
  ai_rejected:         { label: 'AI拒绝',   cls: 'status-red',    icon: XCircle },
  pending_signed:      { label: '待签字',   cls: 'status-amber',  icon: FileText },
  pending_admin:       { label: '待管理员', cls: 'status-blue',   icon: Clock },
  supplement_required: { label: '需补充',   cls: 'status-orange', icon: AlertCircle },
  admin_submitted:     { label: '已提交',   cls: 'status-teal',   icon: CheckCircle },
  completed:           { label: '已完成',   cls: 'status-green',  icon: CheckCircle },
  cancelled:           { label: '已取消',   cls: 'status-gray',   icon: XCircle },
}

const typeConfig: Record<string, { label: string; icon: any }> = {
  meiyu:   { label: '美育场地', icon: Building2 },
  yueyuan: { label: '月苑三楼', icon: Building2 },
  key:     { label: '钥匙借用', icon: Key },
}

function formatDate(s: string) {
  return new Date(s).toLocaleString('zh-CN', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const canCancel = computed(() =>
  app.value && !['completed', 'cancelled'].includes(app.value.status)
)

const canResubmit = computed(() =>
  app.value?.status === 'ai_rejected'
)

const canUploadSigned = computed(() =>
  app.value?.status === 'pending_signed'
)

const canUploadSupplement = computed(() =>
  app.value?.status === 'supplement_required'
)

// Timeline steps
const timeline = computed(() => {
  if (!app.value) return []
  const steps = [
    { key: 'created',   label: '申请创建',  done: true },
    { key: 'ai',        label: 'AI预审核',  done: !['draft'].includes(app.value.status) },
    { key: 'signed',    label: '签字材料',  done: !['draft','ai_reviewing','ai_passed','ai_rejected'].includes(app.value.status) },
    { key: 'admin',     label: '管理员审核', done: ['admin_submitted','completed'].includes(app.value.status) },
    { key: 'completed', label: '申请完成',  done: app.value.status === 'completed' },
  ]
  return steps
})
</script>

<template>
  <AppLayout>
    <!-- Loading skeleton -->
    <div v-if="loading" class="detail-page">
      <div class="skeleton-header">
        <div class="skeleton-line w-1/3 h-8" />
        <div class="skeleton-line w-1/4 h-6" />
      </div>
    </div>

    <div v-else-if="app" class="detail-page">

      <!-- Back + header -->
      <div class="detail-header">
        <button class="back-btn" @click="router.push('/applications')">
          <ChevronLeft :size="18" /> 返回申请列表
        </button>
        <div class="header-right">
          <span class="status-badge-lg" :class="statusConfig[app.status]?.cls ?? 'status-gray'">
            <component :is="statusConfig[app.status]?.icon ?? FileText" :size="14" />
            {{ statusConfig[app.status]?.label ?? app.status }}
          </span>
          <button v-if="canCancel" class="cancel-btn" @click="cancelApp">
            <Trash2 :size="15" /> 取消申请
          </button>
        </div>
      </div>

      <!-- Main grid -->
      <div class="detail-grid">

        <!-- Left: details -->
        <div class="detail-main">

          <!-- App info card -->
          <div class="info-card">
            <div class="info-card-head">
              <div class="info-icon" :class="app.app_type === 'key' ? 'icon-amber' : 'icon-teal'">
                <component :is="typeConfig[app.app_type]?.icon ?? Building2" :size="22" />
              </div>
              <div>
                <h2>{{ typeConfig[app.app_type]?.label ?? app.app_type }}</h2>
                <p class="info-id">申请编号 #{{ app.id }}</p>
              </div>
            </div>

            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">申请时间</span>
                <span class="info-value">{{ formatDate(app.created_at) }}</span>
              </div>
              <div v-if="app.venue_name" class="info-item">
                <span class="info-label">场地名称</span>
                <span class="info-value">{{ app.venue_name }}</span>
              </div>
              <div v-if="app.organization" class="info-item">
                <span class="info-label">申请组织</span>
                <span class="info-value">{{ app.organization }}</span>
              </div>
              <div v-if="app.start_time" class="info-item">
                <span class="info-label">使用时间</span>
                <span class="info-value">{{ formatDate(app.start_time) }} ~ {{ formatDate(app.end_time) }}</span>
              </div>
            </div>
          </div>

          <!-- AI review result -->
          <div v-if="app.ai_review_result" class="review-card" :class="app.status === 'ai_rejected' ? 'review-fail' : 'review-pass'">
            <div class="review-head">
              <component :is="app.status === 'ai_rejected' ? XCircle : CheckCircle" :size="18" />
              <span>AI审核结果</span>
            </div>
            <p class="review-content">{{ app.ai_review_result }}</p>
          </div>

          <!-- Supplement note -->
          <div v-if="app.supplement_note" class="review-card review-warn">
            <div class="review-head">
              <AlertCircle :size="18" />
              <span>管理员补充要求</span>
            </div>
            <p class="review-content">{{ app.supplement_note }}</p>
          </div>

          <!-- Files section -->
          <div class="files-card">
            <h3>申请材料</h3>

            <div v-if="app.files?.length" class="files-list">
              <div
                v-for="f in app.files"
                :key="f.id"
                class="file-row"
              >
                <FileText :size="17" class="file-icon" />
                <div class="file-info">
                  <span class="file-name">材料版本 v{{ f.version }}</span>
                  <span class="file-meta">{{ formatDate(f.created_at) }}</span>
                </div>
                <span class="file-status" :class="f.is_latest ? 'file-latest' : 'file-old'">
                  {{ f.is_latest ? '最新版' : '旧版本' }}
                </span>
                <a
                  :href="`/api/v1/applications/${app.id}/files/${f.id}/download`"
                  class="download-btn"
                  target="_blank"
                >
                  <Download :size="15" />
                </a>
              </div>
            </div>

            <div v-else class="no-files">暂无上传材料</div>

            <!-- Action buttons -->
            <div class="file-actions">
              <label v-if="canResubmit" class="upload-btn upload-btn-primary">
                <RefreshCw :size="15" />
                重新提交材料
                <input type="file" hidden accept=".doc,.docx,.pdf,.jpg,.jpeg,.png" @change="resubmit" />
              </label>

              <label v-if="canUploadSigned || canUploadSupplement" class="upload-btn upload-btn-primary">
                <Loader2 v-if="uploading" :size="15" class="animate-spin" />
                <Upload v-else :size="15" />
                {{ canUploadSupplement ? '上传补充材料' : '上传签字材料' }}
                <input type="file" hidden accept=".doc,.docx,.pdf,.jpg,.jpeg,.png" @change="uploadSigned" />
              </label>
            </div>
          </div>
        </div>

        <!-- Right: timeline -->
        <div class="detail-side">
          <div class="timeline-card">
            <h3>审核进度</h3>
            <div class="timeline">
              <div
                v-for="(t, i) in timeline"
                :key="t.key"
                class="timeline-item"
                :class="{ done: t.done, last: i === timeline.length - 1 }"
              >
                <div class="tl-dot">
                  <Check v-if="t.done" :size="12" />
                </div>
                <div class="tl-line" v-if="i < timeline.length - 1" />
                <span class="tl-label">{{ t.label }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.detail-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: float-up 0.4s ease both;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: 0;
  color: rgba(232,245,240,0.55);
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  transition: color 0.2s;
}

.back-btn:hover { color: #3DD9AC; }

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-badge-lg {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 99px;
  font-size: 13px;
  font-weight: 600;
}

.cancel-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(248,113,113,0.08);
  border: 1px solid rgba(248,113,113,0.2);
  border-radius: 9px;
  color: #f87171;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.cancel-btn:hover { background: rgba(248,113,113,0.15); }

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 20px;
  align-items: start;
}

.detail-main { display: flex; flex-direction: column; gap: 16px; }

/* Info card */
.info-card {
  padding: 22px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
}

.info-card-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}

.info-icon {
  width: 46px; height: 46px;
  border-radius: 12px;
  display: grid; place-items: center;
}

.icon-teal  { background: rgba(61,217,172,0.12);  color: #3DD9AC; }
.icon-amber { background: rgba(247,202,117,0.12); color: #F7CA75; }

.info-card-head h2 {
  margin: 0 0 3px;
  font-size: 18px;
  font-weight: 700;
  color: #e8f5f0;
}

.info-id {
  margin: 0;
  font-size: 12px;
  color: rgba(232,245,240,0.4);
  font-family: monospace;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: rgba(232,245,240,0.4); }
.info-value { font-size: 13px; color: rgba(232,245,240,0.8); }

/* Review card */
.review-card {
  padding: 16px 18px;
  border-radius: 12px;
}

.review-pass { background: rgba(61,217,172,0.06); border: 1px solid rgba(61,217,172,0.2); }
.review-fail { background: rgba(248,113,113,0.06); border: 1px solid rgba(248,113,113,0.2); }
.review-warn { background: rgba(247,202,117,0.06); border: 1px solid rgba(247,202,117,0.2); }

.review-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
}

.review-pass .review-head { color: #3DD9AC; }
.review-fail .review-head { color: #f87171; }
.review-warn .review-head { color: #F7CA75; }

.review-content {
  margin: 0;
  font-size: 13px;
  color: rgba(232,245,240,0.7);
  line-height: 1.7;
}

/* Files card */
.files-card {
  padding: 20px 22px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
}

.files-card h3 {
  margin: 0 0 14px;
  font-size: 15px;
  font-weight: 700;
  color: rgba(232,245,240,0.85);
}

.files-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }

.file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 9px;
}

.file-icon { color: #3DD9AC; flex-shrink: 0; }
.file-info { flex: 1; }
.file-name { display: block; font-size: 13px; font-weight: 600; color: rgba(232,245,240,0.8); }
.file-meta { display: block; font-size: 11px; color: rgba(232,245,240,0.35); margin-top: 1px; }

.file-latest { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 99px; background: rgba(61,217,172,0.12); color: #3DD9AC; border: 1px solid rgba(61,217,172,0.2); }
.file-old    { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 99px; background: rgba(148,163,184,0.1); color: #94a3b8; border: 1px solid rgba(148,163,184,0.15); }

.download-btn {
  display: grid; place-items: center;
  width: 30px; height: 30px;
  border-radius: 7px;
  background: rgba(255,255,255,0.05);
  color: rgba(232,245,240,0.5);
  text-decoration: none;
  transition: background 0.2s, color 0.2s;
}

.download-btn:hover { background: rgba(61,217,172,0.15); color: #3DD9AC; }

.no-files { font-size: 13px; color: rgba(232,245,240,0.35); margin-bottom: 14px; }

.file-actions { display: flex; gap: 10px; flex-wrap: wrap; }

.upload-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 18px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-btn-primary {
  background: rgba(61,217,172,0.1);
  border: 1px solid rgba(61,217,172,0.28);
  color: #3DD9AC;
}

.upload-btn-primary:hover { background: rgba(61,217,172,0.18); }

/* Timeline */
.timeline-card {
  padding: 20px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  position: sticky;
  top: 76px;
}

.timeline-card h3 {
  margin: 0 0 18px;
  font-size: 14px;
  font-weight: 700;
  color: rgba(232,245,240,0.75);
}

.timeline { display: flex; flex-direction: column; gap: 0; }

.timeline-item {
  display: grid;
  grid-template-columns: 24px 1fr;
  grid-template-rows: auto auto;
  gap: 0 12px;
  padding-bottom: 4px;
}

.tl-dot {
  grid-row: 1;
  grid-column: 1;
  width: 24px; height: 24px;
  border-radius: 50%;
  display: grid; place-items: center;
  background: rgba(255,255,255,0.06);
  border: 1.5px solid rgba(255,255,255,0.12);
  color: rgba(232,245,240,0.3);
  font-size: 10px;
  transition: all 0.3s;
}

.timeline-item.done .tl-dot {
  background: rgba(61,217,172,0.18);
  border-color: rgba(61,217,172,0.5);
  color: #3DD9AC;
}

.tl-line {
  grid-row: 2;
  grid-column: 1;
  width: 2px;
  height: 24px;
  background: rgba(255,255,255,0.08);
  margin: 2px auto 2px;
  border-radius: 1px;
  transition: background 0.3s;
}

.timeline-item.done .tl-line {
  background: rgba(61,217,172,0.3);
}

.tl-label {
  grid-row: 1;
  grid-column: 2;
  font-size: 13px;
  font-weight: 600;
  color: rgba(232,245,240,0.4);
  line-height: 24px;
  transition: color 0.3s;
}

.timeline-item.done .tl-label {
  color: rgba(232,245,240,0.8);
}

/* Status badges */
.status-gray   { background: rgba(148,163,184,0.12); color: #94a3b8; border: 1px solid rgba(148,163,184,0.2); }
.status-purple { background: rgba(167,139,250,0.12); color: #a78bfa; border: 1px solid rgba(167,139,250,0.2); }
.status-teal   { background: rgba(61,217,172,0.12);  color: #3DD9AC; border: 1px solid rgba(61,217,172,0.2); }
.status-red    { background: rgba(248,113,113,0.12); color: #f87171; border: 1px solid rgba(248,113,113,0.2); }
.status-amber  { background: rgba(247,202,117,0.12); color: #F7CA75; border: 1px solid rgba(247,202,117,0.2); }
.status-blue   { background: rgba(96,165,250,0.12);  color: #60a5fa; border: 1px solid rgba(96,165,250,0.2); }
.status-orange { background: rgba(251,146,60,0.12);  color: #fb923c; border: 1px solid rgba(251,146,60,0.2); }
.status-green  { background: rgba(74,222,128,0.12);  color: #4ade80; border: 1px solid rgba(74,222,128,0.2); }

/* Skeleton */
.skeleton-header { display: flex; flex-direction: column; gap: 10px; }
.skeleton-line { border-radius: 6px; background-image: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.04) 75%); background-size: 200% 100%; animation: shimmer 1.5s ease infinite; }
.h-8 { height: 32px; }
.h-6 { height: 24px; }
.w-1\/3 { width: 33%; }
.w-1\/4 { width: 25%; }

@media (max-width: 900px) {
  .detail-grid { grid-template-columns: 1fr; }
  .timeline-card { position: static; }
}
</style>
