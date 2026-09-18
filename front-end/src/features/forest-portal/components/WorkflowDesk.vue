<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import type { ApplicationNavigationTarget, PersonalApplicationApi, VenueApiItem } from '../types'
import {
  applicationStatusLabels as labels,
  fileLabels,
  fileStatusLabels,
  signedTypes,
  targetForApplication,
  downloadMaterial,
  type ApplicationFileItem,
} from '../workflow'
import { getSubmissionErrorMessage } from '../submission'
import { getLocalDateKey, offsetDate } from '../utils'
import UserManagementPanel from './UserManagementPanel.vue'
import { dailyTimeSlots, mergeTimeSlots, MAX_MANUAL_TIME_SLOTS } from '../manualTimeSlots'

const props = defineProps<{
  mode: 'personal' | 'admin' | 'secondary' | 'new'
  applicationId?: number
  initialVenueId?: number
  initialDate?: string
}>()
const emit = defineEmits<{
  close: []
  submit: [target: ApplicationNavigationTarget]
  refresh: []
}>()
const auth = useAuthStore()
const loading = ref(true),
  busy = ref(false),
  error = ref(''),
  notice = ref('')
const applications = ref<PersonalApplicationApi[]>([]),
  venues = ref<VenueApiItem[]>([])
const selected = ref<PersonalApplicationApi | null>(null),
  files = ref<ApplicationFileItem[]>([])
const filter = ref(''),
  reason = ref(''),
  requested = ref<string[]>([]),
  confirmCancel = ref(false)
const kind = ref<'venue' | 'key'>('venue'),
  venueId = ref(props.initialVenueId ?? 0)
const date = ref(props.initialDate || getLocalDateKey(offsetDate(new Date(), 1)))
const manualVenueId = ref(0), manualOrganization = ref(''), manualKeyName = ref('')
const manualSlots = ref([{ start_at: '', end_at: '' }])
const batchStartDate = ref(''), batchEndDate = ref(''), batchStartTime = ref(''), batchEndTime = ref('')
const batchMessage = ref('')
const canBatchTimeSlots = computed(() => admin.value && selected.value?.status === 'pending_admin_pre_review'
  && selected.value.application_type !== 'key_borrow'
  && !!manualVenueId.value
  && !venues.value.find(v => v.id === manualVenueId.value)?.name.includes('悦园三楼'))
const batchPreview = computed(() => {
  try {
    const slots = dailyTimeSlots(batchStartDate.value, batchEndDate.value, batchStartTime.value, batchEndTime.value)
    return { slots, message: `共 ${slots.length} 天（含起止日期），每天 ${batchStartTime.value}–${batchEndTime.value}` }
  } catch (e) {
    return { slots: [], message: (e as Error).message }
  }
})
function addDailyTimeSlots() {
  if (!canBatchTimeSlots.value || busy.value) return
  try {
    const added = dailyTimeSlots(batchStartDate.value, batchEndDate.value, batchStartTime.value, batchEndTime.value)
    manualSlots.value = mergeTimeSlots(manualSlots.value, added)
    batchMessage.value = `已合并到下方列表，共 ${manualSlots.value.length} 个时段；可逐条修改或移除。`
  } catch (e) { batchMessage.value = (e as Error).message }
}
const inputDate = (s: string | null) => s ? new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
}).format(new Date(/Z$|[+-]\d\d:\d\d$/.test(s) ? s : `${s}+08:00`)).replace(' ', 'T') : ''
const reviewSlots = () => {
  if (manualSlots.value.some(s => !s.start_at || !s.end_at)) throw new Error('请填写完整借用时间（北京时间）')
  return manualSlots.value.map(s => ({ start_at: `${s.start_at}:00+08:00`, end_at: `${s.end_at}:00+08:00` }))
}
const templates = ref<Array<{ name: string; application_type: string; download_url: string }>>([])
const admin = computed(() => props.mode === 'admin' && auth.isAdmin)
const secondary = computed(() => props.mode === 'secondary' && auth.isSecondaryAdmin)
const section = ref<'applications' | 'users'>('applications')
const countersignedFile = ref<File | null>(null)
const countersignInput = ref<HTMLInputElement | null>(null)
const visibleApplications = computed(() =>
  applications.value.filter((a) => !filter.value || a.status === filter.value),
)
const nameFor = (a: PersonalApplicationApi) =>
  a.application_type === 'key_borrow'
    ? '钥匙借用'
    : venues.value.find((v) => v.id === a.venue_id)?.name || '场地申请'
const stamp = (s: string) => labels[s] || s
const canContinue = computed(
  () =>
    !admin.value &&
    !secondary.value &&
    selected.value &&
    ['ai_rejected', 'pending_signed_files', 'supplement_required'].includes(selected.value.status),
)
const canCancel = computed(
  () =>
    !secondary.value &&
    selected.value &&
    !['completed', 'cancelled', 'rejected'].includes(selected.value.status) &&
    (!selected.value.start_at || new Date(selected.value.start_at) > new Date()),
)
const supplementOptions = computed(() =>
  selected.value ? [...signedTypes(selected.value.application_type), 'supporting_material'] : [],
)
const currentType = computed(
  () =>
    selected.value?.application_type ||
    (venues.value.find((v) => v.id === venueId.value)?.name.includes('悦园三楼')
      ? 'yueyuan_third_floor'
      : 'meiyu_venue'),
)
const matchingTemplates = computed(() =>
  templates.value.filter((t) => t.application_type === currentType.value),
)
const readableDate = (s: string | null) =>
  s ? new Date(/Z$|[+-]\d\d:\d\d$/.test(s) ? s : `${s}+08:00`).toLocaleString('zh-CN', { hour12: false, timeZone: 'Asia/Shanghai' }) : '待材料确认'
let requestVersion = 0

async function openApplication(id: number) {
  const version = ++requestVersion
  busy.value = true
  error.value = ''
  notice.value = ''
  confirmCancel.value = false
  try {
    const [detail, material] = await Promise.all([
      axios.get(`/api/v1/applications/${id}`),
      axios.get(`/api/v1/applications/${id}/files`),
    ])
    if (version !== requestVersion) return
    selected.value = detail.data
    files.value = material.data
    countersignedFile.value = null
    if (countersignInput.value) countersignInput.value.value = ''
    reason.value = ''
    requested.value = []
    manualVenueId.value = detail.data.venue_id ?? 0
    manualOrganization.value = detail.data.borrow_organization ?? detail.data.organization ?? ''
    manualKeyName.value = detail.data.borrowed_key_name ?? ''
    manualSlots.value = [{ start_at: inputDate(detail.data.start_at), end_at: inputDate(detail.data.end_at) }]
    batchStartDate.value = ''; batchEndDate.value = ''; batchStartTime.value = ''; batchEndTime.value = ''; batchMessage.value = ''
  } catch (e) {
    if (version === requestVersion) error.value = getSubmissionErrorMessage(e)
  } finally {
    if (version === requestVersion) busy.value = false
  }
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    if (props.mode === 'admin' && !auth.isAdmin) throw new Error('仅管理员可打开审核台')
    if (props.mode === 'secondary' && !auth.isSecondaryAdmin) throw new Error('仅二级管理员可打开签章工作台')
    const [venueData, templateData] = await Promise.all([
      axios.get('/api/v1/venues'),
      axios.get('/api/v1/templates'),
    ])
    venues.value = venueData.data
    templates.value = templateData.data
    if (!venueId.value) venueId.value = venues.value[0]?.id ?? 0
    if (props.mode !== 'new') {
      applications.value = (
        await axios.get(admin.value ? '/api/v1/admin/applications' : secondary.value ? '/api/v1/secondary/applications' : '/api/v1/applications')
      ).data
      if (props.applicationId) await openApplication(props.applicationId)
    }
  } catch (e) {
    error.value = getSubmissionErrorMessage(e)
  } finally {
    loading.value = false
  }
}
function selectCountersign(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  countersignedFile.value = null
  if (!file) return
  if (!/\.(pdf|png|jpe?g)$/i.test(file.name) || !file.size || file.size > 30 * 1024 * 1024) {
    error.value = '请选择不超过 30 MB 的 PDF、PNG 或 JPG 扫描件，文件不能为空'
    input.value = ''; return
  }
  error.value = ''; countersignedFile.value = file
}
async function secondaryAction(action: 'pass' | 'return' | 'upload') {
  if (!secondary.value || !selected.value || busy.value) return
  if (action === 'return' && !reason.value.trim()) { error.value = '请写明需要修正的原因'; return }
  if (action === 'upload' && !countersignedFile.value) { error.value = '请先选择再次签字盖章后的扫描件'; return }
  const id = selected.value.id
  busy.value = true; error.value = ''; notice.value = ''
  try {
    if (action === 'upload') {
      const body = new FormData(); body.append('file', countersignedFile.value!)
      await axios.post(`/api/v1/secondary/applications/${id}/countersigned-file`, body)
    } else {
      await axios.post(`/api/v1/secondary/applications/${id}/decision`, { passed: action === 'pass', reason: reason.value.trim() || undefined })
    }
    await openApplication(id)
    applications.value = applications.value.map(item => item.id === id ? selected.value! : item)
    notice.value = action === 'upload' ? '再次签章材料已交给一级管理员，请等待最终审核。' : action === 'pass' ? '审核已通过，请完成再次签字盖章后上传扫描件。' : '已退回申请人修正。'
    emit('refresh')
  } catch (e) { error.value = getSubmissionErrorMessage(e) }
  finally { busy.value = false }
}
async function act(
  action: 'cancel' | 'submitted' | 'completed' | 'rejected' | 'supplement' | 'legacy-reject' | 'manual-pass',
) {
  if (!selected.value || busy.value) return
  if (['rejected', 'supplement', 'legacy-reject'].includes(action) && !reason.value.trim()) {
    error.value = '请写明原因，申请人会收到这段说明'
    return
  }
  if (action === 'supplement' && !requested.value.length) {
    error.value = '请勾选需要补交的材料'
    return
  }
  busy.value = true
  error.value = ''
  notice.value = ''
  const id = selected.value.id
  try {
    if (action === 'cancel' && !admin.value) await axios.post(`/api/v1/applications/${id}/cancel`)
    else if (action === 'supplement')
      await axios.post(`/api/v1/admin/applications/${id}/request-supplement`, {
        file_types: requested.value,
        reason: reason.value,
      })
    else if (action === 'manual-pass')
      await axios.post(`/api/v1/admin/applications/${id}/pre-review-decision`, {
        passed: true, venue_id: manualVenueId.value || undefined,
        borrow_organization: manualOrganization.value.trim(), time_slots: reviewSlots(),
      })
    else if (action === 'legacy-reject')
      await axios.post(`/api/v1/admin/applications/${id}/pre-review-decision`, {
        passed: false,
        reason: reason.value,
      })
    else
      await axios.patch(`/api/v1/admin/applications/${id}/status`, {
        status: action === 'cancel' ? 'cancelled' : action,
        reason: reason.value || undefined,
        key_details: action === 'submitted' && selected.value.application_type === 'key_borrow'
          ? { borrowed_key_name: manualKeyName.value.trim(), borrow_organization: manualOrganization.value.trim(), ...reviewSlots()[0] }
          : undefined,
      })
    await openApplication(id)
    applications.value = applications.value.map((a) => (a.id === id ? selected.value! : a))
    notice.value = '已记录本次处理'
    emit('refresh')
  } catch (e) {
    error.value = getSubmissionErrorMessage(e)
  } finally {
    busy.value = false
  }
}
function begin() {
  if (!auth.user?.is_sdu_verified && !auth.user?.is_application_allowed) {
    error.value = '申请权限尚未开通，请先完成身份认证或联系管理员'
    return
  }
  const venue = venues.value.find((v) => v.id === venueId.value)
  if (kind.value === 'venue' && (!venue || date.value <= getLocalDateKey(new Date()))) {
    error.value = '请选择场地和今日之后的日期'
    return
  }
  emit('submit', {
    venueId: venue?.id ?? 0,
    venueName: kind.value === 'key' ? '钥匙借用' : venue!.name,
    date: date.value,
    mode: kind.value === 'key' ? 'key' : 'new',
    applicationType: kind.value === 'key' ? 'key_borrow' : currentType.value,
  })
}
async function download(url: string, name: string) {
  try {
    await downloadMaterial(url, name)
  } catch (e) {
    error.value = getSubmissionErrorMessage(e)
  }
}
function close() {
  if (!busy.value) emit('close')
}
function backToList() {
  selected.value = null
  confirmCancel.value = false
}
const dialog = ref<HTMLElement | null>(null)
function keydown(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
  if (event.key !== 'Tab' || !dialog.value) return
  const items = [
    ...dialog.value.querySelectorAll<HTMLElement>(
      'button:not(:disabled), input, select, textarea, [tabindex="0"]',
    ),
  ]
  const first = items[0],
    last = items.at(-1)
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last?.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first?.focus()
  }
}
const previousFocus = document.activeElement as HTMLElement | null
onMounted(() => {
  void load()
  dialog.value?.focus()
})
onBeforeUnmount(() => {
  requestVersion++
  previousFocus?.focus()
})
</script>

<template>
  <div class="desk-veil" @pointerdown.self="close" @keydown="keydown" @wheel.stop @pointerdown.stop>
    <section
      ref="dialog"
      class="paper-dossier"
      role="dialog"
      aria-modal="true"
      aria-labelledby="desk-title"
      tabindex="-1"
    >
      <header class="dossier-header">
        <div>
          <small>MEIYU · {{ admin || secondary ? 'REVIEW DESK' : 'APPLICATION ARCHIVE' }}</small>
          <h2 id="desk-title">
            {{ props.mode === 'new' ? '寄出一份申请' : admin ? '申请审核台' : secondary ? '签章工作台' : '我的申请档案' }}
          </h2>
        </div>
        <button class="close-leaf" :disabled="busy" @click="close" aria-label="收起档案">×</button>
      </header>
      <nav v-if="admin" class="kind-tabs" aria-label="管理章节">
        <button :aria-pressed="section === 'applications'" :disabled="busy" @click="section = 'applications'">申请审核</button>
        <button :aria-pressed="section === 'users'" :disabled="busy" @click="section = 'users'">用户管理</button>
      </nav>
      <UserManagementPanel v-if="admin && section === 'users'" />
      <template v-else>
      <p v-if="error" class="ink-note error" role="alert">
        {{ error }} <button v-if="loading === false && !selected" @click="load">重试</button>
      </p>
      <p v-if="notice" class="ink-note" role="status">{{ notice }}</p>
      <p v-if="loading" class="empty-note">正在整理档案…</p>
      <template v-else-if="props.mode === 'new'">
        <div class="kind-tabs">
          <button :aria-pressed="kind === 'venue'" @click="kind = 'venue'">场地申请</button
          ><button :aria-pressed="kind === 'key'" @click="kind = 'key'">钥匙借用</button>
        </div>
        <div v-if="kind === 'venue'" class="new-letter">
          <label
            >写给哪一处场地<select v-model="venueId">
              <option v-for="v in venues" :key="v.id" :value="v.id">{{ v.name }}</option>
            </select></label
          >
          <label
            >计划使用日期<input
              type="date"
              v-model="date"
              :min="getLocalDateKey(offsetDate(new Date(), 1))"
          /></label>
          <p>
            申请文件中的场地、日期应与此处一致；具体时段以文件为准。初审通过后，请再次到信箱递交签章材料。
          </p>
          <div class="template-links">
            <button
              v-for="t in matchingTemplates"
              :key="t.name"
              @click="download(t.download_url, t.name)"
            >
              ↓ 取一份{{ t.name.replace('.docx', '') }}
            </button>
          </div>
        </div>
        <div v-else>
          <p class="empty-note">
            图片示例仅供参考。请填写钥匙名称、组织及借还时间并签名，提交清晰完整的 PDF 扫描件。无需 OCR，由管理员人工审核，不调用 AI；不要提交普通拍照原图或示例图片。
          </p>
          <div class="template-links">
            <button v-for="t in templates.filter(item => item.application_type === 'key_borrow')"
              :key="t.name" @click="download(t.download_url, t.name)">↓ 下载钥匙申请图片示例</button>
          </div>
        </div>
        <footer>
          <button class="seal-action" @click="begin">前往信箱 <span>↗</span></button>
        </footer>
      </template>
      <template v-else>
        <div v-if="!selected" class="archive-list">
          <p v-if="secondary" class="ink-note">仅显示指派给你的美育场地签章申请。先下载核对用户材料，审核通过后完成再次签字盖章，再上传扫描件交一级管理员确认。</p>
          <button v-if="admin || secondary" class="text-link" :disabled="busy || loading" @click="load">刷新待办 ↻</button>
          <label class="filter-note"
            >筛选签条
            <select v-model="filter">
              <option value="">全部申请</option>
              <option v-for="(label, key) in labels" :key="key" :value="key">{{ label }}</option>
            </select></label
          >
          <button
            v-for="a in visibleApplications"
            :key="a.id"
            class="archive-row"
            :disabled="busy"
            @click="openApplication(a.id)"
          >
            <span
              ><small>No. {{ String(a.id).padStart(4, '0') }}</small
              ><strong>{{ nameFor(a) }}</strong
              ><small>{{ readableDate(a.start_at || a.created_at) }}</small></span
            ><em :class="a.status">{{ stamp(a.status) }} →</em>
          </button>
          <p v-if="!visibleApplications.length" class="empty-note">这枚签条下暂时没有申请。</p>
        </div>
        <div v-else class="application-detail">
          <button
            class="text-link"
            :disabled="busy"
              @click="backToList"
          >
            ← 回到档案目录
          </button>
          <div class="detail-title">
            <div>
              <small>申请 #{{ selected.id }}</small>
              <h3>{{ nameFor(selected) }}</h3>
            </div>
            <em>{{ stamp(selected.status) }}</em>
          </div>
          <p>{{ selected.purpose_summary || '场地使用申请' }}</p>
          <p class="date-line">
            {{ selected.borrow_organization || selected.organization || '借用组织待确认' }} ·
            {{ selected.applicant_name || '申请人未填写姓名'
            }}<span v-if="selected.applicant_department">
              · {{ selected.applicant_department }}</span
            >
          </p>
          <p class="date-line">
            <span v-if="selected.borrowed_key_name">{{ selected.borrowed_key_name }} · </span>
            {{ readableDate(selected.start_at) }} — {{ readableDate(selected.end_at) }}
          </p>
          <blockquote v-if="selected.review_reason">
            <small>处理说明</small>{{ selected.review_reason }}
          </blockquote>
          <div v-if="selected.required_files.length" class="checklist">
            <h4>本次需要递交</h4>
            <p v-for="r in selected.required_files" :key="r.file_type">○ {{ r.label }}</p>
          </div>
          <button
            v-if="canContinue"
            class="seal-action"
            :disabled="busy"
            @click="emit('submit', targetForApplication(selected, nameFor(selected)))"
          >
            {{
              selected.status === 'ai_rejected'
                ? '修正并重新初审'
                : selected.status === 'pending_signed_files'
                  ? '递交签章材料'
                  : '去信箱补交'
            }}
            ↗
          </button>
          <h4>材料与版本 <small>保留每一次递交</small></h4>
          <p v-if="!files.length" class="empty-note">暂未收到材料。</p>
          <article v-for="file in files" :key="file.id" class="file-entry">
            <div>
              <strong>{{ file.original_filename }}</strong
              ><small
                >{{ fileLabels[file.file_type] || file.file_type }} · 第 {{ file.version }} 版 ·
                {{ fileStatusLabels[file.review_status] || file.review_status }}</small
              >
              <p v-if="file.reject_reason">{{ file.reject_reason }}</p>
            </div>
            <button
              @click="download(file.download_url, file.original_filename)"
              :aria-label="`下载 ${file.original_filename} 第 ${file.version} 版`"
            >
              ↓ 下载
            </button>
          </article>
          <div v-if="secondary && ['pending_secondary_review', 'pending_secondary_signature'].includes(selected.status)" class="review-letter">
            <template v-if="selected.status === 'pending_secondary_review'">
              <h4>核对用户签章材料</h4>
              <p>请下载并核对申请信息、签字和盖章。通过后还需完成再次签章并提交扫描件。</p>
              <textarea v-model="reason" :disabled="busy" maxlength="1000" rows="3" aria-label="签章审核原因" placeholder="需要修正时，请写明原因，申请人会看到此说明。" />
              <div class="review-actions"><button :disabled="busy" @click="secondaryAction('return')">退回修正</button><button class="seal-action" :disabled="busy" @click="secondaryAction('pass')">审核通过 · 准备再次签章</button></div>
            </template>
            <template v-else>
              <h4>递交再次签章扫描件</h4>
              <p>完成再次签字盖章后，提交清晰完整的扫描件，不接受普通拍照照片。支持 PDF、PNG、JPG，单份不超过 30 MB。</p>
              <input ref="countersignInput" class="scan-file-input" type="file" accept=".pdf,.png,.jpg,.jpeg" aria-label="再次签章扫描件" :disabled="busy" @change="selectCountersign" />
              <button class="text-link" :disabled="busy" @click="countersignInput?.click()">＋ {{ countersignedFile ? '换一份扫描件' : '放入再次签章扫描件' }}</button>
              <p v-if="countersignedFile">待递交：{{ countersignedFile.name }}</p>
              <button class="seal-action" :disabled="busy || !countersignedFile" @click="secondaryAction('upload')">{{ busy ? '正在递交…' : '确认递交给一级管理员 ↗' }}</button>
            </template>
          </div>
          <p v-else-if="secondary" class="ink-note">{{ selected.status === 'pending_admin_submit' ? '再次签章材料已递交，等待一级管理员最终审核。' : '当前无需你操作，可刷新待办查看最新进度。' }}</p>
          <p v-if="admin && ['pending_secondary_review', 'pending_secondary_signature'].includes(selected.status)" class="ink-note">此申请正在二级管理员签章环节，完成再次签章后会回到本审核台。需要交接时，可在用户管理中调整二级管理员身份。</p>
          <div
            v-if="
              admin &&
              [
                'pending_admin_submit',
                'submitted',
                'supplement_required',
                'pending_admin_pre_review',
              ].includes(selected.status)
            "
            class="review-letter"
          >
            <h4>审核批注</h4>
            <fieldset v-if="selected.status === 'pending_admin_pre_review' || (selected.application_type === 'key_borrow' && selected.status === 'pending_admin_submit')" class="manual-review-fields" :disabled="busy">
              <legend>对照原件填写 · 北京时间</legend>
              <p>请先下载并阅读材料。场地通过初审前会再次检查占用冲突；钥匙申请不使用 AI。</p>
              <label v-if="selected.application_type !== 'key_borrow'">申请场地
                <select v-model="manualVenueId" aria-label="人工审核场地"><option :value="0" disabled>请选择场地</option><option v-for="v in venues" :key="v.id" :value="v.id">{{ v.name }}</option></select>
              </label>
              <label v-else>钥匙名称<input v-model="manualKeyName" maxlength="255" aria-label="人工审核钥匙名称" /></label>
              <label>借用组织<input v-model="manualOrganization" maxlength="255" aria-label="人工审核借用组织" /></label>
              <p v-if="canBatchTimeSlots">美育馆支持补录今天或过去的借用时段，请按原件填写实际时间。</p>
              <div v-if="canBatchTimeSlots" class="batch-time-slots">
                <h4>连续多天 · 每天固定时段</h4>
                <div class="manual-slot" @input="batchMessage = ''">
                  <label>开始日期<input v-model="batchStartDate" type="date" aria-label="批量开始日期" /></label>
                  <label>结束日期<input v-model="batchEndDate" type="date" :min="batchStartDate || undefined" aria-label="批量结束日期" /></label>
                  <label>每天开始时间<input v-model="batchStartTime" type="time" aria-label="批量每天开始时间" /></label>
                  <label>每天结束时间<input v-model="batchEndTime" type="time" aria-label="批量每天结束时间" /></label>
                </div>
                <p>{{ batchPreview.message }}</p>
                <button type="button" :disabled="!batchPreview.slots.length" @click="addDailyTimeSlots">＋ 批量添加到时段列表</button>
                <p>保留已填时段，自动跳过重复项；最多 {{ MAX_MANUAL_TIME_SLOTS }} 个时段。添加后请核对下方列表，再通过初审。</p>
                <p v-if="batchMessage" role="status">{{ batchMessage }}</p>
              </div>
              <div v-for="(slot, index) in manualSlots" :key="index" class="manual-slot">
                <label>开始时间<input v-model="slot.start_at" type="datetime-local" :aria-label="`借用开始时间 ${index + 1}`" /></label>
                <label>{{ selected.application_type === 'key_borrow' ? '归还时间' : '结束时间' }}<input v-model="slot.end_at" type="datetime-local" :aria-label="`借用结束时间 ${index + 1}`" /></label>
                <button v-if="manualSlots.length > 1" type="button" @click="manualSlots.splice(index, 1)">移除此时段</button>
              </div>
              <button v-if="selected.status === 'pending_admin_pre_review' && manualSlots.length < MAX_MANUAL_TIME_SLOTS" type="button" @click="manualSlots.push({start_at: '', end_at: ''})">＋ 添加借用时段</button>
            </fieldset>
            <textarea
              v-model="reason"
              maxlength="1000"
              rows="3"
              placeholder="写明材料问题或处理说明，申请人可在档案中看到。"
              aria-label="审核原因"
              :disabled="busy"
            />
            <template v-if="selected.status !== 'pending_admin_pre_review'">
              <p>需要补交时，勾选具体材料：</p>
              <div class="requested-checks">
                <label v-for="key in supplementOptions" :key="key"
                  ><input v-model="requested" type="checkbox" :value="key" :disabled="busy" />{{
                    fileLabels[key]
                  }}</label
                >
              </div>
              <div class="review-actions">
                <button :disabled="busy" @click="act('supplement')">退回补齐材料</button
                ><button
                  v-if="selected.status === 'pending_admin_submit'"
                  :disabled="busy"
                  @click="act('rejected')"
                >
                  审核不通过</button
                ><button
                  v-if="selected.status === 'pending_admin_submit'"
                  class="seal-action"
                  :disabled="busy"
                  @click="act('submitted')"
                >
                  审核通过 · 确认使用</button
                ><button
                  v-if="selected.status === 'submitted'"
                  class="seal-action"
                  :disabled="busy"
                  @click="act('completed')"
                >
                  标记完成
                </button>
              </div>
            </template>
            <div v-else class="review-actions">
              <button :disabled="busy" @click="act('legacy-reject')">退回修正 · 重新进行初审</button>
              <button class="seal-action" :disabled="busy" @click="act('manual-pass')">人工初审通过 · 待签章</button>
            </div>
          </div>
          <footer v-if="canCancel">
            <button
              v-if="!confirmCancel"
              class="text-link"
              :disabled="busy"
              @click="confirmCancel = true"
            >
              撤回这份申请</button
            ><span v-else
              >撤回后将释放预约。<button :disabled="busy" @click="act('cancel')">确认撤回</button
              ><button :disabled="busy" @click="confirmCancel = false">保留申请</button></span
            >
          </footer>
        </div>
      </template>
      </template>
    </section>
  </div>
</template>

<style scoped>
.scan-file-input { display: none; }
.desk-veil {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: clamp(12px, 3vw, 36px);
  background: rgba(28, 44, 39, 0.32);
  backdrop-filter: blur(5px);
  font-family: 'Songti SC', 'STSong', Georgia, serif;
  color: #57482f;
  box-sizing: border-box;
}
.paper-dossier {
  width: min(760px, 100%);
  max-height: 90dvh;
  overflow: auto;
  box-sizing: border-box;
  outline: none;
  padding: clamp(22px, 4vw, 48px);
  border: 1px solid #c5b58a;
  border-radius: 5px 18px 8px 4px;
  background: linear-gradient(115deg, #f6efd9, #e9deb8);
  box-shadow:
    8px 13px 0 -5px #c8bb93,
    0 25px 70px #142c354f;
  scrollbar-width: thin;
  scrollbar-color: #9e9878 transparent;
}
button,
input,
select,
textarea {
  font: inherit;
  color: inherit;
}
button {
  cursor: pointer;
  border: 1px solid #9eac9266;
  background: #fff8e733;
  padding: 9px 16px;
  border-radius: 3px 12px 10px 3px;
  transition:
    background 0.18s,
    transform 0.18s;
}
button:hover:not(:disabled) {
  background: #dce0c6;
  transform: translateY(-2px);
}
button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: 2px solid #677e60;
  outline-offset: 3px;
}
button:disabled {
  opacity: 0.5;
  cursor: wait;
}
small {
  font-size: 12px;
  letter-spacing: 0.04em;
  color: #8a7a58;
}
h2 {
  font-size: 32px;
  margin: 8px 0 0;
  font-weight: 500;
}
h3 {
  font-size: 27px;
  margin: 7px 0;
}
h4 {
  font-size: 19px;
  font-weight: 500;
  margin: 25px 0 12px;
}
h4 small {
  margin-left: 12px;
}
.dossier-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 22px;
  border-bottom: 1px solid #a8997066;
}
.close-leaf {
  font-size: 26px;
  background: none;
  border: 0;
  padding: 5px 12px;
}
.kind-tabs {
  display: flex;
  gap: 10px;
  margin: 24px 0;
}
.kind-tabs [aria-pressed='true'],
.seal-action {
  background: #61765b;
  color: #fff7df;
  border-color: #61765b;
}
.seal-action:hover:not(:disabled) {
  background: #496149;
  color: white;
}
.new-letter label {
  display: grid;
  gap: 9px;
  margin: 20px 0;
}
.new-letter p {
  line-height: 1.9;
  color: #7d7159;
}
select,
input[type='date'],
input[type='datetime-local'],
.manual-review-fields input,
textarea {
  box-sizing: border-box;
  background: #fff9e740;
  border: 0;
  border-bottom: 1px solid #a7997866;
  border-radius: 0;
  padding: 10px;
  max-width: 100%;
}
.template-links {
  display: grid;
  gap: 8px;
}
.template-links button {
  text-align: left;
  border: 0;
  font-size: 14px;
}
.archive-list {
  padding-top: 20px;
}
.filter-note {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 14px;
}
.archive-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  text-align: left;
  margin-bottom: 12px;
  padding: 16px 18px;
  gap: 16px;
}
.archive-row span {
  display: grid;
  gap: 7px;
}
.archive-row strong {
  font-size: 20px;
  font-weight: 500;
}
em {
  font-style: normal;
  color: #647756;
  font-size: 14px;
}
.ai_rejected,
.rejected,
.supplement_required {
  color: #a15f49;
}
.text-link {
  border: 0;
  background: none;
  padding: 12px 0;
  color: #727e5f;
}
.detail-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 20px;
}
.date-line {
  font-size: 14px;
  color: #8a7a58;
}
.application-detail > p {
  margin: 8px 0;
  line-height: 1.6;
}
blockquote {
  margin: 22px 0;
  padding: 16px 20px;
  border-left: 3px solid #a06b50;
  background: #b6896620;
  white-space: pre-wrap;
  line-height: 1.8;
  overflow-wrap: anywhere;
}
blockquote small {
  display: block;
}
.checklist {
  border-block: 1px dashed #a89c7866;
  padding-bottom: 10px;
  margin-bottom: 20px;
}
.checklist p {
  font-size: 15px;
}
.file-entry {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #9e927833;
  padding: 14px 0;
}
.file-entry div {
  min-width: 0;
  flex: 1;
}
.file-entry strong {
  font-size: 15px;
  overflow-wrap: anywhere;
  font-weight: 500;
}
.file-entry small {
  display: block;
  margin-top: 6px;
}
.file-entry p {
  font-size: 13px;
  white-space: pre-wrap;
  color: #985f4a;
}
.file-entry button {
  flex-shrink: 0;
  font-size: 13px;
}
.review-letter {
  margin-top: 30px;
  padding-top: 2px;
  border-top: 1px dashed #9a8c68;
}
.review-letter textarea {
  width: 100%;
  resize: vertical;
  line-height: 1.7;
}
.manual-review-fields { margin: 20px 0; padding: 16px; border: 1px dashed #a7997866; min-width: 0; }
.manual-review-fields label { display: grid; gap: 8px; margin: 12px 0; min-width: 0; }
.manual-review-fields input, .manual-review-fields select { width: 100%; color: inherit; font: inherit; }
.manual-slot { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr)); gap: 12px; }
.batch-time-slots { margin: 16px 0; padding: 14px; border: 1px solid #a7997866; border-radius: 8px; background: #a7997810; }
.batch-time-slots h4 { margin: 0; }
.review-letter p {
  font-size: 14px;
}
.requested-checks {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  font-size: 14px;
}
.requested-checks label {
  display: flex;
  align-items: center;
  gap: 7px;
}
.requested-checks input {
  accent-color: #60745f;
}
.review-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 22px 0;
}
.review-actions button {
  font-size: 14px;
}
footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ac9e752e;
}
footer span {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 14px;
}
.empty-note {
  padding: 26px 0;
  line-height: 1.8;
  color: #918164;
}
.ink-note {
  padding: 12px;
  background: #60745f18;
  white-space: pre-wrap;
}
.error {
  color: #9a5944;
  background: #9a615218;
}
@media (max-width: 540px) {
  .requested-checks {
    grid-template-columns: 1fr;
  }
  .archive-row {
    align-items: start;
  }
  .archive-row em {
    max-width: 95px;
  }
  .detail-title {
    align-items: start;
  }
  .paper-dossier {
    max-height: 94dvh;
  }
  .file-entry {
    gap: 6px;
  }
}
@media (prefers-reduced-motion: reduce) {
  button {
    transition: none;
  }
}
@media (max-width: 1024px) {
  .desk-veil { padding: max(12px,env(safe-area-inset-top)) 12px max(12px,env(safe-area-inset-bottom)); }
  .paper-dossier { max-height: calc(var(--portal-height,100dvh) - 32px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); overscroll-behavior: contain; padding: 20px; }
  button { min-height: 44px; touch-action: manipulation; }
  input, select, textarea { font-size: 16px; min-height: 44px; }
  input[type=checkbox] { min-height: auto; }
  .dossier-header { position: sticky; top: -20px; z-index: 2; background: #f2e9cf; margin: -20px -20px 0; padding: 16px 20px; gap: 12px; }
  .dossier-header h2 { font-size: 26px; }
  .close-leaf { flex-shrink: 0; }
}
</style>
