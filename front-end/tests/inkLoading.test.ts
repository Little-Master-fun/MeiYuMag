import test from 'node:test'
import assert from 'node:assert/strict'
import { advanceInkProgress, inkFinishDelay, inkRadius, inkSeeds, inkTarget } from '../src/features/forest-portal/inkLoading.ts'

test('loading cannot claim completion until the scene is assembled', () => {
  assert.equal(inkTarget(100, false), 94)
  assert.equal(inkTarget(5, true), 100)
  assert.equal(inkTarget(NaN, false), 0)
})
test('ink only expands, respects actual progress, and bounds resumed frames', () => {
  assert.equal(advanceInkProgress(50, 30, 32), 50)
  assert.equal(advanceInkProgress(50, 51, 32), 51)
  assert.ok(advanceInkProgress(0, 100, 100000) < 5)
  assert.equal(advanceInkProgress(30, 60, 16, true), 60)
  for (const [, , start] of inkSeeds) {
    assert.equal(inkRadius(start, start), 0)
    assert.ok(inkRadius(start + 10, start) > 0)
    assert.ok(inkRadius(100, start) >= inkRadius(60, start))
  }
})
test('fast loads stay at least two seconds, slow loads only pause briefly', () => {
  assert.equal(inkFinishDelay(0), 2000)
  assert.equal(inkFinishDelay(1200), 800)
  assert.equal(inkFinishDelay(6000), 300)
  assert.equal(inkFinishDelay(1500, true), 500)
  assert.equal(inkFinishDelay(6000, true), 0)
})
