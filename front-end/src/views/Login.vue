<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import axios from 'axios'
import * as THREE from 'three'
import { gsap } from 'gsap'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import GUI from 'three/addons/libs/lil-gui.module.min.js'
import {
  ArrowRight,
  Building2,
  Eye,
  EyeOff,
  FileText,
  LockKeyhole,
  Mail,
  RefreshCw,
  Smartphone,
  Trees,
  UserRound,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import {
  createParchmentPageCanvas,
  type PersonalApplicationItem,
  type ParchmentPageCanvas,
  type VenueUsageBoard,
  type VenueUsageItem,
} from '@/assets/textures/parchmentPage'
import {
  enablePageTurnDeformation,
  type PageTurnShaderUniforms,
} from '@/assets/shaders/pageTurn'
import {
  projectPageContentOntoMaterial,
  type PageContentBounds,
} from '@/assets/shaders/pageContent'
import { enableTreeCrownWind, type WindShaderUniforms } from '@/assets/shaders/treeWind'

const viewport = ref<HTMLDivElement | null>(null)
const venueSelector = ref<HTMLElement | null>(null)
const applicationTab = ref<HTMLButtonElement | null>(null)
const authFormStage = ref<HTMLDivElement | null>(null)
const applicationFileInput = ref<HTMLInputElement | null>(null)
const loadingProgress = ref(0)
const loadError = ref('')
const modelReady = ref(false)
const cinematicActive = ref(false)
const loginPanelVisible = ref(false)
const account = ref('')
const password = ref('')
const passwordVisible = ref(false)
const authMode = ref<'login' | 'register'>('login')
const registerEmail = ref('')
const registerOrganization = ref('')
const registerMobile = ref('')
const registerImageCode = ref('')
const registerSmsCode = ref('')
const registerPassword = ref('')
const registerPasswordConfirm = ref('')
const registerPasswordVisible = ref(false)
const registrationCaptchaUrl = ref('')
const captchaLoading = ref(false)
const smsSending = ref(false)
const smsSent = ref(false)
const smsCountdown = ref(0)
const formError = ref('')
const formNotice = ref('')
const loginSucceeded = ref(false)
const pageTurnAvailable = ref(false)
const pageTurning = ref(false)
const pageTurnCompleted = ref(false)
const pageTurnEnabled = false
const applicationStageActive = ref(false)
const folderPage = ref<'profile' | 'calendar'>('profile')
const submissionNoticeVisible = ref(false)
const submissionNoticeMessage = ref('')
const submissionNoticeMode = ref<'uploading' | 'success' | 'error'>('uploading')
const applicationTabLoading = ref(false)
const submissionFilesUploading = ref(false)

const auth = useAuthStore()

interface VenueApiItem {
  id: number
  name: string
}

interface VenueCalendarEventApi {
  id: string
  title: string
  organization: string | null
  borrow_organization: string | null
  purpose_summary: string | null
  start_at: string
  end_at: string
  status: string
}

interface VenueUsageRangeApi {
  start_date: string
  end_date: string
  venues: Array<{
    venue: VenueApiItem
    events: VenueCalendarEventApi[]
  }>
}

interface PersonalApplicationApi {
  id: number
  application_type: string
  venue_id: number | null
  purpose_summary: string | null
  status: string
  start_at: string | null
  end_at: string | null
  review_reason: string | null
  created_at: string
}

const venueOptions = ref<VenueApiItem[]>([])
const selectedVenueId = ref<number | null>(null)
const venueSelectorReady = ref(false)

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let model: THREE.Object3D | null = null
let houseModel: THREE.Object3D | null = null
let clipboardModel: THREE.Object3D | null = null
let mailboxModel: THREE.Object3D | null = null
let submissionSignModel: THREE.Group | null = null
let submissionSignTween: gsap.core.Tween | null = null
let submissionSignTargetY = 0
let resizeObserver: ResizeObserver | null = null
let animationFrame = 0
let smsCountdownTimer: ReturnType<typeof setInterval> | null = null
let topPage: THREE.Mesh | null = null
let paperSurfaceMesh: THREE.Mesh | null = null
let paperContentBounds: PageContentBounds | null = null
let paperVisibleFacePoints: THREE.Vector3[] = []
let paperVisibleFaceZ = 0
let pageTurnShader: PageTurnShaderUniforms | null = null
let pageContentCanvas: ParchmentPageCanvas | null = null
let personalHomeBoard: VenueUsageBoard | null = null
let venueUsageBoard: VenueUsageBoard | null = null
let pageTurnTimeline: gsap.core.Timeline | null = null
const pageRaycaster = new THREE.Raycaster()
const pagePointer = new THREE.Vector2()
const topPageInitialPosition = new THREE.Vector3()
const topPageInitialRotation = new THREE.Euler()
const topPageInitialScale = new THREE.Vector3(1, 1, 1)

interface CameraFlight {
  startTarget: THREE.Vector3
  endTarget: THREE.Vector3
  currentTarget: THREE.Vector3
  startAngle: number
  angleDelta: number
  startRadius: number
  finalRadius: number
  startHeight: number
  finalHeight: number
  moveDuration: number
  rotationDuration: number
  totalDuration: number
  startedAt: number
}

interface PostLoginFlight {
  startPosition: THREE.Vector3
  endPosition: THREE.Vector3
  startTarget: THREE.Vector3
  endTarget: THREE.Vector3
  currentTarget: THREE.Vector3
  startClipboardPosition: THREE.Vector3
  endClipboardPosition: THREE.Vector3
  startClipboardQuaternion: THREE.Quaternion
  endClipboardQuaternion: THREE.Quaternion
  startClipboardScale: number
  endClipboardScale: number
  cameraDuration: number
  clipboardDuration: number
  overlapDuration: number
  startedAt: number
}

interface ApplicationNavigationTarget {
  venueId: number
  venueName: string
  date: string
  mode?: 'new' | 'resubmit' | 'supplement'
  applicationId?: number
}

interface StagedSubmissionFile {
  id: string
  file: File
}

const submissionContext = ref<ApplicationNavigationTarget | null>(null)
const pendingSubmissionFiles = ref<StagedSubmissionFile[]>([])
const submissionGuide = computed(() => {
  const target = submissionContext.value
  if (!target) return null

  if (target.mode === 'resubmit') {
    return {
      kicker: 'AI REVIEW · RETRY',
      step: '重新提交',
      title: '修正后重新初审',
      requirements: [
        { label: '修改后的场地申请表', extension: '.docx', kind: 'primary' as const },
      ],
      description: '新文件会保存为当前申请的新版本，并立即重新进入 AI 初审。',
    }
  }

  if (target.mode === 'supplement') {
    return {
      kicker: 'APPLICATION · SUPPLEMENT',
      step: '补交材料',
      title: '补充申请材料',
      requirements: [
        { label: '管理员指定的补交材料', extension: '文档 / 图片', kind: 'any' as const },
      ],
      description: '材料送达后，申请会回到管理员审核流程继续处理。',
    }
  }

  return {
    kicker: 'AI REVIEW · FIRST SUBMISSION',
    step: 'AI 初审',
    title: '提交场地申请',
    requirements: [
      { label: '场地申请表', extension: '.docx', kind: 'primary' as const },
      { label: '证明或说明材料', extension: '可选 · 可多份', kind: 'optional' as const },
    ],
    description: '系统将读取申请信息、使用时间，并自动检查场地占用冲突。',
  }
})
const submissionHasPrimaryFile = computed(() =>
  pendingSubmissionFiles.value.some(({ file }) => file.name.toLowerCase().endsWith('.docx')),
)
const submissionRequirementsSatisfied = computed(() => {
  if (!submissionContext.value || pendingSubmissionFiles.value.length === 0) return false
  return submissionContext.value.mode === 'supplement' || submissionHasPrimaryFile.value
})
const submissionCacheSize = computed(() =>
  pendingSubmissionFiles.value.reduce((total, item) => total + item.file.size, 0),
)

interface ApplicationFlight {
  startPosition: THREE.Vector3
  endPosition: THREE.Vector3
  startTarget: THREE.Vector3
  endTarget: THREE.Vector3
  currentTarget: THREE.Vector3
  startClipboardPosition: THREE.Vector3
  endClipboardPosition: THREE.Vector3
  startClipboardQuaternion: THREE.Quaternion
  endClipboardQuaternion: THREE.Quaternion
  startClipboardScale: number
  endClipboardScale: number
  cameraDelay: number
  cameraDuration: number
  clipboardDelay: number
  clipboardDuration: number
  totalDuration: number
  envelopeStarted: boolean
  startedAt: number
}

type SubmissionEnvelopeState = 'hidden' | 'ready' | 'drag' | 'uploading' | 'success' | 'error'

interface SubmissionEnvelopeVisual {
  object: THREE.Object3D
  homeParent: THREE.Object3D
  homePosition: THREE.Vector3
  homeQuaternion: THREE.Quaternion
  homeScale: THREE.Vector3
}

interface PushedTreeAnimation {
  pivot: THREE.Group
  baseQuaternion: THREE.Quaternion
  swayAxis: THREE.Vector3
  swayQuaternion: THREE.Quaternion
  raccoonPivot: THREE.Group
  raccoonBasePosition: THREE.Vector3
  raccoonBaseQuaternion: THREE.Quaternion
  raccoonLeanAxis: THREE.Vector3
  raccoonPushOffset: THREE.Vector3
  raccoonBobOffset: THREE.Vector3
  raccoonLeanQuaternion: THREE.Quaternion
}

let cameraFlight: CameraFlight | null = null
let postLoginFlight: PostLoginFlight | null = null
let applicationFlight: ApplicationFlight | null = null
let selectedApplicationTarget: ApplicationNavigationTarget | null = null
let submissionEnvelope: SubmissionEnvelopeVisual | null = null
let submissionEnvelopeState: SubmissionEnvelopeState = 'hidden'
let submissionEnvelopeTween: gsap.core.Timeline | null = null
let submissionEnvelopeReturnTimer: ReturnType<typeof setTimeout> | null = null
let submissionNoticeTimer: ReturnType<typeof setTimeout> | null = null
let submissionEnvelopeFileName = ''
let submissionEnvelopeMessage = ''
let pushedTreeAnimation: PushedTreeAnimation | null = null
let startCameraTarget: THREE.Vector3 | null = null
let endCameraTarget: THREE.Vector3 | null = null
let finalCameraPosition: THREE.Vector3 | null = null
let debugGui: GUI | null = null

const cameraDebug = {
  startX: -0.8613,
  startY: 0.4236,
  startZ: -0.7209,
  startTargetX: -0.0097,
  startTargetY: -0.0263,
  startTargetZ: 0.064,
  endX: -0.4508,
  endY: 0.1559,
  endZ: -0.0408,
  endTargetX: -0.0097,
  endTargetY: -0.0263,
  endTargetZ: 0.064,
  rotationSpeed: 10,
  moveDuration: 3,
  replay: () => playCameraEntrance(),
}

const cameraReadout = {
  cameraX: 0,
  cameraY: 0,
  cameraZ: 0,
  targetX: 0,
  targetY: 0,
  targetZ: 0,
  rotationX: 0,
  rotationY: 0,
  rotationZ: 0,
  distance: 0,
}

const cameraActions = {
  useCurrentAsStart: () => useCurrentCameraAsStart(),
  printCurrent: () => printCurrentCameraParameters(),
}

const clipboardHomeTransform = {
  x: -0.05,
  y: 0.086,
  z: 0.02,
  rotationX: 0,
  rotationY: 0,
  rotationZ: 0,
  scale: 0.01,
}

const clipboardDebug = { ...clipboardHomeTransform }

const clipboardActions = {
  printCurrent: () => printClipboardParameters(),
}

const postLoginClipboardDebug = {
  x: -0.105,
  y: 0.087,
  z: 0.122,
  rotationX: -3.9,
  rotationY: -24.1,
  rotationZ: -1.6,
  scale: 0.019,
}

const houseDebug = {
  scale: 3,
}

const mailboxDebug = {
  x: -0.14,
  y: 0.03,
  z: 0.016,
  rotationX: 0,
  rotationY: 90,
  rotationZ: 0,
  scale: 0.054,
}

const mailboxActions = {
  focus: () => focusMailbox(),
  printCurrent: () => printMailboxParameters(),
}

const venueTabDebug = {
  leftX: 5,
  leftY: 0,
  rightX: -5,
  rightY: 0,
  left1Y: 0,
  left2Y: 0,
  left3Y: 0,
  left4Y: 0,
  left5Y: 0,
  right1Y: 0,
  right2Y: 0,
  right3Y: 0,
  right4Y: 0,
}

const venueTabActions = {
  printCurrent: () => printVenueTabParameters(),
}

const postLoginMotionDebug = {
  overlapDuration: 1.2,
}

const applicationMotionDebug = {
  cameraDelay: 0.2,
  cameraDuration: 1.9,
  clipboardDelay: 0.1,
  clipboardDuration: 1.25,
}

const applicationMotionActions = {
  replay: () => replayApplicationCamera(),
}

const submissionEnvelopeDebug = {
  x: -0.012,
  y: 0,
  z: -0.039,
  rotationX: 137,
  rotationY: 0,
  rotationZ: -180,
  scale: 0.02,
  flyDuration: 0.9,
  returnDuration: 0.9,
  successHold: 1.05,
  startAdvance: 0.6,
}

const submissionEnvelopeActions = {
  previewOut: () => {
    resetSubmissionEnvelope()
    showSubmissionEnvelope()
  },
  previewReturn: () => hideSubmissionEnvelope(),
  printCurrent: () => printSubmissionEnvelopeParameters(),
}

const submissionSignDebug = {
  maxWidthPx: 850,
  sideInsetPx: 48,
  heightRatio: 0.28,
  z: -0.2,
  topInsetPx: 22,
}

const pushedTreeDebug = {
  enabled: true,
  treeAmplitude: 0.4,
  directionalLean: 0.5,
  speed: 0.48,
  raccoonAmplitude: 0.4,
  raccoonLean: 1.1,
  raccoonTravel: 0.35,
}

const windShaders: WindShaderUniforms[] = []

function resetTopPage() {
  if (!topPage) return
  pageTurnTimeline?.kill()
  pageTurnTimeline = null
  topPage.position.copy(topPageInitialPosition)
  topPage.rotation.copy(topPageInitialRotation)
  topPage.scale.copy(topPageInitialScale)
  topPage.visible = true
  if (pageTurnShader) {
    pageTurnShader.bend.value = 0
    pageTurnShader.curl.value = 0
    pageTurnShader.flutter.value = 0
  }
  pageTurning.value = false
  pageTurnCompleted.value = false
  venueOptions.value = []
  selectedVenueId.value = null
  venueSelectorReady.value = false
}

function triggerPageTurn() {
  if (!topPage || !pageTurnShader || pageTurning.value || cinematicActive.value) return

  resetTopPage()
  pageTurning.value = true

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    topPage.visible = false
    pageTurning.value = false
    pageTurnCompleted.value = true
    return
  }

  const startPosition = topPageInitialPosition
  const startRotation = topPageInitialRotation
  const shader = pageTurnShader
  pageTurnTimeline = gsap
    .timeline({
      onComplete: () => {
        if (topPage) topPage.visible = false
        pageTurning.value = false
        pageTurnCompleted.value = true
        pageTurnTimeline = null
      },
    })
    // A clear left-right wobble works the sheet loose beneath the clamp.
    .to(topPage.rotation, {
      z: startRotation.z + 0.075,
      duration: 0.2,
      ease: 'sine.inOut',
    })
    .to(shader.bend, { value: 0.045, duration: 0.2, ease: 'sine.out' }, '<')
    .to(shader.flutter, { value: 0.012, duration: 0.2, ease: 'sine.out' }, '<')
    .to(topPage.rotation, {
      z: startRotation.z - 0.065,
      duration: 0.24,
      ease: 'sine.inOut',
    })
    .to(shader.bend, { value: 0.065, duration: 0.24, ease: 'sine.inOut' }, '<')
    .to(shader.flutter, { value: 0.02, duration: 0.24, ease: 'sine.inOut' }, '<')
    .to(topPage.rotation, {
      z: startRotation.z + 0.018,
      duration: 0.18,
      ease: 'sine.out',
    })
    .to(shader.curl, { value: 0.06, duration: 0.18, ease: 'sine.out' }, '<')
    // The shader curls the lower sheet toward camera as gravity takes over.
    .addLabel('drop')
    .to(
      topPage.position,
      {
        x: startPosition.x + 0.2,
        // Clipboard_Root contains the Blender-to-glTF 180° Z conversion, so
        // increasing this local Y value moves the page downward on screen.
        y: startPosition.y + 2.35,
        z: startPosition.z + 0.58,
        duration: 1.4,
        ease: 'power2.in',
      },
      'drop',
    )
    .to(
      topPage.rotation,
      {
        x: startRotation.x + 0.82,
        y: startRotation.y + 0.12,
        z: startRotation.z + 0.3,
        duration: 1.4,
        ease: 'power1.inOut',
      },
      'drop',
    )
    .to(shader.bend, { value: 0.18, duration: 0.55, ease: 'sine.out' }, 'drop')
    .to(shader.curl, { value: 0.38, duration: 0.82, ease: 'power1.out' }, 'drop')
    .to(shader.flutter, { value: 0.075, duration: 0.5, ease: 'sine.out' }, 'drop')
    .to(shader.bend, { value: 0.09, duration: 0.75, ease: 'sine.inOut' }, 'drop+=0.55')
    .to(shader.curl, { value: 0.2, duration: 0.58, ease: 'sine.inOut' }, 'drop+=0.82')
}

function fixCutoutMaterial(material: THREE.Material) {
  if (!/^(GrassALPHA|TreeLeafs|Plane)$/.test(material.name)) return
  material.transparent = false
  material.alphaTest = 0.42
  material.depthTest = true
  material.depthWrite = true
  material.side = THREE.DoubleSide
  material.alphaToCoverage = true
  material.needsUpdate = true
}

function fixMailboxMaterial(material: THREE.Material) {
  // The mailbox is exported as one BLEND material even though most of its
  // texture is fully opaque. Rendering the complete mesh in Three.js'
  // transparent pass disables reliable self-occlusion, so the rear geometry
  // can show through the wooden panels. Use an alpha cutout instead: this
  // keeps the leaves/vines cut out while returning the wood to the opaque,
  // depth-writing pass.
  material.transparent = false
  material.opacity = 1
  material.alphaTest = 0.42
  material.depthTest = true
  material.depthWrite = true
  material.side = THREE.DoubleSide
  material.alphaToCoverage = true
  material.needsUpdate = true
}

function setSubmissionEnvelopeState(
  state: SubmissionEnvelopeState,
  message = '',
  fileName = '',
) {
  submissionEnvelopeState = state
  submissionEnvelopeMessage = message
  submissionEnvelopeFileName = fileName
}

function clearSubmissionNotice() {
  if (submissionNoticeTimer) {
    clearTimeout(submissionNoticeTimer)
    submissionNoticeTimer = null
  }
  submissionNoticeVisible.value = false
}

function showSubmissionNotice(
  mode: 'uploading' | 'success' | 'error',
  message: string,
  duration = 0,
) {
  clearSubmissionNotice()
  submissionNoticeMode.value = mode
  submissionNoticeMessage.value = message
  submissionNoticeVisible.value = true
  if (duration <= 0) return
  submissionNoticeTimer = setTimeout(() => {
    submissionNoticeTimer = null
    submissionNoticeVisible.value = false
  }, duration)
}

function registerSubmissionEnvelope(root: THREE.Object3D) {
  const object = root.getObjectByName('Submission_Envelope')
  if (!object?.parent) {
    console.warn('[3D 信封] mailbox.glb 中未找到 Submission_Envelope 节点')
    return null
  }
  object.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return
    child.castShadow = true
    child.receiveShadow = true
  })
  submissionEnvelope = {
    object,
    homeParent: object.parent,
    homePosition: object.position.clone(),
    homeQuaternion: object.quaternion.clone(),
    homeScale: object.scale.clone(),
  }
  setSubmissionEnvelopeState('hidden')
  return submissionEnvelope
}

function getSubmissionEnvelopeTargetQuaternion() {
  return new THREE.Quaternion().setFromEuler(new THREE.Euler(
    THREE.MathUtils.degToRad(submissionEnvelopeDebug.rotationX),
    THREE.MathUtils.degToRad(submissionEnvelopeDebug.rotationY),
    THREE.MathUtils.degToRad(submissionEnvelopeDebug.rotationZ),
  ))
}

function applySubmissionEnvelopeDebugTransform() {
  if (
    !submissionEnvelope
    || !camera
    || submissionEnvelopeState === 'hidden'
    || submissionEnvelope.object.parent !== camera
  ) return
  submissionEnvelope.object.position.set(
    submissionEnvelopeDebug.x,
    submissionEnvelopeDebug.y,
    submissionEnvelopeDebug.z,
  )
  submissionEnvelope.object.quaternion.copy(getSubmissionEnvelopeTargetQuaternion())
  submissionEnvelope.object.scale.setScalar(submissionEnvelopeDebug.scale)
}

function printSubmissionEnvelopeParameters() {
  console.info('[3D 信封动画] 当前参数', { ...submissionEnvelopeDebug })
}

function resetSubmissionEnvelope() {
  submissionEnvelopeTween?.kill()
  submissionEnvelopeTween = null
  if (submissionEnvelopeReturnTimer) {
    clearTimeout(submissionEnvelopeReturnTimer)
    submissionEnvelopeReturnTimer = null
  }
  if (!submissionEnvelope) return
  const { object, homeParent, homePosition, homeQuaternion, homeScale } = submissionEnvelope
  homeParent.add(object)
  object.position.copy(homePosition)
  object.quaternion.copy(homeQuaternion)
  object.scale.copy(homeScale)
  object.visible = true
  setSubmissionEnvelopeState('hidden')
}

function showSubmissionEnvelope() {
  if (!submissionEnvelope || !camera) return
  submissionEnvelopeTween?.kill()
  if (submissionEnvelopeReturnTimer) {
    clearTimeout(submissionEnvelopeReturnTimer)
    submissionEnvelopeReturnTimer = null
  }
  const { object } = submissionEnvelope
  const targetQuaternion = getSubmissionEnvelopeTargetQuaternion()
  const flyDuration = THREE.MathUtils.clamp(submissionEnvelopeDebug.flyDuration, 0.15, 4)
  camera.updateMatrixWorld(true)
  object.updateMatrixWorld(true)
  camera.attach(object)
  setSubmissionEnvelopeState('ready')
  object.visible = true
  submissionEnvelopeTween = gsap
    .timeline()
    .to(object.position, {
      x: submissionEnvelopeDebug.x,
      y: submissionEnvelopeDebug.y,
      z: submissionEnvelopeDebug.z,
      duration: flyDuration,
      ease: 'power3.out',
    }, 0)
    .to(object.quaternion, {
      x: targetQuaternion.x,
      y: targetQuaternion.y,
      z: targetQuaternion.z,
      w: targetQuaternion.w,
      duration: flyDuration,
      ease: 'power3.out',
    }, 0)
    .to(object.scale, {
      x: submissionEnvelopeDebug.scale,
      y: submissionEnvelopeDebug.scale,
      z: submissionEnvelopeDebug.scale,
      duration: flyDuration,
      ease: 'power3.out',
    }, 0)
}

function hideSubmissionEnvelope(onReturned?: () => void) {
  if (!submissionEnvelope || !camera || submissionEnvelopeState === 'hidden') return
  submissionEnvelopeTween?.kill()
  const { object, homeParent, homePosition, homeQuaternion, homeScale } = submissionEnvelope
  camera.updateMatrixWorld(true)
  homeParent.updateMatrixWorld(true)
  const homeWorldMatrix = new THREE.Matrix4().multiplyMatrices(
    homeParent.matrixWorld,
    new THREE.Matrix4().compose(homePosition, homeQuaternion, homeScale),
  )
  const cameraLocalMatrix = new THREE.Matrix4().multiplyMatrices(
    camera.matrixWorldInverse,
    homeWorldMatrix,
  )
  const returnPosition = new THREE.Vector3()
  const returnQuaternion = new THREE.Quaternion()
  const returnScale = new THREE.Vector3()
  cameraLocalMatrix.decompose(returnPosition, returnQuaternion, returnScale)
  const returnDuration = THREE.MathUtils.clamp(submissionEnvelopeDebug.returnDuration, 0.15, 4)
  submissionEnvelopeTween = gsap
    .timeline({
      onComplete: () => {
        if (!submissionEnvelope) return
        homeParent.add(object)
        object.position.copy(homePosition)
        object.quaternion.copy(homeQuaternion)
        object.scale.copy(homeScale)
        setSubmissionEnvelopeState('hidden')
        onReturned?.()
      },
    })
    .to(object.position, {
      x: returnPosition.x,
      y: returnPosition.y,
      z: returnPosition.z,
      duration: returnDuration,
      ease: 'power2.in',
    }, 0)
    .to(object.quaternion, {
      x: returnQuaternion.x,
      y: returnQuaternion.y,
      z: returnQuaternion.z,
      w: returnQuaternion.w,
      duration: returnDuration,
      ease: 'power2.in',
    }, 0)
    .to(object.scale, {
      x: returnScale.x,
      y: returnScale.y,
      z: returnScale.z,
      duration: returnDuration,
      ease: 'power2.in',
    }, 0)
}

function isPointerOverSubmissionEnvelope(clientX: number, clientY: number) {
  if (
    !submissionEnvelope?.object.visible
    || !renderer
    || !camera
    || submissionEnvelopeState === 'hidden'
  ) return false
  const bounds = renderer.domElement.getBoundingClientRect()
  if (!bounds.width || !bounds.height) return false
  pagePointer.set(
    ((clientX - bounds.left) / bounds.width) * 2 - 1,
    -((clientY - bounds.top) / bounds.height) * 2 + 1,
  )
  pageRaycaster.setFromCamera(pagePointer, camera)
  return pageRaycaster.intersectObject(submissionEnvelope.object, true).length > 0
}

function openSubmissionFilePicker() {
  if (
    submissionFilesUploading.value
    || !['ready', 'drag', 'error'].includes(submissionEnvelopeState)
  ) return
  applicationFileInput.value?.click()
}

function getSubmissionFileExtension(filename: string) {
  const dotIndex = filename.lastIndexOf('.')
  return dotIndex >= 0 ? filename.slice(dotIndex).toLowerCase() : ''
}

function formatSubmissionFileSize(size: number) {
  if (size === 0) return '0 KB'
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`
  return `${(size / 1024 / 1024).toFixed(size >= 10 * 1024 * 1024 ? 0 : 1)} MB`
}

function stageSubmissionFiles(files: File[]) {
  if (submissionFilesUploading.value || files.length === 0) return
  const allowedExtensions = new Set(['.doc', '.docx', '.pdf', '.jpg', '.jpeg', '.png'])
  const existing = new Set(
    pendingSubmissionFiles.value.map(({ file }) => `${file.name}:${file.size}:${file.lastModified}`),
  )
  const accepted: StagedSubmissionFile[] = []

  for (const file of files) {
    const identity = `${file.name}:${file.size}:${file.lastModified}`
    if (existing.has(identity)) continue
    const extension = getSubmissionFileExtension(file.name)
    if (!allowedExtensions.has(extension)) {
      showSubmissionNotice('error', `“${file.name}”的格式暂不支持`, 3600)
      continue
    }
    if (file.size > 30 * 1024 * 1024) {
      showSubmissionNotice('error', `“${file.name}”超过 30MB`, 3600)
      continue
    }
    if (pendingSubmissionFiles.value.length + accepted.length >= 10) {
      showSubmissionNotice('error', '一次最多暂存 10 个文件', 3600)
      break
    }
    existing.add(identity)
    accepted.push({
      id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`,
      file,
    })
  }

  if (!accepted.length) return
  pendingSubmissionFiles.value = [...pendingSubmissionFiles.value, ...accepted]
  setSubmissionEnvelopeState(
    'ready',
    `已暂存 ${pendingSubmissionFiles.value.length} 个文件，等待确认`,
  )
}

function removeStagedSubmissionFile(id: string) {
  if (submissionFilesUploading.value) return
  pendingSubmissionFiles.value = pendingSubmissionFiles.value.filter((item) => item.id !== id)
  setSubmissionEnvelopeState(
    'ready',
    pendingSubmissionFiles.value.length
      ? `已暂存 ${pendingSubmissionFiles.value.length} 个文件，等待确认`
      : '点击信封或拖入文件，先暂存后提交',
  )
}

function getSubmissionErrorMessage(error: unknown) {
  if (!axios.isAxiosError(error)) return '文件提交失败，请稍后重试'
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item?.msg === 'string' ? item.msg : ''))
      .filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return error.message || '文件提交失败，请稍后重试'
}

async function submitStagedApplicationFiles() {
  const target = selectedApplicationTarget
  if (
    !target
    || submissionFilesUploading.value
    || (target.mode !== 'supplement' && target.venueId <= 0)
  ) return
  if (['resubmit', 'supplement'].includes(target.mode ?? '') && !target.applicationId) {
    showSubmissionNotice('error', '当前申请信息不完整，请返回个人首页后重试', 3800)
    return
  }
  if (!pendingSubmissionFiles.value.length) {
    const message = '请先将需要提交的文件放入信封'
    setSubmissionEnvelopeState('error', message)
    showSubmissionNotice('error', message, 3800)
    return
  }
  const primaryItem = pendingSubmissionFiles.value.find(({ file }) =>
    file.name.toLowerCase().endsWith('.docx'),
  )
  if (target.mode !== 'supplement' && !primaryItem) {
    const message = 'AI 初审需要一份 .docx 格式的场地申请表'
    setSubmissionEnvelopeState('error', message)
    showSubmissionNotice('error', message, 3800)
    return
  }

  submissionFilesUploading.value = true
  const fileCount = pendingSubmissionFiles.value.length
  setSubmissionEnvelopeState('uploading', `正在送出 ${fileCount} 个文件，请稍候`)
  showSubmissionNotice(
    'uploading',
    target.mode === 'supplement'
      ? `正在上传 ${fileCount} 份补交材料`
      : target.mode === 'resubmit'
        ? `正在重新提交 ${fileCount} 个文件并进行 AI 初审`
      : `正在提交 ${fileCount} 个文件并进行材料初审`,
  )

  try {
    let resultMode: 'success' | 'error' = 'success'
    let successMessage = '文件已送达'
    if (target.mode === 'supplement' && target.applicationId) {
      const formData = new FormData()
      pendingSubmissionFiles.value.forEach(({ file }) => formData.append('files', file))
      formData.append('file_type', 'supplement_file')
      await axios.post(`/api/v1/applications/${target.applicationId}/files/batch`, formData)
      successMessage = `${fileCount} 份补交材料已送达，申请重新进入审核流程`
    } else if (target.mode === 'resubmit' && target.applicationId) {
      const formData = new FormData()
      formData.append('file', primaryItem!.file)
      pendingSubmissionFiles.value
        .filter((item) => item.id !== primaryItem!.id)
        .forEach(({ file }) => formData.append('additional_files', file))
      const { data } = await axios.post(
        `/api/v1/applications/${target.applicationId}/pre-review`,
        formData,
      )
      resultMode = data?.passed ? 'success' : 'error'
      successMessage = data?.passed
        ? '重新初审通过，申请已预占用'
        : '重新初审未通过，请在个人首页查看原因'
    } else {
      const formData = new FormData()
      formData.append('file', primaryItem!.file)
      pendingSubmissionFiles.value
        .filter((item) => item.id !== primaryItem!.id)
        .forEach(({ file }) => formData.append('additional_files', file))
      formData.append(
        'application_type',
        target.venueName.includes('悦园三楼') ? 'yueyuan_third_floor' : 'meiyu_venue',
      )
      formData.append('venue_id', String(target.venueId))
      const { data } = await axios.post('/api/v1/applications/pre-review', formData)
      resultMode = data?.passed ? 'success' : 'error'
      successMessage = data?.passed
        ? '初审通过，申请已预占用'
        : '初审未通过，请在个人首页查看原因并重新提交'
    }
    setSubmissionEnvelopeState(resultMode, successMessage)
    showSubmissionNotice(resultMode, successMessage, 4200)
    void loadPersonalHome()
    void loadVenueUsageBoard()
    submissionEnvelopeReturnTimer = setTimeout(() => {
      submissionEnvelopeReturnTimer = null
      hideSubmissionEnvelope(() => playPostLoginCamera())
    }, Math.max(submissionEnvelopeDebug.successHold, 0) * 1000)
  } catch (error) {
    submissionFilesUploading.value = false
    const message = getSubmissionErrorMessage(error)
    setSubmissionEnvelopeState('error', message)
    showSubmissionNotice('error', message, 3800)
  }
}

function handleApplicationFileChange(event: Event) {
  const input = event.currentTarget as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  stageSubmissionFiles(files)
}

function handleSubmissionDragOver(event: DragEvent) {
  if (!isPointerOverSubmissionEnvelope(event.clientX, event.clientY)) {
    if (submissionEnvelopeState === 'drag') setSubmissionEnvelopeState('ready')
    return
  }
  event.preventDefault()
  if (submissionEnvelopeState === 'ready' || submissionEnvelopeState === 'error') {
    setSubmissionEnvelopeState('drag', '松开即可将文件暂存在信封中')
  }
}

function handleSubmissionDragLeave(event: DragEvent) {
  if (isPointerOverSubmissionEnvelope(event.clientX, event.clientY)) return
  if (submissionEnvelopeState === 'drag') setSubmissionEnvelopeState('ready')
}

function handleSubmissionDrop(event: DragEvent) {
  if (!isPointerOverSubmissionEnvelope(event.clientX, event.clientY)) return
  event.preventDefault()
  event.stopPropagation()
  stageSubmissionFiles(Array.from(event.dataTransfer?.files ?? []))
}

function setupRaccoonPushedTree(root: THREE.Object3D) {
  const tree = root.getObjectByName('BTree002')
  const bird = root.getObjectByName('Bird')
  const raccoon = root.getObjectByName('Racoon')
  const parent = tree?.parent
  const raccoonParent = raccoon?.parent
  if (!tree || !bird || !raccoon || !parent || !raccoonParent) {
    console.warn('[浣熊推树动画] 未找到 BTree002、Bird 或 Racoon 节点')
    return
  }

  root.updateWorldMatrix(true, true)
  const treeBounds = new THREE.Box3().setFromObject(tree)
  const raccoonBounds = new THREE.Box3().setFromObject(raccoon)
  const treeBaseWorld = treeBounds.getCenter(new THREE.Vector3())
  treeBaseWorld.y = treeBounds.min.y
  const raccoonCenterWorld = raccoonBounds.getCenter(new THREE.Vector3())
  const raccoonBaseWorld = raccoonCenterWorld.clone()
  raccoonBaseWorld.y = raccoonBounds.min.y
  const raccoonHeightWorld = raccoonBounds.getSize(new THREE.Vector3()).y

  // The horizontal direction from the raccoon toward the trunk is the push
  // direction. Tilting around up × direction makes the crown move away from it.
  const pushDirectionWorld = treeBaseWorld.clone().sub(raccoonCenterWorld)
  pushDirectionWorld.y = 0
  if (pushDirectionWorld.lengthSq() < 1e-8) pushDirectionWorld.set(0, 0, -1)
  pushDirectionWorld.normalize()
  const swayAxisWorld = new THREE.Vector3(0, 1, 0)
    .cross(pushDirectionWorld)
    .normalize()
  const parentWorldQuaternion = parent.getWorldQuaternion(new THREE.Quaternion())
  const swayAxisLocal = swayAxisWorld
    .clone()
    .applyQuaternion(parentWorldQuaternion.invert())
    .normalize()

  const pivot = new THREE.Group()
  pivot.name = 'Raccoon_Pushed_Tree_Pivot'
  parent.add(pivot)
  pivot.position.copy(parent.worldToLocal(treeBaseWorld.clone()))
  pivot.updateWorldMatrix(true, false)
  pivot.attach(tree)
  pivot.attach(bird)

  // Rotate the raccoon around its feet so the push reads as body weight rather
  // than the whole character floating. Offsets are converted from world space,
  // which keeps the motion stable even though the imported GLB is heavily scaled.
  const raccoonParentWorldQuaternion = raccoonParent.getWorldQuaternion(
    new THREE.Quaternion(),
  )
  const raccoonLeanAxisLocal = swayAxisWorld
    .clone()
    .applyQuaternion(raccoonParentWorldQuaternion.invert())
    .normalize()
  const raccoonPivot = new THREE.Group()
  raccoonPivot.name = 'Raccoon_Push_Pivot'
  raccoonParent.add(raccoonPivot)
  raccoonPivot.position.copy(raccoonParent.worldToLocal(raccoonBaseWorld.clone()))
  const raccoonBasePosition = raccoonPivot.position.clone()
  const raccoonPushPosition = raccoonParent.worldToLocal(
    raccoonBaseWorld
      .clone()
      .addScaledVector(pushDirectionWorld, raccoonHeightWorld * 0.12),
  )
  const raccoonBobPosition = raccoonParent.worldToLocal(
    raccoonBaseWorld.clone().add(new THREE.Vector3(0, -raccoonHeightWorld * 0.035, 0)),
  )
  raccoonPivot.updateWorldMatrix(true, false)
  raccoonPivot.attach(raccoon)

  pushedTreeAnimation = {
    pivot,
    baseQuaternion: pivot.quaternion.clone(),
    swayAxis: swayAxisLocal,
    swayQuaternion: new THREE.Quaternion(),
    raccoonPivot,
    raccoonBasePosition,
    raccoonBaseQuaternion: raccoonPivot.quaternion.clone(),
    raccoonLeanAxis: raccoonLeanAxisLocal,
    raccoonPushOffset: raccoonPushPosition.sub(raccoonBasePosition),
    raccoonBobOffset: raccoonBobPosition.sub(raccoonBasePosition),
    raccoonLeanQuaternion: new THREE.Quaternion(),
  }
}

function updateRaccoonPushedTree(elapsed: number) {
  if (!pushedTreeAnimation) return
  if (!pushedTreeDebug.enabled) {
    pushedTreeAnimation.pivot.quaternion.copy(pushedTreeAnimation.baseQuaternion)
    pushedTreeAnimation.raccoonPivot.position.copy(
      pushedTreeAnimation.raccoonBasePosition,
    )
    pushedTreeAnimation.raccoonPivot.quaternion.copy(
      pushedTreeAnimation.raccoonBaseQuaternion,
    )
    return
  }

  const phase = elapsed * Math.PI * 2 * pushedTreeDebug.speed
  const rawPush = (Math.sin(phase) + 1) * 0.5
  const pushAmount = rawPush * rawPush * (3 - 2 * rawPush)
  const treePhase = phase - 0.32
  const primaryWave = Math.sin(treePhase) * pushedTreeDebug.treeAmplitude
  const secondaryWave =
    Math.sin(treePhase * 2 + 0.65) * pushedTreeDebug.treeAmplitude * 0.12
  const angle = THREE.MathUtils.degToRad(
    pushedTreeDebug.directionalLean + primaryWave + secondaryWave,
  )
  pushedTreeAnimation.swayQuaternion.setFromAxisAngle(pushedTreeAnimation.swayAxis, angle)
  pushedTreeAnimation.pivot.quaternion
    .copy(pushedTreeAnimation.baseQuaternion)
    .multiply(pushedTreeAnimation.swayQuaternion)

  const raccoonMotionAmount = pushAmount * pushedTreeDebug.raccoonAmplitude
  const secondaryBob =
    Math.max(0, Math.sin(phase * 2)) * 0.08 * pushedTreeDebug.raccoonAmplitude
  pushedTreeAnimation.raccoonPivot.position
    .copy(pushedTreeAnimation.raccoonBasePosition)
    .addScaledVector(
      pushedTreeAnimation.raccoonPushOffset,
      raccoonMotionAmount * pushedTreeDebug.raccoonTravel,
    )
    .addScaledVector(
      pushedTreeAnimation.raccoonBobOffset,
      raccoonMotionAmount + secondaryBob,
    )
  pushedTreeAnimation.raccoonLeanQuaternion.setFromAxisAngle(
    pushedTreeAnimation.raccoonLeanAxis,
    THREE.MathUtils.degToRad(raccoonMotionAmount * pushedTreeDebug.raccoonLean),
  )
  pushedTreeAnimation.raccoonPivot.quaternion
    .copy(pushedTreeAnimation.raccoonBaseQuaternion)
    .multiply(pushedTreeAnimation.raccoonLeanQuaternion)
}

function startCameraEntrance(object: THREE.Object3D, framingObject: THREE.Object3D = object) {
  if (!camera || !controls || !viewport.value) return

  // The clipboard is an adjustable foreground prop and must not change the
  // established house composition. Camera framing always follows this object.
  const bounds = new THREE.Box3().setFromObject(framingObject)
  const size = bounds.getSize(new THREE.Vector3())
  const center = bounds.getCenter(new THREE.Vector3())
  const maxDimension = Math.max(size.x, size.y, size.z)
  const modelOffsetX = viewport.value.clientWidth >= 860 ? -maxDimension * 0.18 : 0

  object.position.sub(center)
  object.position.x += modelOffsetX

  const halfFov = THREE.MathUtils.degToRad(camera.fov / 2)
  const distance = (maxDimension / (2 * Math.tan(halfFov))) * 1.35
  const modelTarget = new THREE.Vector3(modelOffsetX, 0, 0)

  // Keep enough depth-buffer precision for the clipboard's nearly coplanar
  // paper layers while still allowing very close inspection.
  camera.near = Math.max(distance / 200, 0.001)
  camera.far = distance * 100
  camera.updateProjectionMatrix()

  controls.target.set(cameraDebug.startTargetX, cameraDebug.startTargetY, cameraDebug.startTargetZ)
  controls.minDistance = 0
  controls.maxDistance = distance * 4
  controls.enabled = false
  controls.autoRotate = false

  startCameraTarget = new THREE.Vector3(
    cameraDebug.startTargetX,
    cameraDebug.startTargetY,
    cameraDebug.startTargetZ,
  )
  endCameraTarget = new THREE.Vector3(
    cameraDebug.endTargetX,
    cameraDebug.endTargetY,
    cameraDebug.endTargetZ,
  )
  finalCameraPosition = new THREE.Vector3(cameraDebug.endX, cameraDebug.endY, cameraDebug.endZ)
  createCameraDebugGui(distance, modelTarget)

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduceMotion) {
    camera.position.copy(finalCameraPosition)
    camera.lookAt(endCameraTarget)
    controls.target.copy(endCameraTarget)
    controls.enabled = true
    controls.autoRotate = false
    controls.update()
    loginPanelVisible.value = true
    cinematicActive.value = false
    return
  }

  playCameraEntrance()
}

function applyClipboardTransform() {
  if (!clipboardModel) return
  clipboardModel.position.set(clipboardDebug.x, clipboardDebug.y, clipboardDebug.z)
  clipboardModel.rotation.set(
    THREE.MathUtils.degToRad(clipboardDebug.rotationX),
    THREE.MathUtils.degToRad(clipboardDebug.rotationY),
    THREE.MathUtils.degToRad(clipboardDebug.rotationZ),
  )
  clipboardModel.scale.setScalar(clipboardDebug.scale)
}

function printClipboardParameters() {
  console.info('[文件夹模型] 当前变换参数', {
    position: {
      x: clipboardDebug.x,
      y: clipboardDebug.y,
      z: clipboardDebug.z,
    },
    rotationDegrees: {
      x: clipboardDebug.rotationX,
      y: clipboardDebug.rotationY,
      z: clipboardDebug.rotationZ,
    },
    scale: clipboardDebug.scale,
  })
}

function applyHouseTransform() {
  houseModel?.scale.setScalar(houseDebug.scale)
}

function applyMailboxTransform() {
  if (!mailboxModel) return
  mailboxModel.position.set(mailboxDebug.x, mailboxDebug.y, mailboxDebug.z)
  mailboxModel.rotation.set(
    THREE.MathUtils.degToRad(mailboxDebug.rotationX),
    THREE.MathUtils.degToRad(mailboxDebug.rotationY),
    THREE.MathUtils.degToRad(mailboxDebug.rotationZ),
  )
  mailboxModel.scale.setScalar(mailboxDebug.scale)
}

function prepareMailboxModel(source: THREE.Object3D) {
  source.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return
    child.castShadow = true
    child.receiveShadow = true
    const materials = Array.isArray(child.material) ? child.material : [child.material]
    materials.forEach(fixMailboxMaterial)
  })

  const bounds = new THREE.Box3().setFromObject(source)
  const center = bounds.getCenter(new THREE.Vector3())
  const size = bounds.getSize(new THREE.Vector3())
  source.position.x -= center.x
  source.position.y -= bounds.min.y
  source.position.z -= center.z

  const normalizedGroup = new THREE.Group()
  normalizedGroup.name = 'Mailbox_Normalized'
  normalizedGroup.scale.setScalar(1 / Math.max(size.y, 0.0001))
  normalizedGroup.add(source)

  const wrapper = new THREE.Group()
  wrapper.name = 'Stylized_Mailbox'
  wrapper.add(normalizedGroup)
  return wrapper
}

function prepareSubmissionSignModel(source: THREE.Object3D) {
  source.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return
    child.castShadow = false
    child.receiveShadow = false
    child.frustumCulled = false
    child.renderOrder = 80

    const materials = Array.isArray(child.material) ? child.material : [child.material]
    for (const material of materials) {
      material.transparent = false
      material.opacity = 1
      material.alphaTest = 0
      // The sign is attached to the camera as a 3D interface element. Disable
      // scene depth testing so nearby house geometry cannot cut holes through
      // the board while keeping its own modeled thickness and lighting.
      material.depthTest = false
      material.depthWrite = false
      material.side = THREE.DoubleSide

      if (material instanceof THREE.MeshStandardMaterial) {
        material.metalness = 0
        material.roughness = 1
        material.normalScale.set(0.22, 0.22)
        material.envMapIntensity = 0.12
        if (material instanceof THREE.MeshPhysicalMaterial) {
          material.specularIntensity = 0.08
        }
      }
      material.needsUpdate = true
    }
  })

  const bounds = new THREE.Box3().setFromObject(source)
  const center = bounds.getCenter(new THREE.Vector3())
  const size = bounds.getSize(new THREE.Vector3())
  source.position.sub(center)

  const normalized = new THREE.Group()
  normalized.name = 'Submission_Sign_Normalized'
  normalized.scale.setScalar(1 / Math.max(size.x, 0.0001))
  normalized.add(source)

  const wrapper = new THREE.Group()
  wrapper.name = 'Submission_Hanging_Sign'
  wrapper.visible = false
  wrapper.add(normalized)
  return wrapper
}

function updateSubmissionSignLayout() {
  if (!submissionSignModel || !camera || !viewport.value) return

  const depth = Math.abs(submissionSignDebug.z)
  const viewHeight = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * depth
  const worldPerPixel = viewHeight / viewport.value.clientHeight
  const signWidthPx = Math.min(
    submissionSignDebug.maxWidthPx,
    viewport.value.clientWidth - submissionSignDebug.sideInsetPx * 2,
  )
  const signWidth = Math.max(signWidthPx, 120) * worldPerPixel
  const signHeightScale = signWidth * submissionSignDebug.heightRatio

  submissionSignModel.scale.set(signWidth, signHeightScale, signWidth)
  // The downloaded sign has a tall rope section above its board. Raising the
  // whole object lets the rope enter from beyond the viewport while the actual
  // board sits directly behind the DOM copy at the top of the page.
  const boardTopInNormalizedModel = 0.0527
  submissionSignTargetY =
    viewHeight / 2
    - submissionSignDebug.topInsetPx * worldPerPixel
    - boardTopInNormalizedModel * signHeightScale
  submissionSignModel.position.x = 0
  submissionSignModel.position.z = submissionSignDebug.z
  if (!submissionSignTween?.isActive()) submissionSignModel.position.y = submissionSignTargetY
}

function showSubmissionSign() {
  if (!submissionSignModel) return
  submissionSignTween?.kill()
  updateSubmissionSignLayout()
  submissionSignModel.visible = true
  submissionSignModel.rotation.set(0, 0, THREE.MathUtils.degToRad(-0.9))

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    submissionSignModel.position.y = submissionSignTargetY
    submissionSignModel.rotation.z = 0
    return
  }

  submissionSignModel.position.y = submissionSignTargetY + 0.035
  submissionSignTween = gsap.to(submissionSignModel.position, {
    y: submissionSignTargetY,
    duration: 0.82,
    ease: 'back.out(1.25)',
    onUpdate: () => {
      if (!submissionSignModel) return
      const remaining = Math.abs(submissionSignModel.position.y - submissionSignTargetY)
      submissionSignModel.rotation.z = THREE.MathUtils.clamp(remaining * -0.32, -0.018, 0)
    },
    onComplete: () => {
      if (submissionSignModel) submissionSignModel.rotation.z = 0
      submissionSignTween = null
    },
  })
}

function hideSubmissionSign(immediate = false) {
  if (!submissionSignModel) return
  submissionSignTween?.kill()
  submissionSignTween = null

  if (immediate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    submissionSignModel.visible = false
    return
  }

  submissionSignTween = gsap.to(submissionSignModel.position, {
    y: submissionSignTargetY + 0.035,
    duration: 0.42,
    ease: 'power2.in',
    onComplete: () => {
      if (submissionSignModel) submissionSignModel.visible = false
      submissionSignTween = null
    },
  })
}

function printMailboxParameters() {
  console.info('[信箱模型] 当前变换参数', {
    position: { x: mailboxDebug.x, y: mailboxDebug.y, z: mailboxDebug.z },
    rotationDegrees: {
      x: mailboxDebug.rotationX,
      y: mailboxDebug.rotationY,
      z: mailboxDebug.rotationZ,
    },
    scale: mailboxDebug.scale,
  })
}

function focusMailbox() {
  if (!mailboxModel || !camera || !controls) return
  const bounds = new THREE.Box3().setFromObject(mailboxModel)
  const center = bounds.getCenter(new THREE.Vector3())
  const size = bounds.getSize(new THREE.Vector3())
  const distance = Math.max(size.x, size.y, size.z, 0.05) * 3.2
  const viewDirection = camera.position.clone().sub(controls.target)
  if (viewDirection.lengthSq() < 0.000001) viewDirection.set(1, 0.6, 1)
  viewDirection.normalize()
  controls.target.copy(center)
  camera.position.copy(center).addScaledVector(viewDirection, distance)
  camera.lookAt(center)
  controls.enabled = true
  controls.update()
}

function printVenueTabParameters() {
  console.info('[场地书签] 当前位置参数', {
    left: {
      x: venueTabDebug.leftX,
      y: venueTabDebug.leftY,
      itemY: [
        venueTabDebug.left1Y,
        venueTabDebug.left2Y,
        venueTabDebug.left3Y,
        venueTabDebug.left4Y,
        venueTabDebug.left5Y,
      ],
    },
    right: {
      x: venueTabDebug.rightX,
      y: venueTabDebug.rightY,
      itemY: [
        venueTabDebug.right1Y,
        venueTabDebug.right2Y,
        venueTabDebug.right3Y,
        venueTabDebug.right4Y,
      ],
    },
  })
}

function applyPostLoginClipboardTransform() {
  Object.assign(clipboardDebug, postLoginClipboardDebug)
  applyClipboardTransform()
  refreshCameraDebugGui()
}

function applyHomeClipboardTransform() {
  Object.assign(clipboardDebug, clipboardHomeTransform)
  applyClipboardTransform()
  refreshCameraDebugGui()
}

function createCameraDebugGui(distance: number, target: THREE.Vector3) {
  debugGui?.destroy()
  debugGui = new GUI({ title: '开场运镜调试', width: 300 })
  debugGui.domElement.style.left = '16px'
  debugGui.domElement.style.right = 'auto'
  debugGui.domElement.style.top = '16px'
  debugGui.domElement.style.zIndex = '10'

  const range = distance * 5
  const step = Math.max(distance * 0.01, 0.01)
  const replayAfterChange = () => playCameraEntrance()

  const readoutFolder = debugGui.addFolder('当前相机参数（实时）')
  addReadOnlyController(readoutFolder, 'cameraX', '相机 X')
  addReadOnlyController(readoutFolder, 'cameraY', '相机 Y')
  addReadOnlyController(readoutFolder, 'cameraZ', '相机 Z')
  addReadOnlyController(readoutFolder, 'targetX', '目标 X')
  addReadOnlyController(readoutFolder, 'targetY', '目标 Y')
  addReadOnlyController(readoutFolder, 'targetZ', '目标 Z')
  addReadOnlyController(readoutFolder, 'rotationX', '旋转 X°')
  addReadOnlyController(readoutFolder, 'rotationY', '旋转 Y°')
  addReadOnlyController(readoutFolder, 'rotationZ', '旋转 Z°')
  addReadOnlyController(readoutFolder, 'distance', '观察距离')

  debugGui.add(cameraActions, 'useCurrentAsStart').name('当前视角设为起点')
  debugGui.add(cameraActions, 'printCurrent').name('输出当前参数')

  const positionFolder = debugGui.addFolder('开局起始位置')
  positionFolder
    .add(cameraDebug, 'startX', target.x - range, target.x + range, step)
    .name('起始 X')
    .onFinishChange(replayAfterChange)
  positionFolder
    .add(cameraDebug, 'startY', target.y - range, target.y + range, step)
    .name('起始 Y')
    .onFinishChange(replayAfterChange)
  positionFolder
    .add(cameraDebug, 'startZ', target.z - range, target.z + range, step)
    .name('起始 Z')
    .onFinishChange(replayAfterChange)
  positionFolder
    .add(cameraDebug, 'startTargetX', target.x - range, target.x + range, step)
    .name('起点目标 X')
    .onFinishChange(replayAfterChange)
  positionFolder
    .add(cameraDebug, 'startTargetY', target.y - range, target.y + range, step)
    .name('起点目标 Y')
    .onFinishChange(replayAfterChange)
  positionFolder
    .add(cameraDebug, 'startTargetZ', target.z - range, target.z + range, step)
    .name('起点目标 Z')
    .onFinishChange(replayAfterChange)

  const endPositionFolder = debugGui.addFolder('运镜结束位置')
  endPositionFolder
    .add(cameraDebug, 'endX', target.x - range, target.x + range, step)
    .name('结束 X')
    .onFinishChange(replayAfterChange)
  endPositionFolder
    .add(cameraDebug, 'endY', target.y - range, target.y + range, step)
    .name('结束 Y')
    .onFinishChange(replayAfterChange)
  endPositionFolder
    .add(cameraDebug, 'endZ', target.z - range, target.z + range, step)
    .name('结束 Z')
    .onFinishChange(replayAfterChange)
  endPositionFolder
    .add(cameraDebug, 'endTargetX', target.x - range, target.x + range, step)
    .name('终点目标 X')
    .onFinishChange(replayAfterChange)
  endPositionFolder
    .add(cameraDebug, 'endTargetY', target.y - range, target.y + range, step)
    .name('终点目标 Y')
    .onFinishChange(replayAfterChange)
  endPositionFolder
    .add(cameraDebug, 'endTargetZ', target.z - range, target.z + range, step)
    .name('终点目标 Z')
    .onFinishChange(replayAfterChange)

  const motionFolder = debugGui.addFolder('运镜速度')
  motionFolder
    .add(cameraDebug, 'rotationSpeed', 10, 180, 1)
    .name('旋转速度 °/秒')
    .onFinishChange(replayAfterChange)
  motionFolder
    .add(cameraDebug, 'moveDuration', 1, 10, 0.1)
    .name('拉近时长 秒')
    .onFinishChange(replayAfterChange)

  const clipboardFolder = debugGui.addFolder('文件夹模型位置与大小')
  clipboardFolder
    .add(clipboardDebug, 'x', -1, 1, 0.001)
    .name('位置 X')
    .onChange(applyClipboardTransform)
  clipboardFolder
    .add(clipboardDebug, 'y', -1, 1, 0.001)
    .name('位置 Y')
    .onChange(applyClipboardTransform)
  clipboardFolder
    .add(clipboardDebug, 'z', -1, 1, 0.001)
    .name('位置 Z')
    .onChange(applyClipboardTransform)
  clipboardFolder
    .add(clipboardDebug, 'rotationX', -180, 180, 0.1)
    .name('旋转 X°')
    .onChange(applyClipboardTransform)
  clipboardFolder
    .add(clipboardDebug, 'rotationY', -180, 180, 0.1)
    .name('旋转 Y°')
    .onChange(applyClipboardTransform)
  clipboardFolder
    .add(clipboardDebug, 'rotationZ', -180, 180, 0.1)
    .name('旋转 Z°')
    .onChange(applyClipboardTransform)
  clipboardFolder
    .add(clipboardDebug, 'scale', 0.01, 0.5, 0.001)
    .name('统一缩放')
    .onChange(applyClipboardTransform)
  clipboardFolder.add(clipboardActions, 'printCurrent').name('输出文件夹参数')

  const houseFolder = debugGui.addFolder('小屋模型大小')
  houseFolder
    .add(houseDebug, 'scale', 0.1, 3, 0.01)
    .name('统一缩放')
    .onChange(applyHouseTransform)

  const mailboxFolder = debugGui.addFolder('信箱模型位置与大小')
  mailboxFolder.add(mailboxDebug, 'x', -2, 2, 0.001).name('位置 X').onChange(applyMailboxTransform)
  mailboxFolder.add(mailboxDebug, 'y', -2, 2, 0.001).name('位置 Y').onChange(applyMailboxTransform)
  mailboxFolder.add(mailboxDebug, 'z', -2, 2, 0.001).name('位置 Z').onChange(applyMailboxTransform)
  mailboxFolder
    .add(mailboxDebug, 'rotationX', -180, 180, 0.1)
    .name('旋转 X°')
    .onChange(applyMailboxTransform)
  mailboxFolder
    .add(mailboxDebug, 'rotationY', -180, 180, 0.1)
    .name('旋转 Y°')
    .onChange(applyMailboxTransform)
  mailboxFolder
    .add(mailboxDebug, 'rotationZ', -180, 180, 0.1)
    .name('旋转 Z°')
    .onChange(applyMailboxTransform)
  mailboxFolder
    .add(mailboxDebug, 'scale', 0.01, 1, 0.001)
    .name('统一缩放')
    .onChange(applyMailboxTransform)
  mailboxFolder.add(mailboxActions, 'focus').name('聚焦信箱')
  mailboxFolder.add(mailboxActions, 'printCurrent').name('输出信箱参数')

  const venueTabFolder = debugGui.addFolder('两侧场地书签位置')
  venueTabFolder.add(venueTabDebug, 'leftX', -180, 180, 1).name('左侧横向 px')
  venueTabFolder.add(venueTabDebug, 'leftY', -180, 180, 1).name('左侧整体上下 px')
  venueTabFolder.add(venueTabDebug, 'rightX', -180, 180, 1).name('右侧横向 px')
  venueTabFolder.add(venueTabDebug, 'rightY', -180, 180, 1).name('右侧整体上下 px')

  const leftVenueTabFolder = venueTabFolder.addFolder('左侧独立上下')
  leftVenueTabFolder.add(venueTabDebug, 'left1Y', -120, 120, 1).name('标签 1 px')
  leftVenueTabFolder.add(venueTabDebug, 'left2Y', -120, 120, 1).name('标签 2 px')
  leftVenueTabFolder.add(venueTabDebug, 'left3Y', -120, 120, 1).name('标签 3 px')
  leftVenueTabFolder.add(venueTabDebug, 'left4Y', -120, 120, 1).name('标签 4 px')
  leftVenueTabFolder.add(venueTabDebug, 'left5Y', -120, 120, 1).name('标签 5 px')

  const rightVenueTabFolder = venueTabFolder.addFolder('右侧独立上下')
  rightVenueTabFolder.add(venueTabDebug, 'right1Y', -120, 120, 1).name('标签 1 px')
  rightVenueTabFolder.add(venueTabDebug, 'right2Y', -120, 120, 1).name('标签 2 px')
  rightVenueTabFolder.add(venueTabDebug, 'right3Y', -120, 120, 1).name('标签 3 px')
  rightVenueTabFolder.add(venueTabDebug, 'right4Y', -120, 120, 1).name('标签 4 px')
  venueTabFolder.add(venueTabActions, 'printCurrent').name('输出书签位置参数')

  const postLoginMotionFolder = debugGui.addFolder('登录后动画衔接')
  postLoginMotionFolder
    .add(postLoginMotionDebug, 'overlapDuration', 0, 1.2, 0.05)
    .name('重叠时间 秒')

  const applicationMotionFolder = debugGui.addFolder('申请运镜时间')
  applicationMotionFolder
    .add(applicationMotionDebug, 'cameraDelay', 0, 2, 0.05)
    .name('镜头延迟 秒')
  applicationMotionFolder
    .add(applicationMotionDebug, 'cameraDuration', 0.5, 5, 0.05)
    .name('镜头时长 秒')
  applicationMotionFolder
    .add(applicationMotionDebug, 'clipboardDelay', 0, 2, 0.05)
    .name('文件夹延迟 秒')
  applicationMotionFolder
    .add(applicationMotionDebug, 'clipboardDuration', 0.4, 4, 0.05)
    .name('文件夹时长 秒')
  applicationMotionFolder.add(applicationMotionActions, 'replay').name('重新预览申请运镜')

  const submissionEnvelopeFolder = debugGui.addFolder('3D 信封动画')
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'x', -0.4, 0.4, 0.001)
    .name('终点 X')
    .onChange(applySubmissionEnvelopeDebugTransform)
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'y', -0.25, 0.25, 0.001)
    .name('终点 Y')
    .onChange(applySubmissionEnvelopeDebugTransform)
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'z', -1, -0.03, 0.001)
    .name('终点 Z')
    .onChange(applySubmissionEnvelopeDebugTransform)
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'rotationX', -180, 180, 0.1)
    .name('旋转 X°')
    .onChange(applySubmissionEnvelopeDebugTransform)
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'rotationY', -180, 180, 0.1)
    .name('旋转 Y°')
    .onChange(applySubmissionEnvelopeDebugTransform)
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'rotationZ', -180, 180, 0.1)
    .name('旋转 Z°')
    .onChange(applySubmissionEnvelopeDebugTransform)
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'scale', 0.01, 0.4, 0.001)
    .name('统一缩放')
    .onChange(applySubmissionEnvelopeDebugTransform)
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'startAdvance', 0, 3, 0.05)
    .name('提前飞出 秒')
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'flyDuration', 0.15, 4, 0.05)
    .name('飞出时长 秒')
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'returnDuration', 0.15, 4, 0.05)
    .name('收回时长 秒')
  submissionEnvelopeFolder
    .add(submissionEnvelopeDebug, 'successHold', 0, 5, 0.05)
    .name('成功停留 秒')
  submissionEnvelopeFolder.add(submissionEnvelopeActions, 'previewOut').name('预览信封飞出')
  submissionEnvelopeFolder.add(submissionEnvelopeActions, 'previewReturn').name('预览信封收回')
  submissionEnvelopeFolder.add(submissionEnvelopeActions, 'printCurrent').name('输出信封参数')

  const pushedTreeFolder = debugGui.addFolder('浣熊推树动画')
  pushedTreeFolder.add(pushedTreeDebug, 'enabled').name('启用')
  pushedTreeFolder
    .add(pushedTreeDebug, 'treeAmplitude', 0, 5, 0.1)
    .name('树与鸟幅度 °')
  pushedTreeFolder
    .add(pushedTreeDebug, 'directionalLean', -3, 4, 0.1)
    .name('受力倾斜 °')
  pushedTreeFolder
    .add(pushedTreeDebug, 'speed', 0.1, 1.5, 0.01)
    .name('整体速度')
  pushedTreeFolder
    .add(pushedTreeDebug, 'raccoonAmplitude', 0, 1.5, 0.05)
    .name('浣熊动作幅度')
  pushedTreeFolder
    .add(pushedTreeDebug, 'raccoonLean', 0, 15, 0.1)
    .name('浣熊前倾 °')
  pushedTreeFolder
    .add(pushedTreeDebug, 'raccoonTravel', 0, 2, 0.05)
    .name('浣熊推进量')

  debugGui.add(cameraDebug, 'replay').name('重新播放运镜')
  positionFolder.close()
  endPositionFolder.close()
  motionFolder.close()
  clipboardFolder.close()
  houseFolder.close()
  mailboxFolder.close()
  venueTabFolder.close()
  leftVenueTabFolder.close()
  rightVenueTabFolder.close()
  postLoginMotionFolder.open()
  applicationMotionFolder.open()
  submissionEnvelopeFolder.open()
  pushedTreeFolder.close()
}

function addReadOnlyController(folder: GUI, property: keyof typeof cameraReadout, label: string) {
  folder.add(cameraReadout, property).name(label).decimals(4).listen().disable()
}

function updateCameraReadout() {
  if (!camera || !controls) return

  cameraReadout.cameraX = camera.position.x
  cameraReadout.cameraY = camera.position.y
  cameraReadout.cameraZ = camera.position.z
  cameraReadout.targetX = controls.target.x
  cameraReadout.targetY = controls.target.y
  cameraReadout.targetZ = controls.target.z
  cameraReadout.rotationX = THREE.MathUtils.radToDeg(camera.rotation.x)
  cameraReadout.rotationY = THREE.MathUtils.radToDeg(camera.rotation.y)
  cameraReadout.rotationZ = THREE.MathUtils.radToDeg(camera.rotation.z)
  cameraReadout.distance = camera.position.distanceTo(controls.target)
}

function getCurrentCameraParameters() {
  updateCameraReadout()
  return {
    position: {
      x: cameraReadout.cameraX,
      y: cameraReadout.cameraY,
      z: cameraReadout.cameraZ,
    },
    target: {
      x: cameraReadout.targetX,
      y: cameraReadout.targetY,
      z: cameraReadout.targetZ,
    },
    rotationDegrees: {
      x: cameraReadout.rotationX,
      y: cameraReadout.rotationY,
      z: cameraReadout.rotationZ,
    },
    distance: cameraReadout.distance,
  }
}

function refreshCameraDebugGui() {
  for (const controller of debugGui?.controllersRecursive() ?? []) {
    controller.updateDisplay()
  }
}

function useCurrentCameraAsStart() {
  const current = getCurrentCameraParameters()
  cameraDebug.startX = current.position.x
  cameraDebug.startY = current.position.y
  cameraDebug.startZ = current.position.z
  cameraDebug.startTargetX = current.target.x
  cameraDebug.startTargetY = current.target.y
  cameraDebug.startTargetZ = current.target.z
  refreshCameraDebugGui()
  console.info('[开场运镜] 已将当前视角设为起点', current)
}

function printCurrentCameraParameters() {
  console.info('[开场运镜] 当前相机参数', getCurrentCameraParameters())
}

function playCameraEntrance() {
  if (!camera || !controls || !startCameraTarget || !endCameraTarget || !finalCameraPosition) return

  postLoginFlight = null
  applicationFlight = null
  selectedApplicationTarget = null
  submissionContext.value = null
  pendingSubmissionFiles.value = []
  submissionFilesUploading.value = false
  applicationStageActive.value = false
  resetSubmissionEnvelope()
  hideSubmissionSign(true)

  startCameraTarget.set(
    cameraDebug.startTargetX,
    cameraDebug.startTargetY,
    cameraDebug.startTargetZ,
  )
  endCameraTarget.set(cameraDebug.endTargetX, cameraDebug.endTargetY, cameraDebug.endTargetZ)
  finalCameraPosition.set(cameraDebug.endX, cameraDebug.endY, cameraDebug.endZ)

  const startOffsetX = cameraDebug.startX - startCameraTarget.x
  const startOffsetZ = cameraDebug.startZ - startCameraTarget.z
  const finalOffsetX = finalCameraPosition.x - endCameraTarget.x
  const finalOffsetZ = finalCameraPosition.z - endCameraTarget.z
  const startAngle = Math.atan2(startOffsetX, startOffsetZ)
  const finalAngle = Math.atan2(finalOffsetX, finalOffsetZ)
  const rawAngleDelta = finalAngle - startAngle
  const angleDelta = Math.atan2(Math.sin(rawAngleDelta), Math.cos(rawAngleDelta))
  const rotationDuration =
    THREE.MathUtils.radToDeg(Math.abs(angleDelta)) / cameraDebug.rotationSpeed
  const totalDuration = Math.max(cameraDebug.moveDuration, rotationDuration)

  cameraFlight = {
    startTarget: startCameraTarget.clone(),
    endTarget: endCameraTarget.clone(),
    currentTarget: startCameraTarget.clone(),
    startAngle,
    angleDelta,
    startRadius: Math.max(Math.hypot(startOffsetX, startOffsetZ), 0.001),
    finalRadius: Math.hypot(finalOffsetX, finalOffsetZ),
    startHeight: cameraDebug.startY - startCameraTarget.y,
    finalHeight: finalCameraPosition.y - endCameraTarget.y,
    moveDuration: cameraDebug.moveDuration,
    rotationDuration: Math.max(rotationDuration, 0.001),
    totalDuration,
    startedAt: performance.now(),
  }
  controls.target.copy(startCameraTarget)
  controls.enabled = false
  controls.autoRotate = false
  loginPanelVisible.value = false
  cinematicActive.value = true
  updateCameraEntrance(performance.now())
}

function playPostLoginCamera() {
  if (!camera || !controls) return

  cameraFlight = null
  applicationFlight = null
  selectedApplicationTarget = null
  submissionContext.value = null
  pendingSubmissionFiles.value = []
  submissionFilesUploading.value = false
  applicationStageActive.value = false
  resetSubmissionEnvelope()
  hideSubmissionSign()
  loginPanelVisible.value = false
  controls.enabled = false
  controls.autoRotate = false
  cinematicActive.value = true

  const endPosition = new THREE.Vector3(-0.1281, 0.0195, 0.1744)
  const endTarget = new THREE.Vector3(-0.0355, 0.0055, -0.0319)
  const endClipboardPosition = new THREE.Vector3(
    postLoginClipboardDebug.x,
    postLoginClipboardDebug.y,
    postLoginClipboardDebug.z,
  )
  const endClipboardQuaternion = new THREE.Quaternion().setFromEuler(
    new THREE.Euler(
      THREE.MathUtils.degToRad(postLoginClipboardDebug.rotationX),
      THREE.MathUtils.degToRad(postLoginClipboardDebug.rotationY),
      THREE.MathUtils.degToRad(postLoginClipboardDebug.rotationZ),
    ),
  )
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduceMotion) {
    camera.position.copy(endPosition)
    camera.lookAt(endTarget)
    controls.target.copy(endTarget)
    applyPostLoginClipboardTransform()
    controls.enabled = true
    controls.update()
    cinematicActive.value = false
    return
  }

  postLoginFlight = {
    startPosition: camera.position.clone(),
    endPosition,
    startTarget: controls.target.clone(),
    endTarget,
    currentTarget: controls.target.clone(),
    startClipboardPosition: clipboardModel?.position.clone() ?? endClipboardPosition.clone(),
    endClipboardPosition,
    startClipboardQuaternion:
      clipboardModel?.quaternion.clone() ?? endClipboardQuaternion.clone(),
    endClipboardQuaternion,
    startClipboardScale: clipboardModel?.scale.x ?? postLoginClipboardDebug.scale,
    endClipboardScale: postLoginClipboardDebug.scale,
    cameraDuration: 2.2,
    clipboardDuration: 1.2,
    overlapDuration: THREE.MathUtils.clamp(postLoginMotionDebug.overlapDuration, 0, 1.2),
    startedAt: performance.now(),
  }
}

function playApplicationCamera(target: ApplicationNavigationTarget) {
  if (!camera || !controls || !clipboardModel || cinematicActive.value) return

  cameraFlight = null
  postLoginFlight = null
  applicationFlight = null
  resetSubmissionEnvelope()
  clearSubmissionNotice()
  selectedApplicationTarget = target
  submissionContext.value = target
  pendingSubmissionFiles.value = []
  submissionFilesUploading.value = false
  applicationStageActive.value = true
  showSubmissionSign()
  controls.enabled = false
  controls.autoRotate = false
  cinematicActive.value = true

  const endPosition = new THREE.Vector3(-0.18, 0.0023, 0.0096)
  const endTarget = new THREE.Vector3(-0.0412, -0.0195, 0.0245)
  const endClipboardPosition = new THREE.Vector3(
    clipboardHomeTransform.x,
    clipboardHomeTransform.y,
    clipboardHomeTransform.z,
  )
  const endClipboardQuaternion = new THREE.Quaternion().setFromEuler(
    new THREE.Euler(
      THREE.MathUtils.degToRad(clipboardHomeTransform.rotationX),
      THREE.MathUtils.degToRad(clipboardHomeTransform.rotationY),
      THREE.MathUtils.degToRad(clipboardHomeTransform.rotationZ),
    ),
  )

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    camera.position.copy(endPosition)
    camera.lookAt(endTarget)
    controls.target.copy(endTarget)
    applyHomeClipboardTransform()
    controls.enabled = true
    controls.update()
    cinematicActive.value = false
    showSubmissionEnvelope()
    return
  }

  const cameraDelay = THREE.MathUtils.clamp(applicationMotionDebug.cameraDelay, 0, 2)
  const cameraDuration = THREE.MathUtils.clamp(applicationMotionDebug.cameraDuration, 0.5, 5)
  const clipboardDelay = THREE.MathUtils.clamp(applicationMotionDebug.clipboardDelay, 0, 2)
  const clipboardDuration = THREE.MathUtils.clamp(
    applicationMotionDebug.clipboardDuration,
    0.4,
    4,
  )
  applicationFlight = {
    startPosition: camera.position.clone(),
    endPosition,
    startTarget: controls.target.clone(),
    endTarget,
    currentTarget: controls.target.clone(),
    startClipboardPosition: clipboardModel.position.clone(),
    endClipboardPosition,
    startClipboardQuaternion: clipboardModel.quaternion.clone(),
    endClipboardQuaternion,
    startClipboardScale: clipboardModel.scale.x,
    endClipboardScale: clipboardHomeTransform.scale,
    cameraDelay,
    cameraDuration,
    clipboardDelay,
    clipboardDuration,
    totalDuration: Math.max(cameraDelay + cameraDuration, clipboardDelay + clipboardDuration),
    envelopeStarted: false,
    startedAt: performance.now(),
  }
}

function replayApplicationCamera() {
  if (!camera || !controls || !clipboardModel) return

  applicationFlight = null
  applicationStageActive.value = false
  cinematicActive.value = false
  resetSubmissionEnvelope()
  hideSubmissionSign(true)
  camera.position.set(-0.1281, 0.0195, 0.1744)
  controls.target.set(-0.0355, 0.0055, -0.0319)
  camera.lookAt(controls.target)
  applyPostLoginClipboardTransform()
  controls.enabled = true
  controls.update()

  const target = selectedApplicationTarget ?? {
    venueId: selectedVenueId.value ?? 0,
    venueName: venueOptions.value.find((venue) => venue.id === selectedVenueId.value)?.name ?? '预览场地',
    date: getLocalDateKey(offsetDate(new Date(), 1)),
  }
  requestAnimationFrame(() => playApplicationCamera(target))
}

function easeInOutCubic(progress: number) {
  return progress < 0.5
    ? 4 * progress * progress * progress
    : 1 - Math.pow(-2 * progress + 2, 3) / 2
}

function updateCameraEntrance(now: number) {
  if (!camera || !controls || !cameraFlight) return false

  const elapsed = (now - cameraFlight.startedAt) / 1000
  const moveProgress = THREE.MathUtils.clamp(elapsed / cameraFlight.moveDuration, 0, 1)
  const rotationProgress = THREE.MathUtils.clamp(elapsed / cameraFlight.rotationDuration, 0, 1)
  const totalProgress = THREE.MathUtils.clamp(elapsed / cameraFlight.totalDuration, 0, 1)
  const orbitProgress = easeInOutCubic(rotationProgress)
  const heightProgress = easeInOutCubic(moveProgress)
  const distanceProgress = 1 - Math.pow(1 - moveProgress, 2.35)
  cameraFlight.currentTarget.lerpVectors(
    cameraFlight.startTarget,
    cameraFlight.endTarget,
    heightProgress,
  )
  const angle = cameraFlight.startAngle + cameraFlight.angleDelta * orbitProgress
  const radius = THREE.MathUtils.lerp(
    cameraFlight.startRadius,
    cameraFlight.finalRadius,
    distanceProgress,
  )
  const height = THREE.MathUtils.lerp(
    cameraFlight.startHeight,
    cameraFlight.finalHeight,
    heightProgress,
  )

  camera.position.set(
    cameraFlight.currentTarget.x + Math.sin(angle) * radius,
    cameraFlight.currentTarget.y + height,
    cameraFlight.currentTarget.z + Math.cos(angle) * radius,
  )
  camera.lookAt(cameraFlight.currentTarget)
  controls.target.copy(cameraFlight.currentTarget)

  if (totalProgress >= 0.68) loginPanelVisible.value = true

  if (totalProgress >= 1) {
    camera.position.copy(finalCameraPosition ?? camera.position)
    camera.lookAt(cameraFlight.endTarget)
    controls.target.copy(cameraFlight.endTarget)
    controls.enabled = true
    controls.autoRotate = false
    controls.update()
    cameraFlight = null
    cinematicActive.value = false
    return false
  }

  return true
}

function updatePostLoginCamera(now: number) {
  if (!camera || !controls || !postLoginFlight) return false

  const elapsed = (now - postLoginFlight.startedAt) / 1000
  const cameraProgress = THREE.MathUtils.clamp(
    elapsed / postLoginFlight.cameraDuration,
    0,
    1,
  )
  const clipboardProgress = THREE.MathUtils.clamp(
    (elapsed - (postLoginFlight.cameraDuration - postLoginFlight.overlapDuration)) /
      postLoginFlight.clipboardDuration,
    0,
    1,
  )
  const easedCameraProgress = easeInOutCubic(cameraProgress)
  const easedClipboardProgress = easeInOutCubic(clipboardProgress)
  camera.position.lerpVectors(
    postLoginFlight.startPosition,
    postLoginFlight.endPosition,
    easedCameraProgress,
  )
  postLoginFlight.currentTarget.lerpVectors(
    postLoginFlight.startTarget,
    postLoginFlight.endTarget,
    easedCameraProgress,
  )
  camera.lookAt(postLoginFlight.currentTarget)
  controls.target.copy(postLoginFlight.currentTarget)
  if (clipboardModel) {
    clipboardModel.position.lerpVectors(
      postLoginFlight.startClipboardPosition,
      postLoginFlight.endClipboardPosition,
      easedClipboardProgress,
    )
    clipboardModel.quaternion.slerpQuaternions(
      postLoginFlight.startClipboardQuaternion,
      postLoginFlight.endClipboardQuaternion,
      easedClipboardProgress,
    )
    clipboardModel.scale.setScalar(
      THREE.MathUtils.lerp(
        postLoginFlight.startClipboardScale,
        postLoginFlight.endClipboardScale,
        easedClipboardProgress,
      ),
    )
  }

  if (clipboardProgress >= 1) {
    camera.position.copy(postLoginFlight.endPosition)
    camera.lookAt(postLoginFlight.endTarget)
    controls.target.copy(postLoginFlight.endTarget)
    applyPostLoginClipboardTransform()
    controls.enabled = true
    controls.update()
    postLoginFlight = null
    cinematicActive.value = false
    return false
  }

  return true
}

function updateApplicationCamera(now: number) {
  if (!camera || !controls || !applicationFlight) return false

  const elapsed = (now - applicationFlight.startedAt) / 1000
  const cameraProgress = THREE.MathUtils.clamp(
    (elapsed - applicationFlight.cameraDelay) / applicationFlight.cameraDuration,
    0,
    1,
  )
  const clipboardProgress = THREE.MathUtils.clamp(
    (elapsed - applicationFlight.clipboardDelay) / applicationFlight.clipboardDuration,
    0,
    1,
  )
  const easedCameraProgress = easeInOutCubic(cameraProgress)
  const easedClipboardProgress = easeInOutCubic(clipboardProgress)

  camera.position.lerpVectors(
    applicationFlight.startPosition,
    applicationFlight.endPosition,
    easedCameraProgress,
  )
  applicationFlight.currentTarget.lerpVectors(
    applicationFlight.startTarget,
    applicationFlight.endTarget,
    easedCameraProgress,
  )
  camera.lookAt(applicationFlight.currentTarget)
  controls.target.copy(applicationFlight.currentTarget)

  if (clipboardModel) {
    clipboardModel.position.lerpVectors(
      applicationFlight.startClipboardPosition,
      applicationFlight.endClipboardPosition,
      easedClipboardProgress,
    )
    clipboardModel.quaternion.slerpQuaternions(
      applicationFlight.startClipboardQuaternion,
      applicationFlight.endClipboardQuaternion,
      easedClipboardProgress,
    )
    clipboardModel.scale.setScalar(
      THREE.MathUtils.lerp(
        applicationFlight.startClipboardScale,
        applicationFlight.endClipboardScale,
        easedClipboardProgress,
      ),
    )
  }

  const envelopeAdvance = THREE.MathUtils.clamp(
    submissionEnvelopeDebug.startAdvance,
    0,
    applicationFlight.totalDuration,
  )
  const envelopeStartAt = applicationFlight.totalDuration - envelopeAdvance
  if (!applicationFlight.envelopeStarted && elapsed >= envelopeStartAt) {
    applicationFlight.envelopeStarted = true
    showSubmissionEnvelope()
  }

  if (elapsed >= applicationFlight.totalDuration) {
    camera.position.copy(applicationFlight.endPosition)
    camera.lookAt(applicationFlight.endTarget)
    controls.target.copy(applicationFlight.endTarget)
    applyHomeClipboardTransform()
    controls.enabled = true
    controls.update()
    const shouldStartEnvelope = !applicationFlight.envelopeStarted
    applicationFlight = null
    cinematicActive.value = false
    if (shouldStartEnvelope) showSubmissionEnvelope()
    return false
  }

  return true
}

function resizeRenderer() {
  if (!viewport.value || !renderer || !camera) return

  const { clientWidth, clientHeight } = viewport.value
  if (!clientWidth || !clientHeight) return

  renderer.setSize(clientWidth, clientHeight, false)
  camera.aspect = clientWidth / clientHeight
  camera.updateProjectionMatrix()
  updateSubmissionSignLayout()
}

function isVisibleInScene(object: THREE.Object3D) {
  let current: THREE.Object3D | null = object
  while (current) {
    if (!current.visible) return false
    current = current.parent
  }
  return true
}

function getPaperPointerPosition(clientX: number, clientY: number) {
  if (
    !renderer
    || !camera
    || !model
    || !pageContentCanvas
    || !paperSurfaceMesh
    || !paperContentBounds
  ) return null

  const bounds = renderer.domElement.getBoundingClientRect()
  if (!bounds.width || !bounds.height) return null
  pagePointer.set(
    ((clientX - bounds.left) / bounds.width) * 2 - 1,
    -((clientY - bounds.top) / bounds.height) * 2 + 1,
  )
  pageRaycaster.setFromCamera(pagePointer, camera)

  const intersections = pageRaycaster.intersectObject(model, true)
  for (const intersection of intersections) {
    const object = intersection.object
    if (!(object instanceof THREE.Mesh) || !isVisibleInScene(object)) continue
    if (object === topPage) continue

    // Only the closest visible surface decides the interaction. This prevents
    // the paper behind the metal clamp or wooden frame from receiving scroll.
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    const materialIndex = intersection.face?.materialIndex ?? 0
    if (materials[materialIndex]?.name !== 'Clean_Yellow_Parchment') return null
    if (object !== paperSurfaceMesh) return null

    const localPoint = object.worldToLocal(intersection.point.clone())
    const normalizedX = (localPoint.x - paperContentBounds.minX) / paperContentBounds.width
    // CanvasTexture uploads with flipY enabled. The shader's inverted V is
    // flipped once more during upload, so Canvas pixel Y follows local Y.
    const normalizedY = (localPoint.y - paperContentBounds.minY) / paperContentBounds.height
    if (
      normalizedX < 0
      || normalizedX > 1
      || normalizedY < 0
      || normalizedY > 1
    ) return null
    return { x: normalizedX, y: normalizedY }
  }

  return null
}

function isPointerOverPaper(clientX: number, clientY: number) {
  return getPaperPointerPosition(clientX, clientY) !== null
}

function handlePaperWheel(event: WheelEvent) {
  if (!pageContentCanvas || !isPointerOverPaper(event.clientX, event.clientY)) return

  event.preventDefault()
  event.stopImmediatePropagation()
  const deltaScale = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? 18 : event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? 700 : 1
  const delta = THREE.MathUtils.clamp(event.deltaY * deltaScale, -260, 260)
  pageContentCanvas.scrollBy(delta)
}

function handlePaperPointerMove(event: PointerEvent) {
  if (!renderer || !pageContentCanvas) return
  if (isPointerOverSubmissionEnvelope(event.clientX, event.clientY)) {
    pageContentCanvas.pointerLeave()
    renderer.domElement.style.cursor = submissionEnvelopeState === 'uploading' ? 'progress' : 'pointer'
    return
  }
  const pointer = getPaperPointerPosition(event.clientX, event.clientY)
  if (!pointer) {
    pageContentCanvas.pointerLeave()
    renderer.domElement.style.cursor = ''
    return
  }

  pageContentCanvas.pointerMove(pointer.x, pointer.y)
  renderer.domElement.style.cursor = pageContentCanvas.getPageAction(pointer.x, pointer.y)
    ? 'pointer'
    : ''
}

function handlePaperPointerLeave() {
  pageContentCanvas?.pointerLeave()
  if (renderer) renderer.domElement.style.cursor = ''
}

async function startNewVenueApplication() {
  if (applicationTabLoading.value) return
  let venue = venueOptions.value.find((item) => item.id === selectedVenueId.value)
    ?? venueOptions.value[0]
    ?? venueUsageBoard?.venues[0]
  if (!venue) {
    applicationTabLoading.value = true
    await loadVenueUsageBoard()
    applicationTabLoading.value = false
    venue = venueOptions.value.find((item) => item.id === selectedVenueId.value)
      ?? venueOptions.value[0]
      ?? venueUsageBoard?.venues[0]
    if (!venue) {
      showSubmissionNotice('error', '场地信息加载失败，请稍后再试', 3200)
      return
    }
  }
  selectedVenueId.value = venue.id
  playApplicationCamera({
    venueId: venue.id,
    venueName: venue.name,
    date: getLocalDateKey(offsetDate(new Date(), 1)),
    mode: 'new',
  })
}

function handlePaperClick(event: PointerEvent) {
  if (isPointerOverSubmissionEnvelope(event.clientX, event.clientY)) {
    openSubmissionFilePicker()
    return
  }
  if (!pageContentCanvas || cinematicActive.value || applicationStageActive.value) return
  const pointer = getPaperPointerPosition(event.clientX, event.clientY)
  if (!pointer) return
  const action = pageContentCanvas.getPageAction(pointer.x, pointer.y)
  if (action?.type === 'switch-page') {
    switchFolderPage(action.page)
    return
  }
  if (action?.type === 'resubmit') {
    const application = action.application
    playApplicationCamera({
      venueId: application.venueId ?? 0,
      venueName: application.venueName,
      date: application.startAt
        ? getLocalDateKey(new Date(application.startAt))
        : getLocalDateKey(new Date()),
      mode: 'resubmit',
      applicationId: application.id,
    })
    return
  }
  if (action?.type === 'supplement') {
    const application = action.application
    playApplicationCamera({
      venueId: application.venueId ?? 0,
      venueName: application.venueName,
      date: application.startAt
        ? getLocalDateKey(new Date(application.startAt))
        : getLocalDateKey(new Date()),
      mode: 'supplement',
      applicationId: application.id,
    })
    return
  }
  const target = pageContentCanvas.getApplicationTarget(pointer.x, pointer.y)
  if (!target) return

  playApplicationCamera(target)
}

function cachePaperFacePoints(paper: THREE.Mesh) {
  paper.geometry.computeBoundingBox()
  const bounds = paper.geometry.boundingBox
  const positions = paper.geometry.getAttribute('position')
  const normals = paper.geometry.getAttribute('normal')
  paperVisibleFacePoints = []
  if (
    !bounds
    || !(positions instanceof THREE.BufferAttribute)
    || !(normals instanceof THREE.BufferAttribute)
  ) return

  const depth = Math.max(bounds.max.z - bounds.min.z, 0.00001)
  const clusterSize = depth * 0.035
  const point = new THREE.Vector3()
  const normal = new THREE.Vector3()
  const faceClusters = new Map<number, THREE.Vector3[]>()

  for (let index = 0; index < positions.count; index += 1) {
    point.fromBufferAttribute(positions, index)
    normal.fromBufferAttribute(normals, index)
    if (Math.abs(normal.z) < 0.85) continue

    const clusterKey = Math.round(point.z / clusterSize)
    const cluster = faceClusters.get(clusterKey) ?? []
    cluster.push(point.clone())
    faceClusters.set(clusterKey, cluster)
  }

  let largestSurfaceArea = Number.NEGATIVE_INFINITY
  for (const cluster of faceClusters.values()) {
    const surfaceBounds = new THREE.Box3().setFromPoints(cluster)
    const surfaceArea = (surfaceBounds.max.x - surfaceBounds.min.x)
      * (surfaceBounds.max.y - surfaceBounds.min.y)
    if (surfaceArea <= largestSurfaceArea) continue

    largestSurfaceArea = surfaceArea
    paperVisibleFacePoints = cluster
    paperVisibleFaceZ = cluster.reduce((sum, facePoint) => sum + facePoint.z, 0) / cluster.length
  }
}

function updateVenueSelectorPosition() {
  const positioningLayer = venueSelector.value ?? applicationTab.value?.parentElement
  if (
    !positioningLayer
    || !paperSurfaceMesh
    || !renderer
    || !camera
    || (!venueSelectorReady.value && !applicationTab.value)
  ) return

  const selectorBounds = positioningLayer.getBoundingClientRect()
  const rendererBounds = renderer.domElement.getBoundingClientRect()
  if (!selectorBounds.width || !rendererBounds.width || rendererBounds.width < 860) return

  paperSurfaceMesh.geometry.computeBoundingBox()
  const paperBounds = paperSurfaceMesh.geometry.boundingBox
  if (!paperBounds) return

  paperSurfaceMesh.updateWorldMatrix(true, false)
  let minX = Number.POSITIVE_INFINITY
  let maxX = Number.NEGATIVE_INFINITY
  let minY = Number.POSITIVE_INFINITY
  let maxY = Number.NEGATIVE_INFINITY
  const projectedCorner = new THREE.Vector3()
  for (const localPoint of paperVisibleFacePoints) {
    projectedCorner
        .copy(localPoint)
        .applyMatrix4(paperSurfaceMesh.matrixWorld)
        .project(camera)

    const screenX = rendererBounds.left
      + (projectedCorner.x * 0.5 + 0.5) * rendererBounds.width
      - selectorBounds.left
    const screenY = rendererBounds.top
      + (-projectedCorner.y * 0.5 + 0.5) * rendererBounds.height
      - selectorBounds.top
    minX = Math.min(minX, screenX)
    maxX = Math.max(maxX, screenX)
    minY = Math.min(minY, screenY)
    maxY = Math.max(maxY, screenY)
  }

  // The broad front plane supplies the precise left/right paper edges. Keep
  // the full geometry height for the deliberately irregular top and bottom.
  for (const x of [paperBounds.min.x, paperBounds.max.x]) {
    for (const y of [paperBounds.min.y, paperBounds.max.y]) {
      projectedCorner
        .set(x, y, paperVisibleFaceZ)
        .applyMatrix4(paperSurfaceMesh.matrixWorld)
        .project(camera)
      const screenY = rendererBounds.top
        + (-projectedCorner.y * 0.5 + 0.5) * rendererBounds.height
        - selectorBounds.top
      minY = Math.min(minY, screenY)
      maxY = Math.max(maxY, screenY)
    }
  }

  if (![minX, maxX, minY, maxY].every(Number.isFinite)) return

  const paperHeight = maxY - minY
  const leftSlots = [0.14, 0.31, 0.47, 0.64, 0.83]
  const rightSlots = [0.21, 0.38, 0.56, 0.75]
  const leftItemOffsets = [
    venueTabDebug.left1Y,
    venueTabDebug.left2Y,
    venueTabDebug.left3Y,
    venueTabDebug.left4Y,
    venueTabDebug.left5Y,
  ]
  const rightItemOffsets = [
    venueTabDebug.right1Y,
    venueTabDebug.right2Y,
    venueTabDebug.right3Y,
    venueTabDebug.right4Y,
  ]
  const venueButtons = venueSelector.value?.querySelectorAll<HTMLElement>('.venue-float-button') ?? []

  venueButtons.forEach((venueButton, index) => {
    const isLeft = index % 2 === 0
    const sideIndex = Math.floor(index / 2)
    const verticalRatio = isLeft
      ? (leftSlots[sideIndex] ?? 0.5)
      : (rightSlots[sideIndex] ?? 0.5)
    const sideOffsetY = isLeft ? venueTabDebug.leftY : venueTabDebug.rightY
    const itemOffsetY = isLeft
      ? (leftItemOffsets[sideIndex] ?? 0)
      : (rightItemOffsets[sideIndex] ?? 0)

    // Anchor each ordinary DOM button directly to the projected paper edge.
    // The 14px overlap remains visible; there is intentionally no clipping or
    // simulated depth occlusion in this DOM version.
    venueButton.style.left = `${isLeft ? minX + venueTabDebug.leftX : maxX + venueTabDebug.rightX}px`
    venueButton.style.top = `${minY + paperHeight * verticalRatio + sideOffsetY + itemOffsetY}px`
  })

  if (applicationTab.value) {
    applicationTab.value.style.left = `${maxX - 5}px`
    applicationTab.value.style.top = `${minY + paperHeight * 0.86}px`
  }
}

function animate() {
  if (!renderer || !scene || !camera) return
  animationFrame = requestAnimationFrame(animate)

  const elapsed = performance.now() * 0.001
  for (const shader of windShaders) shader.time.value = elapsed
  updateRaccoonPushedTree(elapsed)
  if (pageTurnShader) pageTurnShader.time.value = elapsed
  pageContentCanvas?.tick()

  const now = performance.now()
  const cameraIsMoving =
    updateCameraEntrance(now) || updatePostLoginCamera(now) || updateApplicationCamera(now)
  if (!cameraIsMoving) controls?.update()
  updateVenueSelectorPosition()
  updateCameraReadout()
  renderer.render(scene, camera)
}

async function handleLogin() {
  if (!account.value.trim() || !password.value) {
    formError.value = '请输入邮箱或手机号及密码'
    return
  }

  formError.value = ''
  loginSucceeded.value = false
  const success = await auth.login(account.value.trim(), password.value)

  if (success) {
    loginSucceeded.value = true
    folderPage.value = 'profile'
    void loadPersonalHome()
    playPostLoginCamera()
    return
  }

  formError.value = auth.error || '登录失败，请检查账号和密码'
}

function getLocalDateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function cleanPurposeSummary(value: string | null) {
  if (!value) return '场地使用申请'
  return value.replace(/^\[DEMO_USAGE:[^\]]+\]\s*/, '')
}

function offsetDate(date: Date, days: number) {
  const nextDate = new Date(date)
  nextDate.setDate(nextDate.getDate() + days)
  return nextDate
}

async function loadVenueUsageBoard() {
  if (!pageContentCanvas) return
  const today = new Date()
  const dateKey = getLocalDateKey(today)
  const mode = auth.isAdmin ? 'management' : 'user-detail'
  const rangeStart = getLocalDateKey(mode === 'management' ? today : offsetDate(today, -15))
  const rangeEnd = getLocalDateKey(mode === 'management' ? today : offsetDate(today, 15))
  venueSelectorReady.value = false
  const loadingBoard: VenueUsageBoard = {
    mode,
    date: dateKey,
    rangeStart,
    rangeEnd,
    state: 'loading',
    venues: [],
  }
  venueUsageBoard = loadingBoard
  if (folderPage.value === 'calendar') pageContentCanvas.updateUsageBoard(loadingBoard)

  try {
    const { data } = await axios.get<VenueUsageRangeApi>('/api/v1/venues/usage-range', {
      params: { start_date: rangeStart, end_date: rangeEnd },
    })

    const usageItems: VenueUsageItem[] = data.venues.map(({ venue, events }) => ({
      id: venue.id,
      name: venue.name,
      events: events
        .filter(
          (event) =>
            mode !== 'management' || getLocalDateKey(new Date(event.start_at)) === dateKey,
        )
        .sort(
          (first, second) =>
            new Date(first.start_at).getTime() - new Date(second.start_at).getTime(),
        )
        .map((event) => ({
          id: event.id,
          organization:
            event.borrow_organization || event.organization || event.title || '场地申请',
          purpose: cleanPurposeSummary(event.purpose_summary),
          startAt: event.start_at,
          endAt: event.end_at,
          status: event.status,
        })),
    }))

    venueUsageBoard = {
      mode,
      date: dateKey,
      rangeStart: data.start_date,
      rangeEnd: data.end_date,
      state: 'ready',
      venues: usageItems,
    }
    if (folderPage.value === 'calendar') pageContentCanvas.updateUsageBoard(venueUsageBoard)
    if (mode === 'user-detail') {
      venueOptions.value = data.venues.map(({ venue }) => venue)
      selectedVenueId.value = venueOptions.value[0]?.id ?? null
      venueSelectorReady.value = venueOptions.value.length > 0
    } else {
      venueOptions.value = []
      selectedVenueId.value = null
    }
  } catch (error) {
    console.error('[场地使用看板] 数据加载失败', error)
    venueUsageBoard = {
      mode,
      date: dateKey,
      rangeStart,
      rangeEnd,
      state: 'error',
      venues: [],
      error: '请确认本地后端服务已启动',
    }
    if (folderPage.value === 'calendar') pageContentCanvas.updateUsageBoard(venueUsageBoard)
    venueOptions.value = []
    selectedVenueId.value = null
    venueSelectorReady.value = false
  }
}

async function loadPersonalHome() {
  if (!pageContentCanvas) return
  const dateKey = getLocalDateKey(new Date())
  personalHomeBoard = {
    mode: 'profile',
    date: dateKey,
    state: 'loading',
    venues: [],
    applications: [],
  }
  if (folderPage.value === 'profile') pageContentCanvas.updateUsageBoard(personalHomeBoard)

  try {
    if (!auth.user) await auth.fetchMe()
    const [applicationsResponse, venuesResponse] = await Promise.all([
      axios.get<PersonalApplicationApi[]>('/api/v1/applications'),
      axios.get<VenueApiItem[]>('/api/v1/venues'),
    ])
    const user = auth.user
    if (!user) throw new Error('当前用户信息不可用')
    const venueNames = new Map(venuesResponse.data.map((venue) => [venue.id, venue.name]))
    const applications: PersonalApplicationItem[] = applicationsResponse.data.map(
      (application) => ({
        id: application.id,
        applicationType: application.application_type,
        venueId: application.venue_id,
        venueName: application.venue_id
          ? venueNames.get(application.venue_id) ?? `场地 #${application.venue_id}`
          : application.application_type === 'key_borrow'
            ? '钥匙借用'
            : '综合申请',
        purpose: cleanPurposeSummary(application.purpose_summary),
        status: application.status,
        startAt: application.start_at,
        endAt: application.end_at,
        reviewReason: application.review_reason,
        createdAt: application.created_at,
      }),
    )
    personalHomeBoard = {
      mode: 'profile',
      date: dateKey,
      state: 'ready',
      venues: [],
      profile: {
        email: user.email,
        organization: user.department || '未填写所属组织',
        role: user.role,
        verified: user.is_sdu_verified,
        applicationAllowed: user.is_application_allowed || user.is_sdu_verified,
      },
      applications,
    }
  } catch (error) {
    console.error('[个人首页] 数据加载失败', error)
    personalHomeBoard = {
      mode: 'profile',
      date: dateKey,
      state: 'error',
      venues: [],
      applications: [],
      error: '请确认本地后端服务已启动并重新登录',
    }
  }
  if (folderPage.value === 'profile') pageContentCanvas.updateUsageBoard(personalHomeBoard)
}

function switchFolderPage(page: 'profile' | 'calendar') {
  if (folderPage.value === page) return
  folderPage.value = page
  if (page === 'profile') {
    if (personalHomeBoard) pageContentCanvas?.transitionUsageBoard(personalHomeBoard)
    else void loadPersonalHome()
    return
  }
  if (venueUsageBoard) pageContentCanvas?.transitionUsageBoard(venueUsageBoard)
  else void loadVenueUsageBoard()
}

function selectUsageVenue(venueId: number) {
  if (venueId === selectedVenueId.value) return
  selectedVenueId.value = venueId
  pageContentCanvas?.selectVenue(venueId)
}

function stopSmsCountdown() {
  if (smsCountdownTimer) clearInterval(smsCountdownTimer)
  smsCountdownTimer = null
  smsCountdown.value = 0
}

function startSmsCountdown() {
  stopSmsCountdown()
  smsCountdown.value = 60
  smsCountdownTimer = setInterval(() => {
    smsCountdown.value -= 1
    if (smsCountdown.value <= 0) stopSmsCountdown()
  }, 1000)
}

function revokeRegistrationCaptcha() {
  if (!registrationCaptchaUrl.value) return
  URL.revokeObjectURL(registrationCaptchaUrl.value)
  registrationCaptchaUrl.value = ''
}

async function loadRegistrationCaptcha() {
  captchaLoading.value = true
  formError.value = ''
  formNotice.value = ''
  smsSent.value = false
  stopSmsCountdown()

  const captcha = await auth.requestRegistrationCaptcha()
  revokeRegistrationCaptcha()
  if (captcha) registrationCaptchaUrl.value = URL.createObjectURL(captcha)
  else formError.value = auth.error || '图片验证码加载失败，请稍后重试'
  captchaLoading.value = false
}

function changeAuthMode(mode: 'login' | 'register') {
  if (authMode.value === mode) return
  authMode.value = mode
  formError.value = ''
  formNotice.value = ''
  loginSucceeded.value = false
  if (mode === 'register' && !registrationCaptchaUrl.value) {
    void loadRegistrationCaptcha()
  }
}

function handleAuthFormBeforeLeave(element: Element) {
  if (!authFormStage.value) return
  authFormStage.value.style.height = `${(element as HTMLElement).offsetHeight}px`
}

function handleAuthFormBeforeEnter(element: Element) {
  const stage = authFormStage.value
  if (!stage) return
  const nextForm = element as HTMLElement
  void stage.offsetHeight
  requestAnimationFrame(() => {
    const nextHeight = nextForm.scrollHeight
    stage.style.height = `${nextHeight}px`
  })
}

function handleAuthFormAfterEnter() {
  if (authFormStage.value) authFormStage.value.style.height = 'auto'
}

function invalidateSmsVerification() {
  if (!smsSent.value) return
  smsSent.value = false
  formNotice.value = '手机号或图片验证码已修改，请重新获取短信验证码。'
  stopSmsCountdown()
}

async function handleSendRegistrationSms() {
  if (!/^\d{11}$/.test(registerMobile.value)) {
    formError.value = '请输入11位手机号'
    return
  }
  if (!/^\d{4}$/.test(registerImageCode.value)) {
    formError.value = '请输入图片中的4位验证码'
    return
  }

  smsSending.value = true
  formError.value = ''
  formNotice.value = ''
  const success = await auth.sendRegistrationSms(
    registerMobile.value,
    registerImageCode.value,
  )
  smsSending.value = false

  if (success) {
    smsSent.value = true
    formNotice.value = '短信验证码已发送，请在两分钟内完成注册。'
    startSmsCountdown()
    return
  }

  const errorMessage = auth.error || '短信验证码发送失败'
  await loadRegistrationCaptcha()
  formError.value = errorMessage
}

async function handleRegister() {
  const email = registerEmail.value.trim()
  const organization = registerOrganization.value.trim()
  if (!email || !organization) {
    formError.value = '请填写邮箱和所属组织'
    return
  }
  if (!/^\d{11}$/.test(registerMobile.value)) {
    formError.value = '请输入11位手机号'
    return
  }
  if (!smsSent.value || !/^\d{6}$/.test(registerSmsCode.value)) {
    formError.value = '请先完成手机验证并输入6位短信验证码'
    return
  }
  if (registerPassword.value.length < 8) {
    formError.value = '密码至少需要8个字符'
    return
  }
  if (registerPassword.value !== registerPasswordConfirm.value) {
    formError.value = '两次输入的密码不一致'
    return
  }

  formError.value = ''
  formNotice.value = ''
  loginSucceeded.value = false
  const success = await auth.register(
    email,
    registerPassword.value,
    organization,
    registerMobile.value,
    registerSmsCode.value,
  )

  if (success) {
    loginSucceeded.value = true
    stopSmsCountdown()
    folderPage.value = 'profile'
    void loadPersonalHome()
    playPostLoginCamera()
    return
  }

  const errorMessage = auth.error || '注册失败，请检查认证信息'
  registerSmsCode.value = ''
  smsSent.value = false
  await loadRegistrationCaptcha()
  formError.value = errorMessage
}

function disposeMaterial(material: THREE.Material) {
  for (const value of Object.values(material)) {
    if (value instanceof THREE.Texture) value.dispose()
  }
  material.dispose()
}

onMounted(() => {
  if (!viewport.value) return

  scene = new THREE.Scene()
  scene.background = new THREE.Color('#f5ecd9')
  scene.fog = new THREE.FogExp2('#f5ecd9', 0.008)

  camera = new THREE.PerspectiveCamera(42, 1, 0.1, 1000)
  camera.position.set(4, 3, 6)

  renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.15
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFShadowMap
  viewport.value.appendChild(renderer.domElement)
  scene.add(camera)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.06
  controls.enabled = false
  controls.autoRotate = false
  controls.enableRotate = true
  controls.enablePan = true
  controls.enableZoom = true
  renderer.domElement.addEventListener('wheel', handlePaperWheel, {
    capture: true,
    passive: false,
  })
  renderer.domElement.addEventListener('pointermove', handlePaperPointerMove, { passive: true })
  renderer.domElement.addEventListener('pointerleave', handlePaperPointerLeave)
  renderer.domElement.addEventListener('click', handlePaperClick)
  renderer.domElement.addEventListener('dragover', handleSubmissionDragOver)
  renderer.domElement.addEventListener('dragleave', handleSubmissionDragLeave)
  renderer.domElement.addEventListener('drop', handleSubmissionDrop)

  scene.add(new THREE.HemisphereLight('#fff5dc', '#847b66', 2.25))

  const keyLight = new THREE.DirectionalLight('#fff3d2', 3.4)
  keyLight.position.set(6, 10, 8)
  keyLight.castShadow = true
  keyLight.shadow.mapSize.set(2048, 2048)
  // The imported clipboard contains broad, nearly coplanar paper surfaces.
  // A small normal offset prevents directional-shadow self-intersection from
  // appearing as diagonal bands across the otherwise flat sheet.
  keyLight.shadow.bias = -0.0002
  keyLight.shadow.normalBias = 0.015
  keyLight.shadow.radius = 2
  scene.add(keyLight)

  const fillLight = new THREE.DirectionalLight('#d8e6cf', 1.5)
  fillLight.position.set(-8, 4, -5)
  scene.add(fillLight)

  const loadingManager = new THREE.LoadingManager()
  loadingManager.onProgress = (_url, loaded, total) => {
    loadingProgress.value = Math.round((loaded / total) * 100)
  }
  const loader = new GLTFLoader(loadingManager)
  const houseUrl = `${import.meta.env.BASE_URL}models/forest_house.glb`
  const clipboardUrl = `${import.meta.env.BASE_URL}models/downloaded_clipboard.glb`
  const mailboxUrl = `${import.meta.env.BASE_URL}models/mailbox.glb`
  const submissionSignUrl = `${import.meta.env.BASE_URL}models/hanging-wooden-sign-themed.glb`

  Promise.all([
    loader.loadAsync(houseUrl),
    loader.loadAsync(clipboardUrl),
    loader.loadAsync(mailboxUrl),
    loader.loadAsync(submissionSignUrl),
  ])
    .then(([houseGltf, clipboardGltf, mailboxGltf, submissionSignGltf]) => {
      if (!scene || !camera) return

      model = new THREE.Group()
      model.name = 'Login_Scene_Models'
      houseModel = houseGltf.scene
      houseModel.name = 'Forest_House'
      clipboardModel = clipboardGltf.scene
      clipboardModel.name = 'Wooden_Clipboard'
      mailboxModel = prepareMailboxModel(mailboxGltf.scene)
      submissionSignModel = prepareSubmissionSignModel(submissionSignGltf.scene)
      applyClipboardTransform()
      applyMailboxTransform()
      model.add(houseModel, clipboardModel, mailboxModel)
      camera.add(submissionSignModel)
      updateSubmissionSignLayout()
      registerSubmissionEnvelope(mailboxModel)

      const topPageObject = clipboardModel.getObjectByName('Top_Page')
      topPage = topPageObject instanceof THREE.Mesh ? topPageObject : null
      pageContentCanvas = createParchmentPageCanvas(
        renderer?.capabilities.getMaxAnisotropy() ?? 1,
      )
      const leafyTreeParts: THREE.Mesh[] = []

      houseModel.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.castShadow = true
          child.receiveShadow = true
          const materials = Array.isArray(child.material) ? child.material : [child.material]
          materials.forEach(fixCutoutMaterial)
          if (child.name === 'Redwood_BrichTree_0' || child.name === 'RedwoodAlpha_TreeLeafs_0')
            leafyTreeParts.push(child)
        }
      })
      setupRaccoonPushedTree(houseModel)

      clipboardModel.traverse((child) => {
        if (!(child instanceof THREE.Mesh)) return
        if (child.name === 'Downloaded_Clipboard_Mesh_1') {
          paperSurfaceMesh = child
          cachePaperFacePoints(child)
        }
        child.castShadow = true
        child.receiveShadow = true
        const materials = Array.isArray(child.material) ? child.material : [child.material]
        materials.forEach(fixCutoutMaterial)

        // Paint the Canvas content into the clipboard's original paper material.
        if (child !== topPage && pageContentCanvas) {
          const contentBounds = projectPageContentOntoMaterial(
            child,
            'Clean_Yellow_Parchment',
            pageContentCanvas.texture,
          )
          if (child === paperSurfaceMesh && contentBounds) paperContentBounds = contentBounds
        }
      })

      if (topPage && pageTurnEnabled) {
        topPage.geometry.computeBoundingBox()
        const pageBounds = topPage.geometry.boundingBox?.clone()
        if (pageBounds) {
          pageTurnShader = enablePageTurnDeformation(topPage, pageBounds)
          topPageInitialPosition.copy(topPage.position)
          topPageInitialRotation.copy(topPage.rotation)
          topPageInitialScale.copy(topPage.scale)
          pageTurnAvailable.value = true
          pageTurnCompleted.value = false
        }
      } else if (topPage) {
        // The static page already exists in the downloaded model. Keeping this
        // helper sheet visible would add thickness and cause side-view clipping.
        topPage.visible = false
      }

      const leafyTreeBounds = new THREE.Box3()
      for (const treePart of leafyTreeParts) {
        treePart.geometry.computeBoundingBox()
        if (treePart.geometry.boundingBox) {
          leafyTreeBounds.union(treePart.geometry.boundingBox)
        }
      }
      for (const treePart of leafyTreeParts) {
        enableTreeCrownWind(treePart, windShaders, {
          bounds: leafyTreeBounds,
          phase: 0.65,
          strength: 0.18,
        })
      }

      scene.add(model)
      startCameraEntrance(model, houseModel)
      // Match live GUI editing: establish the house-based camera composition at
      // its authored size first, then apply the saved visual scale.
      applyHouseTransform()
      loadingProgress.value = 100
      modelReady.value = true
    })
    .catch((error) => {
      console.error('Failed to load GLB models', error)
      loadError.value = '场景模型加载失败，请检查模型路径或浏览器 WebGL 支持。'
    })

  resizeObserver = new ResizeObserver(resizeRenderer)
  resizeObserver.observe(viewport.value)
  resizeRenderer()
  animate()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animationFrame)
  stopSmsCountdown()
  revokeRegistrationCaptcha()
  submissionEnvelopeTween?.kill()
  submissionSignTween?.kill()
  if (submissionEnvelopeReturnTimer) clearTimeout(submissionEnvelopeReturnTimer)
  if (submissionNoticeTimer) clearTimeout(submissionNoticeTimer)
  pageTurnTimeline?.kill()
  resizeObserver?.disconnect()
  controls?.dispose()
  debugGui?.destroy()
  renderer?.domElement.removeEventListener('wheel', handlePaperWheel, true)
  renderer?.domElement.removeEventListener('pointermove', handlePaperPointerMove)
  renderer?.domElement.removeEventListener('pointerleave', handlePaperPointerLeave)
  renderer?.domElement.removeEventListener('click', handlePaperClick)
  renderer?.domElement.removeEventListener('dragover', handleSubmissionDragOver)
  renderer?.domElement.removeEventListener('dragleave', handleSubmissionDragLeave)
  renderer?.domElement.removeEventListener('drop', handleSubmissionDrop)

  resetSubmissionEnvelope()

  submissionSignModel?.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return
    child.geometry.dispose()
    if (Array.isArray(child.material)) child.material.forEach(disposeMaterial)
    else disposeMaterial(child.material)
  })
  submissionSignModel?.removeFromParent()

  model?.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return
    child.geometry.dispose()
    if (Array.isArray(child.material)) child.material.forEach(disposeMaterial)
    else disposeMaterial(child.material)
  })

  renderer?.dispose()
  renderer?.domElement.remove()
  pageContentCanvas?.texture.dispose()
  renderer = null
  scene = null
  camera = null
  controls = null
  model = null
  houseModel = null
  clipboardModel = null
  mailboxModel = null
  submissionSignModel = null
  submissionSignTween = null
  topPage = null
  paperSurfaceMesh = null
  paperContentBounds = null
  paperVisibleFacePoints = []
  paperVisibleFaceZ = 0
  pageTurnShader = null
  pageContentCanvas = null
  personalHomeBoard = null
  venueUsageBoard = null
  pageTurnTimeline = null
  pageTurnAvailable.value = false
  pageTurning.value = false
  pageTurnCompleted.value = false
  cameraFlight = null
  postLoginFlight = null
  applicationFlight = null
  selectedApplicationTarget = null
  submissionEnvelope = null
  submissionEnvelopeTween = null
  submissionEnvelopeReturnTimer = null
  pushedTreeAnimation = null
  startCameraTarget = null
  endCameraTarget = null
  finalCameraPosition = null
  debugGui = null
  windShaders.length = 0
})
</script>

<template>
  <main class="model-page">
    <div ref="viewport" class="model-viewport" />
    <input
      ref="applicationFileInput"
      class="submission-file-input"
      type="file"
      accept=".doc,.docx,.pdf,.jpg,.jpeg,.png"
      multiple
      aria-label="选择一份或多份申请材料"
      @change="handleApplicationFileChange"
    />

    <Transition name="submission-notice">
      <aside
        v-if="submissionNoticeVisible"
        class="submission-success-notice"
        :class="submissionNoticeMode"
        role="status"
        aria-live="polite"
      >
        <span class="submission-success-mark" aria-hidden="true">
          {{ submissionNoticeMode === 'uploading' ? '↻' : submissionNoticeMode === 'success' ? '✓' : '!' }}
        </span>
        <span>
          <strong>
            {{
              submissionNoticeMode === 'uploading'
                ? '申请文件正在上传'
                : submissionNoticeMode === 'success'
                  ? '申请文件已送达'
                  : '文件提交失败'
            }}
          </strong>
          <small>{{ submissionNoticeMessage }}</small>
        </span>
      </aside>
    </Transition>

    <Transition name="submission-guide">
      <aside
        v-if="applicationStageActive && submissionContext && submissionGuide"
        class="submission-guide"
        aria-label="当前文件提交说明"
      >
        <div class="submission-guide-title">
          <span class="submission-guide-step">{{ submissionGuide.step }}</span>
          <span>
            <small>{{ submissionGuide.kicker }}</small>
            <strong>{{ submissionGuide.title }}</strong>
          </span>
        </div>
        <div class="submission-guide-context">
          <span>{{ submissionContext.venueName }}</span>
          <span>
            {{ submissionContext.applicationId ? `申请 #${submissionContext.applicationId}` : '新申请' }}
          </span>
        </div>
        <div class="submission-guide-requirements">
          <div
            v-for="requirement in submissionGuide.requirements"
            :key="requirement.label"
            class="submission-guide-requirement"
            :class="{
              fulfilled:
                requirement.kind === 'optional'
                  ? pendingSubmissionFiles.length > 1
                  : requirement.kind === 'any'
                    ? pendingSubmissionFiles.length > 0
                    : submissionHasPrimaryFile,
            }"
          >
            <FileText :size="17" :stroke-width="1.55" />
            <span>
              <strong>{{ requirement.label }}</strong>
              <small>{{ requirement.extension }}</small>
            </span>
            <i aria-hidden="true" />
          </div>
        </div>
        <p>{{ submissionGuide.description }}</p>
      </aside>
    </Transition>

    <Transition name="submission-cache">
      <aside
        v-if="applicationStageActive && submissionContext"
        class="submission-cache-bubble"
        :class="{ empty: pendingSubmissionFiles.length === 0 }"
        aria-label="待提交文件缓存"
      >
        <span class="submission-cache-tail" aria-hidden="true" />
        <header>
          <span>
            <small>ENVELOPE POCKET</small>
            <strong>信封里的文件</strong>
          </span>
          <em>{{ pendingSubmissionFiles.length }} 份 · {{ formatSubmissionFileSize(submissionCacheSize) }}</em>
        </header>

        <div v-if="pendingSubmissionFiles.length" class="submission-cache-list">
          <article
            v-for="(item, index) in pendingSubmissionFiles"
            :key="item.id"
            class="submission-cache-item"
          >
            <span class="submission-cache-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="submission-cache-name">
              <strong>{{ item.file.name }}</strong>
              <small>{{ getSubmissionFileExtension(item.file.name) }} · {{ formatSubmissionFileSize(item.file.size) }}</small>
            </span>
            <button
              type="button"
              :disabled="submissionFilesUploading"
              :aria-label="`移除 ${item.file.name}`"
              @click.stop="removeStagedSubmissionFile(item.id)"
            >
              ×
            </button>
          </article>
        </div>
        <p v-else class="submission-cache-empty">
          信封还是空的<br>
          <small>点击 3D 信封或将文件拖放进来</small>
        </p>

        <footer>
          <button
            type="button"
            class="submission-cache-add"
            :disabled="submissionFilesUploading"
            @click.stop="openSubmissionFilePicker"
          >
            <span aria-hidden="true">＋</span> 继续放入
          </button>
          <button
            type="button"
            class="submission-cache-submit"
            :disabled="!submissionRequirementsSatisfied || submissionFilesUploading"
            @click.stop="submitStagedApplicationFiles"
          >
            <span class="submission-cache-seal" aria-hidden="true">✓</span>
            <span>{{ submissionFilesUploading ? '正在送出' : '封缄并送出' }}</span>
          </button>
        </footer>
      </aside>
    </Transition>

    <div v-if="!modelReady && !loadError" class="loading-panel">
      <div class="loading-track">
        <span :style="{ width: `${loadingProgress}%` }" />
      </div>
      <p>正在加载小屋、文件夹与信箱模型 {{ loadingProgress }}%</p>
    </div>

    <div v-if="loadError" class="error-panel">{{ loadError }}</div>

    <Transition name="login-card">
      <section
        v-if="loginPanelVisible"
        class="login-card"
        :class="{ 'register-card': authMode === 'register' }"
        aria-labelledby="auth-title"
      >
        <div class="card-ornament" aria-hidden="true">
          <span />
          <Trees :size="18" :stroke-width="1.6" />
          <span />
        </div>

        <header class="card-heading">
          <p>MEIYU SYSTEM</p>
          <Transition name="auth-heading" mode="out-in">
            <div :key="authMode" class="card-heading-copy">
              <h1 id="auth-title">{{ authMode === 'login' ? '欢迎回来' : '加入我们' }}</h1>
              <span>
                {{ authMode === 'login' ? '登录美育活动管理系统' : '完成手机认证后创建账户' }}
              </span>
            </div>
          </Transition>
        </header>

        <div class="auth-mode-switch" role="tablist" aria-label="账户操作">
          <button
            type="button"
            role="tab"
            :aria-selected="authMode === 'login'"
            :class="{ active: authMode === 'login' }"
            @click="changeAuthMode('login')"
          >
            登录
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="authMode === 'register'"
            :class="{ active: authMode === 'register' }"
            @click="changeAuthMode('register')"
          >
            注册
          </button>
        </div>

        <div ref="authFormStage" class="auth-form-stage">
          <Transition
            name="auth-form"
            mode="out-in"
            @before-leave="handleAuthFormBeforeLeave"
            @before-enter="handleAuthFormBeforeEnter"
            @after-enter="handleAuthFormAfterEnter"
          >
        <form
          v-if="authMode === 'login'"
          key="login"
          class="login-form"
          @submit.prevent="handleLogin"
        >
          <label class="form-field">
            <span>账号</span>
            <span class="input-shell">
              <UserRound :size="18" :stroke-width="1.7" aria-hidden="true" />
              <input
                v-model="account"
                name="account"
                type="text"
                autocomplete="username"
                placeholder="邮箱或手机号"
                :disabled="auth.loading || loginSucceeded"
              />
            </span>
          </label>

          <label class="form-field">
            <span>密码</span>
            <span class="input-shell">
              <LockKeyhole :size="18" :stroke-width="1.7" aria-hidden="true" />
              <input
                v-model="password"
                name="password"
                :type="passwordVisible ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入密码"
                :disabled="auth.loading || loginSucceeded"
              />
              <button
                type="button"
                class="password-toggle"
                :aria-label="passwordVisible ? '隐藏密码' : '显示密码'"
                @click="passwordVisible = !passwordVisible"
              >
                <EyeOff v-if="passwordVisible" :size="17" aria-hidden="true" />
                <Eye v-else :size="17" aria-hidden="true" />
              </button>
            </span>
          </label>

          <p v-if="formError" class="form-message error-message" role="alert">
            {{ formError }}
          </p>
          <p v-if="loginSucceeded" class="form-message success-message" role="status">
            身份验证成功，欢迎回来。
          </p>

          <button class="login-button" type="submit" :disabled="auth.loading || loginSucceeded">
            <span>{{ auth.loading ? '正在验证…' : loginSucceeded ? '登录成功' : '进入系统' }}</span>
            <ArrowRight v-if="!auth.loading" :size="18" :stroke-width="1.8" aria-hidden="true" />
            <span v-else class="button-spinner" aria-hidden="true" />
          </button>
        </form>

        <form
          v-else
          key="register"
          class="login-form register-form"
          @submit.prevent="handleRegister"
        >
          <div class="register-grid">
            <label class="form-field full-field">
              <span>邮箱</span>
              <span class="input-shell">
                <Mail :size="17" :stroke-width="1.7" aria-hidden="true" />
                <input
                  v-model="registerEmail"
                  name="register-email"
                  type="email"
                  autocomplete="email"
                  placeholder="用作登录账号"
                  :disabled="auth.loading || loginSucceeded"
                  required
                />
              </span>
            </label>

            <label class="form-field full-field">
              <span>所属组织</span>
              <span class="input-shell">
                <Building2 :size="17" :stroke-width="1.7" aria-hidden="true" />
                <input
                  v-model="registerOrganization"
                  name="organization"
                  type="text"
                  autocomplete="organization"
                  placeholder="学院、社团或部门名称"
                  :disabled="auth.loading || loginSucceeded"
                  required
                />
              </span>
            </label>

            <label class="form-field full-field">
              <span>认证手机号</span>
              <span class="input-shell">
                <Smartphone :size="17" :stroke-width="1.7" aria-hidden="true" />
                <input
                  v-model="registerMobile"
                  name="mobile"
                  type="tel"
                  inputmode="numeric"
                  autocomplete="tel"
                  maxlength="11"
                  placeholder="山大统一身份认证手机号"
                  :disabled="auth.loading || loginSucceeded"
                  required
                  @input="invalidateSmsVerification"
                />
              </span>
            </label>

            <label class="form-field full-field">
              <span>图片验证码</span>
              <span class="verification-control captcha-control">
                <span class="input-shell">
                  <input
                    v-model="registerImageCode"
                    name="image-code"
                    type="text"
                    inputmode="numeric"
                    autocomplete="off"
                    maxlength="4"
                    placeholder="4位验证码"
                    :disabled="auth.loading || loginSucceeded"
                    required
                    @input="invalidateSmsVerification"
                  />
                </span>
                <button
                  class="captcha-button"
                  type="button"
                  :disabled="captchaLoading || smsSending || auth.loading"
                  title="点击更换图片验证码"
                  @click="loadRegistrationCaptcha"
                >
                  <img
                    v-if="registrationCaptchaUrl && !captchaLoading"
                    :src="registrationCaptchaUrl"
                    alt="图片验证码，点击可更换"
                  />
                  <span v-else>{{ captchaLoading ? '加载中' : '重新获取' }}</span>
                  <RefreshCw :size="14" :class="{ spinning: captchaLoading }" aria-hidden="true" />
                </button>
              </span>
            </label>

            <label class="form-field full-field">
              <span>短信验证码</span>
              <span class="verification-control">
                <span class="input-shell">
                  <input
                    v-model="registerSmsCode"
                    name="sms-code"
                    type="text"
                    inputmode="numeric"
                    autocomplete="one-time-code"
                    maxlength="6"
                    placeholder="6位短信验证码"
                    :disabled="auth.loading || loginSucceeded"
                    required
                  />
                </span>
                <button
                  class="send-code-button"
                  type="button"
                  :disabled="smsSending || smsCountdown > 0 || auth.loading || loginSucceeded"
                  @click="handleSendRegistrationSms"
                >
                  {{ smsSending ? '发送中…' : smsCountdown > 0 ? `${smsCountdown}s 后重发` : '获取验证码' }}
                </button>
              </span>
            </label>

            <label class="form-field">
              <span>设置密码</span>
              <span class="input-shell">
                <LockKeyhole :size="17" :stroke-width="1.7" aria-hidden="true" />
                <input
                  v-model="registerPassword"
                  name="register-password"
                  :type="registerPasswordVisible ? 'text' : 'password'"
                  autocomplete="new-password"
                  minlength="8"
                  placeholder="至少8个字符"
                  :disabled="auth.loading || loginSucceeded"
                  required
                />
                <button
                  type="button"
                  class="password-toggle"
                  :aria-label="registerPasswordVisible ? '隐藏密码' : '显示密码'"
                  @click="registerPasswordVisible = !registerPasswordVisible"
                >
                  <EyeOff v-if="registerPasswordVisible" :size="16" aria-hidden="true" />
                  <Eye v-else :size="16" aria-hidden="true" />
                </button>
              </span>
            </label>

            <label class="form-field">
              <span>确认密码</span>
              <span class="input-shell">
                <LockKeyhole :size="17" :stroke-width="1.7" aria-hidden="true" />
                <input
                  v-model="registerPasswordConfirm"
                  name="register-password-confirm"
                  :type="registerPasswordVisible ? 'text' : 'password'"
                  autocomplete="new-password"
                  minlength="8"
                  placeholder="再次输入密码"
                  :disabled="auth.loading || loginSucceeded"
                  required
                />
              </span>
            </label>
          </div>

          <p v-if="formError" class="form-message error-message" role="alert">
            {{ formError }}
          </p>
          <p v-else-if="formNotice" class="form-message info-message" role="status">
            {{ formNotice }}
          </p>
          <p v-if="loginSucceeded" class="form-message success-message" role="status">
            手机认证和账户注册成功。
          </p>

          <button class="login-button" type="submit" :disabled="auth.loading || loginSucceeded">
            <span>{{ auth.loading ? '正在认证并创建…' : loginSucceeded ? '注册成功' : '认证并创建账户' }}</span>
            <ArrowRight v-if="!auth.loading" :size="18" :stroke-width="1.8" aria-hidden="true" />
            <span v-else class="button-spinner" aria-hidden="true" />
          </button>
        </form>
          </Transition>
        </div>

        <p class="privacy-note">
          {{
            authMode === 'login'
              ? '支持已认证的邮箱、手机号或学号登录'
              : '认证成功前不会创建用户名、密码和组织记录'
          }}
        </p>
      </section>
    </Transition>

    <Transition name="application-tab">
      <button
        v-if="loginSucceeded && folderPage === 'profile' && !cinematicActive && !applicationStageActive"
        ref="applicationTab"
        class="application-edge-tab"
        type="button"
        :disabled="applicationTabLoading"
        aria-label="发起场地申请"
        @click="startNewVenueApplication"
      >
        <span class="application-tab-sprig" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <span>场地申请</span>
        <span class="application-tab-seal" aria-hidden="true">
          <i />
        </span>
      </button>
    </Transition>

    <Transition name="venue-selector">
      <nav
        v-if="folderPage === 'calendar' && venueSelectorReady && !cinematicActive && !applicationStageActive"
        ref="venueSelector"
        class="venue-floating-selector"
        aria-label="选择要查看的场地"
      >
        <button
          v-for="(venue, index) in venueOptions"
          :key="venue.id"
          type="button"
          class="venue-float-button"
          :class="{ active: selectedVenueId === venue.id }"
          :style="{ animationDelay: `${index * 65}ms` }"
          :aria-pressed="selectedVenueId === venue.id"
          @click="selectUsageVenue(venue.id)"
        >
          <span class="venue-button-mark" aria-hidden="true" />
          <span>{{ venue.name }}</span>
        </button>
      </nav>
    </Transition>

    <button
      v-if="pageTurnEnabled && modelReady && pageTurnAvailable && !cinematicActive && !applicationStageActive"
      class="page-turn-button"
      type="button"
      :disabled="pageTurning"
      @click="triggerPageTurn"
    >
      {{ pageTurning ? '纸页正在落下…' : pageTurnCompleted ? '再次翻页' : '翻到下一页' }}
    </button>

  </main>
</template>

<style scoped>
.model-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #f5ecd9;
  color-scheme: light;
  font-family: Inter, 'PingFang SC', 'Microsoft YaHei', ui-sans-serif, system-ui, sans-serif;
}

.model-viewport,
.model-viewport :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}

.submission-file-input {
  position: fixed;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}

.submission-success-notice {
  position: absolute;
  top: 28px;
  left: 50%;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 280px;
  max-width: min(440px, calc(100vw - 32px));
  padding: 13px 18px 13px 14px;
  border: 1px solid rgba(91, 111, 80, 0.48);
  border-radius: 5px 18px 5px 18px;
  background:
    linear-gradient(145deg, rgba(249, 241, 217, 0.96), rgba(226, 211, 171, 0.94)),
    #efe2bf;
  box-shadow:
    0 14px 34px rgba(45, 54, 37, 0.22),
    inset 0 1px rgba(255, 255, 255, 0.68);
  color: #4f6049;
  pointer-events: none;
  backdrop-filter: blur(10px);
  transform: translateX(-50%);
}

.submission-success-notice > span:last-child {
  display: grid;
  gap: 2px;
}

.submission-success-notice strong {
  color: #43533f;
  font-family: 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 15px;
  letter-spacing: 0.06em;
}

.submission-success-notice small {
  color: rgba(74, 86, 66, 0.76);
  font-size: 12px;
}

.submission-success-mark {
  display: grid;
  flex: 0 0 31px;
  width: 31px;
  height: 31px;
  place-items: center;
  border: 1px solid rgba(85, 109, 77, 0.52);
  border-radius: 50% 44% 52% 46%;
  background: #687f62;
  color: #f8efd7;
  font-family: Georgia, serif;
  font-size: 18px;
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.22);
  transform: rotate(-5deg);
}

.submission-success-notice.uploading .submission-success-mark {
  background: #788670;
  animation: submission-mark-spin 1.1s linear infinite;
}

.submission-success-notice.error {
  border-color: rgba(139, 83, 63, 0.5);
  color: #805443;
}

.submission-success-notice.error .submission-success-mark {
  border-color: rgba(132, 74, 55, 0.58);
  background: #9a624e;
}

.submission-success-notice.error strong {
  color: #744936;
}

@keyframes submission-mark-spin {
  from {
    transform: rotate(-5deg);
  }

  to {
    transform: rotate(355deg);
  }
}

.submission-notice-enter-active,
.submission-notice-leave-active {
  transition:
    opacity 280ms ease,
    transform 360ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 280ms ease;
}

.submission-notice-enter-from,
.submission-notice-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: translate(-50%, -16px) scale(0.96);
}

.submission-guide {
  position: absolute;
  top: 30px;
  left: 50%;
  z-index: 12;
  display: grid;
  grid-template-columns: 1.1fr 0.7fr 1.55fr;
  gap: 22px;
  align-items: center;
  width: min(850px, calc(100vw - 96px));
  min-height: 104px;
  padding: 16px 46px 15px;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: #fff0c8;
  pointer-events: none;
  transform: translateX(-50%) rotate(-0.2deg);
}

.submission-guide-title {
  display: flex;
  align-items: center;
  gap: 13px;
}

.submission-guide-title > span:last-child {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.submission-guide-title small {
  overflow: hidden;
  color: rgba(255, 236, 193, 0.62);
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 8px;
  letter-spacing: 0.12em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submission-guide-title strong {
  color: #fff0ca;
  font-family: 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 21px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-shadow: 0 1px rgba(49, 34, 19, 0.52);
}

.submission-guide-step {
  display: grid;
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  place-items: center;
  border: 1px solid rgba(43, 54, 39, 0.7);
  border-radius: 48% 43% 51% 45%;
  background: #60735a;
  color: #fff0cf;
  font-family: 'Songti SC', 'STSong', serif;
  font-size: 11px;
  line-height: 1.15;
  text-align: center;
  box-shadow:
    inset 0 1px rgba(255, 255, 255, 0.13),
    0 2px 4px rgba(40, 29, 18, 0.3);
  transform: rotate(-4deg);
}

.submission-guide-context {
  display: grid;
  gap: 6px;
  padding: 2px 20px;
  border-right: 1px solid rgba(255, 231, 184, 0.16);
  border-left: 1px solid rgba(255, 231, 184, 0.16);
  color: rgba(255, 239, 204, 0.78);
  font-family: 'Songti SC', 'STSong', serif;
  font-size: 13px;
  text-align: center;
}

.submission-guide-context span:last-child {
  color: rgba(255, 235, 192, 0.5);
  font-family: Georgia, serif;
  font-size: 10px;
  letter-spacing: 0.08em;
}

.submission-guide-requirements {
  display: flex;
  gap: 8px;
  min-width: 0;
}

.submission-guide-requirement {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) 8px;
  gap: 7px;
  align-items: center;
  min-width: 0;
  padding: 8px 9px;
  border: 1px solid rgba(47, 34, 20, 0.27);
  border-radius: 3px 8px 3px 7px;
  background: rgba(50, 35, 20, 0.15);
  color: rgba(255, 238, 199, 0.68);
  box-shadow: inset 0 1px rgba(255, 248, 222, 0.09);
}

.submission-guide-requirement > span {
  display: grid;
  gap: 1px;
  min-width: 0;
}

.submission-guide-requirement strong,
.submission-guide-requirement small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submission-guide-requirement strong {
  font-family: 'Songti SC', 'STSong', serif;
  font-size: 11px;
  font-weight: 500;
}

.submission-guide-requirement small {
  color: rgba(255, 233, 188, 0.46);
  font-size: 8px;
}

.submission-guide-requirement i {
  width: 7px;
  height: 7px;
  border: 1px solid rgba(255, 229, 180, 0.44);
  border-radius: 50%;
}

.submission-guide-requirement.fulfilled {
  background: rgba(67, 91, 61, 0.48);
  color: #fff0c8;
}

.submission-guide-requirement.fulfilled i {
  border-color: #dce0af;
  background: #dce0af;
  box-shadow: 0 0 0 2px rgba(220, 224, 175, 0.14);
}

.submission-guide > p {
  position: absolute;
  right: 46px;
  bottom: 5px;
  margin: 0;
  color: rgba(255, 234, 188, 0.38);
  font-family: 'Songti SC', 'STSong', serif;
  font-size: 8px;
  letter-spacing: 0.04em;
}

.submission-cache-bubble {
  position: absolute;
  bottom: clamp(62px, 9vh, 112px);
  left: 42%;
  z-index: 18;
  width: min(410px, calc(100vw - 42px));
  padding: 16px 17px 15px;
  border: 1px solid rgba(94, 79, 49, 0.34);
  border-radius: 20px 17px 22px 16px / 18px 22px 17px 20px;
  background:
    linear-gradient(100deg, rgba(113, 91, 48, 0.04), transparent 25%, rgba(113, 91, 48, 0.04)),
    rgba(246, 237, 205, 0.96);
  box-shadow:
    0 18px 42px rgba(39, 44, 33, 0.24),
    inset 0 1px rgba(255, 255, 255, 0.66);
  color: #5d4a2d;
  transform: translateX(-50%) rotate(-0.5deg);
}

.submission-cache-tail {
  position: absolute;
  top: -24px;
  right: 54px;
  width: 52px;
  height: 34px;
  background: rgba(246, 237, 205, 0.96);
  clip-path: polygon(8% 100%, 100% 100%, 0 0);
  filter: drop-shadow(-1px -1px rgba(94, 79, 49, 0.22));
}

.submission-cache-bubble header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
  padding: 0 3px 10px;
  border-bottom: 1px solid rgba(102, 82, 47, 0.18);
}

.submission-cache-bubble header > span {
  display: grid;
  gap: 1px;
}

.submission-cache-bubble header small {
  color: rgba(93, 74, 42, 0.46);
  font-family: Georgia, serif;
  font-size: 8px;
  letter-spacing: 0.12em;
}

.submission-cache-bubble header strong {
  color: #59411e;
  font-family: 'Songti SC', 'STSong', serif;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.submission-cache-bubble header em {
  color: rgba(83, 102, 75, 0.75);
  font-family: 'Songti SC', 'STSong', serif;
  font-size: 10px;
  font-style: normal;
}

.submission-cache-list {
  display: grid;
  gap: 6px;
  max-height: 150px;
  margin: 9px 0;
  overflow: auto;
  scrollbar-color: rgba(92, 110, 82, 0.4) transparent;
  scrollbar-width: thin;
}

.submission-cache-item {
  display: grid;
  grid-template-columns: 27px minmax(0, 1fr) 25px;
  gap: 8px;
  align-items: center;
  padding: 7px 8px;
  border: 1px solid rgba(99, 79, 43, 0.15);
  border-radius: 4px 11px 4px 9px;
  background: rgba(255, 252, 232, 0.46);
}

.submission-cache-index {
  color: rgba(91, 74, 43, 0.43);
  font-family: Georgia, serif;
  font-size: 10px;
}

.submission-cache-name {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.submission-cache-name strong,
.submission-cache-name small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submission-cache-name strong {
  color: #5c4727;
  font-family: 'Songti SC', 'STSong', serif;
  font-size: 11px;
  font-weight: 500;
}

.submission-cache-name small {
  color: rgba(88, 71, 42, 0.47);
  font-size: 8px;
}

.submission-cache-item > button {
  width: 23px;
  height: 23px;
  padding: 0;
  border: 1px solid rgba(134, 78, 57, 0.34);
  border-radius: 50% 45% 48% 42%;
  background: transparent;
  color: #95624e;
  font-family: Georgia, serif;
  font-size: 18px;
  line-height: 19px;
  cursor: pointer;
  transition: 180ms ease;
}

.submission-cache-item > button:hover:not(:disabled) {
  background: #95624e;
  color: #f8edcf;
  transform: rotate(8deg) scale(1.05);
}

.submission-cache-empty {
  margin: 14px 0 12px;
  color: rgba(87, 70, 41, 0.62);
  font-family: 'Songti SC', 'STSong', serif;
  font-size: 13px;
  line-height: 1.65;
  text-align: center;
}

.submission-cache-empty small {
  color: rgba(87, 70, 41, 0.4);
  font-size: 9px;
}

.submission-cache-bubble footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 2px;
}

.submission-cache-bubble footer button {
  border: 0;
  font-family: 'Songti SC', 'STSong', serif;
  cursor: pointer;
}

.submission-cache-add {
  padding: 7px 4px;
  background: transparent;
  color: #62745a;
  font-size: 11px;
  letter-spacing: 0.04em;
}

.submission-cache-add span {
  display: inline-grid;
  width: 20px;
  height: 20px;
  margin-right: 4px;
  place-items: center;
  border: 1px solid rgba(87, 107, 79, 0.45);
  border-radius: 50%;
}

.submission-cache-submit {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 12px 3px 4px;
  border-radius: 22px 5px 5px 22px !important;
  background: rgba(95, 114, 86, 0.12);
  color: #52654c;
  font-size: 11px;
  letter-spacing: 0.07em;
}

.submission-cache-seal {
  display: grid;
  width: 31px;
  height: 31px;
  place-items: center;
  border: 1px solid rgba(112, 64, 49, 0.52);
  border-radius: 48% 43% 51% 45%;
  background: #9c624e;
  color: #f7e9c9;
  font-family: Georgia, serif;
  font-size: 13px;
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.16);
  transition: transform 220ms ease;
}

.submission-cache-submit:hover:not(:disabled) .submission-cache-seal {
  transform: rotate(-8deg) scale(1.06);
}

.submission-cache-bubble button:disabled {
  cursor: default;
  filter: grayscale(0.45);
  opacity: 0.42;
}

.submission-guide-enter-active,
.submission-guide-leave-active {
  transition:
    opacity 380ms ease,
    transform 520ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 380ms ease;
}

.submission-guide-enter-from,
.submission-guide-leave-to {
  opacity: 0;
  filter: blur(5px);
  transform: translate(-50%, -18px) rotate(-1deg) scale(0.97);
}

.submission-cache-enter-active,
.submission-cache-leave-active {
  transition:
    opacity 320ms ease,
    transform 460ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 320ms ease;
}

.submission-cache-enter-from,
.submission-cache-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: translate(-50%, 20px) rotate(-2deg) scale(0.96);
}

@media (max-width: 720px) {
  .submission-guide {
    top: 16px;
    grid-template-columns: 1fr 1fr;
    gap: 9px;
    width: calc(100vw - 28px);
    min-height: 0;
    padding: 13px 20px;
  }

  .submission-guide-context {
    border-right: 0;
  }

  .submission-guide-requirements {
    grid-column: 1 / -1;
  }

  .submission-guide > p {
    display: none;
  }

  .submission-cache-bubble {
    bottom: 24px;
    left: 50%;
    width: calc(100vw - 28px);
  }
}

.loading-panel,
.error-panel {
  position: absolute;
  top: 50%;
  left: 50%;
  width: min(320px, calc(100vw - 48px));
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  background: rgba(7, 17, 13, 0.78);
  color: rgba(238, 255, 247, 0.82);
  text-align: center;
  backdrop-filter: blur(16px);
  transform: translate(-50%, -50%);
}

.loading-panel p {
  margin: 12px 0 0;
  font-size: 13px;
}

.loading-track {
  height: 5px;
  overflow: hidden;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.1);
}

.loading-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #3dd9ac, #f7ca75);
  transition: width 180ms ease;
}

.error-panel {
  border-color: rgba(248, 113, 113, 0.35);
  color: #fecaca;
}

.login-card {
  position: absolute;
  top: 50%;
  right: clamp(28px, 8vw, 128px);
  z-index: 2;
  width: min(390px, calc(100vw - 48px));
  padding: 30px 32px 24px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.88);
  border-radius: 4px 24px 4px 24px;
  background:
    linear-gradient(145deg, rgba(255, 253, 246, 0.91), rgba(240, 231, 211, 0.8)),
    rgba(248, 242, 226, 0.88);
  box-shadow:
    0 32px 80px rgba(77, 68, 46, 0.17),
    0 4px 18px rgba(77, 68, 46, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  color: #29453c;
  backdrop-filter: blur(18px) saturate(0.9);
  transform: translateY(-50%);
  transition:
    width 520ms cubic-bezier(0.22, 1, 0.36, 1),
    padding 520ms cubic-bezier(0.22, 1, 0.36, 1),
    border-radius 420ms ease,
    box-shadow 420ms ease;
}

.login-card.register-card {
  width: min(470px, calc(100vw - 48px));
  max-height: calc(100vh - 32px);
  padding: 24px 28px 20px;
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.login-card.register-card::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}

.login-card::before,
.login-card::after {
  position: absolute;
  content: '';
  pointer-events: none;
}

.login-card::before {
  top: -76px;
  right: -64px;
  width: 190px;
  height: 190px;
  border: 1px solid rgba(92, 124, 99, 0.16);
  border-radius: 50%;
  box-shadow:
    0 0 0 18px rgba(92, 124, 99, 0.035),
    0 0 0 36px rgba(92, 124, 99, 0.025);
}

.login-card::after {
  right: 22px;
  bottom: 18px;
  width: 54px;
  height: 1px;
  background: rgba(156, 84, 62, 0.38);
  box-shadow: 8px 4px 0 rgba(156, 84, 62, 0.17);
  transform: rotate(-8deg);
}

.card-ornament {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 11px;
  color: #718c73;
}

.card-ornament span {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(93, 124, 99, 0.46));
}

.card-ornament span:last-child {
  background: linear-gradient(90deg, rgba(93, 124, 99, 0.46), transparent);
}

.card-heading {
  position: relative;
  z-index: 1;
  margin: 18px 0 25px;
  text-align: center;
}

.card-heading p,
.card-heading h1,
.card-heading span {
  margin: 0;
}

.card-heading-copy {
  display: grid;
  justify-items: center;
}

.card-heading p {
  color: #9b5d49;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.24em;
}

.card-heading h1 {
  margin-top: 6px;
  color: #29453c;
  font-family: 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 30px;
  font-weight: 600;
  letter-spacing: 0.06em;
}

.card-heading span {
  display: block;
  margin-top: 7px;
  color: rgba(56, 76, 67, 0.58);
  font-size: 12px;
  letter-spacing: 0.08em;
}

.register-card .card-heading {
  margin: 13px 0 16px;
}

.register-card .card-heading h1 {
  font-size: 27px;
}

.auth-mode-switch {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 4px;
  margin-bottom: 19px;
  padding: 4px;
  border: 1px solid rgba(86, 112, 92, 0.16);
  border-radius: 3px 13px 3px 13px;
  background: rgba(219, 210, 188, 0.3);
}

.auth-mode-switch button {
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 2px 10px 2px 10px;
  background: transparent;
  color: rgba(41, 69, 60, 0.55);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition:
    color 160ms ease,
    background-color 160ms ease,
    box-shadow 160ms ease;
}

.auth-mode-switch button.active {
  background: rgba(255, 253, 246, 0.86);
  box-shadow: 0 3px 12px rgba(63, 75, 57, 0.08);
  color: #355849;
}

.auth-form-stage {
  position: relative;
  overflow: hidden;
  transition: height 520ms cubic-bezier(0.22, 1, 0.36, 1);
}

.auth-form-enter-active {
  transition:
    opacity 360ms ease,
    transform 440ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 360ms ease;
}

.auth-form-leave-active {
  transition:
    opacity 210ms ease,
    transform 260ms ease,
    filter 210ms ease;
}

.auth-form-enter-from {
  opacity: 0;
  filter: blur(5px);
  transform: translateX(18px) scale(0.985);
}

.auth-form-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: translateX(-14px) scale(0.99);
}

.auth-heading-enter-active,
.auth-heading-leave-active {
  transition:
    opacity 220ms ease,
    transform 280ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 220ms ease;
}

.auth-heading-enter-from {
  opacity: 0;
  filter: blur(3px);
  transform: translateY(7px);
}

.auth-heading-leave-to {
  opacity: 0;
  filter: blur(3px);
  transform: translateY(-5px);
}

.login-form {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 17px;
}

.register-form {
  gap: 12px;
}

.register-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.register-grid .full-field {
  grid-column: 1 / -1;
}

.register-form .form-field {
  gap: 6px;
}

.register-form .input-shell {
  min-height: 43px;
  padding-inline: 12px;
}

.register-form .input-shell input {
  font-size: 13px;
}

.verification-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 126px;
  align-items: stretch;
  gap: 8px;
}

.captcha-control {
  grid-template-columns: minmax(0, 1fr) 142px;
}

.captcha-button,
.send-code-button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 43px;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid rgba(86, 112, 92, 0.25);
  border-radius: 3px 12px 3px 12px;
  background: rgba(247, 241, 225, 0.82);
  color: #466755;
  font-size: 11px;
  white-space: nowrap;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background-color 160ms ease;
}

.captcha-button:hover:not(:disabled),
.send-code-button:hover:not(:disabled) {
  border-color: rgba(75, 111, 88, 0.55);
  background: rgba(255, 253, 246, 0.96);
}

.captcha-button:disabled,
.send-code-button:disabled {
  cursor: default;
  opacity: 0.65;
}

.captcha-button img {
  width: 92px;
  height: 32px;
  object-fit: fill;
  image-rendering: auto;
}

.captcha-button:has(img) {
  justify-content: space-between;
  padding-inline: 7px;
}

.spinning {
  animation: button-spin 700ms linear infinite;
}

.form-field {
  display: grid;
  gap: 8px;
}

.form-field > span:first-child {
  color: rgba(41, 69, 60, 0.72);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.input-shell {
  display: flex;
  align-items: center;
  min-height: 49px;
  gap: 11px;
  padding: 0 14px;
  border: 1px solid rgba(86, 112, 92, 0.25);
  border-radius: 3px 13px 3px 13px;
  background: rgba(255, 253, 246, 0.66);
  color: rgba(74, 101, 84, 0.62);
  box-shadow: inset 0 1px 3px rgba(72, 61, 41, 0.035);
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background-color 180ms ease;
}

.input-shell:focus-within {
  border-color: rgba(75, 111, 88, 0.62);
  background: rgba(255, 254, 250, 0.88);
  box-shadow:
    0 0 0 3px rgba(83, 126, 97, 0.09),
    inset 0 1px 3px rgba(72, 61, 41, 0.035);
}

.input-shell input {
  width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #29453c;
  font-size: 14px;
}

.input-shell input::placeholder {
  color: rgba(67, 87, 79, 0.38);
}

.password-toggle {
  display: grid;
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
  padding: 0;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgba(74, 101, 84, 0.55);
  cursor: pointer;
  transition:
    color 160ms ease,
    background-color 160ms ease;
}

.password-toggle:hover {
  background: rgba(83, 126, 97, 0.08);
  color: #456c57;
}

.form-message {
  margin: -5px 0 0;
  padding: 9px 11px;
  border-radius: 3px 10px 3px 10px;
  font-size: 12px;
  line-height: 1.45;
}

.error-message {
  background: rgba(165, 74, 58, 0.08);
  color: #9b4e40;
}

.success-message {
  background: rgba(72, 125, 87, 0.1);
  color: #3f7650;
}

.info-message {
  background: rgba(71, 102, 91, 0.08);
  color: #4a695c;
}

.login-button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50px;
  gap: 10px;
  margin-top: 2px;
  border: 0;
  border-radius: 3px 15px 3px 15px;
  background: linear-gradient(112deg, rgba(255, 255, 255, 0.07), transparent 45%), #416455;
  box-shadow: 0 12px 26px rgba(51, 82, 67, 0.2);
  color: #f9f3e5;
  font-weight: 650;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    background-color 180ms ease;
}

.login-button:hover:not(:disabled) {
  background-color: #355849;
  box-shadow: 0 15px 32px rgba(51, 82, 67, 0.25);
  transform: translateY(-2px);
}

.login-button:disabled {
  cursor: default;
  opacity: 0.72;
}

.button-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.32);
  border-top-color: #fff;
  border-radius: 50%;
  animation: button-spin 700ms linear infinite;
}

.privacy-note {
  position: relative;
  z-index: 1;
  margin: 17px 0 0;
  color: rgba(56, 76, 67, 0.42);
  font-size: 10px;
  letter-spacing: 0.06em;
  text-align: center;
}

.login-card-enter-active {
  transition:
    opacity 1s ease,
    transform 1.15s cubic-bezier(0.2, 0.8, 0.2, 1),
    filter 1s ease;
}

.login-card-leave-active {
  pointer-events: none;
  transition:
    opacity 0.65s ease,
    transform 0.75s cubic-bezier(0.4, 0, 0.2, 1),
    filter 0.65s ease;
}

.login-card-enter-from {
  opacity: 0;
  filter: blur(8px);
  transform: translate(48px, calc(-50% + 16px)) scale(0.96);
}

.login-card-leave-to {
  opacity: 0;
  filter: blur(8px);
  transform: translate(42px, -50%) scale(0.97);
}

@keyframes button-spin {
  to {
    transform: rotate(360deg);
  }
}

.application-edge-tab {
  position: absolute;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 158px;
  min-height: 48px;
  padding: 10px 45px 10px 29px;
  border: 1px solid rgba(111, 83, 49, 0.38);
  border-left-color: rgba(111, 83, 49, 0.2);
  background:
    linear-gradient(138deg, rgba(255, 247, 218, 0.72), rgba(218, 192, 137, 0.26)),
    #ead7a6;
  box-shadow: inset 0 1px rgba(255, 252, 232, 0.74);
  clip-path: polygon(0 8%, 91% 3%, 100% 18%, 97% 37%, 100% 57%, 96% 95%, 4% 91%, 0 79%, 2% 58%, 0 39%);
  filter: drop-shadow(0 10px 10px rgba(60, 47, 30, 0.19));
  color: #59442d;
  font-family: 'Kaiti SC', 'STKaiti', 'Songti SC', serif;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.1em;
  cursor: pointer;
  transform: translateY(-50%) rotate(-1.8deg);
  transform-origin: left center;
  transition:
    color 180ms ease,
    border-color 180ms ease,
    background 220ms ease,
    filter 220ms ease,
    transform 260ms cubic-bezier(0.22, 1, 0.36, 1);
}

.application-edge-tab::before {
  position: absolute;
  top: 10px;
  right: 43px;
  left: 26px;
  border-top: 1px dashed rgba(122, 91, 50, 0.3);
  content: '';
}

.application-edge-tab:not(:disabled):hover {
  border-color: rgba(122, 86, 47, 0.55);
  background:
    linear-gradient(138deg, rgba(255, 250, 225, 0.88), rgba(226, 199, 143, 0.3)),
    #f0dfb2;
  filter: drop-shadow(0 15px 14px rgba(64, 49, 30, 0.28));
  color: #4f3a25;
  transform: translate(13px, calc(-50% - 3px)) rotate(-0.5deg) scale(1.035);
}

.application-edge-tab:not(:disabled):active {
  transform: translate(9px, calc(-50% - 1px)) rotate(-0.5deg) scale(0.99);
}

.application-edge-tab:disabled {
  cursor: wait;
  opacity: 0.78;
}

.application-edge-tab:focus-visible {
  filter:
    drop-shadow(0 0 2px rgba(255, 244, 207, 1))
    drop-shadow(0 0 7px rgba(101, 119, 96, 0.9));
}

.application-tab-sprig {
  position: absolute;
  top: 9px;
  left: 10px;
  width: 15px;
  height: 30px;
  transform: rotate(-16deg);
  transition: transform 300ms cubic-bezier(0.22, 1, 0.36, 1);
}

.application-tab-sprig::before {
  position: absolute;
  top: 2px;
  bottom: 1px;
  left: 7px;
  width: 2px;
  border-radius: 2px;
  background: #72806a;
  content: '';
  transform: rotate(8deg);
}

.application-tab-sprig i {
  position: absolute;
  width: 10px;
  height: 5px;
  border-radius: 70% 30% 65% 35%;
  background: #87927a;
}

.application-tab-sprig i:nth-child(1) {
  top: 5px;
  left: 0;
  transform: rotate(-34deg);
}

.application-tab-sprig i:nth-child(2) {
  top: 13px;
  left: 7px;
  transform: rotate(28deg);
}

.application-tab-sprig i:nth-child(3) {
  top: 22px;
  left: 0;
  transform: rotate(-28deg);
}

.application-edge-tab:not(:disabled):hover .application-tab-sprig {
  transform: rotate(-7deg) translateY(-2px);
}

.application-tab-seal {
  position: absolute;
  top: 50%;
  right: 9px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #a4664d;
  box-shadow:
    0 3px 7px rgba(81, 42, 32, 0.22),
    inset 0 0 0 3px rgba(107, 54, 40, 0.56),
    inset 0 0 0 5px rgba(236, 194, 149, 0.15);
  transform: translateY(-50%) rotate(-8deg);
  transition: transform 280ms cubic-bezier(0.22, 1, 0.36, 1);
}

.application-tab-seal i,
.application-tab-seal i::after {
  position: absolute;
  width: 10px;
  height: 5px;
  border-radius: 70% 30% 65% 35%;
  background: #f0d6aa;
  content: '';
}

.application-tab-seal i {
  top: 15px;
  left: 8px;
  transform: rotate(-34deg);
}

.application-tab-seal i::after {
  top: -6px;
  left: 8px;
  transform: rotate(12deg);
}

.application-edge-tab:not(:disabled):hover .application-tab-seal {
  transform: translateY(-50%) rotate(5deg) scale(1.08);
}

.application-tab-enter-active,
.application-tab-leave-active {
  transition:
    opacity 260ms ease,
    filter 260ms ease,
    transform 340ms cubic-bezier(0.22, 1, 0.36, 1);
}

.application-tab-enter-from,
.application-tab-leave-to {
  opacity: 0;
  filter: blur(3px);
  transform: translate(-22px, -50%) rotate(-4deg) scale(0.92);
}

.venue-floating-selector {
  position: absolute;
  inset: 0;
  z-index: 4;
  pointer-events: none;
}

.venue-float-button {
  --venue-rotation: 0deg;
  --venue-shift-x: 0%;
  position: absolute;
  display: flex;
  align-items: center;
  min-width: 142px;
  min-height: 39px;
  max-width: 188px;
  gap: 8px;
  padding: 8px 13px 8px 11px;
  border: 1px solid rgba(91, 113, 88, 0.42);
  border-radius: 15px 5px 5px 15px;
  background:
    linear-gradient(138deg, rgba(255, 253, 242, 0.94), rgba(225, 216, 191, 0.88)),
    #eee4ca;
  box-shadow:
    0 9px 22px rgba(60, 55, 39, 0.15),
    inset 0 1px rgba(255, 255, 255, 0.75);
  color: #4f5f4f;
  font-family: 'Songti SC', 'STSong', serif;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.25;
  text-align: left;
  cursor: pointer;
  pointer-events: auto;
  backdrop-filter: blur(8px);
  transform: translate(var(--venue-shift-x), -50%) rotate(var(--venue-rotation));
  transition:
    color 180ms ease,
    border-color 180ms ease,
    background 220ms ease,
    box-shadow 220ms ease,
    transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
  animation: venue-button-pop 520ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.venue-float-button:hover {
  border-color: rgba(71, 102, 78, 0.7);
  box-shadow:
    0 13px 28px rgba(60, 55, 39, 0.2),
    inset 0 1px rgba(255, 255, 255, 0.78);
  transform: translate(var(--venue-shift-x), calc(-50% - 3px)) rotate(var(--venue-rotation)) scale(1.035);
}

.venue-float-button.active {
  border-color: rgba(52, 86, 67, 0.78);
  background:
    linear-gradient(138deg, rgba(255, 255, 255, 0.08), transparent 55%),
    #536f5c;
  box-shadow:
    0 12px 28px rgba(44, 72, 56, 0.25),
    inset 0 1px rgba(255, 255, 255, 0.18);
  color: #fbf3df;
}

.venue-button-mark {
  flex: 0 0 auto;
  width: 7px;
  height: 7px;
  border: 1px solid currentColor;
  border-radius: 70% 30% 65% 35%;
  background: rgba(88, 116, 91, 0.18);
  transform: rotate(28deg);
}

.venue-float-button.active .venue-button-mark {
  background: #e6d29f;
}

.venue-float-button:nth-child(odd) {
  --venue-shift-x: -100%;
  flex-direction: row-reverse;
  justify-content: flex-start;
  border-radius: 15px 4px 4px 15px;
  text-align: right;
}

.venue-float-button:nth-child(even) {
  --venue-shift-x: 0%;
  border-radius: 4px 15px 15px 4px;
}

.venue-float-button:nth-child(1) {
  --venue-rotation: -2deg;
}

.venue-float-button:nth-child(2) {
  --venue-rotation: 2deg;
}

.venue-float-button:nth-child(3) {
  --venue-rotation: 1.5deg;
}

.venue-float-button:nth-child(4) {
  --venue-rotation: -2.5deg;
}

.venue-float-button:nth-child(5) {
  --venue-rotation: -1deg;
}

.venue-float-button:nth-child(6) {
  --venue-rotation: 2deg;
}

.venue-float-button:nth-child(7) {
  --venue-rotation: 2.5deg;
}

.venue-float-button:nth-child(8) {
  --venue-rotation: -1.5deg;
}

.venue-float-button:nth-child(9) {
  --venue-rotation: -2deg;
}

.venue-selector-enter-active,
.venue-selector-leave-active {
  transition: opacity 320ms ease;
}

.venue-selector-enter-from,
.venue-selector-leave-to {
  opacity: 0;
}

@keyframes venue-button-pop {
  from {
    opacity: 0;
    filter: blur(5px);
    transform: translate(var(--venue-shift-x), -35%) rotate(var(--venue-rotation)) scale(0.82);
  }
}

.page-turn-button {
  position: absolute;
  bottom: 24px;
  left: 38%;
  z-index: 3;
  min-width: 132px;
  padding: 10px 18px;
  border: 1px solid rgba(111, 87, 48, 0.25);
  border-radius: 3px 14px 3px 14px;
  background: rgba(239, 220, 172, 0.86);
  box-shadow:
    0 12px 30px rgba(74, 57, 32, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.62);
  color: #5d4a2d;
  font-family: 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  backdrop-filter: blur(10px);
  transform: translateX(-50%);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    opacity 180ms ease;
}

.page-turn-button:hover:not(:disabled) {
  box-shadow:
    0 15px 34px rgba(74, 57, 32, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
  transform: translateX(-50%) translateY(-2px);
}

.page-turn-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

@media (max-width: 859px) {
  .login-card {
    top: auto;
    right: 50%;
    bottom: 22px;
    width: min(420px, calc(100vw - 32px));
    padding: 22px 23px 18px;
    transform: translateX(50%);
  }

  .card-heading {
    margin: 12px 0 18px;
  }

  .card-heading h1 {
    font-size: 25px;
  }

  .login-form {
    gap: 12px;
  }

  .input-shell {
    min-height: 45px;
  }

  .login-card-enter-from {
    transform: translate(50%, 32px) scale(0.97);
  }

  .page-turn-button {
    top: 18px;
    bottom: auto;
    left: 50%;
  }

  .venue-floating-selector {
    top: auto;
    right: 12px;
    bottom: 12px;
    left: 12px;
    display: flex;
    gap: 8px;
    padding: 7px;
    overflow-x: auto;
    border: 1px solid rgba(255, 255, 255, 0.34);
    border-radius: 16px 5px 16px 5px;
    background: rgba(238, 228, 202, 0.76);
    backdrop-filter: blur(12px);
    scrollbar-width: none;
  }

  .venue-floating-selector::-webkit-scrollbar {
    display: none;
  }

  .venue-float-button,
  .venue-float-button:nth-child(n) {
    position: static;
    flex: 0 0 auto;
    max-width: none;
    white-space: nowrap;
    transform: none;
  }

  .venue-float-button:hover {
    transform: translateY(-2px);
  }
}

@media (max-width: 520px) {
  .login-card.register-card {
    width: calc(100vw - 24px);
    max-height: calc(100vh - 20px);
    padding: 18px 18px 16px;
  }

  .register-grid {
    grid-template-columns: 1fr;
  }

  .register-grid .form-field {
    grid-column: 1;
  }

  .verification-control,
  .captcha-control {
    grid-template-columns: minmax(0, 1fr) 118px;
  }

  .captcha-button img {
    width: 75px;
  }
}

@media (max-height: 690px) and (max-width: 859px) {
  .login-card {
    bottom: 10px;
    padding-block: 17px 14px;
  }

  .card-ornament,
  .privacy-note {
    display: none;
  }

  .card-heading {
    margin-top: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-card-enter-active,
  .login-card-leave-active,
  .login-button,
  .page-turn-button,
  .input-shell {
    transition-duration: 1ms;
  }

  .auth-form-stage,
  .auth-form-enter-active,
  .auth-form-leave-active,
  .auth-heading-enter-active,
  .auth-heading-leave-active {
    transition-duration: 1ms;
  }

  .venue-float-button {
    animation-duration: 1ms;
    transition-duration: 1ms;
  }
}
</style>
