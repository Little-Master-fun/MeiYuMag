<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as THREE from 'three'
import { gsap } from 'gsap'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import GUI from 'three/addons/libs/lil-gui.module.min.js'
import { ArrowRight, Eye, EyeOff, LockKeyhole, Trees, UserRound } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import {
  createParchmentPageCanvas,
  type ParchmentPageCanvas,
} from '@/assets/textures/parchmentPage'
import {
  enablePageTurnDeformation,
  type PageTurnShaderUniforms,
} from '@/assets/shaders/pageTurn'
import { projectPageContentOntoMaterial } from '@/assets/shaders/pageContent'
import { enableTreeCrownWind, type WindShaderUniforms } from '@/assets/shaders/treeWind'

const viewport = ref<HTMLDivElement | null>(null)
const loadingProgress = ref(0)
const loadError = ref('')
const modelReady = ref(false)
const cinematicActive = ref(false)
const loginPanelVisible = ref(false)
const account = ref('')
const password = ref('')
const passwordVisible = ref(false)
const formError = ref('')
const loginSucceeded = ref(false)
const pageTurnAvailable = ref(false)
const pageTurning = ref(false)
const pageTurnCompleted = ref(false)
const pageTurnEnabled = false

const auth = useAuthStore()

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let model: THREE.Object3D | null = null
let houseModel: THREE.Object3D | null = null
let clipboardModel: THREE.Object3D | null = null
let resizeObserver: ResizeObserver | null = null
let animationFrame = 0
let topPage: THREE.Mesh | null = null
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

let cameraFlight: CameraFlight | null = null
let postLoginFlight: PostLoginFlight | null = null
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

  debugGui.add(cameraDebug, 'replay').name('重新播放运镜')
  positionFolder.close()
  endPositionFolder.close()
  motionFolder.close()
  clipboardFolder.open()
  houseFolder.open()
  postLoginMotionFolder.open()
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

function animate() {
  if (!renderer || !scene || !camera) return
  animationFrame = requestAnimationFrame(animate)

  const elapsed = performance.now() * 0.001
  for (const shader of windShaders) shader.time.value = elapsed
  if (pageTurnShader) pageTurnShader.time.value = elapsed
  pageContentCanvas?.tick()

  const now = performance.now()
  const cameraIsMoving = updateCameraEntrance(now) || updatePostLoginCamera(now)
  if (!cameraIsMoving) controls?.update()
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
    playPostLoginCamera()
    return
  }

  formError.value = auth.error || '登录失败，请检查账号和密码'
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
  controls.enablePan = true
  controls.mouseButtons.RIGHT = THREE.MOUSE.PAN
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
        'Holle world',
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

      clipboardModel.traverse((child) => {
        if (!(child instanceof THREE.Mesh)) return
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
  pageTurnShader = null
  pageContentCanvas = null
  pageTurnTimeline = null
  pageTurnAvailable.value = false
  pageTurning.value = false
  pageTurnCompleted.value = false
  cameraFlight = null
  postLoginFlight = null
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
      <section v-if="loginPanelVisible" class="login-card" aria-labelledby="login-title">
        <div class="card-ornament" aria-hidden="true">
          <span />
          <Trees :size="18" :stroke-width="1.6" />
          <span />
        </div>

        <header class="card-heading">
          <p>MEIYU SYSTEM</p>
          <h1 id="login-title">欢迎回来</h1>
          <span>登录美育活动管理系统</span>
        </header>

        <form class="login-form" @submit.prevent="handleLogin">
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

        <p class="privacy-note">使用已认证的邮箱或手机号登录</p>
      </section>
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

    <div v-if="modelReady && !cinematicActive" class="viewer-hint">
      左键旋转 · 右键平移 · 滚轮缩放
    </div>
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

.login-form {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 17px;
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

.viewer-hint {
  position: absolute;
  right: 18px;
  bottom: 18px;
  padding: 9px 13px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  background: rgba(7, 17, 13, 0.62);
  color: rgba(238, 255, 247, 0.58);
  font-size: 12px;
  letter-spacing: 0.04em;
  backdrop-filter: blur(12px);
  pointer-events: none;
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

  .viewer-hint {
    display: none;
  }

  .page-turn-button {
    top: 18px;
    bottom: auto;
    left: 50%;
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
}
</style>
