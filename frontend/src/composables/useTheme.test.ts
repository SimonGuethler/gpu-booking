import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

function installBrowserMocks(stored: string | null, systemDark: boolean) {
  let changeListener: ((event: { matches: boolean }) => void) | undefined
  const classToggle = vi.fn()
  const setItem = vi.fn()

  vi.stubGlobal('localStorage', {
    getItem: vi.fn(() => stored),
    setItem,
  })
  vi.stubGlobal('document', {
    documentElement: {
      classList: { toggle: classToggle },
      style: { colorScheme: '' },
    },
  })
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({
      matches: systemDark,
      addEventListener: vi.fn(
        (_event: string, listener: (event: { matches: boolean }) => void) => {
          changeListener = listener
        },
      ),
    })),
  )

  return { classToggle, setItem, emitSystemChange: (matches: boolean) => changeListener?.({ matches }) }
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.resetModules()
})

describe('useTheme', () => {
  it('folgt ohne gespeicherte Auswahl dem Systemmodus', async () => {
    const browser = installBrowserMocks(null, true)
    const { useTheme } = await import('./useTheme')

    const state = useTheme()

    expect(state.isDark.value).toBe(true)
    expect(browser.classToggle).toHaveBeenLastCalledWith('app-dark', true)

    browser.emitSystemChange(false)
    await nextTick()
    expect(state.isDark.value).toBe(false)
  })

  it('bevorzugt die gespeicherte Auswahl und persistiert Umschaltungen', async () => {
    const browser = installBrowserMocks('light', true)
    const { useTheme } = await import('./useTheme')
    const state = useTheme()

    expect(state.isDark.value).toBe(false)
    state.toggleTheme()
    await nextTick()

    expect(state.isDark.value).toBe(true)
    expect(browser.setItem).toHaveBeenCalledWith('gpu-booking-theme', 'dark')
    expect(browser.classToggle).toHaveBeenLastCalledWith('app-dark', true)
  })
})
