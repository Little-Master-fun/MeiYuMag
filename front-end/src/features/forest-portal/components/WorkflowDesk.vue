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

const props = defineProps<{
  mode: 'personal' | 'admin' | 'new'
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
const templates = ref<Array<{ name: string; application_type: string; download_url: string }>>([])
const admin = computed(() => props.mode === 'admin' && auth.isAdmin)
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
    selected.value &&
    ['ai_rejected', 'pending_signed_files', 'supplement_required'].includes(selected.value.status),
)
const canCancel = computed(
  () =>
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
  s ? new Date(s).toLocaleString('zh-CN', { hour12: false }) : '待材料确认'
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
    reason.value = ''
    requested.value = []
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
    const [venueData, templateData] = await Promise.all([
      axios.get('/api/v1/venues'),
      axios.get('/api/v1/templates'),
    ])
    venues.value = venueData.data
    templates.value = templateData.data
    if (!venueId.value) venueId.value = venues.value[0]?.id ?? 0
    if (props.mode !== 'new') {
      applications.value = (
        await axios.get(admin.value ? '/api/v1/admin/applications' : '/api/v1/applications')
      ).data
      if (props.applicationId) await openApplication(props.applicationId)
    }
  } catch (e) {
    error.value = getSubmissionErrorMessage(e)
  } finally {
    loading.value = false
  }
}
async function act(
  action: 'cancel' | 'submitted' | 'completed' | 'rejected' | 'supplement' | 'legacy-reject',
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
    else if (action === 'legacy-reject')
      await axios.post(`/api/v1/admin/applications/${id}/pre-review-decision`, {
        passed: false,
        reason: reason.value,
      })
    else
      await axios.patch(`/api/v1/admin/applications/${id}/status`, {
        status: action === 'cancel' ? 'cancelled' : action,
        reason: reason.value || undefined,
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
          <small>MEIYU · {{ admin ? 'REVIEW DESK' : 'APPLICATION ARCHIVE' }}</small>
          <h2 id="desk-title">
            {{ props.mode === 'new' ? '寄出一份申请' : admin ? '申请审核台' : '我的申请档案' }}
          </h2>
        </div>
        <button class="close-leaf" :disabled="busy" @click="close" aria-label="收起档案">×</button>
      </header>
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
        <p v-else class="empty-note">
          带上一份填写完整的 PDF 钥匙借用申请表，写明借用名称、组织及借还时间。
        </p>
        <footer>
          <button class="seal-action" @click="begin">前往信箱 <span>↗</span></button>
        </footer>
      </template>
      <template v-else>
        <div v-if="!selected" class="archive-list">
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
            <button v-else :disabled="busy" @click="act('legacy-reject')">
              退回修正 · 重新进行初审
            </button>
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
    </section>
  </div>
</template>

<style scoped>
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
</style>
