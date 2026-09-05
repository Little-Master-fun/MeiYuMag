import * as THREE from 'three'

export function fixCutoutMaterial(material: THREE.Material) {
  if (!/^(GrassALPHA|TreeLeafs|Plane)$/.test(material.name)) return
  material.transparent = false
  material.alphaTest = 0.42
  material.depthTest = true
  material.depthWrite = true
  material.side = THREE.DoubleSide
  material.alphaToCoverage = true
  material.needsUpdate = true
}

export function fixMailboxMaterial(material: THREE.Material) {
  // Most of the mailbox texture is opaque. Keeping the whole mesh in the
  // transparent render pass lets rear geometry show through its wood panels.
  material.transparent = false
  material.opacity = 1
  material.alphaTest = 0.42
  material.depthTest = true
  material.depthWrite = true
  material.side = THREE.DoubleSide
  material.alphaToCoverage = true
  material.needsUpdate = true
}

export function prepareMailboxModel(source: THREE.Object3D) {
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

export function disposeMaterial(material: THREE.Material) {
  for (const value of Object.values(material)) {
    if (value instanceof THREE.Texture) value.dispose()
  }
  material.dispose()
}
