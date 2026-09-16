import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  calendarDays,
  isMobileViewport,
  mobileEnvelopeLayout,
  mobilePaperFraming,
  mobileReaderBounds,
} from '../src/features/forest-portal/mobileLayout.ts'

test('mobile layout includes landscape phones and preserves desktop above 1024px', () => {
  assert(isMobileViewport(390))
  assert(isMobileViewport(932))
  assert(isMobileViewport(1024))
  assert(!isMobileViewport(1025))
})
test('mobile paper uses the available width instead of shrinking for bookmark rails', () => {
  const bounds = { minX: 0.4, maxX: 2, minY: -1.2, maxY: 1.4 }
  for (const [width, height] of [
    [320, 568],
    [390, 844],
    [932, 430],
  ]) {
    const frame = mobilePaperFraming(width!, height!, bounds)
    const left = ((bounds.minX * frame.scale - frame.offsetX + 1) * width!) / 2
    const right = ((bounds.maxX * frame.scale - frame.offsetX + 1) * width!) / 2
    assert(left >= 18 - 0.001)
    assert(right <= width! - 18 + 0.001)
    assert(Math.abs(right - left - Math.min(width! - 36, 600)) < 0.001)
    assert(Math.abs((left + right) / 2 - width! / 2) < 0.001)
    const top = (1 - (bounds.maxY * frame.scale - frame.offsetY)) * height! / 2
    assert(top >= 76 - 0.001)
    const zoomed = mobilePaperFraming(width!, height!, bounds, 2, { x: 12, y: 20 })
    assert.equal(zoomed.scale, frame.scale * 2)
    assert(Math.abs(zoomed.offsetX - (frame.offsetX * 2 - 24 / width!)) < 0.001)
  }
})
test('native mobile reader stays within paper sides and visible viewport, including landscape', () => {
  for (const [width, height, paperBottom] of [[320, 568, 500], [390, 844, 690], [844, 390, 970]]) {
    const bounds = mobileReaderBounds(18, 76, width! - 18, paperBottom!, height!)
    assert(bounds.left > 18)
    assert(bounds.width > 240)
    assert(bounds.left + bounds.width < width! - 18)
    assert(bounds.top >= 106)
    assert(bounds.height > 150)
    assert(bounds.top + bounds.height <= height! - 19)
    assert(bounds.top + bounds.height <= paperBottom! - 19)
  }
})
test('calendar spans month boundaries and includes both endpoints', () => {
  const days = calendarDays('2026-08-23', '2026-09-22', [])
  assert.equal(days.length, 31)
  assert.equal(days[0]?.key, '2026-08-23')
  assert.equal(days.at(-1)?.key, '2026-09-22')
  assert.equal(days.find((day) => day.key === '2026-09-01')?.day, 1)
  assert.equal(calendarDays('invalid', '2026-09-22', []).length, 0)
  assert.equal(calendarDays('2026-09-22', '2026-09-01', []).length, 0)
})
test('overnight occupancy covers each day but not the day after an exact midnight end', () => {
  const event = {
    id: '1',
    organization: '测试',
    purpose: '测试',
    status: 'confirmed',
    startAt: '2026-09-01T23:00:00',
    endAt: '2026-09-03T00:00:00',
  }
  const days = calendarDays('2026-09-01', '2026-09-03', [event])
  assert.deepEqual(
    days.map((day) => day.events.length),
    [1, 1, 0],
  )
})
test('envelope fits portrait and short landscape without changing desktop constants', () => {
  for (const [width, height] of [
    [320, 568],
    [390, 844],
    [430, 932],
    [844, 390],
  ]) {
    const layout = mobileEnvelopeLayout(width!, height!)
    assert(layout.centerX - layout.width / 2 >= 0)
    assert(layout.centerX + layout.width / 2 <= width!)
    assert(layout.centerY > 0 && layout.centerY < height!)
  }
})
