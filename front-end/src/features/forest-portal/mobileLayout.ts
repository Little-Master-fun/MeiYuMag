import type { VenueUsageEvent } from '@/assets/textures/parchmentPage'

// Include large phones in landscape and portrait tablets.
export const MOBILE_BREAKPOINT = 1024
export const isMobileViewport = (width: number) => width <= MOBILE_BREAKPOINT

export function mobileReaderBounds(left: number, top: number, right: number, bottom: number, viewportHeight: number) {
  const inset = Math.min(22, (right - left) * 0.055)
  // Clear the metal clip while keeping the reading area as tall as possible.
  const contentTop = top + Math.min(52, (bottom - top) * 0.09)
  return {
    left: Math.round(left + inset),
    top: Math.round(contentTop),
    width: Math.round(right - left - inset * 2),
    height: Math.max(0, Math.round(Math.min(bottom - 20, viewportHeight - 20) - contentTop)),
  }
}

export function mobilePaperFraming(
  width: number,
  height: number,
  bounds: { minX: number; maxX: number; minY: number; maxY: number },
  zoom = 1,
  pan = { x: 0, y: 0 },
) {
  // Bookmarks now sit inside the mobile reader: give the sheet the screen width.
  // In landscape crop the lower paper, rather than shrink text to fit its height.
  const paperWidth = Math.min(width - 36, 600)
  const scale = (paperWidth * 2 / width) / Math.max(bounds.maxX - bounds.minX, 0.001) * zoom
  const paperHeight = ((bounds.maxY - bounds.minY) * scale * height) / 2
  const top = Math.max(76, (height - paperHeight) / 2 - 10)
  return {
    scale,
    offsetX: ((bounds.minX + bounds.maxX) * scale) / 2 - (pan.x * 2) / width,
    offsetY: bounds.maxY * scale - 1 + top * 2 / height + (pan.y * 2) / height,
    paperHeight,
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
