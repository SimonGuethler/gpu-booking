import { computed, ref } from 'vue'

import { endOfWeek, formatGermanDate, startOfWeek } from '../calendar/logic'

export function useWeek() {
  const weekStart = ref<Date>(startOfWeek(new Date()))

  const weekEnd = computed(() => endOfWeek(weekStart.value))
  const weekLabel = computed(() => {
    const s = weekStart.value
    const e = new Date(weekEnd.value.getTime() - 86_400_000)
    return `${formatGermanDate(s)} – ${formatGermanDate(e)}`
  })

  function previousWeek(): void {
    const previous = new Date(weekStart.value)
    previous.setDate(previous.getDate() - 7)
    weekStart.value = previous
  }

  function nextWeek(): void {
    const next = new Date(weekStart.value)
    next.setDate(next.getDate() + 7)
    weekStart.value = next
  }

  function goToday(): void {
    weekStart.value = startOfWeek(new Date())
  }

  return { weekStart, weekEnd, weekLabel, previousWeek, nextWeek, goToday }
}
