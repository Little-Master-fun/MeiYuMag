import type { VenueUsageEvent } from '@/assets/textures/parchmentPage'

// Include large phones in landscape and portrait tablets.
export const MOBILE_BREAKPOINT = 1024
export const isMobileViewport = (width: number) => width <= MOBILE_BREAKPOINT

export function mobilePaperFraming(
  width: number,
  height: number,
  bounds: { minX: number; maxX: number; minY: number; maxY: number },
  zoom = 1,
  pan = { x: 0, y: 0 },
) {
  const margin = Math.min(76, width * 0.19)
  const scale =
    Math.min(
      (2 - (4 * margin) / width) / Math.max(bounds.maxX - bounds.minX, 0.001),
      Math.max(0.1, 2 - 240 / height) / Math.max(bounds.maxY - bounds.minY, 0.001),
    ) * zoom
  return {
    scale,
    offsetX: ((bounds.minX + bounds.maxX) * scale) / 2 - (pan.x * 2) / width,
    offsetY: ((bounds.minY + bounds.maxY) * scale) / 2 + 34 / height + (pan.y * 2) / height,
    paperHeight: ((bounds.maxY - bounds.minY) * scale * height) / 2,
  }
}
export function calendarDays(start: string, end: string, events: VenueUsageEvent[]) {
  const cursor = new Date(`${start}T12:00:00`)
  const last = new Date(`${end}T12:00:00`)
  if (!Number.isFinite(+cursor) || !Number.isFinite(+last) || cursor > last) return []
  const days = []
  // Defensive cap for a malformed API range; the normal window is 31 days.
  while (cursor <= last && days.length < 62) {
    const key = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}-${String(cursor.getDate()).padStart(2, '0')}`
    const from = new Date(cursor)
    from.setHours(0, 0, 0, 0)
    const until = new Date(from)
    until.setDate(until.getDate() + 1)
    days.push({
      key,
      day: cursor.getDate(),
      month: cursor.getMonth() + 1,
      weekday: cursor.getDay(),
      events: events.filter(
        (event) => +new Date(event.startAt) < +until && +new Date(event.endAt) > +from,
      ),
    })
    cursor.setDate(cursor.getDate() + 1)
  }
  return days
}

export function mobileEnvelopeLayout(width: number, height: number) {
  const compact = height < 540
  const shortPortrait = height < 640
  return {
    width: Math.max(
      90,
      Math.min(
        width * (compact ? 0.3 : 0.74),
        330,
        height * (compact ? 0.5 : shortPortrait ? 0.3 : 0.35),
      ),
    ),
    centerX: compact ? width * 0.25 : width * 0.5,
    centerY: compact ? height * 0.63 : Math.max(Math.min(270, height * 0.45), height * 0.39),
    signHeight: compact ? 130 : shortPortrait ? 240 : 260,
  }
}
