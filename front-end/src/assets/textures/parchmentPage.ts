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

export interface VenueUsageBoard {
  mode: 'management' | 'user-matrix' | 'user-detail'
  date: string
  rangeStart?: string
  rangeEnd?: string
  state: 'loading' | 'ready' | 'error'
  venues: VenueUsageItem[]
  error?: string
}

export interface ParchmentPageCanvas {
  texture: THREE.CanvasTexture
  updateUsageBoard: (board: VenueUsageBoard) => void
  selectVenue: (venueId: number) => void
  scrollBy: (delta: number) => void
  tick: () => void
}

const PAGE_WIDTH = 1024
const PAGE_HEIGHT = 1400
const CONTENT_TOP = 660
const CARD_GAP = 24

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
  if (board.mode === 'user-matrix') return 2400
  if (board.mode === 'user-detail') return 2550
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
) {
  roundedRect(ctx, x, 430, 238, 118, 18)
  ctx.fillStyle = 'rgba(255, 252, 239, 0.3)'
  ctx.fill()
  ctx.strokeStyle = 'rgba(92, 72, 47, 0.16)'
  ctx.lineWidth = 2
  ctx.stroke()

  ctx.textAlign = 'left'
  ctx.fillStyle = '#58452f'
  ctx.font = '600 48px "Palatino Linotype", Palatino, Georgia, serif'
  ctx.fillText(String(value).padStart(2, '0'), x + 25, 492)
  ctx.fillStyle = 'rgba(77, 60, 40, 0.6)'
  ctx.font = '24px "Songti SC", "STSong", serif'
  ctx.fillText(label, x + 94, 491)
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
  const overlapping = events.filter((event) => {
    if (getEventDateKey(event.startAt) !== dateKey) return false
    return getHourValue(event.startAt) < slotEnd && getHourValue(event.endAt) > slotStart
  })
  if (!overlapping.length) return 'rgba(96, 116, 95, 0.1)'
  if (overlapping.some((event) => ['confirmed', 'reserved'].includes(event.status))) {
    return '#60745f'
  }
  if (overlapping.some((event) => event.status === 'supplement_required')) return '#9a6152'
  if (overlapping.some((event) => event.status === 'pending_admin_pre_review')) return '#737583'
  return '#ad8248'
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
  ctx.fillText('MEIYU  ·  VENUE AVAILABILITY', 120, 208)
  ctx.fillStyle = '#58452f'
  ctx.font = '600 70px "Songti SC", "STSong", Georgia, serif'
  ctx.fillText('场地占用日历', 120, 300)
  ctx.fillStyle = 'rgba(77, 60, 40, 0.62)'
  ctx.font = '27px "Songti SC", "STSong", serif'
  ctx.fillText(
    `${board.rangeStart || board.date}  —  ${board.rangeEnd || board.date} · 前后各15天`,
    120,
    354,
  )

  ctx.strokeStyle = 'rgba(93, 73, 48, 0.25)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(120, 392)
  ctx.lineTo(904, 392)
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
  const todayIndex = Math.max(0, rangeDates.indexOf(board.date))
  const displayDates = [
    ...rangeDates.slice(todayIndex),
    ...rangeDates.slice(0, todayIndex).reverse(),
  ]
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

function drawUserVenueDetailBoard(
  ctx: CanvasRenderingContext2D,
  board: VenueUsageBoard,
  selectedVenueId: number | null,
  scrollY: number,
  contentHeight: number,
) {
  ctx.clearRect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
  const selectedVenue =
    board.venues.find((venue) => venue.id === selectedVenueId) ?? board.venues[0]
  ctx.save()
  ctx.translate(0, -scrollY)

  ctx.textAlign = 'left'
  ctx.fillStyle = 'rgba(89, 70, 47, 0.58)'
  ctx.font = '600 20px "Palatino Linotype", Palatino, serif'
  ctx.fillText('MEIYU  ·  VENUE SCHEDULE', 120, 208)
  ctx.fillStyle = '#58452f'
  ctx.font = '600 62px "Songti SC", "STSong", Georgia, serif'
  ctx.fillText(selectedVenue?.name || '场地使用详情', 120, 296)
  ctx.fillStyle = 'rgba(77, 60, 40, 0.62)'
  ctx.font = '25px "Songti SC", "STSong", serif'
  ctx.fillText(
    `${board.rangeStart || board.date}  —  ${board.rangeEnd || board.date} · 点击两侧书签切换场地`,
    120,
    352,
  )

  ctx.strokeStyle = 'rgba(93, 73, 48, 0.25)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(120, 392)
  ctx.lineTo(904, 392)
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
  const todayIndex = Math.max(0, rangeDates.indexOf(board.date))
  const displayDates = [
    ...rangeDates.slice(todayIndex),
    ...rangeDates.slice(0, todayIndex).reverse(),
  ]
  const occupiedDates = new Set(selectedVenue.events.map((event) => getEventDateKey(event.startAt)))
  drawStat(ctx, 120, rangeDates.length, '查阅天数')
  drawStat(ctx, 393, occupiedDates.size, '占用天数')
  drawStat(ctx, 666, rangeDates.length - occupiedDates.size, '可申请天数')

  drawRangeLegend(ctx, 120, 'rgba(96, 116, 95, 0.1)', '空闲')
  drawRangeLegend(ctx, 254, '#60745f', '已占用')
  drawRangeLegend(ctx, 414, '#ad8248', '预占用')
  drawRangeLegend(ctx, 574, '#737583', '审核中')
  drawRangeLegend(ctx, 734, '#9a6152', '待补充')

  const tableX = 120
  const tableY = 632
  const tableWidth = 784
  const headerHeight = 60
  const rowHeight = 54
  roundedRect(ctx, tableX, tableY, tableWidth, headerHeight, 16)
  ctx.fillStyle = 'rgba(88, 69, 47, 0.08)'
  ctx.fill()
  ctx.fillStyle = 'rgba(77, 60, 40, 0.54)'
  ctx.font = '600 20px "Songti SC", "STSong", serif'
  ctx.textAlign = 'left'
  ctx.fillText('日期', tableX + 16, tableY + 38)
  ctx.textAlign = 'center'
  ctx.font = '18px "Palatino Linotype", Palatino, serif'
  ;[8, 12, 16, 20, 22].forEach((hour) => {
    const x = 278 + ((hour - 8) / 14) * 438
    ctx.fillText(`${String(hour).padStart(2, '0')}:00`, x, tableY + 38)
  })
  ctx.textAlign = 'right'
  ctx.font = '600 20px "Songti SC", "STSong", serif'
  ctx.fillText('申请状态', tableX + tableWidth - 16, tableY + 38)

  displayDates.forEach((dateKey, index) => {
    const date = new Date(`${dateKey}T12:00:00`)
    const y = tableY + headerHeight + index * rowHeight
    const dayEvents = selectedVenue.events.filter(
      (event) => getEventDateKey(event.startAt) === dateKey,
    )
    const isToday = dateKey === board.date
    const isPast = dateKey < board.date
    const isWeekend = date.getDay() === 0 || date.getDay() === 6

    if (isToday) {
      roundedRect(ctx, tableX, y + 3, tableWidth, rowHeight - 6, 11)
      ctx.fillStyle = 'rgba(173, 130, 72, 0.13)'
      ctx.fill()
      ctx.strokeStyle = 'rgba(137, 91, 45, 0.42)'
      ctx.lineWidth = 2
      ctx.stroke()
    } else if (isWeekend) {
      ctx.fillStyle = 'rgba(88, 69, 47, 0.035)'
      ctx.fillRect(tableX, y, tableWidth, rowHeight)
    }

    ctx.globalAlpha = isPast ? 0.74 : 1
    const weekday = ['日', '一', '二', '三', '四', '五', '六'][date.getDay()]
    const label = `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')} 周${weekday}`
    ctx.textAlign = 'left'
    ctx.fillStyle = isToday ? '#765525' : 'rgba(77, 60, 40, 0.72)'
    ctx.font = `${isToday ? '600' : '400'} 21px "Palatino Linotype", "Songti SC", serif`
    ctx.fillText(isToday ? `${label} · 今` : label, tableX + 14, y + 34)

    drawVenueDetailTimeline(ctx, dayEvents, y + 21)
    ctx.textAlign = 'right'
    if (!dayEvents.length) {
      ctx.fillStyle = '#60745f'
      ctx.font = '600 20px "Songti SC", "STSong", serif'
      ctx.fillText('全天可申请', tableX + tableWidth - 14, y + 34)
    } else {
      const mainStyle = statusStyles[dayEvents[0]?.status ?? 'confirmed'] ?? statusStyles.confirmed
      ctx.fillStyle = mainStyle.text
      ctx.font = '600 19px "Songti SC", "STSong", serif'
      ctx.fillText(
        dayEvents.length > 1 ? `${dayEvents.length} 段占用` : mainStyle.label,
        tableX + tableWidth - 14,
        y + 34,
      )
    }
    ctx.globalAlpha = 1

    ctx.strokeStyle = 'rgba(93, 73, 48, 0.075)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(tableX, y + rowHeight)
    ctx.lineTo(tableX + tableWidth, y + rowHeight)
    ctx.stroke()
  })

  const footerY = tableY + headerHeight + displayDates.length * rowHeight + 82
  ctx.textAlign = 'center'
  ctx.fillStyle = 'rgba(77, 60, 40, 0.45)'
  ctx.font = '22px "Songti SC", "STSong", serif'
  ctx.fillText('列表顺序：今天 → 未来15天 → 过去15天', PAGE_WIDTH / 2, footerY)
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
) {
  if (board.mode === 'user-detail') {
    drawUserVenueDetailBoard(ctx, board, selectedVenueId, scrollY, contentHeight)
    return
  }
  if (board.mode === 'user-matrix') {
    drawUserRangeBoard(ctx, board, scrollY, contentHeight)
    return
  }
  ctx.clearRect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
  ctx.save()
  ctx.translate(0, -scrollY)

  ctx.textAlign = 'left'
  ctx.fillStyle = 'rgba(89, 70, 47, 0.58)'
  ctx.font = '600 20px "Palatino Linotype", Palatino, serif'
  ctx.fillText('MEIYU  ·  VENUE BOARD', 120, 208)

  ctx.fillStyle = '#58452f'
  ctx.font = '600 70px "Songti SC", "STSong", Georgia, serif'
  ctx.fillText('场地使用一览', 120, 300)

  ctx.fillStyle = 'rgba(77, 60, 40, 0.62)'
  ctx.font = '27px "Songti SC", "STSong", serif'
  ctx.fillText(formatDate(board.date), 120, 354)

  ctx.strokeStyle = 'rgba(93, 73, 48, 0.25)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(120, 392)
  ctx.lineTo(904, 392)
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

export function createParchmentPageCanvas(maxAnisotropy: number): ParchmentPageCanvas {
  const canvas = document.createElement('canvas')
  canvas.width = PAGE_WIDTH
  canvas.height = PAGE_HEIGHT
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Canvas 2D context is unavailable')

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
    drawParchment(context, board, currentScroll, contentHeight, selectedVenueId)
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
    pendingVenueId = null
    fadePhase = 'idle'
    fadeOpacity = 1
    currentScroll = 0
    targetScroll = 0
    render()
  }

  const selectVenue = (venueId: number) => {
    if (venueId === selectedVenueId || !board.venues.some((venue) => venue.id === venueId)) return
    pendingVenueId = venueId
    fadePhase = 'out'
  }

  const scrollBy = (delta: number) => {
    const maxScroll = Math.max(0, contentHeight - PAGE_HEIGHT)
    targetScroll = THREE.MathUtils.clamp(targetScroll + delta, 0, maxScroll)
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
        selectedVenueId = pendingVenueId
        pendingVenueId = null
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
  return { texture, updateUsageBoard, selectVenue, scrollBy, tick }
}
