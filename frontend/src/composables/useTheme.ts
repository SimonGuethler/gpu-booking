import { computed, ref } from 'vue'

export type AppTheme = 'light' | 'dark'

const STORAGE_KEY = 'gpu-booking-theme'
const theme = ref<AppTheme>('light')
let initialized = false

function storedTheme(): AppTheme | null {
  try {
    const value = globalThis.localStorage?.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

function systemTheme(): AppTheme {
  return globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(value: AppTheme): void {
  theme.value = value
  globalThis.document?.documentElement.classList.toggle('app-dark', value === 'dark')
  if (globalThis.document) globalThis.document.documentElement.style.colorScheme = value
}

export function initializeTheme(): void {
  if (initialized) return
  initialized = true
  applyTheme(storedTheme() ?? systemTheme())

  globalThis.matchMedia?.('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
    if (storedTheme() === null) applyTheme(event.matches ? 'dark' : 'light')
  })
}

export function useTheme() {
  initializeTheme()

  function toggleTheme(): void {
    const nextTheme: AppTheme = theme.value === 'dark' ? 'light' : 'dark'
    try {
      globalThis.localStorage?.setItem(STORAGE_KEY, nextTheme)
    } catch {
      // Die Auswahl gilt weiterhin für die aktuelle Sitzung.
    }
    applyTheme(nextTheme)
  }

  return {
    theme,
    isDark: computed(() => theme.value === 'dark'),
    toggleTheme,
  }
}
