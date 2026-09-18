import { test } from 'node:test'
import assert from 'node:assert/strict'
import { dailyTimeSlots, mergeTimeSlots } from '../src/features/forest-portal/manualTimeSlots.ts'

test('fifteen daily bookings include both endpoints across a month boundary', () => {
  const slots = dailyTimeSlots('2026-09-25', '2026-10-09', '08:30', '17:00')
  assert.equal(slots.length, 15)
  assert.deepEqual(slots[0], { start_at: '2026-09-25T08:30', end_at: '2026-09-25T17:00' })
  assert.deepEqual(slots.at(-1), { start_at: '2026-10-09T08:30', end_at: '2026-10-09T17:00' })
  assert.equal(dailyTimeSlots('2028-02-28', '2028-03-01', '09:00', '12:00').length, 3)
  assert.equal(dailyTimeSlots('2026-12-31', '2027-01-01', '09:00', '12:00').length, 2)
})

test('invalid dates, inverted ranges, overnight and oversized batches are rejected', () => {
  for (const [start, end, from, to] of [
    ['', '2026-10-15', '09:00', '12:00'],
    ['2026-02-30', '2026-03-01', '09:00', '12:00'],
    ['2026-10-15', '2026-10-01', '09:00', '12:00'],
    ['2026-10-01', '2026-10-21', '09:00', '12:00'],
    ['2026-10-01', '2026-10-15', '22:00', '08:00'],
    ['2026-10-01', '2026-10-15', '09:00', '09:00'],
    ['2026-10-01', '2026-10-15', '09:00', '25:00'],
  ]) assert.throws(() => dailyTimeSlots(start!, end!, from!, to!))
})

test('batch merge replaces empty rows, preserves edits, and is idempotent', () => {
  const batch = dailyTimeSlots('2026-10-01', '2026-10-15', '09:00', '12:00')
  const existing = [{ start_at: '', end_at: '' }, { start_at: '2026-10-01T14:00', end_at: '2026-10-01T16:00' }]
  const merged = mergeTimeSlots(existing, batch)
  assert.equal(merged.length, 16)
  assert.deepEqual(merged[1], existing[1])
  assert.deepEqual(mergeTimeSlots(merged, batch), merged)
  assert.equal(existing.length, 2)
})

test('merge rejects overlaps, incomplete rows and combined overflow without changing existing slots', () => {
  const batch = dailyTimeSlots('2026-10-01', '2026-10-15', '09:00', '12:00')
  const overlap = [{ start_at: '2026-10-02T11:00', end_at: '2026-10-02T13:00' }]
  assert.throws(() => mergeTimeSlots(overlap, batch), /重叠/)
  assert.equal(overlap.length, 1)
  assert.throws(() => mergeTimeSlots([{ start_at: '2026-10-02T11:00', end_at: '' }], batch), /补全/)
  assert.throws(() => mergeTimeSlots(dailyTimeSlots('2026-10-16', '2026-10-21', '09:00', '12:00'), batch), /超过/)
  assert.equal(mergeTimeSlots([{ start_at: '2026-10-01T12:00', end_at: '2026-10-01T13:00' }], batch).length, 16)
})
