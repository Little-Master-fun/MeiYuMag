import * as THREE from 'three'
import treeWindVertexChunk from './vertex.glsl?raw'

export interface WindShaderUniforms {
  time: { value: number }
  phase: { value: number }
  strength: { value: number }
  minZ: { value: number }
  height: { value: number }
}

interface TreeWindOptions {
  bounds: THREE.Box3
  phase?: number
  strength?: number
}

const windUniformDeclarations = `
  uniform float uWindTime;
  uniform float uWindPhase;
  uniform float uWindStrength;
  uniform float uWindMinZ;
  uniform float uWindHeight;
`

export function enableTreeCrownWind(
  mesh: THREE.Mesh,
  windShaders: WindShaderUniforms[],
  { bounds, phase = 0, strength = 0.18 }: TreeWindOptions,
) {
  const applyWind = (sourceMaterial: THREE.Material) => {
    const material = sourceMaterial.clone()

    material.onBeforeCompile = (shader) => {
      const uniforms: WindShaderUniforms = {
        time: { value: 0 },
        phase: { value: phase },
        strength: { value: strength },
        minZ: { value: bounds.min.z },
        height: { value: Math.max(bounds.max.z - bounds.min.z, 0.001) },
      }

      shader.uniforms.uWindTime = uniforms.time
      shader.uniforms.uWindPhase = uniforms.phase
      shader.uniforms.uWindStrength = uniforms.strength
      shader.uniforms.uWindMinZ = uniforms.minZ
      shader.uniforms.uWindHeight = uniforms.height
      shader.vertexShader = windUniformDeclarations + shader.vertexShader
      shader.vertexShader = shader.vertexShader.replace(
        '#include <begin_vertex>',
        treeWindVertexChunk,
      )
      windShaders.push(uniforms)
    }

    material.customProgramCacheKey = () => 'tree-crown-wind-v1'
    material.needsUpdate = true
    return material
  }

  if (Array.isArray(mesh.material)) mesh.material = mesh.material.map(applyWind)
  else mesh.material = applyWind(mesh.material)
}
