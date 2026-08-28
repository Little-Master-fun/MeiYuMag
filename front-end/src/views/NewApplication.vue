<script setup lang="ts">
import { ref, computed } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import axios from 'axios'
import {
  Building2, Key, ChevronRight, ChevronLeft, Upload,
  Check, Loader2, Info, Calendar, FileText, AlertCircle
} from 'lucide-vue-next'

const router = useRouter()
const notify = useNotificationsStore()

// Step management
const step = ref(1)
const STEPS = ['选择类型', '填写信息', '上传材料', '提交完成']

// Form state
const appType = ref<'meiyu' | 'yueyuan' | 'key' | ''>('')
const venueId = ref<number | null>(null)
const organization = ref('')
const purpose = ref('')
const startDate = ref('')
const endDate = ref('')
const selectedFile = ref<File | null>(null)
const dragOver = ref(false)
const submitting = ref(false)
const createdAppId = ref<number | null>(null)

const venues = ref<any[]>([])
const loadingVenues = ref(false)

async function loadVenues() {
  loadingVenues.value = true
  try {
    const { data } = await axios.get('/api/v1/venues')
    venues.value = data
  } catch { /* ignore */ } finally {
    loadingVenues.value = false
  }
}

const typeCards = [
  {
    type: 'meiyu',
    title: '美育场地',
    desc: '申请美育中心场地使用，需提交活动策划书',
    icon: Building2,
    color: 'teal',
    tag: '需AI预审',
  },
  {
    type: 'yueyuan',
    title: '月苑三楼',
    desc: '申请月苑三楼活动场地，需提交活动申报材料',
    icon: Building2,
    color: 'blue',
    tag: '需AI预审',
  },
  {
    type: 'key',
    title: '钥匙借用',
    desc: '申请借用场地钥匙，需提交借用申请说明',
    icon: Key,
    color: 'amber',
    tag: '快速审核',
  },
]

function selectType(t: string) {
  appType.value = t as any
  if (t !== 'key') loadVenues()
}

function nextStep() {
  if (step.value === 1 && !appType.value) {
    notify.warning('请选择申请类型')
    return
  }
  if (step.value === 2 && !organization.value) {
    notify.warning('请填写申请组织')
    return
  }
  step.value++
}

function prevStep() {
  if (step.value > 1) step.value--
}

function handleFileDrop(e: DragEvent) {
  dragOver.value = false
  const file = e.dataTransfer?.files[0]
  if (file) selectedFile.value = file
}

function handleFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) selectedFile.value = input.files[0]
}

function formatFileSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function submit() {
  if (!selectedFile.value) {
    notify.warning('请上传申请材料')
    return
  }
  submitting.value = true
  try {
    // 1. Create application
    const { data: app } = await axios.post('/api/v1/applications', {
      app_type: appType.value,
      venue_id: venueId.value,
    })
    createdAppId.value = app.id

    // 2. Upload file for pre-review
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    await axios.post(`/api/v1/applications/${app.id}/pre-review`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    step.value = 4
    notify.success('申请提交成功', '材料已上传，正在进行AI预审核')
  } catch (e: any) {
    notify.error('提交失败', e.response?.data?.detail || '请稍后重试')
  } finally {
    submitting.value = false
  }
}

const colorMap: Record<string, string> = {
  teal: 'type-teal', blue: 'type-blue', amber: 'type-amber',
}
</script>

<template>
  <AppLayout>
    <div class="new-app-page">

      <!-- Page header -->
      <div class="page-header">
        <h1>新建申请</h1>
        <p>请按步骤完成申请信息填写</p>
      </div>

      <!-- Stepper -->
      <div class="stepper">
        <div
          v-for="(s, i) in STEPS"
          :key="i"
          class="step-item"
          :class="{
            'step-done':   step > i + 1,
            'step-active': step === i + 1,
          }"
        >
          <div class="step-circle">
            <Check v-if="step > i + 1" :size="14" />
            <span v-else>{{ i + 1 }}</span>
          </div>
          <span class="step-label">{{ s }}</span>
          <div v-if="i < STEPS.length - 1" class="step-line" />
        </div>
      </div>

      <!-- Step 1: Type selection -->
      <Transition name="slide-up" mode="out-in">
        <div v-if="step === 1" key="step1" class="step-content">
          <h2>选择申请类型</h2>
          <p class="step-desc">请选择您需要申请的场地或资源类型</p>

          <div class="type-cards">
            <button
              v-for="card in typeCards"
              :key="card.type"
              class="type-card"
              :class="[colorMap[card.color], { selected: appType === card.type }]"
              @click="selectType(card.type)"
            >
              <div class="type-card-icon">
                <component :is="card.icon" :size="26" />
              </div>
              <div class="type-card-body">
                <div class="type-card-head">
                  <h3>{{ card.title }}</h3>
                  <span class="type-tag">{{ card.tag }}</span>
                </div>
                <p>{{ card.desc }}</p>
              </div>
              <div class="type-check">
                <Check :size="16" />
              </div>
            </button>
          </div>

          <div class="step-nav">
            <div />
            <button class="btn-next" @click="nextStep">
              下一步 <ChevronRight :size="17" />
            </button>
          </div>
        </div>

        <!-- Step 2: Info -->
        <div v-else-if="step === 2" key="step2" class="step-content">
          <h2>填写申请信息</h2>
          <p class="step-desc">请填写您的组织信息和申请目的</p>

          <div class="form-grid">
            <div class="field">
              <label class="field-label">申请组织/社团 <span class="required">*</span></label>
              <input
                v-model="organization"
                type="text"
                placeholder="例：山东大学某某社团"
                class="field-input"
              />
            </div>

            <div v-if="appType !== 'key'" class="field">
              <label class="field-label">选择场地</label>
              <select v-model="venueId" class="field-input">
                <option :value="null">{{ loadingVenues ? '加载中...' : '请选择场地' }}</option>
                <option v-for="v in venues" :key="v.id" :value="v.id">{{ v.name }}</option>
              </select>
            </div>

            <div v-if="appType !== 'key'" class="field">
              <label class="field-label">活动开始时间</label>
              <input v-model="startDate" type="datetime-local" class="field-input" />
            </div>

            <div v-if="appType !== 'key'" class="field">
              <label class="field-label">活动结束时间</label>
              <input v-model="endDate" type="datetime-local" class="field-input" />
            </div>

            <div class="field col-span-2">
              <label class="field-label">活动目的/说明</label>
              <textarea
                v-model="purpose"
                rows="3"
                placeholder="简要描述活动目的和内容..."
                class="field-input"
              />
            </div>
          </div>

          <div class="step-nav">
            <button class="btn-prev" @click="prevStep">
              <ChevronLeft :size="17" /> 上一步
            </button>
            <button class="btn-next" @click="nextStep">
              下一步 <ChevronRight :size="17" />
            </button>
          </div>
        </div>

        <!-- Step 3: Upload -->
        <div v-else-if="step === 3" key="step3" class="step-content">
          <h2>上传申请材料</h2>
          <p class="step-desc">请上传完整的申请文件，支持 Word / PDF / 图片格式</p>

          <!-- Info tip -->
          <div class="info-tip">
            <Info :size="15" />
            <span>
              {{ appType === 'key' ? '请上传钥匙借用申请说明文件' : '请上传活动策划书，AI将对材料进行智能预审' }}
            </span>
          </div>

          <!-- Drop zone -->
          <div
            class="drop-zone"
            :class="{ 'drag-over': dragOver, 'has-file': !!selectedFile }"
            @dragover.prevent="dragOver = true"
            @dragleave="dragOver = false"
            @drop.prevent="handleFileDrop"
          >
            <template v-if="selectedFile">
              <FileText :size="36" class="dz-file-icon" />
              <p class="dz-filename">{{ selectedFile.name }}</p>
              <p class="dz-filesize">{{ formatFileSize(selectedFile.size) }}</p>
              <label class="dz-change-btn">
                更换文件
                <input type="file" accept=".doc,.docx,.pdf,.jpg,.jpeg,.png" hidden @change="handleFileInput" />
              </label>
            </template>
            <template v-else>
              <Upload :size="36" class="dz-upload-icon" />
              <p class="dz-text">拖拽文件至此，或</p>
              <label class="dz-select-btn">
                选择文件
                <input type="file" accept=".doc,.docx,.pdf,.jpg,.jpeg,.png" hidden @change="handleFileInput" />
              </label>
              <p class="dz-hint">支持 .doc .docx .pdf .jpg .png，最大 30MB</p>
            </template>
          </div>

          <div class="step-nav">
            <button class="btn-prev" @click="prevStep">
              <ChevronLeft :size="17" /> 上一步
            </button>
            <button
              class="btn-submit"
              :disabled="submitting || !selectedFile"
              @click="submit"
            >
              <Loader2 v-if="submitting" :size="17" class="animate-spin" />
              <template v-else>
                提交申请 <ChevronRight :size="17" />
              </template>
            </button>
          </div>
        </div>

        <!-- Step 4: Success -->
        <div v-else key="step4" class="step-content step-success">
          <div class="success-icon">
            <Check :size="40" />
          </div>
          <h2>申请提交成功！</h2>
          <p class="step-desc">
            您的申请已成功提交，系统正在进行AI预审核。<br />
            审核结果将通过邮件通知您，请注意查收。
          </p>

          <div class="success-actions">
            <button class="btn-outline" @click="router.push('/applications')">
              查看我的申请
            </button>
            <button class="btn-next" @click="router.push('/dashboard')">
              返回首页
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </AppLayout>
</template>

<style scoped>
.new-app-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 760px;
}

.page-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 800;
  color: #e8f5f0;
  animation: float-up 0.4s ease both;
}
.page-header p {
  margin: 0;
  font-size: 13px;
  color: rgba(232,245,240,0.5);
  animation: float-up 0.4s ease both 0.05s;
}

/* Stepper */
.stepper {
  display: flex;
  align-items: center;
  gap: 0;
  animation: float-up 0.4s ease both 0.08s;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.step-circle {
  width: 30px; height: 30px;
  border-radius: 50%;
  display: grid; place-items: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  background: rgba(255,255,255,0.06);
  border: 1.5px solid rgba(255,255,255,0.15);
  color: rgba(232,245,240,0.4);
  transition: all 0.3s ease;
}

.step-label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(232,245,240,0.4);
  white-space: nowrap;
  transition: color 0.3s;
}

.step-line {
  flex: 1;
  height: 1.5px;
  background: rgba(255,255,255,0.08);
  margin: 0 8px;
  transition: background 0.3s;
}

.step-item.step-active .step-circle {
  background: rgba(61,217,172,0.18);
  border-color: #3DD9AC;
  color: #3DD9AC;
  box-shadow: 0 0 12px rgba(61,217,172,0.25);
}

.step-item.step-active .step-label {
  color: #3DD9AC;
}

.step-item.step-done .step-circle {
  background: #3DD9AC;
  border-color: #3DD9AC;
  color: #060e0c;
}

.step-item.step-done .step-label {
  color: rgba(232,245,240,0.65);
}

.step-item.step-done .step-line {
  background: rgba(61,217,172,0.35);
}

/* Step content */
.step-content {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 28px;
  animation: float-up 0.4s ease both;
}

.step-content h2 {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 700;
  color: #e8f5f0;
}

.step-desc {
  margin: 0 0 22px;
  font-size: 14px;
  color: rgba(232,245,240,0.5);
}

/* Type cards */
.type-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.type-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  background: rgba(255,255,255,0.03);
  border: 1.5px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.type-card:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(61,217,172,0.25);
}

.type-card.selected {
  border-color: rgba(61,217,172,0.5);
  background: rgba(61,217,172,0.07);
}

.type-teal.selected  { border-color: rgba(61,217,172,0.5);  background: rgba(61,217,172,0.07); }
.type-blue.selected  { border-color: rgba(96,165,250,0.5);  background: rgba(96,165,250,0.07); }
.type-amber.selected { border-color: rgba(247,202,117,0.5); background: rgba(247,202,117,0.07); }

.type-card-icon {
  width: 48px; height: 48px;
  border-radius: 12px;
  display: grid; place-items: center;
  flex-shrink: 0;
}

.type-teal  .type-card-icon { background: rgba(61,217,172,0.15);  color: #3DD9AC; }
.type-blue  .type-card-icon { background: rgba(96,165,250,0.15);  color: #60a5fa; }
.type-amber .type-card-icon { background: rgba(247,202,117,0.15); color: #F7CA75; }

.type-card-body { flex: 1; }

.type-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.type-card-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: rgba(232,245,240,0.9);
}

.type-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 99px;
  background: rgba(61,217,172,0.12);
  color: #3DD9AC;
  border: 1px solid rgba(61,217,172,0.2);
}

.type-card-body p {
  margin: 0;
  font-size: 13px;
  color: rgba(232,245,240,0.5);
}

.type-check {
  width: 24px; height: 24px;
  border-radius: 50%;
  display: grid; place-items: center;
  background: rgba(61,217,172,0.15);
  color: #3DD9AC;
  opacity: 0;
  transform: scale(0.7);
  transition: opacity 0.2s, transform 0.2s;
}

.type-card.selected .type-check {
  opacity: 1;
  transform: scale(1);
}

/* Form grid */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.col-span-2 { grid-column: span 2; }

.field { display: flex; flex-direction: column; gap: 7px; }

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(232,245,240,0.65);
}

.required { color: #f87171; }

.field-input {
  padding: 11px 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 9px;
  color: #e8f5f0;
  font-size: 13px;
  transition: border-color 0.2s;
  resize: vertical;
}

.field-input::placeholder { color: rgba(232,245,240,0.28); }
.field-input:focus { outline: none; border-color: rgba(61,217,172,0.45); background: rgba(61,217,172,0.03); }
.field-input option { background: #0d1f1c; }

/* Info tip */
.info-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(96,165,250,0.08);
  border: 1px solid rgba(96,165,250,0.2);
  border-radius: 9px;
  color: rgba(96,165,250,0.9);
  font-size: 13px;
  margin-bottom: 16px;
}

/* Drop zone */
.drop-zone {
  border: 2px dashed rgba(255,255,255,0.15);
  border-radius: 14px;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: rgba(255,255,255,0.02);
  margin-bottom: 24px;
  text-align: center;
}

.drop-zone.drag-over {
  border-color: rgba(61,217,172,0.5);
  background: rgba(61,217,172,0.05);
}

.drop-zone.has-file {
  border-color: rgba(61,217,172,0.35);
  background: rgba(61,217,172,0.04);
}

.dz-upload-icon { color: rgba(232,245,240,0.25); }
.dz-file-icon   { color: #3DD9AC; }
.dz-filename    { margin: 0; font-size: 14px; font-weight: 600; color: rgba(232,245,240,0.85); }
.dz-filesize    { margin: 0; font-size: 12px; color: rgba(232,245,240,0.4); }
.dz-text        { margin: 0; font-size: 14px; color: rgba(232,245,240,0.55); }
.dz-hint        { margin: 0; font-size: 11px; color: rgba(232,245,240,0.3); }

.dz-select-btn,
.dz-change-btn {
  display: inline-block;
  padding: 9px 18px;
  background: rgba(61,217,172,0.1);
  border: 1px solid rgba(61,217,172,0.3);
  border-radius: 8px;
  color: #3DD9AC;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.dz-select-btn:hover,
.dz-change-btn:hover { background: rgba(61,217,172,0.18); }

/* Navigation */
.step-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.btn-prev {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 11px 20px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  color: rgba(232,245,240,0.7);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-prev:hover { background: rgba(255,255,255,0.09); }

.btn-next, .btn-submit {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 11px 24px;
  background: linear-gradient(90deg, #3DD9AC, #5FCBB8);
  border: 0;
  border-radius: 10px;
  color: #060e0c;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
}

.btn-next:hover, .btn-submit:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(61,217,172,0.25);
}

.btn-submit:disabled {
  opacity: 0.5;
  pointer-events: none;
}

/* Success step */
.step-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 52px 28px;
  gap: 12px;
}

.success-icon {
  width: 80px; height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(61,217,172,0.2), rgba(61,217,172,0.08));
  border: 2px solid rgba(61,217,172,0.4);
  display: grid; place-items: center;
  color: #3DD9AC;
  animation: bounce-in 0.5s ease both;
  box-shadow: 0 0 30px rgba(61,217,172,0.2);
  margin-bottom: 8px;
}

.success-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.btn-outline {
  padding: 11px 22px;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 10px;
  color: rgba(232,245,240,0.7);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.btn-outline:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.35);
}

@media (max-width: 600px) {
  .form-grid { grid-template-columns: 1fr; }
  .col-span-2 { grid-column: span 1; }
  .stepper { overflow-x: auto; }
}
</style>
