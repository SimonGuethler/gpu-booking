import { describe, expect, it } from 'vitest'
import { computed, ref } from 'vue'

import type { BookingFormValues } from './validation'
import { buildDailyIntervals, createBookingSchema } from './validation'
import { addHours, roundToHour } from '../utils/time'

function validValues(overrides: Record<string, unknown> = {}): BookingFormValues {
  const start = roundToHour(new Date())
  return {
    mode: 'train',
    projectId: 1,
    serverId: null,
    gpuIds: [2],
    start,
    end: addHours(start, 2),
    schedule: 'continuous',
    dailyStart: '08:00',
    dailyEnd: '16:00',
    description: '',
    ...overrides,
  } as BookingFormValues
}

function errorsFor(values: BookingFormValues, maxBookingDays = 7): string[] {
  const schema = createBookingSchema(false, maxBookingDays)
  const result = schema.safeParse(values)
  if (result.success) return []
  return result.error.issues.map((issue) => issue.message)
}

describe('createBookingSchema (Nutzer, 7-Tage-Limit)', () => {
  it('gültige Buchung hat keine Fehler', () => {
    expect(errorsFor(validValues())).toEqual([])
  })

  it('fehlendes Projekt → Pflichtfehler', () => {
    const errors = errorsFor(validValues({ projectId: null }))
    expect(errors).toContain('Bitte ein Projekt wählen.')
  })

  it('train ohne GPUs → Pflichtfehler', () => {
    const errors = errorsFor(validValues({ gpuIds: [] }))
    expect(errors).toContain('Bitte mindestens eine GPU wählen.')
  })

  it('cpu mit Server und ohne GPUs → kein Fehler', () => {
    expect(errorsFor(validValues({ mode: 'cpu', serverId: 1, gpuIds: [] }))).toEqual([])
  })

  it('cpu ohne Server → Pflichtfehler', () => {
    const errors = errorsFor(validValues({ mode: 'cpu', serverId: null, gpuIds: [] }))
    expect(errors).toContain('Bitte einen Server wählen.')
  })

  it('Start mit Minuten → Fehler', () => {
    const start = roundToHour(new Date())
    start.setMinutes(30)
    const errors = errorsFor(validValues({ start }))
    expect(errors).toContain('Start muss auf einer vollen Stunde liegen.')
  })

  it('Start oder Ende mit Millisekunden → Fehler', () => {
    const start = roundToHour(new Date())
    start.setMilliseconds(1)
    expect(errorsFor(validValues({ start }))).toContain(
      'Start muss auf einer vollen Stunde liegen.',
    )

    const end = addHours(roundToHour(new Date()), 2)
    end.setMilliseconds(1)
    expect(errorsFor(validValues({ end }))).toContain('Ende muss auf einer vollen Stunde liegen.')
  })

  it('Ende vor Start → Fehler', () => {
    const start = roundToHour(new Date())
    const errors = errorsFor(validValues({ start: addHours(start, 4), end: addHours(start, 2) }))
    expect(errors).toContain('Ende muss nach dem Start liegen.')
  })

  it('kürzer als 1 Stunde → Fehler', () => {
    const start = roundToHour(new Date())
    const errors = errorsFor(validValues({ start, end: start }))
    expect(errors).toContain('Mindestdauer ist 1 Stunde.')
  })

  it('über 7 Tage für Nutzer → Fehler', () => {
    const start = roundToHour(new Date())
    const errors = errorsFor(validValues({ start, end: addHours(start, 8 * 24) }))
    expect(errors).toContain('Maximale Dauer ist 7 Tage (168 h).')
  })

  it('genau 7 Tage für Nutzer → ok', () => {
    const start = roundToHour(new Date())
    expect(errorsFor(validValues({ start, end: addHours(start, 7 * 24) }))).toEqual([])
  })

  it('verwendet das konfigurierte Dauerlimit', () => {
    const start = roundToHour(new Date())
    expect(errorsFor(validValues({ start, end: addHours(start, 2 * 24) }), 1)).toContain(
      'Maximale Dauer ist 1 Tag (24 h).',
    )
  })
})

describe('tägliche Buchungsintervalle', () => {
  it('kürzt den ersten und letzten Tag auf den gezogenen Zeitraum', () => {
    const intervals = buildDailyIntervals(
      new Date(2026, 5, 1, 10),
      new Date(2026, 5, 3, 12),
      '08:00',
      '16:00',
    )

    expect(intervals.map(({ start, end }) => [start.getDate(), start.getHours(), end.getHours()])).toEqual([
      [1, 10, 16],
      [2, 8, 16],
      [3, 8, 12],
    ])
  })

  it('überspringt Tage, an denen die Tageszeit außerhalb des Rahmens liegt', () => {
    const intervals = buildDailyIntervals(
      new Date(2026, 5, 1, 18),
      new Date(2026, 5, 2, 12),
      '08:00',
      '16:00',
    )
    expect(intervals).toHaveLength(1)
    expect(intervals[0].start.getHours()).toBe(8)
    expect(intervals[0].end.getHours()).toBe(12)
  })

  it('validiert Reihenfolge und volle Stunden', () => {
    expect(errorsFor(validValues({ schedule: 'daily', dailyStart: '16:00', dailyEnd: '08:00' }))).toContain(
      'Das tägliche Ende muss nach dem täglichen Start liegen.',
    )
    expect(errorsFor(validValues({ schedule: 'daily', dailyStart: '08:30' }))).toContain(
      'Der tägliche Start muss auf einer vollen Stunde liegen.',
    )
  })
})

describe('createBookingSchema (Admin, ohne Limit)', () => {
  it('über 7 Tage → ok', () => {
    const start = roundToHour(new Date())
    const values = validValues({ start, end: addHours(start, 14 * 24) })
    const schema = createBookingSchema(true, 7)
    expect(schema.safeParse(values).success).toBe(true)
  })

  it('gpuIds-Pflicht bleibt bestehen', () => {
    const schema = createBookingSchema(true, 7)
    const result = schema.safeParse(validValues({ gpuIds: [] }))
    expect(result.success).toBe(false)
    expect(result.error!.issues.some((i) => i.path[0] === 'gpuIds')).toBe(true)
  })
})

describe('reaktiver Rollenwechsel', () => {
  it('aktualisiert das Dauerlimit, sobald der Adminstatus geladen wurde', () => {
    const isAdmin = ref(false)
    const schema = computed(() => createBookingSchema(isAdmin.value, 7))
    const start = roundToHour(new Date())
    const values = validValues({ start, end: addHours(start, 14 * 24) })

    expect(schema.value.safeParse(values).success).toBe(false)
    isAdmin.value = true
    expect(schema.value.safeParse(values).success).toBe(true)
  })
})
