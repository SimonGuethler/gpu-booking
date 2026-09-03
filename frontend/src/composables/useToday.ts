import { computed, getCurrentScope, onScopeDispose, readonly, ref } from 'vue'

const MIDNIGHT_BUFFER_MS = 25

export function startOfLocalDay(value: Date): Date {
  const start = new Date(value)
  start.setHours(0, 0, 0, 0)
  return start
}

export function useToday(now: () => Date = () => new Date()) {
  const todayStart = ref(startOfLocalDay(now()))
  const todayEnd = computed(() => {
    const end = new Date(todayStart.value)
    end.setDate(end.getDate() + 1)
    return end
  })
  let timer: ReturnType<typeof setTimeout> | null = null

  function scheduleNextDay(): void {
    if (timer !== null) globalThis.clearTimeout(timer)
    const current = now()
    const nextDay = startOfLocalDay(current)
    nextDay.setDate(nextDay.getDate() + 1)
    timer = globalThis.setTimeout(
      refresh,
      Math.max(0, nextDay.getTime() - current.getTime()) + MIDNIGHT_BUFFER_MS,
    )
  }

  function refresh(): void {
    todayStart.value = startOfLocalDay(now())
    scheduleNextDay()
  }

  function handleVisibilityChange(): void {
    if (document.visibilityState === 'visible') refresh()
  }

  scheduleNextDay()
  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', handleVisibilityChange)
  }

  if (getCurrentScope()) {
    onScopeDispose(() => {
      if (timer !== null) globalThis.clearTimeout(timer)
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', handleVisibilityChange)
      }
    })
  }

  return { todayStart: readonly(todayStart), todayEnd }
}
