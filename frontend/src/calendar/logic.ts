export const CAL_DAY_WIDTH = 170

export interface BookingDraft {
  start: Date
  end: Date
  gpuIds: number[]
  serverId: number | null
  mode: 'train' | 'cpu'
}

const germanDateFormatter = new Intl.DateTimeFormat('de-DE', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})
const germanTimeFormatter = new Intl.DateTimeFormat('de-DE', {
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

export function formatGermanDate(date: Date): string {
  return germanDateFormatter.format(date)
}

export function formatGermanTime(date: Date): string {
  return germanTimeFormatter.format(date)
}

export function formatGermanDateTime(date: Date): string {
  return `${formatGermanDate(date)}, ${formatGermanTime(date)} Uhr`
}

export function bookingMatchesResourceRow(
  row: { type: 'gpu' | 'cpu'; serverId: number | null; gpuId: number | null },
  booking: { mode: string; server_id: number | null; gpus: { id: number }[] },
): boolean {
  if (row.type === 'gpu') return booking.gpus.some((gpu) => gpu.id === row.gpuId)
  return booking.mode === 'cpu' && booking.server_id === row.serverId
}

export function msFromPointer(
  x: number,
  y: number,
  dayWidth: number,
  columnHeight: number,
  weekStart: Date,
): number {
  const day = Math.max(0, Math.min(6, Math.floor(x / dayWidth)))
  const hour = Math.max(0, Math.min(23.9999, (y / columnHeight) * 24))
  const d = new Date(weekStart)
  d.setDate(d.getDate() + day)
  d.setHours(0, 0, 0, 0)
  d.setMinutes(hour * 60)
  return d.getTime()
}

export function formatHourRange(startMs: number, endMs: number): string {
  const start = new Date(startMs)
  const end = new Date(endMs)
  const sameDay = start.toDateString() === end.toDateString()
  if (sameDay) return `${formatGermanTime(start)}–${formatGermanTime(end)} Uhr`
  return (
    `${formatGermanDate(start)}, ${formatGermanTime(start)} Uhr – ` +
    `${formatGermanDate(end)}, ${formatGermanTime(end)} Uhr`
  )
}

export function parseNaiveUtc(value: string): Date {
  return new Date(value.endsWith('Z') ? value : `${value}Z`)
}

export function formatLocalDateTimeRange(
  startAt: string,
  endAt: string,
  timeZone?: string,
): string {
  const formatter = new Intl.DateTimeFormat('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone,
  })
  return `${formatter.format(parseNaiveUtc(startAt))} Uhr – ${formatter.format(parseNaiveUtc(endAt))} Uhr`
}

export function toNaiveUtc(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}` +
    `T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:00`
  )
}

export function startOfWeek(date: Date): Date {
  const d = new Date(date)
  const day = (d.getDay() + 6) % 7
  d.setDate(d.getDate() - day)
  d.setHours(0, 0, 0, 0)
  return d
}

export function endOfWeek(weekStart: Date): Date {
  const d = new Date(weekStart)
  d.setDate(d.getDate() + 7)
  return d
}

export function snapToHour(date: Date): Date {
  const d = new Date(date)
  d.setMinutes(0, 0, 0)
  return d
}

export function snapRange(start: Date, end: Date): { start: Date; end: Date } {
  const snappedStart = snapToHour(start)
  let snappedEnd = snapToHour(end)
  if (snappedEnd <= snappedStart) snappedEnd = new Date(snappedStart.getTime() + 3600_000)
  return { start: snappedStart, end: snappedEnd }
}

export interface SegmentedBlock {
  start: number
  end: number
}

export function segmentByDay(
  start: number,
  end: number,
  dayStart: number,
  dayEnd: number,
): SegmentedBlock | null {
  const from = Math.max(start, dayStart)
  const to = Math.min(end, dayEnd)
  if (to <= from) return null
  return { start: from, end: to }
}

export interface Interval {
  start: number
  end: number
}

export interface ColumnLayout {
  column: number
  total: number
}

export interface CalendarBlockPosition {
  topPercent: number
  heightPercent: number
  leftPx: number
  widthPx: number
}

export function selectionRowIndexes(startIndex: number, currentIndex: number): number[] {
  if (startIndex < 0 || currentIndex < 0) return []
  const from = Math.min(startIndex, currentIndex)
  const to = Math.max(startIndex, currentIndex)
  return Array.from({ length: to - from + 1 }, (_, offset) => from + offset)
}

export function calendarBlockPosition(options: {
  dayIndex: number
  start: number
  end: number
  dayStart: number
  dayEnd: number
  dayWidth: number
  column: number
  total: number
  exclusive: boolean
}): CalendarBlockPosition {
  const dayDuration = options.dayEnd - options.dayStart
  const topPercent = ((options.start - options.dayStart) / dayDuration) * 100
  const heightPercent = Math.max(((options.end - options.start) / dayDuration) * 100, 2.5)
  const columnWidth = options.exclusive ? options.dayWidth : options.dayWidth / options.total
  const columnOffset = options.exclusive ? 0 : options.column * columnWidth

  return {
    topPercent,
    heightPercent,
    leftPx: options.dayIndex * options.dayWidth + columnOffset + 3,
    widthPx: Math.max(columnWidth - 6, 12),
  }
}

export function layoutColumns(intervals: Interval[]): ColumnLayout[] {
  const indexed = intervals
    .map((interval, index) => ({ interval, index }))
    .sort((a, b) => a.interval.start - b.interval.start || a.interval.end - b.interval.end)

  const result: ColumnLayout[] = new Array(intervals.length)
  const active: { end: number; column: number }[] = []
  let maxColumn = 0

  for (const { interval, index } of indexed) {
    for (let i = active.length - 1; i >= 0; i--) {
      if (active[i].end <= interval.start) active.splice(i, 1)
    }
    const used = new Set(active.map((a) => a.column))
    let column = 0
    while (used.has(column)) column++
    active.push({ end: interval.end, column })
    maxColumn = Math.max(maxColumn, column)
    result[index] = { column, total: 0 }
  }

  const total = maxColumn + 1
  for (const layout of result) layout.total = total
  return result
}
