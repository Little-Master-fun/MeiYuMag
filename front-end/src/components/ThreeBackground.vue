<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'

const canvasRef = ref<HTMLCanvasElement | null>(null)

let animFrame: number
let renderer: THREE.WebGLRenderer
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let particlesMesh: THREE.Points
let linesMesh: THREE.LineSegments
const mouse = { x: 0, y: 0 }

const PARTICLE_COUNT = 220
const CONNECTION_DIST = 90
const SPREAD = 400

function init(canvas: HTMLCanvasElement) {
  const w = canvas.offsetWidth
  const h = canvas.offsetHeight

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(w, h)
  renderer.setClearColor(0x000000, 0)

  scene = new THREE.Scene()

  camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 1000)
  camera.position.z = 280

  // ── Particles ──
  const positions = new Float32Array(PARTICLE_COUNT * 3)
  const colors    = new Float32Array(PARTICLE_COUNT * 3)
  const sizes     = new Float32Array(PARTICLE_COUNT)
  const velocities: { x: number; y: number; z: number; phase: number }[] = []

  const teal = new THREE.Color('#3DD9AC')
  const gold = new THREE.Color('#F7CA75')
  const mid  = new THREE.Color('#5DB8C8')

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    positions[i * 3]     = (Math.random() - 0.5) * SPREAD
    positions[i * 3 + 1] = (Math.random() - 0.5) * SPREAD * 0.7
    positions[i * 3 + 2] = (Math.random() - 0.5) * 80

    const t = Math.random()
    const c = t < 0.5 ? teal.clone().lerp(mid, t * 2) : mid.clone().lerp(gold, (t - 0.5) * 2)
    colors[i * 3]     = c.r
    colors[i * 3 + 1] = c.g
    colors[i * 3 + 2] = c.b

    sizes[i] = Math.random() * 2.5 + 0.8

    velocities.push({
      x: (Math.random() - 0.5) * 0.14,
      y: (Math.random() - 0.5) * 0.1,
      z: 0,
      phase: Math.random() * Math.PI * 2,
    })
  }

  const pGeo = new THREE.BufferGeometry()
  pGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  pGeo.setAttribute('color',    new THREE.BufferAttribute(colors, 3))
  pGeo.setAttribute('size',     new THREE.BufferAttribute(sizes, 1))

  const pMat = new THREE.PointsMaterial({
    size: 2.4,
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    sizeAttenuation: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })

  particlesMesh = new THREE.Points(pGeo, pMat)
  scene.add(particlesMesh)

  // ── Lines ──
  const maxLines = PARTICLE_COUNT * 6
  const linePositions = new Float32Array(maxLines * 2 * 3)
  const lineColors    = new Float32Array(maxLines * 2 * 3)

  const lGeo = new THREE.BufferGeometry()
  lGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3).setUsage(THREE.DynamicDrawUsage))
  lGeo.setAttribute('color',    new THREE.BufferAttribute(lineColors,    3).setUsage(THREE.DynamicDrawUsage))

  const lMat = new THREE.LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.4,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })

  linesMesh = new THREE.LineSegments(lGeo, lMat)
  scene.add(linesMesh)

  // ── Animation Loop ──
  let t = 0
  function tick() {
    t += 0.004
    animFrame = requestAnimationFrame(tick)

    const pos = pGeo.attributes.position.array as Float32Array
    const half = SPREAD / 2

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const v = velocities[i]
      pos[i * 3]     += v.x
      pos[i * 3 + 1] += v.y + Math.sin(t + v.phase) * 0.04

      // Wrap boundaries
      if (pos[i * 3] >  half) pos[i * 3] = -half
      if (pos[i * 3] < -half) pos[i * 3] =  half
      if (pos[i * 3 + 1] >  SPREAD * 0.35) pos[i * 3 + 1] = -SPREAD * 0.35
      if (pos[i * 3 + 1] < -SPREAD * 0.35) pos[i * 3 + 1] =  SPREAD * 0.35

      // Mouse attraction (subtle)
      const mx = mouse.x * (SPREAD / 2)
      const my = mouse.y * (SPREAD * 0.35)
      const dx = mx - pos[i * 3]
      const dy = my - pos[i * 3 + 1]
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 120) {
        pos[i * 3]     += (dx / dist) * 0.08
        pos[i * 3 + 1] += (dy / dist) * 0.06
      }
    }
    pGeo.attributes.position.needsUpdate = true

    // Update connections
    const lPos = lGeo.attributes.position.array as Float32Array
    const lCol = lGeo.attributes.color.array as Float32Array
    let lineIdx = 0

    for (let a = 0; a < PARTICLE_COUNT; a++) {
      for (let b = a + 1; b < PARTICLE_COUNT; b++) {
        const dx = pos[a * 3] - pos[b * 3]
        const dy = pos[a * 3 + 1] - pos[b * 3 + 1]
        const dz = pos[a * 3 + 2] - pos[b * 3 + 2]
        const d  = Math.sqrt(dx * dx + dy * dy + dz * dz)
        if (d < CONNECTION_DIST && lineIdx < maxLines) {
          const alpha = (1 - d / CONNECTION_DIST)
          const ca = colors[a * 3], cb = colors[b * 3]
          const cr = (ca + cb) / 2
          const cg = (colors[a * 3 + 1] + colors[b * 3 + 1]) / 2
          const cb2 = (colors[a * 3 + 2] + colors[b * 3 + 2]) / 2

          lPos[lineIdx * 6]     = pos[a * 3];     lPos[lineIdx * 6 + 1] = pos[a * 3 + 1]; lPos[lineIdx * 6 + 2] = pos[a * 3 + 2]
          lPos[lineIdx * 6 + 3] = pos[b * 3];     lPos[lineIdx * 6 + 4] = pos[b * 3 + 1]; lPos[lineIdx * 6 + 5] = pos[b * 3 + 2]

          lCol[lineIdx * 6]     = cr * alpha; lCol[lineIdx * 6 + 1] = cg * alpha; lCol[lineIdx * 6 + 2] = cb2 * alpha
          lCol[lineIdx * 6 + 3] = cr * alpha; lCol[lineIdx * 6 + 4] = cg * alpha; lCol[lineIdx * 6 + 5] = cb2 * alpha

          lineIdx++
        }
      }
    }

    lGeo.setDrawRange(0, lineIdx * 2)
    lGeo.attributes.position.needsUpdate = true
    lGeo.attributes.color.needsUpdate    = true

    // Slow camera rotation
    camera.position.x = Math.sin(t * 0.12) * 18
    camera.position.y = Math.cos(t * 0.09) * 10
    camera.lookAt(0, 0, 0)

    renderer.render(scene, camera)
  }
  tick()
}

function onResize() {
  const canvas = canvasRef.value
  if (!canvas || !renderer) return
  const w = canvas.offsetWidth
  const h = canvas.offsetHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

function onMouseMove(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  mouse.x = ((e.clientX - rect.left) / rect.width  - 0.5) * 2
  mouse.y = -((e.clientY - rect.top)  / rect.height - 0.5) * 2
}

onMounted(() => {
  if (!canvasRef.value) return
  init(canvasRef.value)
  window.addEventListener('resize', onResize)
  window.addEventListener('mousemove', onMouseMove)
})

onUnmounted(() => {
  cancelAnimationFrame(animFrame)
  renderer?.dispose()
  window.removeEventListener('resize', onResize)
  window.removeEventListener('mousemove', onMouseMove)
})
</script>

<template>
  <canvas ref="canvasRef" class="w-full h-full" />
</template>
