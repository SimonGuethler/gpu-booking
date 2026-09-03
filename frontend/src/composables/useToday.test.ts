import { effectScope } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { startOfLocalDay, useToday } from './useToday'

afterEach(() => {
  vi.useRealTimers()
})

describe('useToday', () => {
  it('berechnet lokale Tagesgrenzen', () => {
    const start = startOfLocalDay(new Date(2026, 5, 7, 14, 30))
    expect(start).toEqual(new Date(2026, 5, 7, 0, 0, 0, 0))
  })

  it('wechselt die reaktiven Grenzen exakt nach Mitternacht', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 5, 7, 23, 59, 59, 900))
    const scope = effectScope()
    const today = scope.run(() => useToday())!

    expect(today.todayStart.value).toEqual(new Date(2026, 5, 7, 0, 0, 0, 0))
    vi.advanceTimersByTime(200)
    expect(today.todayStart.value).toEqual(new Date(2026, 5, 8, 0, 0, 0, 0))
    expect(today.todayEnd.value).toEqual(new Date(2026, 5, 9, 0, 0, 0, 0))

    scope.stop()
  })
})
