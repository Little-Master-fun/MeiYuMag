export function getLocalDateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function cleanPurposeSummary(value: string | null) {
  if (!value) return '场地使用申请'
  return value.replace(/^\[DEMO_USAGE:[^\]]+\]\s*/, '')
}

export function offsetDate(date: Date, days: number) {
  const nextDate = new Date(date)
  nextDate.setDate(nextDate.getDate() + days)
  return nextDate
}
