import * as THREE from 'three'
import pageTurnNormalChunk from './normal.glsl?raw'
import pageTurnVertexChunk from './vertex.glsl?raw'

export interface PageTurnShaderUniforms {
  time: { value: number }
  bend: { value: number }
  curl: { value: number }
  flutter: { value: number }
  width: { value: number }
  height: { value: number }
}

const pageTurnShaderDeclarations = `
  uniform float uPageTime;
  uniform float uPageBend;
  uniform float uPageCurl;
  uniform float uPageFlutter;
  uniform float uPageWidth;
  uniform float uPageHeight;

  float pageDeformOffset(vec3 pagePosition) {
    float pageWeight = clamp(-pagePosition.y / uPageHeight, 0.0, 1.0);
    float hingeWeight = smoothstep(0.015, 0.18, pageWeight);
    float horizontalPhase = pagePosition.x / uPageWidth * 6.28318530718;
    float broadBend = sin(pageWeight * 2.72) * uPageBend;
    float bottomCurl = pow(pageWeight, 2.35) * uPageCurl;
    float sideRipple = (
      sin(horizontalPhase + uPageTime * 7.0 + pageWeight * 2.2) * 0.5 + 0.5
    ) * pow(pageWeight, 1.35) * uPageFlutter;
    float fallingRipple = sin(
      pageWeight * 9.0 - uPageTime * 4.0
    ) * pageWeight * uPageFlutter * 0.35;
    return hingeWeight * (broadBend + bottomCurl + sideRipple + fallingRipple);
  }
`

export function enablePageTurnDeformation(
  mesh: THREE.Mesh,
  bounds: THREE.Box3,
): PageTurnShaderUniforms {
  const size = bounds.getSize(new THREE.Vector3())
  const uniforms: PageTurnShaderUniforms = {
    time: { value: 0 },
    bend: { value: 0 },
    curl: { value: 0 },
    flutter: { value: 0 },
    width: { value: Math.max(size.x, 0.001) },
    height: { value: Math.max(size.y, 0.001) },
  }

  const applyDeformation = (sourceMaterial: THREE.Material) => {
    const material = sourceMaterial.clone()
    material.side = THREE.DoubleSide
    // At rest the animated sheet is intentionally coincident with the page
    // underneath. A raster depth offset selects the top sheet without moving
    // it forward in 3D, so both pages read as one continuous object.
    material.polygonOffset = true
    material.polygonOffsetFactor = -1
    material.polygonOffsetUnits = -1
    material.onBeforeCompile = (shader) => {
      shader.uniforms.uPageTime = uniforms.time
      shader.uniforms.uPageBend = uniforms.bend
      shader.uniforms.uPageCurl = uniforms.curl
      shader.uniforms.uPageFlutter = uniforms.flutter
      shader.uniforms.uPageWidth = uniforms.width
      shader.uniforms.uPageHeight = uniforms.height
      shader.vertexShader = pageTurnShaderDeclarations + shader.vertexShader
      shader.vertexShader = shader.vertexShader.replace(
        '#include <beginnormal_vertex>',
        pageTurnNormalChunk,
      )
      shader.vertexShader = shader.vertexShader.replace(
        '#include <begin_vertex>',
        pageTurnVertexChunk,
      )
    }
    material.customProgramCacheKey = () => 'soft-page-turn-v1'
    material.needsUpdate = true
    return material
  }

  if (Array.isArray(mesh.material)) mesh.material = mesh.material.map(applyDeformation)
  else mesh.material = applyDeformation(mesh.material)

  // The animated vertices can leave the imported bounding volume, and the
  // standard shadow depth material would not contain our vertex deformation.
  mesh.frustumCulled = false
  mesh.castShadow = false
  return uniforms
}
