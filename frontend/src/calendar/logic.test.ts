import { describe, expect, it } from 'vitest'

import {
  bookingMatchesResourceRow,
  calendarBlockPosition,
  formatGermanDate,
  formatGermanDateTime,
  formatGermanTime,
  formatLocalDateTimeRange,
  formatHourRange,
  layoutColumns,
  msFromPointer,
  parseNaiveUtc,
  selectionRowIndexes,
  segmentByDay,
  snapRange,
  snapToHour,
  startOfWeek,
  toNaiveUtc,
} from './logic'

describe('bookingMatchesResourceRow', () => {
  const assignedCpu = { mode: 'cpu', server_id: 2, gpus: [] }
  const unassignedCpu = { mode: 'cpu', server_id: null, gpus: [] }

  it('zeigt zugeordnete CPU-Buchungen nur am passenden Server', () => {
    expect(
      bookingMatchesResourceRow(
        { type: 'cpu', serverId: 2, gpuId: null },
        assignedCpu,
      ),
    ).toBe(true)
    expect(
      bookingMatchesResourceRow(
        { type: 'cpu', serverId: 3, gpuId: null },
        assignedCpu,
      ),
    ).toBe(false)
  })

  it('zeigt unzugeordnete CPU-Buchungen ausschließlich in der eigenen Zeile', () => {
    expect(
      bookingMatchesResourceRow(
        { type: 'cpu', serverId: null, gpuId: null },
        unassignedCpu,
      ),
    ).toBe(true)
    expect(
      bookingMatchesResourceRow(
        { type: 'cpu', serverId: 2, gpuId: null },
        unassignedCpu,
      ),
    ).toBe(false)
  })
})

describe('selectionRowIndexes', () => {
  it('liefert den zusammenhängenden Bereich in beide Richtungen', () => {
    expect(selectionRowIndexes(1, 3)).toEqual([1, 2, 3])
    expect(selectionRowIndexes(3, 1)).toEqual([1, 2, 3])
  })

  it('berechnet beim Zurückziehen einen frischen kleineren Bereich', () => {
    expect(selectionRowIndexes(1, 4)).toEqual([1, 2, 3, 4])
    expect(selectionRowIndexes(1, 2)).toEqual([1, 2])
    expect(selectionRowIndexes(-1, 2)).toEqual([])
  })
})

describe('calendarBlockPosition', () => {
  const base = {
    dayIndex: 2,
    start: new Date(2026, 5, 3, 9).getTime(),
    end: new Date(2026, 5, 3, 12).getTime(),
    dayStart: new Date(2026, 5, 3, 0).getTime(),
    dayEnd: new Date(2026, 5, 4, 0).getTime(),
    dayWidth: 170,
  }

  it('begrenzt exklusive Buchungen auf genau eine Tagesspalte', () => {
    const position = calendarBlockPosition({
      ...base,
      column: 0,
      total: 1,
      exclusive: true,
    })
    expect(position.leftPx).toBe(343)
    expect(position.widthPx).toBe(164)
    expect(position.topPercent).toBe(37.5)
    expect(position.heightPercent).toBe(12.5)
  })

  it('ordnet parallele geteilte Buchungen innerhalb des Tages nebeneinander an', () => {
    const position = calendarBlockPosition({
      ...base,
      column: 1,
      total: 2,
      exclusive: false,
    })
    expect(position.leftPx).toBe(428)
    expect(position.widthPx).toBe(79)
  })
})

describe('parseNaiveUtc / toNaiveUtc', () => {
  it('behandelt naive Strings als UTC', () => {
    const d = parseNaiveUtc('2026-06-01T14:00:00')
    expect(d.toISOString()).toBe('2026-06-01T14:00:00.000Z')
    expect(toNaiveUtc(d)).toBe('2026-06-01T14:00:00')
  })

  it('formatiert UTC-Konfliktzeiten in der gewählten lokalen Zeitzone', () => {
    const result = formatLocalDateTimeRange(
      '2026-06-01T10:00:00',
      '2026-06-01T12:00:00',
      'Europe/Berlin',
    )
    expect(result).toContain('12:00')
    expect(result).toContain('14:00')
    expect(result).toContain('01.06.2026')
    expect(result).not.toContain('10:00')
  })
})

describe('deutsche Datums- und Zeitformate', () => {
  const date = new Date(2026, 5, 1, 9, 5)

  it('formatiert Datum als DD.MM.YYYY', () => {
    expect(formatGermanDate(date)).toBe('01.06.2026')
  })

  it('formatiert Uhrzeit immer vierstellig im 24-Stunden-Format', () => {
    expect(formatGermanTime(date)).toBe('09:05')
    expect(formatGermanDateTime(date)).toBe('01.06.2026, 09:05 Uhr')
  })
})

describe('startOfWeek', () => {
  it('liefert Montag 00:00 lokaler Zeit', () => {
    const week = startOfWeek(new Date(2026, 5, 4)) // Donnerstag
    expect(week.getDay()).toBe(1)
    expect(week.getHours()).toBe(0)
    expect(week.getMinutes()).toBe(0)
  })
})

describe('snapToHour / snapRange', () => {
  it('rundet auf volle Stunde ab', () => {
    const d = new Date(2026, 5, 1, 14, 45)
    const snapped = snapToHour(d)
    expect(snapped.getHours()).toBe(14)
    expect(snapped.getMinutes()).toBe(0)
  })

  it('SnapRange: identische Zeiten ergeben mindestens 1 Stunde', () => {
    const start = new Date(2026, 5, 1, 14, 40)
    const { start: s, end: e } = snapRange(start, new Date(2026, 5, 1, 14, 59))
    expect(e.getTime() - s.getTime()).toBe(3_600_000)
    expect(s.getHours()).toBe(14)
    expect(e.getHours()).toBe(15)
  })

  it('SnapRange: Bereich über zwei Stunden bleibt erhalten', () => {
    const { start: s, end: e } = snapRange(
      new Date(2026, 5, 1, 14, 20),
      new Date(2026, 5, 1, 16, 30),
    )
    expect(e.getTime() - s.getTime()).toBe(2 * 3_600_000)
  })
})

describe('segmentByDay', () => {
  const day = new Date(2026, 5, 1).getTime()
  const dayEnd = new Date(2026, 5, 2).getTime()

  it('segmentiert über Mitternacht', () => {
    const seg = segmentByDay(
      new Date(2026, 5, 1, 22, 0).getTime(),
      new Date(2026, 5, 2, 2, 0).getTime(),
      day,
      dayEnd,
    )
    expect(seg).toEqual({ start: new Date(2026, 5, 1, 22, 0).getTime(), end: dayEnd })
  })

  it('liefert null außerhalb des Tages', () => {
    expect(segmentByDay(dayEnd, dayEnd + 3600_000, day, dayEnd)).toBeNull()
  })
})

describe('layoutColumns (dev-Nebeneinander)', () => {
  it('nicht überlappende Blöcke belegen Spalte 0', () => {
    const layouts = layoutColumns([
      { start: 10, end: 11 },
      { start: 11, end: 12 },
    ])
    expect(layouts.map((l) => l.column)).toEqual([0, 0])
  })

  it('drei überlappende Blöcke werden nebeneinander gelegt', () => {
    const layouts = layoutColumns([
      { start: 10, end: 13 },
      { start: 11, end: 14 },
      { start: 12, end: 15 },
    ])
    expect(new Set(layouts.map((l) => l.column)).size).toBe(3)
    expect(layouts.every((l) => l.total === 3)).toBe(true)
  })

  it('Kette: zwei gleichzeitige, dann dritter dazwischen', () => {
    const layouts = layoutColumns([
      { start: 10, end: 16 },
      { start: 10, end: 12 },
      { start: 12, end: 14 },
    ])
    const columns = layouts.map((l) => l.column)
    expect(new Set(columns).size).toBe(2)
    expect(columns[0]).toBe(1)
    expect(columns[1]).toBe(0)
    expect(columns[2]).toBe(0)
  })
})

describe('formatHourRange', () => {
  it('formatiert Zeitraum innerhalb eines Tages', () => {
    const start = new Date(2026, 5, 1, 9, 0).getTime()
    const end = new Date(2026, 5, 1, 11, 30).getTime()
    expect(formatHourRange(start, end)).toBe('09:00–11:30 Uhr')
  })

  it('formatiert Zeitraum über Mitternacht mit Datumsangabe', () => {
    const start = new Date(2026, 5, 1, 22, 0).getTime()
    const end = new Date(2026, 5, 2, 2, 0).getTime()
    expect(formatHourRange(start, end)).toContain('22:00')
    expect(formatHourRange(start, end)).toContain('02:00')
    expect(formatHourRange(start, end)).toBe(
      '01.06.2026, 22:00 Uhr – 02.06.2026, 02:00 Uhr',
    )
  })
})

describe('msFromPointer', () => {
  const weekStart = startOfWeek(new Date(2026, 5, 1)) // Montag 00:00

  it('Position am Montag um 12:00', () => {
    const ms = msFromPointer(0, 132, 170, 264, weekStart)
    expect(ms).toBe(new Date(2026, 5, 1, 12, 0).getTime())
  })

  it('Position am Donnerstag um 07:30', () => {
    const ms = msFromPointer(3 * 170, 66 + 16.5, 170, 264, weekStart)
    expect(ms).toBe(new Date(2026, 5, 4, 7, 30).getTime())
  })

  it('Position am Sonntag um 23:59', () => {
    const d = new Date(msFromPointer(6 * 170, 263.9, 170, 264, weekStart))
    expect(d.getDay()).toBe(0)
    expect(d.getHours()).toBe(23)
    expect(d.getMinutes()).toBe(59)
  })
})
