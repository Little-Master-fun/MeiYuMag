import * as THREE from 'three'

export type VenueUsageStatus =
  | 'confirmed'
  | 'reserved'
  | 'pre_reserved'
  | 'pending_admin_pre_review'
  | 'supplement_required'

export interface VenueUsageEvent {
  id: string
  organization: string
  purpose: string
  startAt: string
  endAt: string
  status: VenueUsageStatus | string
}

export interface VenueUsageItem {
  id: number
  name: string
  events: VenueUsageEvent[]
}

export interface PersonalHomeProfile {
  email: string
  organization: string
  role: 'user' | 'admin'
  verified: boolean
  applicationAllowed: boolean
}

export interface PersonalApplicationItem {
  id: number
  applicationType: string
  venueId: number | null
  venueName: string
  purpose: string
  status: string
  startAt: string | null
  endAt: string | null
  reviewReason: string | null
  createdAt: string
}

export interface VenueUsageBoard {
  mode: 'management' | 'user-matrix' | 'user-detail' | 'profile'
  date: string
  rangeStart?: string
  rangeEnd?: string
  state: 'loading' | 'ready' | 'error'
  venues: VenueUsageItem[]
  profile?: PersonalHomeProfile
  applications?: PersonalApplicationItem[]
  error?: string
}

export type ParchmentPageAction =
  | { type: 'switch-page'; page: 'profile' | 'calendar' }
  | { type: 'detail'; application: PersonalApplicationItem }

export interface ParchmentPageCanvas {
  texture: THREE.CanvasTexture
  updateUsageBoard: (board: VenueUsageBoard) => void
  transitionUsageBoard: (board: VenueUsageBoard) => void
  selectVenue: (venueId: number) => void
  scrollBy: (delta: number) => void
  pointerMove: (normalizedX: number, normalizedY: number) => void
  getApplicationTarget: (
    normalizedX: number,
    normalizedY: number,
  ) => { venueId: number; venueName: string; date: string } | null
  getPageAction: (normalizedX: number, normalizedY: number) => ParchmentPageAction | null
  pointerLeave: () => void
  tick: () => void
}

const PAGE_WIDTH = 1024
const PAGE_HEIGHT = 1400
const CONTENT_TOP = 660
const CARD_GAP = 24
const DETAIL_TABLE_X = 120
const DETAIL_TABLE_Y = 632
const DETAIL_TABLE_WIDTH = 784
const DETAIL_HEADER_HEIGHT = 48
const DETAIL_ROW_HEIGHT = 112
const DETAIL_CALENDAR_COLUMNS = 7
const DETAIL_CELL_WIDTH = DETAIL_TABLE_WIDTH / DETAIL_CALENDAR_COLUMNS

function isHistoricalApplicationStatus(status: string) {
  return ['completed', 'cancelled', 'rejected'].includes(status)
}

const statusStyles: Record<string, { label: string; color: string; text: string }> = {
  confirmed: { label: '已确认', color: '#60745f', text: '#394c3b' },
  reserved: { label: '已预约', color: '#60745f', text: '#394c3b' },
  pre_reserved: { label: '预占用', color: '#ad8248', text: '#765525' },
  pending_admin_pre_review: { label: '审核中', color: '#737583', text: '#515361' },
  supplement_required: { label: '待补充', color: '#9a6152', text: '#743f34' },
}

function roundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  const corner = Math.min(radius, width / 2, height / 2)
  ctx.beginPath()
  ctx.moveTo(x + corner, y)
  ctx.lineTo(x + width - corner, y)
  ctx.quadraticCurveTo(x + width, y, x + width, y + corner)
  ctx.lineTo(x + width, y + height - corner)
  ctx.quadraticCurveTo(x + width, y + height, x + width - corner, y + height)
  ctx.lineTo(x + corner, y + height)
  ctx.quadraticCurveTo(x, y + height, x, y + height - corner)
  ctx.lineTo(x, y + corner)
  ctx.quadraticCurveTo(x, y, x + corner, y)
  ctx.closePath()
}

function formatDate(dateValue: string) {
  const date = new Date(`${dateValue}T12:00:00`)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(date)
}

function formatTime(dateValue: string) {
  const date = new Date(dateValue)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function getHourValue(dateValue: string) {
  const date = new Date(dateValue)
  return date.getHours() + date.getMinutes() / 60
}

function calculateContentHeight(board: VenueUsageBoard) {
  if (board.state !== 'ready') return PAGE_HEIGHT
  if (board.mode === 'profile') {
    const applications = board.applications ?? []
    const activeCount = applications.filter(
      (application) => !isHistoricalApplicationStatus(application.status),
    ).length
    const historyCount = applications.length - activeCount
    return Math.max(PAGE_HEIGHT, 850 + activeCount * 112 + historyCount * 92)
  }
  if (board.mode === 'user-matrix') return 2400
  if (board.mode === 'user-detail') return PAGE_HEIGHT
  const cardsHeight = board.venues.reduce(
    (height, venue) => height + Math.max(166, 142 + venue.events.length * 42),
    0,
  )
  return CONTENT_TOP + cardsHeight + Math.max(0, board.venues.length - 1) * CARD_GAP + 190
}

function drawStat(
  ctx: CanvasRenderingContext2D,
  x: number,
  value: number,
  label: string,
  y = 430,
) {
  roundedRect(ctx, x, y, 238, 118, 18)
  ctx.fillStyle = 'rgba(255, 252, 239, 0.3)'
  ctx.fill()
  ctx.strokeStyle = 'rgba(92, 72, 47, 0.16)'
  ctx.lineWidth = 2
  ctx.stroke()

  ctx.textAlign = 'left'
  ctx.fillStyle = '#58452f'
  ctx.font = '600 48px "Palatino Linotype", Palatino, Georgia, serif'
  ctx.fillText(String(value).padStart(2, '0'), x + 25, y + 62)
  ctx.fillStyle = 'rgba(77, 60, 40, 0.6)'
  ctx.font = '24px "Songti SC", "STSong", serif'
  ctx.fillText(label, x + 94, y + 61)
}

function drawTimeline(
  ctx: CanvasRenderingContext2D,
  events: VenueUsageEvent[],
  y: number,
) {
  const timelineX = 146
  const timelineWidth = 732
  const startHour = 8
  const endHour = 22

  ctx.fillStyle = 'rgba(93, 73, 48, 0.1)'
  roundedRect(ctx, timelineX, y, timelineWidth, 12, 6)
  ctx.fill()

  for (const hour of [8, 12, 16, 20, 22]) {
    const progress = (hour - startHour) / (endHour - startHour)
    const x = timelineX + progress * timelineWidth
    ctx.fillStyle = 'rgba(85, 66, 44, 0.46)'
    ctx.font = '19px "Palatino Linotype", Palatino, serif'
    ctx.textAlign = hour === 8 ? 'left' : hour === 22 ? 'right' : 'center'
    ctx.fillText(`${String(hour).padStart(2, '0')}:00`, x, y - 10)
  }

  for (const event of events) {
    const start = THREE.MathUtils.clamp(getHourValue(event.startAt), startHour, endHour)
    const end = THREE.MathUtils.clamp(getHourValue(event.endAt), startHour, endHour)
    const x = timelineX + ((start - startHour) / (endHour - startHour)) * timelineWidth
    const width = Math.max(10, ((end - start) / (endHour - startHour)) * timelineWidth)
    const style = statusStyles[event.status] ?? statusStyles.confirmed
    ctx.fillStyle = style.color
    roundedRect(ctx, x, y - 2, width, 16, 8)
    ctx.fill()
  }
}

function drawVenueCard(
  ctx: CanvasRenderingContext2D,
  venue: VenueUsageItem,
  index: number,
  y: number,
) {
  const height = Math.max(166, 142 + venue.events.length * 42)
  roundedRect(ctx, 120, y, 784, height, 22)
  ctx.fillStyle = 'rgba(255, 252, 239, 0.2)'
  ctx.fill()
  ctx.strokeStyle = 'rgba(92, 72, 47, 0.16)'
  ctx.lineWidth = 2
  ctx.stroke()

  ctx.textAlign = 'left'
  ctx.fillStyle = 'rgba(91, 70, 45, 0.5)'
  ctx.font = '600 21px "Palatino Linotype", Palatino, serif'
  ctx.fillText(String(index + 1).padStart(2, '0'), 146, y + 45)
  ctx.fillStyle = '#58452f'
  ctx.font = '600 34px "Songti SC", "STSong", serif'
  ctx.fillText(venue.name, 198, y + 47)

  const countText = venue.events.length ? `${venue.events.length} 项申请` : '今日空闲'
  ctx.textAlign = 'right'
  ctx.fillStyle = venue.events.length ? 'rgba(88, 69, 47, 0.62)' : '#60745f'
  ctx.font = '600 22px "Songti SC", "STSong", serif'
  ctx.fillText(countText, 878, y + 44)

  drawTimeline(ctx, venue.events, y + 88)

  if (!venue.events.length) {
    ctx.textAlign = 'left'
    ctx.fillStyle = 'rgba(77, 60, 40, 0.54)'
    ctx.font = '25px "Songti SC", "STSong", serif'
    ctx.fillText('暂无使用安排，可提交场地申请', 146, y + 139)
    return height
  }

  venue.events.forEach((event, eventIndex) => {
    const rowY = y + 137 + eventIndex * 42
    const style = statusStyles[event.status] ?? statusStyles.confirmed
    ctx.fillStyle = style.color
    ctx.beginPath()
    ctx.arc(154, rowY - 7, 6, 0, Math.PI * 2)
    ctx.fill()

    ctx.textAlign = 'left'
    ctx.fillStyle = '#58452f'
    ctx.font = '600 23px "Palatino Linotype", "Songti SC", serif'
    ctx.fillText(`${formatTime(event.startAt)}–${formatTime(event.endAt)}`, 174, rowY)

    ctx.fillStyle = 'rgba(77, 60, 40, 0.72)'
    ctx.font = '23px "Songti SC", "STSong", serif'
    const description = `${event.organization} · ${event.purpose}`
    ctx.fillText(description.length > 28 ? `${description.slice(0, 28)}…` : description, 340, rowY)

    ctx.textAlign = 'right'
    ctx.fillStyle = style.text
    ctx.font = '600 20px "Songti SC", "STSong", serif'
    ctx.fillText(style.label, 878, rowY)
  })

  return height
}

function getDateRange(startDate: string, endDate: string) {
  const dates: string[] = []
  const cursor = new Date(`${startDate}T12:00:00`)
  const end = new Date(`${endDate}T12:00:00`)
  while (cursor <= end) {
    dates.push(
      `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}-${String(cursor.getDate()).padStart(2, '0')}`,
    )
    cursor.setDate(cursor.getDate() + 1)
  }
  return dates
}

function getEventDateKey(dateValue: string) {
  const date = new Date(dateValue)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function getSlotColor(
  events: VenueUsageEvent[],
  dateKey: string,
  slotStart: number,
  slotEnd: number,
) {
  const overlapping = getSlotEvents(events, dateKey, slotStart, slotEnd)
  if (!overlapping.length) return 'rgba(96, 116, 95, 0.1)'
  if (overlapping.some((event) => ['confirmed', 'reserved'].includes(event.status))) {
    return '#60745f'
  }
  if (overlapping.some((event) => event.status === 'supplement_required')) return '#9a6152'
  if (overlapping.some((event) => event.status === 'pending_admin_pre_review')) return '#737583'
  return '#ad8248'
}

function getSlotEvents(
  events: VenueUsageEvent[],
  dateKey: string,
  slotStart: number,
  slotEnd: number,
) {
  return events.filter((event) => {
    if (getEventDateKey(event.startAt) !== dateKey) return false
    return getHourValue(event.startAt) < slotEnd && getHourValue(event.endAt) > slotStart
  })
}

function getDisplayDates(board: VenueUsageBoard) {
  const rangeDates = getDateRange(
    board.rangeStart || board.date,
    board.rangeEnd || board.date,
  )
  const todayIndex = Math.max(0, rangeDates.indexOf(board.date))
  return [
    ...rangeDates.slice(todayIndex),
    ...rangeDates.slice(0, todayIndex).reverse(),
  ]
}

function drawRangeLegend(
  ctx: CanvasRenderingContext2D,
  x: number,
  color: string,
  label: string,
) {
  ctx.fillStyle = color
  roundedRect(ctx, x, 586, 24, 12, 6)
  ctx.fill()
  ctx.textAlign = 'left'
  ctx.fillStyle = 'rgba(77, 60, 40, 0.64)'
  ctx.font = '21px "Songti SC", "STSong", serif'
  ctx.fillText(label, x + 34, 599)
}

function drawUserRangeBoard(
  ctx: CanvasRenderingContext2D,
  board: VenueUsageBoard,
  scrollY: number,
  contentHeight: number,
) {
  ctx.clearRect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
  ctx.save()
  ctx.translate(0, -scrollY)

  ctx.textAlign = 'left'
  ctx.fillStyle = 'rgba(89, 70, 47, 0.58)'
  ctx.font = '600 20px "Palatino Linotype", Palatino, serif'
  ctx.fillText('MEIYU  ·  VENUE AVAILABILITY', 120, 240)
  ctx.fillStyle = '#58452f'
  ctx.font = '600 70px "Songti SC", "STSong", Georgia, serif'
  ctx.fillText('场地占用日历', 120, 312)
  ctx.fillStyle = 'rgba(77, 60, 40, 0.62)'
  ctx.font = '27px "Songti SC", "STSong", serif'
  ctx.fillText(
    `${board.rangeStart || board.date}  —  ${board.rangeEnd || board.date} · 前后各15天`,
    120,
    364,
  )

  ctx.strokeStyle = 'rgba(93, 73, 48, 0.25)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(120, 400)
  ctx.lineTo(904, 400)
  ctx.stroke()

  if (board.state === 'loading') {
    ctx.fillStyle = 'rgba(77, 60, 40, 0.6)'
    ctx.font = '30px "Songti SC", "STSong", serif'
    ctx.fillText('正在读取未来与历史场地排期…', 120, 480)
    ctx.restore()
    return
  }

  if (board.state === 'error') {
    ctx.fillStyle = '#8b5548'
    ctx.font = '30px "Songti SC", "STSong", serif'
    ctx.fillText('场地数据暂时无法读取', 120, 466)
    ctx.fillStyle = 'rgba(77, 60, 40, 0.58)'
    ctx.font = '24px "Songti SC", "STSong", serif'
    ctx.fillText(board.error || '请稍后重试', 120, 516)
    ctx.restore()
    return
  }

  const rangeDates = getDateRange(
    board.rangeStart || board.date,
    board.rangeEnd || board.date,
  )
  const displayDates = getDisplayDates(board)
  const eventCount = board.venues.reduce((count, venue) => count + venue.events.length, 0)
  drawStat(ctx, 120, rangeDates.length, '查阅天数')
  drawStat(ctx, 393, board.venues.length, '开放场地')
  drawStat(ctx, 666, eventCount, '预约记录')

  drawRangeLegend(ctx, 120, 'rgba(96, 116, 95, 0.1)', '空闲')
  drawRangeLegend(ctx, 254, '#60745f', '已占用')
  drawRangeLegend(ctx, 414, '#ad8248', '预占用')
  drawRangeLegend(ctx, 574, '#737583', '审核中')
  drawRangeLegend(ctx, 734, '#9a6152', '待补充')

  const gridX = 120
  const gridY = 632
  const dateWidth = 100
  const venueWidth = 76
  const headerHeight = 58
  const rowHeight = 42
  const gridWidth = dateWidth + board.venues.length * venueWidth

  roundedRect(ctx, gridX, gridY, gridWidth, headerHeight, 16)
  ctx.fillStyle = 'rgba(88, 69, 47, 0.08)'
  ctx.fill()
  ctx.fillStyle = 'rgba(77, 60, 40, 0.52)'
  ctx.font = '600 20px "Songti SC", "STSong", serif'
  ctx.textAlign = 'left'
  ctx.fillText('日期', gridX + 15, gridY + 36)

  board.venues.forEach((venue, venueIndex) => {
    const x = gridX + dateWidth + venueIndex * venueWidth
    ctx.textAlign = 'center'
    ctx.fillStyle = '#58452f'
    ctx.font = '600 21px "Palatino Linotype", Palatino, serif'
    ctx.fillText(String(venueIndex + 1).padStart(2, '0'), x + venueWidth / 2, gridY + 28)
    ctx.fillStyle = 'rgba(77, 60, 40, 0.44)'
    ctx.font = '17px "Songti SC", "STSong", serif'
    ctx.fillText('早 午 晚', x + venueWidth / 2, gridY + 49)
  })

  const todayKey = board.date
  displayDates.forEach((dateKey, dateIndex) => {
    const date = new Date(`${dateKey}T12:00:00`)
    const y = gridY + headerHeight + dateIndex * rowHeight
    const isToday = dateKey === todayKey
    const isPast = dateKey < todayKey
    const isWeekend = date.getDay() === 0 || date.getDay() === 6

    if (isToday) {
      roundedRect(ctx, gridX, y + 2, gridWidth, rowHeight - 4, 10)
      ctx.fillStyle = 'rgba(173, 130, 72, 0.12)'
      ctx.fill()
      ctx.strokeStyle = 'rgba(137, 91, 45, 0.42)'
      ctx.lineWidth = 2
      ctx.stroke()
    } else if (isWeekend) {
      ctx.fillStyle = 'rgba(88, 69, 47, 0.035)'
      ctx.fillRect(gridX, y, gridWidth, rowHeight)
    }

    ctx.globalAlpha = isPast ? 0.76 : 1
    ctx.textAlign = 'left'
    ctx.fillStyle = isToday ? '#765525' : 'rgba(77, 60, 40, 0.68)'
    ctx.font = `${isToday ? '600' : '400'} 19px "Palatino Linotype", "Songti SC", serif`
    const weekday = ['日', '一', '二', '三', '四', '五', '六'][date.getDay()]
    const dateLabel = `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')} ${weekday}`
    ctx.fillText(isToday ? `${dateLabel} 今` : dateLabel, gridX + 10, y + 27)

    board.venues.forEach((venue, venueIndex) => {
      const cellX = gridX + dateWidth + venueIndex * venueWidth
      const slots = [
        [8, 12],
        [12, 18],
        [18, 22],
      ]
      slots.forEach(([slotStart, slotEnd], slotIndex) => {
        ctx.fillStyle = getSlotColor(venue.events, dateKey, slotStart, slotEnd)
        roundedRect(ctx, cellX + 7 + slotIndex * 22, y + 11, 17, 20, 5)
        ctx.fill()
      })
    })

    ctx.globalAlpha = 1
    ctx.strokeStyle = 'rgba(93, 73, 48, 0.075)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(gridX, y + rowHeight)
    ctx.lineTo(gridX + gridWidth, y + rowHeight)
    ctx.stroke()
  })

  const mappingY = gridY + headerHeight + displayDates.length * rowHeight + 74
  ctx.textAlign = 'left'
  ctx.fillStyle = '#58452f'
  ctx.font = '600 32px "Songti SC", "STSong", serif'
  ctx.fillText('场地编号', gridX, mappingY)

  board.venues.forEach((venue, index) => {
    const column = index % 3
    const row = Math.floor(index / 3)
    const x = gridX + column * 262
    const y = mappingY + 54 + row * 48
    ctx.fillStyle = 'rgba(91, 70, 45, 0.5)'
    ctx.font = '600 20px "Palatino Linotype", Palatino, serif'
    ctx.fillText(String(index + 1).padStart(2, '0'), x, y)
    ctx.fillStyle = 'rgba(77, 60, 40, 0.76)'
    ctx.font = '22px "Songti SC", "STSong", serif'
    const shortName = venue.name.length > 9 ? `${venue.name.slice(0, 9)}…` : venue.name
    ctx.fillText(shortName, x + 40, y)
  })

  ctx.textAlign = 'center'
  ctx.fillStyle = 'rgba(77, 60, 40, 0.45)'
  ctx.font = '22px "Songti SC", "STSong", serif'
  ctx.fillText('每格依次表示早间、午间、晚间占用状态', PAGE_WIDTH / 2, mappingY + 235)
  ctx.restore()

  const maxScroll = Math.max(0, contentHeight - PAGE_HEIGHT)
  if (maxScroll <= 0) return
  const progress = scrollY / maxScroll
  ctx.fillStyle = 'rgba(93, 73, 48, 0.1)'
  ctx.fillRect(PAGE_WIDTH - 70, 220, 3, 930)
  ctx.fillStyle = 'rgba(93, 73, 48, 0.42)'
  ctx.fillRect(PAGE_WIDTH - 72, 220 + progress * 850, 7, 80)
}

function drawVenueDetailTimeline(
  ctx: CanvasRenderingContext2D,
  events: VenueUsageEvent[],
  y: number,
) {
  const startHour = 8
  const endHour = 22
  const x = 278
  const width = 438
  ctx.fillStyle = 'rgba(96, 116, 95, 0.1)'
  roundedRect(ctx, x, y, width, 14, 7)
  ctx.fill()

  events.forEach((event) => {
    const eventStart = THREE.MathUtils.clamp(getHourValue(event.startAt), startHour, endHour)
    const eventEnd = THREE.MathUtils.clamp(getHourValue(event.endAt), startHour, endHour)
    const eventX = x + ((eventStart - startHour) / (endHour - startHour)) * width
    const eventWidth = Math.max(10, ((eventEnd - eventStart) / (endHour - startHour)) * width)
    const style = statusStyles[event.status] ?? statusStyles.confirmed
    ctx.fillStyle = style.color
    roundedRect(ctx, eventX, y - 2, eventWidth, 18, 8)
    ctx.fill()
  })
}

function drawCalendarEventBars(
  ctx: CanvasRenderingContext2D,
  events: VenueUsageEvent[],
  x: number,
  y: number,
  width: number,
) {
  if (!events.length) return
  const startHour = 8
  const endHour = 22
  events.slice(0, 4).forEach((event, index) => {
    const eventStart = THREE.MathUtils.clamp(getHourValue(event.startAt), startHour, endHour)
    const eventEnd = THREE.MathUtils.clamp(getHourValue(event.endAt), startHour, endHour)
    const eventX = x + ((eventStart - startHour) / (endHour - startHour)) * width
    const eventWidth = Math.max(6, ((eventEnd - eventStart) / (endHour - startHour)) * width)
    const style = statusStyles[event.status] ?? statusStyles.confirmed
    ctx.fillStyle = style.color
    roundedRect(ctx, eventX, y + index * 8, eventWidth, 6, 3)
    ctx.fill()
  })
}

function drawVenueUsageHoverCard(
  ctx: CanvasRenderingContext2D,
  dateKey: string,
  events: VenueUsageEvent[],
  rowY: number,
  scrollY: number,
) {
  const date = new Date(`${dateKey}T12:00:00`)
  const weekday = ['日', '一', '二', '三', '四', '五', '六'][date.getDay()]
  const tooltipHeight = 188
  const tooltipY = THREE.MathUtils.clamp(
    rowY - tooltipHeight - 10,
    scrollY + 410,
    scrollY + PAGE_HEIGHT - tooltipHeight - 78,
  )
  const tooltipX = 138
  const tooltipWidth = 748

  ctx.save()
  ctx.shadowColor = 'rgba(69, 53, 35, 0.2)'
  ctx.shadowBlur = 24
  ctx.shadowOffsetY = 10
  roundedRect(ctx, tooltipX, tooltipY, tooltipWidth, tooltipHeight, 18)
  ctx.fillStyle = 'rgba(250, 239, 203, 0.98)'
  ctx.fill()
  ctx.shadowColor = 'transparent'
  ctx.strokeStyle = 'rgba(117, 86, 47, 0.32)'
  ctx.lineWidth = 2
  ctx.stroke()

  ctx.textAlign = 'left'
  ctx.fillStyle = '#58452f'
  ctx.font = '600 24px "Songti SC", "STSong", serif'
  ctx.fillText(
    `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')} 周${weekday} · 占用详情`,
    tooltipX + 22,
    tooltipY + 37,
  )
  ctx.textAlign = 'right'
  ctx.fillStyle = 'rgba(77, 60, 40, 0.55)'
  ctx.font = '18px "Songti SC", "STSong", serif'
  ctx.fillText('08:00 — 22:00', tooltipX + tooltipWidth - 22, tooltipY + 36)

  drawVenueDetailTimeline(ctx, events, tooltipY + 78)

  const event = events[0]
  if (event) {
    const style = statusStyles[event.status] ?? statusStyles.confirmed
    ctx.textAlign = 'left'
    ctx.fillStyle = style.color
    ctx.beginPath()
    ctx.arc(164, tooltipY + 136, 6, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = '#58452f'
    ctx.font = '600 20px "Palatino Linotype", "Songti SC", serif'
    ctx.fillText(`${formatTime(event.startAt)}–${formatTime(event.endAt)}`, 181, tooltipY + 143)
    ctx.fillStyle = 'rgba(77, 60, 40, 0.72)'
    ctx.font = '19px "Songti SC", "STSong", serif'
    const description = `${event.organization} · ${event.purpose}`
    ctx.fillText(description.length > 26 ? `${description.slice(0, 26)}…` : description, 348, tooltipY + 143)
    ctx.textAlign = 'right'
    ctx.fillStyle = style.text
    ctx.font = '600 18px "Songti SC", "STSong", serif'
    ctx.fillText(events.length > 1 ? `另有 ${events.length - 1} 项` : style.label, 860, tooltipY + 143)
  }
  ctx.restore()
}

function drawUserVenueDetailBoard(
  ctx: CanvasRenderingContext2D,
  board: VenueUsageBoard,
  selectedVenueId: number | null,
  scrollY: number,
  contentHeight: number,
  hoveredDateKey: string | null,
  hoveredDateKind: 'occupied' | 'available' | null,
) {
  ctx.clearRect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
  const selectedVenue =
    board.venues.find((venue) => venue.id === selectedVenueId) ?? board.venues[0]
  ctx.save()
  ctx.translate(0, -scrollY)

  ctx.textAlign = 'left'
  ctx.fillStyle = 'rgba(89, 70, 47, 0.58)'
  ctx.font = '600 20px "Palatino Linotype", Palatino, serif'
  ctx.fillText('MEIYU  ·  VENUE SCHEDULE', 120, 240)
  ctx.fillStyle = '#58452f'
  ctx.font = '600 62px "Songti SC", "STSong", Georgia, serif'
  ctx.fillText(selectedVenue?.name || '场地使用详情', 120, 312)
  ctx.fillStyle = 'rgba(77, 60, 40, 0.62)'
  ctx.font = '25px "Songti SC", "STSong", serif'
  ctx.fillText(
    `${board.rangeStart || board.date}  —  ${board.rangeEnd || board.date} · 点击两侧书签切换场地`,
    120,
    364,
  )

  ctx.strokeStyle = 'rgba(93, 73, 48, 0.25)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(120, 400)
  ctx.lineTo(904, 400)
  ctx.stroke()

  if (board.state === 'loading') {
    ctx.fillStyle = 'rgba(77, 60, 40, 0.6)'
    ctx.font = '30px "Songti SC", "STSong", serif'
    ctx.fillText('正在整理场地使用时间…', 120, 480)
    ctx.restore()
    return
  }

  if (board.state === 'error' || !selectedVenue) {
    ctx.fillStyle = '#8b5548'
    ctx.font = '30px "Songti SC", "STSong", serif'
    ctx.fillText('场地数据暂时无法读取', 120, 466)
    ctx.restore()
    return
  }

  const rangeDates = getDateRange(
    board.rangeStart || board.date,
    board.rangeEnd || board.date,
  )
  const firstRangeDate = new Date(`${rangeDates[0] ?? board.date}T12:00:00`)
  const leadingEmptyCells = (firstRangeDate.getDay() + 6) % 7
  const calendarRows = Math.ceil((leadingEmptyCells + rangeDates.length) / DETAIL_CALENDAR_COLUMNS)
  const occupiedDates = new Set(selectedVenue.events.map((event) => getEventDateKey(event.startAt)))
  drawStat(ctx, 120, rangeDates.length, '查阅天数')
  drawStat(ctx, 393, occupiedDates.size, '占用天数')
  drawStat(ctx, 666, rangeDates.length - occupiedDates.size, '可申请天数')

  drawRangeLegend(ctx, 120, 'rgba(96, 116, 95, 0.1)', '空闲')
  drawRangeLegend(ctx, 254, '#60745f', '已占用')
  drawRangeLegend(ctx, 414, '#ad8248', '预占用')
  drawRangeLegend(ctx, 574, '#737583', '审核中')
  drawRangeLegend(ctx, 734, '#9a6152', '待补充')

  const tableX = DETAIL_TABLE_X
  const tableY = DETAIL_TABLE_Y
  const tableWidth = DETAIL_TABLE_WIDTH
  const headerHeight = DETAIL_HEADER_HEIGHT
  const rowHeight = DETAIL_ROW_HEIGHT
  roundedRect(ctx, tableX, tableY, tableWidth, headerHeight, 16)
  ctx.fillStyle = 'rgba(88, 69, 47, 0.08)'
  ctx.fill()
  const weekLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  weekLabels.forEach((label, columnIndex) => {
    const x = tableX + columnIndex * DETAIL_CELL_WIDTH
    ctx.textAlign = 'center'
    ctx.fillStyle = columnIndex >= 5 ? 'rgba(142, 91, 55, 0.68)' : 'rgba(77, 60, 40, 0.62)'
    ctx.font = '600 19px "Songti SC", "STSong", serif'
    ctx.fillText(label, x + DETAIL_CELL_WIDTH / 2, tableY + 32)
  })

  rangeDates.forEach((dateKey, dateIndex) => {
    const calendarIndex = leadingEmptyCells + dateIndex
    const columnIndex = calendarIndex % DETAIL_CALENDAR_COLUMNS
    const rowIndex = Math.floor(calendarIndex / DETAIL_CALENDAR_COLUMNS)
    const date = new Date(`${dateKey}T12:00:00`)
    const x = tableX + columnIndex * DETAIL_CELL_WIDTH
    const y = tableY + headerHeight + rowIndex * rowHeight
    const dayEvents = selectedVenue.events.filter(
      (event) => getEventDateKey(event.startAt) === dateKey,
    )
    const isToday = dateKey === board.date
    const isPast = dateKey < board.date
    const isWeekend = date.getDay() === 0 || date.getDay() === 6
    const isAvailableFuture = dateKey > board.date && dayEvents.length === 0

    roundedRect(ctx, x + 2, y + 2, DETAIL_CELL_WIDTH - 4, rowHeight - 4, 10)
    ctx.fillStyle = isToday
      ? 'rgba(173, 130, 72, 0.15)'
      : isAvailableFuture
        ? 'rgba(255, 252, 239, 0.17)'
      : isWeekend
        ? 'rgba(112, 77, 48, 0.055)'
        : 'rgba(255, 252, 239, 0.08)'
    ctx.fill()
    ctx.strokeStyle = isToday
      ? 'rgba(137, 91, 45, 0.46)'
      : 'rgba(93, 73, 48, 0.105)'
    ctx.lineWidth = isToday ? 2 : 1
    ctx.stroke()

    if (dateKey === hoveredDateKey && dayEvents.length) {
      roundedRect(ctx, x + 2, y + 2, DETAIL_CELL_WIDTH - 4, rowHeight - 4, 10)
      ctx.fillStyle = 'rgba(173, 130, 72, 0.1)'
      ctx.fill()
      ctx.strokeStyle = 'rgba(117, 86, 47, 0.34)'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    if (dateKey === hoveredDateKey && hoveredDateKind === 'available') {
      roundedRect(ctx, x + 2, y + 2, DETAIL_CELL_WIDTH - 4, rowHeight - 4, 10)
      ctx.fillStyle = 'rgba(173, 130, 72, 0.1)'
      ctx.fill()
      ctx.strokeStyle = 'rgba(117, 86, 47, 0.34)'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    ctx.globalAlpha = isPast ? 0.74 : 1
    ctx.textAlign = 'left'
    ctx.fillStyle = isToday ? '#765525' : 'rgba(77, 60, 40, 0.72)'
    ctx.font = `${isToday ? '600' : '400'} 20px "Palatino Linotype", "Songti SC", serif`
    const dateLabel = date.getDate() === 1 || dateIndex === 0
      ? `${date.getMonth() + 1}月${date.getDate()}日`
      : String(date.getDate())
    ctx.fillText(isToday ? `${dateLabel} · 今` : dateLabel, x + 10, y + 27)

    drawCalendarEventBars(ctx, dayEvents, x + 10, y + 43, DETAIL_CELL_WIDTH - 20)

    ctx.textAlign = 'left'
    if (!dayEvents.length) {
      ctx.fillStyle = isAvailableFuture ? '#60745f' : 'rgba(77, 92, 72, 0.48)'
      ctx.font = `${isAvailableFuture ? '600' : '400'} 17px "Songti SC", "STSong", serif`
      ctx.fillText(isAvailableFuture ? '可申请' : '暂无安排', x + 10, y + 91)
    } else {
      const mainStyle = statusStyles[dayEvents[0]?.status ?? 'confirmed'] ?? statusStyles.confirmed
      ctx.fillStyle = mainStyle.text
      ctx.font = '600 17px "Songti SC", "STSong", serif'
      ctx.fillText(
        dayEvents.length > 1 ? `${dayEvents.length} 项申请` : mainStyle.label,
        x + 10,
        y + 91,
      )
    }
    ctx.globalAlpha = 1
  })

  if (hoveredDateKey && hoveredDateKind === 'occupied') {
    const hoveredIndex = rangeDates.indexOf(hoveredDateKey)
    const hoveredEvents = selectedVenue.events.filter(
      (event) => getEventDateKey(event.startAt) === hoveredDateKey,
    )
    if (hoveredIndex >= 0 && hoveredEvents.length) {
      const hoveredCalendarIndex = leadingEmptyCells + hoveredIndex
      const hoveredRowY = tableY
        + headerHeight
        + Math.floor(hoveredCalendarIndex / DETAIL_CALENDAR_COLUMNS) * rowHeight
      drawVenueUsageHoverCard(ctx, hoveredDateKey, hoveredEvents, hoveredRowY, scrollY)
    }
  }

  const footerY = tableY + headerHeight + calendarRows * rowHeight + 30
  ctx.textAlign = 'center'
  ctx.fillStyle = 'rgba(77, 60, 40, 0.45)'
  ctx.font = '22px "Songti SC", "STSong", serif'
  ctx.fillText('悬浮有占用的日期查看详细时段 · 展示过去15天与未来15天', PAGE_WIDTH / 2, footerY)
  ctx.restore()

  const maxScroll = Math.max(0, contentHeight - PAGE_HEIGHT)
  if (maxScroll <= 0) return
  const progress = scrollY / maxScroll
  ctx.fillStyle = 'rgba(93, 73, 48, 0.1)'
  ctx.fillRect(PAGE_WIDTH - 70, 220, 3, 930)
  ctx.fillStyle = 'rgba(93, 73, 48, 0.42)'
  ctx.fillRect(PAGE_WIDTH - 72, 220 + progress * 850, 7, 80)
}

const PAGE_TAB_Y = 260
const PAGE_TAB_WIDTH = 126
const PAGE_TAB_HEIGHT = 42
const PROFILE_TAB_X = 632
const CALENDAR_TAB_X = 770

function drawFolderPageTabs(ctx: CanvasRenderingContext2D, active: 'profile' | 'calendar') {
  const tabs = [
    { key: 'profile' as const, label: '个人首页', x: PROFILE_TAB_X },
    { key: 'calendar' as const, label: '场地日历', x: CALENDAR_TAB_X },
  ]
  for (const tab of tabs) {
    roundedRect(ctx, tab.x, PAGE_TAB_Y, PAGE_TAB_WIDTH, PAGE_TAB_HEIGHT, 13)
    ctx.fillStyle = tab.key === active ? '#657760' : 'rgba(255, 252, 239, 0.34)'
    ctx.fill()
    ctx.strokeStyle = tab.key === active
      ? 'rgba(72, 89, 68, 0.66)'
      : 'rgba(92, 72, 47, 0.18)'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.textAlign = 'center'
    ctx.fillStyle = tab.key === active ? '#f7efd9' : 'rgba(77, 60, 40, 0.7)'
    ctx.font = '600 20px "Songti SC", "STSong", serif'
    ctx.fillText(tab.label, tab.x + PAGE_TAB_WIDTH / 2, PAGE_TAB_Y + 28)
  }
}

const personalStatusStyles: Record<string, { label: string; color: string; text: string }> = {
  draft: { label: '草稿', color: '#8b8477', text: '#5f594f' },
  ai_reviewing: { label: 'AI审核中', color: '#77758a', text: '#535166' },
  ai_passed: { label: 'AI通过', color: '#5f7a70', text: '#3f5b52' },
  ai_rejected: { label: 'AI未通过', color: '#9a6152', text: '#743f34' },
  rejected: { label: '未通过', color: '#9a6152', text: '#743f34' },
  pending_signed_files: { label: '待签章材料', color: '#ad8248', text: '#765525' },
  pending_signed: { label: '待签章材料', color: '#ad8248', text: '#765525' },
  pending_admin_pre_review: { label: '等待人工初审', color: '#737583', text: '#515361' },
  pending_admin: { label: '等待管理员', color: '#737583', text: '#515361' },
  pending_admin_submit: { label: '待管理员审核', color: '#60745f', text: '#394c3b' },
  supplement_required: { label: '需要补交', color: '#9a6152', text: '#743f34' },
  admin_submitted: { label: '已提交', color: '#60745f', text: '#394c3b' },
  submitted: { label: '已审核确认', color: '#60745f', text: '#394c3b' },
  completed: { label: '已完成', color: '#60745f', text: '#394c3b' },
  cancelled: { label: '已取消', color: '#8b8477', text: '#5f594f' },
}

function formatCompactDate(dateValue: string | null) {
  if (!dateValue) return '时间待确认'
  const date = new Date(dateValue)
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`
}

function getPersonalApplicationGroups(board: VenueUsageBoard) {
  const applications = board.applications ?? []
  return {
    active: applications.filter(
      (application) => !isHistoricalApplicationStatus(application.status),
    ),
    history: applications.filter(
      (application) => isHistoricalApplicationStatus(application.status),
    ),
  }
}

function drawPersonalApplicationRow(
  ctx: CanvasRenderingContext2D,
  application: PersonalApplicationItem,
  y: number,
  compact = false,
) {
  const height = compact ? 76 : 96
  roundedRect(ctx, 120, y, 784, height, 17)
  const needsUserAction = ['supplement_required', 'ai_rejected', 'pending_signed_files'].includes(application.status)
  ctx.fillStyle = needsUserAction
    ? 'rgba(154, 97, 82, 0.09)'
    : 'rgba(255, 252, 239, 0.22)'
  ctx.fill()
  ctx.strokeStyle = needsUserAction
    ? 'rgba(154, 97, 82, 0.32)'
    : 'rgba(92, 72, 47, 0.14)'
  ctx.lineWidth = 2
  ctx.stroke()

  const style = personalStatusStyles[application.status]
    ?? { label: application.status, color: '#8b8477', text: '#5f594f' }
  ctx.textAlign = 'left'
  ctx.fillStyle = '#58452f'
  ctx.font = `600 ${compact ? 22 : 25}px "Songti SC", "STSong", serif`
  ctx.fillText(application.venueName || '场地申请', 146, y + (compact ? 33 : 38))
  ctx.fillStyle = 'rgba(77, 60, 40, 0.55)'
  ctx.font = `${compact ? 17 : 19}px "Songti SC", "STSong", serif`
  const purpose = application.status === 'ai_rejected'
    ? `未通过原因：${application.reviewReason || '申请材料未满足初审要求'}`
    : application.purpose || '申请内容待补充'
  ctx.fillText(
    application.status === 'ai_rejected'
      ? (purpose.length > 31 ? `${purpose.slice(0, 31)}…` : purpose)
      : `${formatCompactDate(application.startAt || application.createdAt)} · ${purpose.length > 22 ? `${purpose.slice(0, 22)}…` : purpose}`,
    146,
    y + (compact ? 60 : 73),
  )

  if (needsUserAction) {
    roundedRect(ctx, 720, y + 24, 154, 50, 14)
    ctx.fillStyle = '#93604f'
    ctx.fill()
    ctx.textAlign = 'center'
    ctx.fillStyle = '#fbf2dc'
    ctx.font = '600 19px "Songti SC", "STSong", serif'
    ctx.fillText(
      application.status === 'ai_rejected' ? '重新提交  →' : application.status === 'pending_signed_files' ? '签章材料  →' : '补交材料  →',
      797,
      y + 56,
    )
  } else {
    ctx.fillStyle = style.color
    roundedRect(ctx, 742, y + (compact ? 20 : 28), 132, 38, 12)
    ctx.fill()
    ctx.textAlign = 'center'
    ctx.fillStyle = '#fff8e7'
    ctx.font = '600 17px "Songti SC", "STSong", serif'
    ctx.fillText(style.label, 808, y + (compact ? 45 : 53))
  }
}

function drawPersonalHomeBoard(
  ctx: CanvasRenderingContext2D,
  board: VenueUsageBoard,
  scrollY: number,
  contentHeight: number,
) {
  ctx.clearRect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
  ctx.save()
  ctx.translate(0, -scrollY)
  drawFolderPageTabs(ctx, 'profile')

  ctx.textAlign = 'left'
  ctx.fillStyle = 'rgba(89, 70, 47, 0.58)'
  ctx.font = '600 20px "Palatino Linotype", Palatino, serif'
  ctx.fillText('MEIYU  ·  PERSONAL DESK', 120, 240)
  ctx.fillStyle = '#58452f'
  ctx.font = '600 62px "Songti SC", "STSong", Georgia, serif'
  ctx.fillText('我的首页', 120, 312)
  ctx.fillStyle = 'rgba(77, 60, 40, 0.62)'
  ctx.font = '25px "Songti SC", "STSong", serif'
  ctx.fillText('个人信息、申请进度与历史记录', 120, 364)

  ctx.strokeStyle = 'rgba(93, 73, 48, 0.25)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(120, 400)
  ctx.lineTo(904, 400)
  ctx.stroke()

  if (board.state === 'loading') {
    ctx.fillStyle = 'rgba(77, 60, 40, 0.6)'
    ctx.font = '30px "Songti SC", "STSong", serif'
    ctx.fillText('正在整理您的个人档案与申请记录…', 120, 480)
    ctx.restore()
    return
  }
  if (board.state === 'error' || !board.profile) {
    ctx.fillStyle = '#8b5548'
    ctx.font = '30px "Songti SC", "STSong", serif'
    ctx.fillText('个人信息暂时无法读取', 120, 470)
    ctx.fillStyle = 'rgba(77, 60, 40, 0.58)'
    ctx.font = '23px "Songti SC", "STSong", serif'
    ctx.fillText(board.error || '请稍后重试', 120, 516)
    ctx.restore()
    return
  }

  const profile = board.profile
  const groups = getPersonalApplicationGroups(board)
  const actionRequiredCount = (board.applications ?? []).filter(
    (application) => ['supplement_required', 'ai_rejected', 'pending_signed_files'].includes(application.status),
  ).length
  roundedRect(ctx, 120, 430, 784, 132, 22)
  ctx.fillStyle = 'rgba(255, 252, 239, 0.26)'
  ctx.fill()
  ctx.strokeStyle = 'rgba(92, 72, 47, 0.16)'
  ctx.stroke()
  ctx.fillStyle = '#657760'
  ctx.beginPath()
  ctx.arc(176, 496, 34, 0, Math.PI * 2)
  ctx.fill()
  ctx.textAlign = 'center'
  ctx.fillStyle = '#f8efd8'
  ctx.font = '600 28px Georgia, serif'
  ctx.fillText(profile.email.slice(0, 1).toUpperCase(), 176, 506)
  ctx.textAlign = 'left'
  ctx.fillStyle = '#58452f'
  ctx.font = '600 28px "Songti SC", "STSong", serif'
  ctx.fillText(profile.email, 230, 482)
  ctx.fillStyle = 'rgba(77, 60, 40, 0.58)'
  ctx.font = '21px "Songti SC", "STSong", serif'
  ctx.fillText(profile.organization || '未填写所属组织', 230, 519)
  ctx.textAlign = 'right'
  ctx.fillStyle = profile.verified ? '#50684f' : '#8b6548'
  ctx.font = '600 20px "Songti SC", "STSong", serif'
  ctx.fillText(profile.verified ? '手机身份已认证' : '身份待认证', 872, 487)
  ctx.fillStyle = 'rgba(77, 60, 40, 0.5)'
  ctx.font = '18px "Songti SC", "STSong", serif'
  ctx.fillText(profile.applicationAllowed ? '具有场地申请权限' : '申请权限待开通', 872, 521)

  drawStat(ctx, 120, board.applications?.length ?? 0, '全部申请', 590)
  drawStat(ctx, 393, groups.active.length, '进行中', 590)
  drawStat(ctx, 666, actionRequiredCount, '待处理', 590)

  let cursorY = 760
  ctx.textAlign = 'left'
  ctx.fillStyle = '#58452f'
  ctx.font = '600 31px "Songti SC", "STSong", serif'
  ctx.fillText('当前申请', 120, cursorY)
  cursorY += 28
  if (!groups.active.length) {
    ctx.fillStyle = 'rgba(77, 60, 40, 0.5)'
    ctx.font = '23px "Songti SC", "STSong", serif'
    ctx.fillText('暂无进行中的申请，可前往场地日历发起申请。', 120, cursorY + 45)
    cursorY += 94
  } else {
    for (const application of groups.active) {
      drawPersonalApplicationRow(ctx, application, cursorY)
      cursorY += 112
    }
  }

  cursorY += 30
  ctx.textAlign = 'left'
  ctx.fillStyle = '#58452f'
  ctx.font = '600 31px "Songti SC", "STSong", serif'
  ctx.fillText('历史申请', 120, cursorY)
  cursorY += 28
  if (!groups.history.length) {
    ctx.fillStyle = 'rgba(77, 60, 40, 0.5)'
    ctx.font = '23px "Songti SC", "STSong", serif'
    ctx.fillText('完成或取消的申请会保存在这里。', 120, cursorY + 45)
  } else {
    for (const application of groups.history) {
      drawPersonalApplicationRow(ctx, application, cursorY, true)
      cursorY += 92
    }
  }
  ctx.restore()

  const maxScroll = Math.max(0, contentHeight - PAGE_HEIGHT)
  if (maxScroll <= 0) return
  const progress = scrollY / maxScroll
  ctx.fillStyle = 'rgba(93, 73, 48, 0.1)'
  ctx.fillRect(PAGE_WIDTH - 70, 220, 3, 930)
  ctx.fillStyle = 'rgba(93, 73, 48, 0.42)'
  ctx.fillRect(PAGE_WIDTH - 72, 220 + progress * 850, 7, 80)
}

function drawParchment(
  ctx: CanvasRenderingContext2D,
  board: VenueUsageBoard,
  scrollY: number,
  contentHeight: number,
  selectedVenueId: number | null,
  hoveredDateKey: string | null,
  hoveredDateKind: 'occupied' | 'available' | null,
) {
  if (board.mode === 'profile') {
    drawPersonalHomeBoard(ctx, board, scrollY, contentHeight)
    return
  }
  if (board.mode === 'user-detail') {
    drawUserVenueDetailBoard(
      ctx,
      board,
      selectedVenueId,
      scrollY,
      contentHeight,
      hoveredDateKey,
      hoveredDateKind,
    )
    ctx.save()
    ctx.translate(0, -scrollY)
    drawFolderPageTabs(ctx, 'calendar')
    ctx.restore()
    return
  }
  if (board.mode === 'user-matrix') {
    drawUserRangeBoard(ctx, board, scrollY, contentHeight)
    ctx.save()
    ctx.translate(0, -scrollY)
    drawFolderPageTabs(ctx, 'calendar')
    ctx.restore()
    return
  }
  ctx.clearRect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
  ctx.save()
  ctx.translate(0, -scrollY)
  drawFolderPageTabs(ctx, 'calendar')

  ctx.textAlign = 'left'
  ctx.fillStyle = 'rgba(89, 70, 47, 0.58)'
  ctx.font = '600 20px "Palatino Linotype", Palatino, serif'
  ctx.fillText('MEIYU  ·  VENUE BOARD', 120, 240)

  ctx.fillStyle = '#58452f'
  ctx.font = '600 70px "Songti SC", "STSong", Georgia, serif'
  ctx.fillText('场地使用一览', 120, 312)

  ctx.fillStyle = 'rgba(77, 60, 40, 0.62)'
  ctx.font = '27px "Songti SC", "STSong", serif'
  ctx.fillText(formatDate(board.date), 120, 364)

  ctx.strokeStyle = 'rgba(93, 73, 48, 0.25)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(120, 400)
  ctx.lineTo(904, 400)
  ctx.stroke()

  if (board.state === 'loading') {
    ctx.fillStyle = 'rgba(77, 60, 40, 0.6)'
    ctx.font = '30px "Songti SC", "STSong", serif'
    ctx.fillText('正在整理今日场地排期…', 120, 480)
    ctx.restore()
    return
  }

  if (board.state === 'error') {
    ctx.fillStyle = '#8b5548'
    ctx.font = '30px "Songti SC", "STSong", serif'
    ctx.fillText('场地数据暂时无法读取', 120, 466)
    ctx.fillStyle = 'rgba(77, 60, 40, 0.58)'
    ctx.font = '24px "Songti SC", "STSong", serif'
    ctx.fillText(board.error || '请稍后重试', 120, 516)
    ctx.restore()
    return
  }

  const eventCount = board.venues.reduce((count, venue) => count + venue.events.length, 0)
  const occupiedCount = board.venues.filter((venue) => venue.events.length).length
  const pendingCount = board.venues.reduce(
    (count, venue) =>
      count +
      venue.events.filter((event) => !['confirmed', 'reserved'].includes(event.status)).length,
    0,
  )
  drawStat(ctx, 120, eventCount, '今日申请')
  drawStat(ctx, 393, occupiedCount, '使用场地')
  drawStat(ctx, 666, pendingCount, '待处理')

  ctx.fillStyle = '#58452f'
  ctx.font = '600 34px "Songti SC", "STSong", serif'
  ctx.fillText('今日场地排期', 120, 626)
  ctx.textAlign = 'right'
  ctx.fillStyle = 'rgba(77, 60, 40, 0.5)'
  ctx.font = '21px "Songti SC", "STSong", serif'
  ctx.fillText('08:00 — 22:00', 904, 625)

  let cardY = CONTENT_TOP
  board.venues.forEach((venue, index) => {
    cardY += drawVenueCard(ctx, venue, index, cardY) + CARD_GAP
  })

  ctx.textAlign = 'center'
  ctx.fillStyle = 'rgba(77, 60, 40, 0.45)'
  ctx.font = '22px "Songti SC", "STSong", serif'
  ctx.fillText('将鼠标移到纸张上滚动，查看全部场地', PAGE_WIDTH / 2, cardY + 45)
  ctx.restore()

  const maxScroll = Math.max(0, contentHeight - PAGE_HEIGHT)
  if (maxScroll <= 0) return
  const progress = scrollY / maxScroll
  ctx.fillStyle = 'rgba(93, 73, 48, 0.1)'
  ctx.fillRect(PAGE_WIDTH - 70, 220, 3, 930)
  ctx.fillStyle = 'rgba(93, 73, 48, 0.42)'
  ctx.fillRect(PAGE_WIDTH - 72, 220 + progress * 850, 7, 80)
}

export function createParchmentPageCanvas(maxAnisotropy: number, pixelScale = 1): ParchmentPageCanvas {
  const canvas = document.createElement('canvas')
  canvas.width = Math.floor(PAGE_WIDTH * pixelScale)
  canvas.height = Math.floor(PAGE_HEIGHT * pixelScale)
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Canvas 2D context is unavailable')
  // Supersample glyphs without changing the layout, scroll or raycast coordinates.
  context.setTransform(canvas.width / PAGE_WIDTH, 0, 0, canvas.height / PAGE_HEIGHT, 0, 0)

  const today = new Date()
  let board: VenueUsageBoard = {
    mode: 'management',
    date: `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`,
    state: 'loading',
    venues: [],
  }
  let contentHeight = calculateContentHeight(board)
  let currentScroll = 0
  let targetScroll = 0
  let selectedVenueId: number | null = null
  let hoveredDateKey: string | null = null
  let hoveredDateKind: 'occupied' | 'available' | null = null
  let pendingBoard: VenueUsageBoard | null = null
  let pendingVenueId: number | null = null
  let fadePhase: 'idle' | 'out' | 'in' = 'idle'
  let fadeOpacity = 1
  let lastTickAt = performance.now()

  const texture = new THREE.CanvasTexture(canvas)
  texture.name = 'Parchment_Venue_Usage_Board'
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = Math.min(maxAnisotropy, 8)
  texture.minFilter = THREE.LinearMipmapLinearFilter
  texture.magFilter = THREE.LinearFilter

  const render = () => {
    drawParchment(
      context,
      board,
      currentScroll,
      contentHeight,
      selectedVenueId,
      hoveredDateKey,
      hoveredDateKind,
    )
    if (fadeOpacity < 0.999) {
      context.save()
      context.globalCompositeOperation = 'destination-in'
      context.fillStyle = `rgba(0, 0, 0, ${fadeOpacity})`
      context.fillRect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
      context.restore()
    }
    texture.needsUpdate = true
  }

  const updateUsageBoard = (nextBoard: VenueUsageBoard) => {
    board = nextBoard
    contentHeight = calculateContentHeight(board)
    if (!board.venues.some((venue) => venue.id === selectedVenueId)) {
      selectedVenueId = board.venues[0]?.id ?? null
    }
    pendingBoard = null
    pendingVenueId = null
    hoveredDateKey = null
    hoveredDateKind = null
    fadePhase = 'idle'
    fadeOpacity = 1
    currentScroll = 0
    targetScroll = 0
    render()
  }

  const transitionUsageBoard = (nextBoard: VenueUsageBoard) => {
    pendingBoard = nextBoard
    pendingVenueId = null
    hoveredDateKey = null
    hoveredDateKind = null
    fadePhase = 'out'
  }

  const selectVenue = (venueId: number) => {
    if (venueId === selectedVenueId || !board.venues.some((venue) => venue.id === venueId)) return
    hoveredDateKey = null
    hoveredDateKind = null
    pendingBoard = null
    pendingVenueId = venueId
    fadePhase = 'out'
  }

  const scrollBy = (delta: number) => {
    const maxScroll = Math.max(0, contentHeight - PAGE_HEIGHT)
    targetScroll = THREE.MathUtils.clamp(targetScroll + delta, 0, maxScroll)
    if (hoveredDateKey) {
      hoveredDateKey = null
      hoveredDateKind = null
      render()
    }
  }

  const clearHover = () => {
    if (!hoveredDateKey) return
    hoveredDateKey = null
    hoveredDateKind = null
    render()
  }

  const getCalendarPointerTarget = (normalizedX: number, normalizedY: number) => {
    const canvasX = normalizedX * PAGE_WIDTH
    const canvasY = normalizedY * PAGE_HEIGHT
    const selectedVenue =
      board.venues.find((venue) => venue.id === selectedVenueId) ?? board.venues[0]
    const contentY = canvasY + currentScroll
    const bodyTop = DETAIL_TABLE_Y + DETAIL_HEADER_HEIGHT
    const rangeDates = getDateRange(board.rangeStart || board.date, board.rangeEnd || board.date)
    const firstRangeDate = new Date(`${rangeDates[0] ?? board.date}T12:00:00`)
    const leadingEmptyCells = (firstRangeDate.getDay() + 6) % 7
    const calendarRows = Math.ceil(
      (leadingEmptyCells + rangeDates.length) / DETAIL_CALENDAR_COLUMNS,
    )
    const bodyBottom = bodyTop + calendarRows * DETAIL_ROW_HEIGHT

    if (
      board.mode !== 'user-detail'
      || board.state !== 'ready'
      || !selectedVenue
      || canvasX < DETAIL_TABLE_X
      || canvasX > DETAIL_TABLE_X + DETAIL_TABLE_WIDTH
      || contentY < bodyTop
      || contentY >= bodyBottom
    ) {
      clearHover()
      return null
    }

    const columnIndex = Math.min(
      DETAIL_CALENDAR_COLUMNS - 1,
      Math.floor((canvasX - DETAIL_TABLE_X) / DETAIL_CELL_WIDTH),
    )
    const rowIndex = Math.floor((contentY - bodyTop) / DETAIL_ROW_HEIGHT)
    const calendarIndex = rowIndex * DETAIL_CALENDAR_COLUMNS + columnIndex
    const dateKey = rangeDates[calendarIndex - leadingEmptyCells]
    if (!dateKey) {
      clearHover()
      return null
    }

    const dayEvents = selectedVenue.events.filter(
      (event) => getEventDateKey(event.startAt) === dateKey,
    )
    if (dayEvents.length > 0) {
      return { date: dateKey, kind: 'occupied' as const, venue: selectedVenue }
    }
    if (dateKey > board.date) {
      return { date: dateKey, kind: 'available' as const, venue: selectedVenue }
    }
    return null
  }

  const pointerMove = (normalizedX: number, normalizedY: number) => {
    const target = getCalendarPointerTarget(normalizedX, normalizedY)
    const nextHoveredDateKey = target?.date ?? null
    const nextHoveredDateKind = target?.kind ?? null
    if (
      nextHoveredDateKey !== hoveredDateKey
      || nextHoveredDateKind !== hoveredDateKind
    ) {
      hoveredDateKey = nextHoveredDateKey
      hoveredDateKind = nextHoveredDateKind
      render()
    }
  }

  const getApplicationTarget = (normalizedX: number, normalizedY: number) => {
    const target = getCalendarPointerTarget(normalizedX, normalizedY)
    if (!target || target.kind !== 'available') return null
    return {
      venueId: target.venue.id,
      venueName: target.venue.name,
      date: target.date,
    }
  }

  const getPageAction = (
    normalizedX: number,
    normalizedY: number,
  ): ParchmentPageAction | null => {
    if (fadePhase !== 'idle') return null
    const canvasX = normalizedX * PAGE_WIDTH
    const contentY = normalizedY * PAGE_HEIGHT + currentScroll
    if (contentY >= PAGE_TAB_Y && contentY <= PAGE_TAB_Y + PAGE_TAB_HEIGHT) {
      if (canvasX >= PROFILE_TAB_X && canvasX <= PROFILE_TAB_X + PAGE_TAB_WIDTH) {
        return { type: 'switch-page', page: 'profile' }
      }
      if (canvasX >= CALENDAR_TAB_X && canvasX <= CALENDAR_TAB_X + PAGE_TAB_WIDTH) {
        return { type: 'switch-page', page: 'calendar' }
      }
    }
    if (board.mode !== 'profile' || board.state !== 'ready') return null

    const { active, history } = getPersonalApplicationGroups(board)
    const firstRowY = 788
    for (let index = 0; index < active.length; index += 1) {
      const application = active[index]
      const rowY = firstRowY + index * 112
      if (
        application && canvasX >= 120
        && canvasX <= 904
        && contentY >= rowY
        && contentY <= rowY + 96
      ) {
        return { type: 'detail', application }
      }
    }
    const historyStart = firstRowY + (active.length ? active.length * 112 : 94) + 58
    for (let i = 0; i < history.length; i++) {
      const application = history[i]!
      if (canvasX >= 120 && canvasX <= 904 && contentY >= historyStart + i * 92 && contentY <= historyStart + i * 92 + 76) return { type: 'detail', application }
    }
    return null
  }

  const tick = () => {
    const now = performance.now()
    const deltaSeconds = Math.min((now - lastTickAt) / 1000, 0.05)
    lastTickAt = now
    let needsRender = false

    if (fadePhase === 'out') {
      fadeOpacity = Math.max(0, fadeOpacity - deltaSeconds / 0.22)
      needsRender = true
      if (fadeOpacity <= 0) {
        if (pendingBoard) {
          board = pendingBoard
          pendingBoard = null
          contentHeight = calculateContentHeight(board)
          if (!board.venues.some((venue) => venue.id === selectedVenueId)) {
            selectedVenueId = board.venues[0]?.id ?? null
          }
        } else {
          selectedVenueId = pendingVenueId
          pendingVenueId = null
        }
        currentScroll = 0
        targetScroll = 0
        fadePhase = 'in'
      }
    } else if (fadePhase === 'in') {
      fadeOpacity = Math.min(1, fadeOpacity + deltaSeconds / 0.32)
      needsRender = true
      if (fadeOpacity >= 1) fadePhase = 'idle'
    }

    const difference = targetScroll - currentScroll
    if (Math.abs(difference) < 0.1) {
      if (currentScroll !== targetScroll) {
        currentScroll = targetScroll
        needsRender = true
      }
    } else {
      currentScroll += difference * 0.14
      needsRender = true
    }
    if (needsRender) render()
  }

  render()
  return {
    texture,
    updateUsageBoard,
    transitionUsageBoard,
    selectVenue,
    scrollBy,
    pointerMove,
    getApplicationTarget,
    getPageAction,
    pointerLeave: clearHover,
    tick,
  }
}
