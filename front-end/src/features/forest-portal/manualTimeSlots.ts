export interface ManualTimeSlot {
  start_at: string
  end_at: string
}

export const MAX_MANUAL_TIME_SLOTS = 20

export function dailyTimeSlots(startDate: string, endDate: string, startTime: string, endTime: string): ManualTimeSlot[] {
  const parseDate = (value: string) => {
    const date = new Date(`${value}T00:00:00Z`)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== value) {
      throw new Error('请填写有效的起止日期')
    }
    return date.getTime()
  }
  const first = parseDate(startDate), last = parseDate(endDate)
  if (last < first) throw new Error('结束日期不能早于开始日期')
  if (![startTime, endTime].every(value => /^([01]\d|2[0-3]):[0-5]\d$/.test(value))) {
    throw new Error('请填写每天的开始和结束时间')
  }
  if (endTime <= startTime) throw new Error('每天结束时间须晚于开始时间；跨天借用请单独添加时段')
  const count = (last - first) / 86400000 + 1
  if (count > MAX_MANUAL_TIME_SLOTS) throw new Error(`一次最多填写 ${MAX_MANUAL_TIME_SLOTS} 个时段，请缩短日期范围`)
  return Array.from({ length: count }, (_, index) => {
    const date = new Date(first + index * 86400000).toISOString().slice(0, 10)
    return { start_at: `${date}T${startTime}`, end_at: `${date}T${endTime}` }
  })
}

export function mergeTimeSlots(existing: ManualTimeSlot[], added: ManualTimeSlot[]): ManualTimeSlot[] {
  const slots = existing.filter(slot => slot.start_at || slot.end_at)
  if (slots.some(slot => !slot.start_at || !slot.end_at)) throw new Error('请先补全或移除列表中未填写完整的时段')
  const unique = new Map([...slots, ...added].map(slot => [`${slot.start_at}/${slot.end_at}`, slot]))
  const result = [...unique.values()].sort((a, b) => a.start_at.localeCompare(b.start_at))
  if (result.length > MAX_MANUAL_TIME_SLOTS) throw new Error(`合并后超过 ${MAX_MANUAL_TIME_SLOTS} 个时段，请缩短日期范围或移除多余时段`)
  for (let index = 0; index < result.length; index++) {
    const slot = result[index]!
    if (slot.end_at <= slot.start_at) throw new Error('列表中的结束时间须晚于开始时间')
    if (index && slot.start_at < result[index - 1]!.end_at) throw new Error('批量时段与列表中的时段重叠，请先调整或移除重叠时段')
  }
  return result
}
