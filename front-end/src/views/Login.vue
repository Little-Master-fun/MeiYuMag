<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
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
  type ParchmentPageCanvas,
  type VenueUsageBoard,
  type VenueUsageItem,
} from '@/assets/textures/parchmentPage'
import {
  enablePageTurnDeformation,
  type PageTurnShaderUniforms,
} from '@/assets/shaders/pageTurn'
import { projectPageContentOntoMaterial } from '@/assets/shaders/pageContent'
import { enableTreeCrownWind, type WindShaderUniforms } from '@/assets/shaders/treeWind'

const viewport = ref<HTMLDivElement | null>(null)
const venueSelector = ref<HTMLElement | null>(null)
const authFormStage = ref<HTMLDivElement | null>(null)
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
let resizeObserver: ResizeObserver | null = null
let animationFrame = 0
let smsCountdownTimer: ReturnType<typeof setInterval> | null = null
let topPage: THREE.Mesh | null = null
let paperSurfaceMesh: THREE.Mesh | null = null
let paperVisibleFacePoints: THREE.Vector3[] = []
let paperVisibleFaceZ = 0
let pageTurnShader: PageTurnShaderUniforms | null = null
let pageContentCanvas: ParchmentPageCanvas | null = null
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

const clipboardDebug = {
  x: -0.05,
  y: 0.086,
  z: 0.02,
  rotationX: 0,
  rotationY: 0,
  rotationZ: 0,
  scale: 0.01,
}

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

const postLoginMotionDebug = {
  overlapDuration: 1.2,
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
    controls.enabled = false
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

function applyPostLoginClipboardTransform() {
  Object.assign(clipboardDebug, postLoginClipboardDebug)
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

  const postLoginMotionFolder = debugGui.addFolder('登录后动画衔接')
  postLoginMotionFolder
    .add(postLoginMotionDebug, 'overlapDuration', 0, 1.2, 0.05)
    .name('重叠时间 秒')

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
  clipboardFolder.open()
  houseFolder.open()
  postLoginMotionFolder.open()
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
    controls.enabled = false
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
    controls.enabled = false
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
    controls.enabled = false
    controls.update()
    postLoginFlight = null
    cinematicActive.value = false
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
}

function isVisibleInScene(object: THREE.Object3D) {
  let current: THREE.Object3D | null = object
  while (current) {
    if (!current.visible) return false
    current = current.parent
  }
  return true
}

function isPointerOverPaper(clientX: number, clientY: number) {
  if (!renderer || !camera || !model || !pageContentCanvas) return false

  const bounds = renderer.domElement.getBoundingClientRect()
  if (!bounds.width || !bounds.height) return false
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
    return materials[materialIndex]?.name === 'Clean_Yellow_Parchment'
  }

  return false
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
  if (!renderer) return
  renderer.domElement.style.cursor = isPointerOverPaper(event.clientX, event.clientY)
    ? 'ns-resize'
    : ''
}

function handlePaperPointerLeave() {
  if (renderer) renderer.domElement.style.cursor = ''
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
  if (
    !venueSelector.value
    || !paperSurfaceMesh
    || !renderer
    || !camera
    || !venueSelectorReady.value
  ) return

  const selectorBounds = venueSelector.value.getBoundingClientRect()
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
  const tabClips = venueSelector.value.querySelectorAll<HTMLElement>('.venue-tab-clip')

  tabClips.forEach((tabClip, index) => {
    const isLeft = index % 2 === 0
    const sideIndex = Math.floor(index / 2)
    const verticalRatio = isLeft
      ? (leftSlots[sideIndex] ?? 0.5)
      : (rightSlots[sideIndex] ?? 0.5)

    // Each clip ends exactly at the projected paper edge. The button extends
    // 14px beneath it, but that part is clipped so the real 3D sheet remains
    // visible in front and creates a convincing foreground occlusion.
    tabClip.style.left = `${isLeft ? 0 : maxX}px`
    tabClip.style.width = `${isLeft ? minX : selectorBounds.width - maxX}px`
    tabClip.style.top = `${minY + paperHeight * verticalRatio}px`
  })
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
  const cameraIsMoving = updateCameraEntrance(now) || updatePostLoginCamera(now)
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
    void loadVenueUsageBoard()
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
  pageContentCanvas.updateUsageBoard(loadingBoard)

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

    pageContentCanvas.updateUsageBoard({
      mode,
      date: dateKey,
      rangeStart: data.start_date,
      rangeEnd: data.end_date,
      state: 'ready',
      venues: usageItems,
    })
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
    pageContentCanvas.updateUsageBoard({
      mode,
      date: dateKey,
      rangeStart,
      rangeEnd,
      state: 'error',
      venues: [],
      error: '请确认本地后端服务已启动',
    })
    venueOptions.value = []
    selectedVenueId.value = null
    venueSelectorReady.value = false
  }
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
    void loadVenueUsageBoard()
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

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.06
  controls.enabled = false
  controls.autoRotate = false
  controls.enableRotate = false
  controls.enablePan = false
  controls.enableZoom = false
  renderer.domElement.addEventListener('wheel', handlePaperWheel, {
    capture: true,
    passive: false,
  })
  renderer.domElement.addEventListener('pointermove', handlePaperPointerMove, { passive: true })
  renderer.domElement.addEventListener('pointerleave', handlePaperPointerLeave)

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

  Promise.all([loader.loadAsync(houseUrl), loader.loadAsync(clipboardUrl)])
    .then(([houseGltf, clipboardGltf]) => {
      if (!scene) return

      model = new THREE.Group()
      model.name = 'Login_Scene_Models'
      houseModel = houseGltf.scene
      houseModel.name = 'Forest_House'
      clipboardModel = clipboardGltf.scene
      clipboardModel.name = 'Wooden_Clipboard'
      applyClipboardTransform()
      model.add(houseModel, clipboardModel)

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
          projectPageContentOntoMaterial(
            child,
            'Clean_Yellow_Parchment',
            pageContentCanvas.texture,
          )
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
      loadError.value = '小屋或文件夹模型加载失败，请检查文件路径或浏览器 WebGL 支持。'
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
  pageTurnTimeline?.kill()
  resizeObserver?.disconnect()
  controls?.dispose()
  debugGui?.destroy()
  renderer?.domElement.removeEventListener('wheel', handlePaperWheel, true)
  renderer?.domElement.removeEventListener('pointermove', handlePaperPointerMove)
  renderer?.domElement.removeEventListener('pointerleave', handlePaperPointerLeave)

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
  topPage = null
  paperSurfaceMesh = null
  paperVisibleFacePoints = []
  paperVisibleFaceZ = 0
  pageTurnShader = null
  pageContentCanvas = null
  pageTurnTimeline = null
  pageTurnAvailable.value = false
  pageTurning.value = false
  pageTurnCompleted.value = false
  cameraFlight = null
  postLoginFlight = null
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

    <div v-if="!modelReady && !loadError" class="loading-panel">
      <div class="loading-track">
        <span :style="{ width: `${loadingProgress}%` }" />
      </div>
      <p>正在加载木质文件夹模型 {{ loadingProgress }}%</p>
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

    <Transition name="venue-selector">
      <nav
        v-if="venueSelectorReady && !cinematicActive"
        ref="venueSelector"
        class="venue-floating-selector"
        aria-label="选择要查看的场地"
      >
        <span
          v-for="(venue, index) in venueOptions"
          :key="venue.id"
          class="venue-tab-clip"
          :class="index % 2 === 0 ? 'left' : 'right'"
        >
          <button
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
        </span>
      </nav>
    </Transition>

    <button
      v-if="pageTurnEnabled && modelReady && pageTurnAvailable && !cinematicActive"
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

.venue-floating-selector {
  position: absolute;
  inset: 0;
  z-index: 4;
  pointer-events: none;
}

.venue-tab-clip {
  position: absolute;
  height: 88px;
  overflow: hidden;
  pointer-events: none;
  transform: translateY(-50%);
}

.venue-float-button {
  --venue-rotation: 0deg;
  position: absolute;
  top: 50%;
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
  transform: translateY(-50%) rotate(var(--venue-rotation));
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
  transform: translateY(calc(-50% - 3px)) rotate(var(--venue-rotation)) scale(1.035);
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

.venue-tab-clip.left .venue-float-button {
  right: -14px;
  flex-direction: row-reverse;
  justify-content: flex-start;
  border-radius: 15px 4px 4px 15px;
  text-align: right;
}

.venue-tab-clip.right .venue-float-button {
  left: -14px;
  border-radius: 4px 15px 15px 4px;
}

.venue-tab-clip:nth-child(1) .venue-float-button {
  --venue-rotation: -2deg;
}

.venue-tab-clip:nth-child(2) .venue-float-button {
  --venue-rotation: 2deg;
}

.venue-tab-clip:nth-child(3) .venue-float-button {
  --venue-rotation: 1.5deg;
}

.venue-tab-clip:nth-child(4) .venue-float-button {
  --venue-rotation: -2.5deg;
}

.venue-tab-clip:nth-child(5) .venue-float-button {
  --venue-rotation: -1deg;
}

.venue-tab-clip:nth-child(6) .venue-float-button {
  --venue-rotation: 2deg;
}

.venue-tab-clip:nth-child(7) .venue-float-button {
  --venue-rotation: 2.5deg;
}

.venue-tab-clip:nth-child(8) .venue-float-button {
  --venue-rotation: -1.5deg;
}

.venue-tab-clip:nth-child(9) .venue-float-button {
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
    transform: translateY(-35%) rotate(var(--venue-rotation)) scale(0.82);
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

  .venue-tab-clip,
  .venue-tab-clip:nth-child(n) {
    position: static;
    width: auto !important;
    height: auto;
    overflow: visible;
    transform: none;
  }

  .venue-float-button,
  .venue-tab-clip:nth-child(n) .venue-float-button {
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
