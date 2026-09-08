<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BookOpen, CalendarDays, Download, FileText, FolderOpen, Mail, X } from 'lucide-vue-next'
import { loadMaterialLibrary, type MaterialTemplate } from '../materialLibrary'
import { downloadMaterial } from '../workflow'

const props = withDefaults(defineProps<{ initialTab?: 'steps' | 'rules' | 'materials' }>(), {
  initialTab: 'steps',
})
const emit = defineEmits<{ close: [] }>()
const tab = ref(props.initialTab)
const paper = ref<HTMLElement | null>(null)
const pageScroll = ref<HTMLElement | null>(null)
const closeButton = ref<HTMLButtonElement | null>(null)
const templates = ref<MaterialTemplate[]>([])
const group = ref('all')
const loading = ref(false)
const error = ref('')
const downloadStatus = ref('')
const downloading = ref('')
const previousFocus = document.activeElement as HTMLElement | null
const groups = [
  { id: 'all', label: '全部材料' },
  { id: 'meiyu_venue', label: '美育馆场地' },
  { id: 'yueyuan_third_floor', label: '悦园三楼' },
  { id: 'key_borrow', label: '钥匙借用' },
]
const visibleTemplates = computed(() =>
  templates.value.filter(
    (item) =>
      group.value === 'all' ||
      item.application_type === group.value ||
      item.application_type === 'all',
  ),
)
const steps = [
  {
    icon: CalendarDays,
    title: '在日历选一天',
    text: '进入场地日历，用两侧书签选择场地。日历展示今天前后各 15 天；日期中的色条表示不同申请状态。点击可申请日期，或从个人首页的“场地申请”进入。',
  },
  {
    icon: FileText,
    title: '按木牌准备材料',
    text: '确认申请场地和日期，下载示例或模板。美育馆初审提交申请表，悦园三楼提交策划书，均为一份 DOCX；钥匙借用提交一份 PDF。文件中的场地和日期须与所选信息一致。',
  },
  {
    icon: Mail,
    title: '把文件放进信封',
    text: '点击 3D 信封或拖入文件，先在气泡里暂存；可继续添加、删除。签章或补交阶段要为每份文件选择材料用途。核对清单后点击“封缄并送出”，才会上传。',
  },
  {
    icon: FolderOpen,
    title: '回到文件夹查进度',
    text: '上传完成后返回文件夹。在个人首页或申请档案查看状态、审核原因和文件版本；需要签章、补交或重新初审时，从该申请继续前往信箱。',
  },
]
const statuses = [
  {
    label: '初审未通过',
    tone: 'rust',
    text: 'AI 检查未通过会直接退回并显示原因。修改 DOCX 后从原申请重新提交，保留文件版本。',
  },
  {
    label: '待签章材料',
    tone: 'ochre',
    text: '初审通过，进入预占用。按清单填写原表，完成真实签字盖章后提交；悦园三楼需要原文件与签章扫描件。',
  },
  {
    label: '待管理员审核',
    tone: 'stone',
    text: '等待管理员核对。AI 初审通过或文件上传成功，都不代表已获准使用场地。',
  },
  {
    label: '待补交材料',
    tone: 'rust',
    text: '按管理员给出的原因和材料清单补交，每种要求的材料对应一份文件，齐全后再次送审。',
  },
  {
    label: '已审核确认',
    tone: 'sage',
    text: '管理员已确认申请，场地占用转为确认状态。请按审批结果和场地管理要求使用。',
  },
  {
    label: '已完成或已取消',
    tone: 'stone',
    text: '在历史申请中查看。未开始且允许取消的申请，可在档案中取消并释放占用；正式驳回后需另行发起新申请。',
  },
]
async function load() {
  loading.value = true
  error.value = ''
  try {
    templates.value = await loadMaterialLibrary()
  } catch {
    error.value = '材料目录暂时没取到，请稍后重试。'
  } finally {
    loading.value = false
  }
}
async function download(item: MaterialTemplate) {
  if (downloading.value) return
  downloading.value = item.id
  downloadStatus.value = `正在取出 ${item.name}`
  try {
    await downloadMaterial(item.download_url, item.name)
    downloadStatus.value = `已开始下载 ${item.name}`
  } catch {
    downloadStatus.value = '下载未成功，请检查网络后再试。'
  } finally {
    downloading.value = ''
  }
}
function keydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.stopPropagation()
    emit('close')
  }
  if (event.key !== 'Tab') return
  const elements = Array.from(
    paper.value?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], [tabindex="0"]') ??
      [],
  )
  const first = elements[0],
    last = elements.at(-1)
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last?.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first?.focus()
  }
}
onMounted(async () => {
  void load()
  await nextTick()
  closeButton.value?.focus()
})
watch(tab, () => {
  if (pageScroll.value) pageScroll.value.scrollTop = 0
})
onBeforeUnmount(() => previousFocus?.isConnected && previousFocus.focus())
</script>

<template>
  <div
    class="guide-veil"
    @pointerdown.self="emit('close')"
    @pointerdown.stop
    @click.stop
    @wheel.stop
    @keydown="keydown"
  >
    <section
      ref="paper"
      class="guide-paper"
      role="dialog"
      aria-modal="true"
      aria-labelledby="application-guide-title"
    >
      <button
        ref="closeButton"
        class="guide-close"
        aria-label="收起使用指南"
        @click="emit('close')"
      >
        <X :size="21" />
      </button>
      <header class="guide-heading">
        <span class="guide-stamp" aria-hidden="true"
          ><BookOpen :size="27" :stroke-width="1.25"
        /></span>
        <div>
          <small>MEIYU · FIELD NOTES</small>
          <h1 id="application-guide-title">申请使用指南</h1>
          <p>从挑选场地，到收到审核结果。</p>
        </div>
      </header>
      <nav class="guide-tabs" aria-label="指南章节">
        <button :aria-pressed="tab === 'steps'" @click="tab = 'steps'">01 如何申请</button>
        <button :aria-pressed="tab === 'rules'" @click="tab = 'rules'">02 审核与规则</button>
        <button :aria-pressed="tab === 'materials'" @click="tab = 'materials'">
          03 示例与模板
        </button>
      </nav>
      <div ref="pageScroll" class="guide-scroll">
        <Transition name="guide-page" mode="out-in">
          <div v-if="tab === 'steps'" key="steps" class="guide-content">
            <div class="journey-strip" aria-label="日历选场地，准备材料，信封提交，档案查进度">
              <template v-for="(step, index) in steps" :key="step.title"
                ><span
                  ><component :is="step.icon" :size="26" :stroke-width="1.25" /><small>{{
                    ['选日期', '备材料', '寄申请', '查进度'][index]
                  }}</small></span
                ><i v-if="index < 3" aria-hidden="true">⤳</i></template
              >
            </div>
            <ol class="guide-steps">
              <li v-for="(step, index) in steps" :key="step.title">
                <span class="step-number">0{{ index + 1 }}</span>
                <div>
                  <h2>{{ step.title }}</h2>
                  <p>{{ step.text }}</p>
                </div>
              </li>
            </ol>
            <button class="guide-next" @click="tab = 'materials'">
              去材料夹取一份示例 <Download :size="16" />
            </button>
          </div>
          <div v-else-if="tab === 'rules'" key="rules" class="guide-content">
            <p class="guide-intro">
              以下说明对应当前系统流程，不代替学校或场地的正式管理规定；实际使用以管理员确认结果为准。
            </p>
            <dl class="status-notes">
              <div v-for="status in statuses" :key="status.label">
                <dt :class="status.tone">{{ status.label }}</dt>
                <dd>{{ status.text }}</dd>
              </div>
            </dl>
            <section class="guide-notes">
              <h2>寄出之前，再核对一下</h2>
              <p>
                申请账号需具备场地申请权限。空闲日期只是当前占用情况，实际提交时系统仍会检查时间冲突，预占用不等于最终许可。
              </p>
              <p>
                初审主文件为一份 DOCX；钥匙借用为一份 PDF。附加材料支持
                DOC、DOCX、PDF、JPG、JPEG、PNG，每份不超过 30 MB，一次最多 10 份、合计不超过 100
                MB。
              </p>
              <p>
                信封暂存发生在当前页面，刷新或关闭页面不会保留未上传文件。请等到上传成功再离开；失败时先核对提示，不要反复新建同一申请。
              </p>
              <p>钥匙借用走独立申请流程：系统提取 PDF 信息后交管理员审核，不等同于场地初审通过。</p>
            </section>
          </div>
          <div v-else key="materials" class="guide-content">
            <p class="guide-intro">
              “模板”是项目已有原表；“填写示例”用于理解所需信息，含虚构内容，不能原样提交。签章材料请填写原表、打印签章后扫描，示例不含有效签章。
            </p>
            <nav class="material-filters" aria-label="按申请类型筛选材料">
              <button
                v-for="item in groups"
                :key="item.id"
                :aria-pressed="group === item.id"
                @click="group = item.id"
              >
                {{ item.label }}
              </button>
            </nav>
            <p v-if="loading" role="status">正在打开材料夹…</p>
            <p v-else-if="error" role="alert">
              {{ error }} <button class="guide-next" @click="load">重新取阅</button>
            </p>
            <ul v-else class="material-library">
              <li v-for="item in visibleTemplates" :key="item.id">
                <FileText :size="24" :stroke-width="1.2" aria-hidden="true" />
                <div>
                  <span class="material-kind"
                    >{{ item.kind === 'example' ? '填写示例' : '原表模板' }} ·
                    {{ item.name.split('.').pop()?.toUpperCase() }}</span
                  >
                  <h2>{{ item.name.replace(/\.(docx|pdf)$/i, '') }}</h2>
                  <p>{{ item.description }}</p>
                </div>
                <button
                  :disabled="!!downloading"
                  :aria-label="`下载${item.name}`"
                  @click="download(item)"
                >
                  <Download :size="18" /><span>{{
                    downloading === item.id ? '取出中' : '取一份'
                  }}</span>
                </button>
              </li>
            </ul>
            <p class="download-status" role="status" aria-live="polite">{{ downloadStatus }}</p>
          </div>
        </Transition>
      </div>
      <footer class="guide-footer">使用时也可以直接点击信箱木牌上的材料名称取阅。</footer>
    </section>
  </div>
</template>

<style scoped>
.guide-veil {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: 26px;
  background: rgb(27 38 31 / 38%);
  backdrop-filter: blur(6px);
}
.guide-paper {
  position: relative;
  display: flex;
  flex-direction: column;
  width: min(760px, 100%);
  max-height: calc(100dvh - 52px);
  overflow: hidden;
  padding: 40px 46px 24px;
  box-sizing: border-box;
  background: linear-gradient(115deg, #f6f0de, #ebe0bc);
  color: #614a2c;
  font-family: 'Songti SC', 'STSong', serif;
  border: 1px solid #d6c69d;
  border-radius: 5px 18px 7px 4px;
  box-shadow:
    0 25px 70px #17261d55,
    inset 7px 0 #baa16a15;
}
.guide-scroll {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: #b5ae8c transparent;
  scrollbar-width: thin;
  margin-right: -12px;
  padding-right: 12px;
}
.guide-heading,
.guide-tabs,
.guide-footer {
  flex-shrink: 0;
}
button {
  font: inherit;
  cursor: pointer;
}
button:focus-visible {
  outline: 2px solid #607457;
  outline-offset: 4px;
}
.guide-close {
  position: absolute;
  top: 16px;
  right: 16px;
  padding: 7px;
  border: 0;
  background: transparent;
  color: #74674b;
  border-radius: 50%;
}
.guide-close:hover {
  background: #d5c49d55;
}
.guide-heading {
  display: flex;
  align-items: center;
  gap: 21px;
  margin-bottom: 28px;
}
.guide-heading small {
  color: #9d916f;
  font:
    10px Georgia,
    serif;
  letter-spacing: 0.13em;
}
.guide-heading h1 {
  margin: 7px 0 5px;
  font-size: 32px;
  font-weight: 500;
}
.guide-heading p {
  margin: 0;
  color: #9a875c;
  font-size: 14px;
}
.guide-stamp {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 65px;
  height: 68px;
  color: #ede9ce;
  background: #687958;
  border-radius: 48% 45% 49% 44%;
  transform: rotate(-7deg);
  box-shadow: inset 0 0 0 4px #eee7ca20;
}
.guide-tabs {
  display: flex;
  border-bottom: 1px solid #b7a27066;
  gap: 10px;
}
.guide-tabs button {
  color: #8b7952;
  padding: 12px 16px;
  border: 1px solid transparent;
  border-bottom: 0;
  background: transparent;
  border-radius: 8px 8px 0 0;
  font-size: 14px;
}
.guide-tabs button[aria-pressed='true'] {
  background: #d9d7b766;
  color: #526547;
  border-color: #b7a27066;
}
.guide-tabs button:hover {
  color: #526547;
  background: #d9d7b744;
}
.guide-content {
  padding: 22px 0 12px;
}
.journey-strip {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 16px 4px 22px;
  color: #6b795b;
}
.journey-strip span {
  display: grid;
  justify-items: center;
  gap: 10px;
}
.journey-strip small {
  font-size: 12px;
}
.journey-strip i {
  color: #aa9566;
  font-size: 26px;
  font-style: normal;
}
.guide-steps {
  list-style: none;
  padding: 0;
  margin: 0;
}
.guide-steps li {
  display: flex;
  gap: 18px;
  padding: 14px 0;
}
.step-number {
  font:
    italic 23px Georgia,
    serif;
  color: #9f956e;
  padding-top: 3px;
}
h2 {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 500;
}
p {
  font-size: 14px;
  line-height: 1.85;
  margin: 0;
  color: #85734f;
}
.guide-next {
  display: inline-flex;
  align-items: center;
  gap: 15px;
  border: 0;
  border-bottom: 1px dashed #8e9977;
  padding: 9px 0;
  margin-top: 12px;
  background: none;
  color: #5e7254;
  font-size: 14px;
}
.guide-next:hover {
  color: #374d33;
}
.guide-intro {
  margin-bottom: 18px;
}
.status-notes {
  margin: 0;
}
.status-notes > div {
  display: grid;
  grid-template-columns: 118px 1fr;
  gap: 18px;
  padding: 14px 0;
  border-bottom: 1px dashed #bcaa8055;
}
.status-notes dt {
  font-size: 14px;
  padding-top: 3px;
}
.status-notes dd {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: #85734f;
}
.sage {
  color: #5d734d;
}
.ochre {
  color: #a28139;
}
.rust {
  color: #a06447;
}
.stone {
  color: #827c6a;
}
.guide-notes {
  margin-top: 24px;
}
.guide-notes p {
  margin-top: 12px;
}
.material-filters {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.material-filters button {
  background: transparent;
  color: #85734f;
  border: 0;
  border-bottom: 1px solid transparent;
  padding: 6px 9px;
  font-size: 13px;
}
.material-filters button[aria-pressed='true'] {
  color: #53684b;
  border-bottom-color: #6d7d5c;
}
.material-filters button:hover {
  background: #d9d7b744;
}
.material-library {
  list-style: none;
  margin: 0;
  padding: 0;
}
.material-library li {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) auto;
  align-items: center;
  gap: 15px;
  padding: 18px 0;
  border-bottom: 1px solid #c3b28755;
}
.material-library > li > svg {
  color: #9e9e7b;
}
.material-kind {
  display: block;
  font-size: 10px;
  letter-spacing: 0.06em;
  color: #9c916b;
  margin-bottom: 5px;
}
.material-library h2 {
  font-size: 16px;
}
.material-library p {
  font-size: 12px;
  line-height: 1.65;
}
.material-library button {
  display: grid;
  gap: 6px;
  justify-items: center;
  border: 0;
  border-radius: 3px 12px 12px 3px;
  padding: 11px;
  background: #d8ddc044;
  color: #657853;
  font-size: 11px;
  transition:
    transform 0.2s,
    background 0.2s;
}
.material-library button:hover {
  transform: translateY(-2px);
  background: #d8ddc0bb;
}
.material-library button:disabled {
  opacity: 0.5;
  cursor: wait;
}
.download-status {
  min-height: 22px;
  font-size: 12px;
  margin-top: 12px;
  color: #657853;
  overflow-wrap: anywhere;
}
.guide-footer {
  color: #a08f66;
  padding-top: 18px;
  border-top: 1px solid #b7a27055;
  font-size: 12px;
  line-height: 1.6;
}
.guide-page-enter-active,
.guide-page-leave-active {
  transition:
    opacity 0.16s,
    transform 0.16s;
}
.guide-page-enter-from,
.guide-page-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
@media (max-width: 600px) {
  .guide-veil {
    padding: 12px;
  }
  .guide-paper {
    padding: 34px 20px 20px;
    max-height: calc(100dvh - 24px);
  }
  .guide-heading {
    gap: 14px;
  }
  .guide-heading h1 {
    font-size: 25px;
  }
  .guide-stamp {
    width: 49px;
    height: 53px;
  }
  .guide-tabs {
    gap: 0;
  }
  .guide-tabs button {
    flex: 1;
    font-size: 12px;
    padding: 11px 4px;
  }
  .status-notes > div {
    grid-template-columns: 1fr;
    gap: 5px;
  }
  .material-library li {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
  }
  .material-library > li > svg {
    display: none;
  }
  .guide-steps li {
    gap: 12px;
  }
}
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    transition: none !important;
  }
}
@media (max-width: 1024px) {
  .guide-paper { max-height: calc(var(--portal-height,100dvh) - 32px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); }
  button { min-height: 44px; touch-action: manipulation; }
  .guide-close { min-width: 44px; }
  .guide-tabs button { min-height: 44px; }
}
</style>
