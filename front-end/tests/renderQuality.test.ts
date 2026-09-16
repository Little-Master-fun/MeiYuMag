import { test } from 'node:test'
import assert from 'node:assert/strict'
import { paperTextureScale, scenePixelRatio } from '../src/features/forest-portal/renderQuality.ts'

test('Retina paper uses double-resolution glyphs with a bounded backing store', () => {
  assert.equal(paperTextureScale(2, 4096), 2)
  assert.equal(paperTextureScale(3, 4096), 2)
  assert.equal(paperTextureScale(1, 4096), 1)
  assert(paperTextureScale(3, 2048) * 1400 <= 2048)
})

test('only settled folder reading raises screen resolution', () => {
  assert.equal(scenePixelRatio(1600, 1000, 2, false, false, 1.5), 1.25)
  assert.equal(scenePixelRatio(1600, 1000, 2, false, true, 1.5), 2)
  assert.equal(scenePixelRatio(390, 844, 3, true, false, 1.5), 1.25)
  assert.equal(scenePixelRatio(390, 844, 3, true, true, 1.5), 2)
  assert.equal(scenePixelRatio(1440, 900, 1, false, true, 1.5), 1)
  const largeRatio = scenePixelRatio(3840, 2160, 2, false, true, 1.5)
  assert(3840 * 2160 * largeRatio ** 2 <= 8_000_000 + 0.001)
})
