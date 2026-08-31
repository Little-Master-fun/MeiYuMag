import * as THREE from 'three'

export interface PageContentBounds {
  minX: number
  minY: number
  width: number
  height: number
}

const pageContentVertexDeclarations = `
  varying vec3 vPageContentPosition;
`

const pageContentFragmentDeclarations = `
  uniform sampler2D uPageContentTexture;
  uniform vec4 uPageContentBounds;
  varying vec3 vPageContentPosition;
`

const pageContentFragmentChunk = `
  vec2 pageContentUv = vec2(
    (vPageContentPosition.x - uPageContentBounds.x) / uPageContentBounds.z,
    1.0 - (vPageContentPosition.y - uPageContentBounds.y) / uPageContentBounds.w
  );
  float pageContentInside = step(0.0, pageContentUv.x)
    * step(pageContentUv.x, 1.0)
    * step(0.0, pageContentUv.y)
    * step(pageContentUv.y, 1.0);
  vec4 pageContentSample = texture2D(uPageContentTexture, pageContentUv);
  diffuseColor.rgb = mix(
    diffuseColor.rgb,
    pageContentSample.rgb,
    pageContentSample.a * pageContentInside
  );
`

function getMaterialBounds(mesh: THREE.Mesh, materialIndex: number): PageContentBounds | null {
  const geometry = mesh.geometry
  const position = geometry.getAttribute('position')
  if (!position) return null

  const relevantGroups = geometry.groups.filter((group) => group.materialIndex === materialIndex)
  const groups = relevantGroups.length
    ? relevantGroups
    : [{ start: 0, count: geometry.index?.count ?? position.count, materialIndex }]
  const vertexIndices = new Set<number>()
  for (const group of groups) {
    for (let offset = group.start; offset < group.start + group.count; offset += 1) {
      vertexIndices.add(geometry.index ? geometry.index.getX(offset) : offset)
    }
  }

  const bounds = new THREE.Box3()
  const vertex = new THREE.Vector3()
  for (const vertexIndex of vertexIndices) {
    vertex.fromBufferAttribute(position, vertexIndex)
    bounds.expandByPoint(vertex)
  }
  if (bounds.isEmpty()) return null

  return {
    minX: bounds.min.x,
    minY: bounds.min.y,
    width: Math.max(bounds.max.x - bounds.min.x, 0.001),
    height: Math.max(bounds.max.y - bounds.min.y, 0.001),
  }
}

export function projectPageContentOntoMaterial(
  mesh: THREE.Mesh,
  materialName: string,
  texture: THREE.CanvasTexture,
): PageContentBounds | null {
  const sourceMaterials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
  const materialIndex = sourceMaterials.findIndex((material) => material.name === materialName)
  if (materialIndex < 0) return null

  const bounds = getMaterialBounds(mesh, materialIndex)
  const sourceMaterial = sourceMaterials[materialIndex]
  if (!bounds || !(sourceMaterial instanceof THREE.MeshStandardMaterial)) return null

  const material = sourceMaterial.clone()
  // The source OBJ contains paper folds extremely close to the board surface.
  // Pull only the paper depth slightly forward, without moving its geometry,
  // so close camera views cannot alternate between parchment and wood pixels.
  material.depthTest = true
  material.depthWrite = true
  material.polygonOffset = true
  material.polygonOffsetFactor = -1
  material.polygonOffsetUnits = -4
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uPageContentTexture = { value: texture }
    shader.uniforms.uPageContentBounds = {
      value: new THREE.Vector4(bounds.minX, bounds.minY, bounds.width, bounds.height),
    }
    shader.vertexShader = pageContentVertexDeclarations + shader.vertexShader
    shader.vertexShader = shader.vertexShader.replace(
      '#include <begin_vertex>',
      '#include <begin_vertex>\nvPageContentPosition = position;',
    )
    shader.fragmentShader = pageContentFragmentDeclarations + shader.fragmentShader
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <map_fragment>',
      `#include <map_fragment>\n${pageContentFragmentChunk}`,
    )
  }
  material.customProgramCacheKey = () => 'projected-page-content-v1'
  material.needsUpdate = true

  const updatedMaterials = [...sourceMaterials]
  updatedMaterials[materialIndex] = material
  mesh.material = Array.isArray(mesh.material) ? updatedMaterials : material
  mesh.renderOrder = Math.max(mesh.renderOrder, 1)
  return bounds
}
