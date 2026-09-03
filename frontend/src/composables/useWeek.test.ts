import { afterEach, describe, expect, it, vi } from 'vitest'

import { useWeek } from './useWeek'

afterEach(() => {
  vi.useRealTimers()
})

describe('useWeek', () => {
  it('behält die gewählte Woche über Montag hinweg bis Heute gewählt wird', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 5, 7, 23, 59))
    const week = useWeek()
    const selectedWeek = week.weekStart.value.getTime()

    vi.setSystemTime(new Date(2026, 5, 8, 0, 1))
    expect(week.weekStart.value.getTime()).toBe(selectedWeek)

    week.goToday()
    expect(week.weekStart.value).toEqual(new Date(2026, 5, 8, 0, 0, 0, 0))
  })
})
