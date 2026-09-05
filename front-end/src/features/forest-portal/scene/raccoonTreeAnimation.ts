import * as THREE from 'three'

export interface PushedTreeSettings {
  enabled: boolean
  treeAmplitude: number
  directionalLean: number
  speed: number
  raccoonAmplitude: number
  raccoonLean: number
  raccoonTravel: number
}

export interface RaccoonTreeAnimationController {
  update: (elapsed: number) => void
  reset: () => void
}

export function createRaccoonTreeAnimation(
  root: THREE.Object3D,
  settings: PushedTreeSettings,
): RaccoonTreeAnimationController | null {
  const tree = root.getObjectByName('BTree002')
  const bird = root.getObjectByName('Bird')
  const raccoon = root.getObjectByName('Racoon')
  const parent = tree?.parent
  const raccoonParent = raccoon?.parent
  if (!tree || !bird || !raccoon || !parent || !raccoonParent) {
    console.warn('[浣熊推树动画] 未找到 BTree002、Bird 或 Racoon 节点')
    return null
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

  const pushDirectionWorld = treeBaseWorld.clone().sub(raccoonCenterWorld)
  pushDirectionWorld.y = 0
  if (pushDirectionWorld.lengthSq() < 1e-8) pushDirectionWorld.set(0, 0, -1)
  pushDirectionWorld.normalize()
  const swayAxisWorld = new THREE.Vector3(0, 1, 0)
    .cross(pushDirectionWorld)
    .normalize()
  const parentWorldQuaternion = parent.getWorldQuaternion(new THREE.Quaternion())
  const swayAxis = swayAxisWorld
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

  const raccoonParentWorldQuaternion = raccoonParent.getWorldQuaternion(
    new THREE.Quaternion(),
  )
  const raccoonLeanAxis = swayAxisWorld
    .clone()
    .applyQuaternion(raccoonParentWorldQuaternion.invert())
    .normalize()
  const raccoonPivot = new THREE.Group()
  raccoonPivot.name = 'Raccoon_Push_Pivot'
  raccoonParent.add(raccoonPivot)
  raccoonPivot.position.copy(raccoonParent.worldToLocal(raccoonBaseWorld.clone()))
  const raccoonBasePosition = raccoonPivot.position.clone()
  const raccoonPushOffset = raccoonParent
    .worldToLocal(
      raccoonBaseWorld
        .clone()
        .addScaledVector(pushDirectionWorld, raccoonHeightWorld * 0.12),
    )
    .sub(raccoonBasePosition)
  const raccoonBobOffset = raccoonParent
    .worldToLocal(
      raccoonBaseWorld.clone().add(new THREE.Vector3(0, -raccoonHeightWorld * 0.035, 0)),
    )
    .sub(raccoonBasePosition)
  raccoonPivot.updateWorldMatrix(true, false)
  raccoonPivot.attach(raccoon)

  const baseQuaternion = pivot.quaternion.clone()
  const swayQuaternion = new THREE.Quaternion()
  const raccoonBaseQuaternion = raccoonPivot.quaternion.clone()
  const raccoonLeanQuaternion = new THREE.Quaternion()

  function reset() {
    pivot.quaternion.copy(baseQuaternion)
    raccoonPivot.position.copy(raccoonBasePosition)
    raccoonPivot.quaternion.copy(raccoonBaseQuaternion)
  }

  function update(elapsed: number) {
    if (!settings.enabled) {
      reset()
      return
    }

    const phase = elapsed * Math.PI * 2 * settings.speed
    const rawPush = (Math.sin(phase) + 1) * 0.5
    const pushAmount = rawPush * rawPush * (3 - 2 * rawPush)
    const treePhase = phase - 0.32
    const primaryWave = Math.sin(treePhase) * settings.treeAmplitude
    const secondaryWave = Math.sin(treePhase * 2 + 0.65) * settings.treeAmplitude * 0.12
    const angle = THREE.MathUtils.degToRad(
      settings.directionalLean + primaryWave + secondaryWave,
    )
    swayQuaternion.setFromAxisAngle(swayAxis, angle)
    pivot.quaternion.copy(baseQuaternion).multiply(swayQuaternion)

    const raccoonMotionAmount = pushAmount * settings.raccoonAmplitude
    const secondaryBob =
      Math.max(0, Math.sin(phase * 2)) * 0.08 * settings.raccoonAmplitude
    raccoonPivot.position
      .copy(raccoonBasePosition)
      .addScaledVector(
        raccoonPushOffset,
        raccoonMotionAmount * settings.raccoonTravel,
      )
      .addScaledVector(raccoonBobOffset, raccoonMotionAmount + secondaryBob)
    raccoonLeanQuaternion.setFromAxisAngle(
      raccoonLeanAxis,
      THREE.MathUtils.degToRad(raccoonMotionAmount * settings.raccoonLean),
    )
    raccoonPivot.quaternion.copy(raccoonBaseQuaternion).multiply(raccoonLeanQuaternion)
  }

  return { reset, update }
}
