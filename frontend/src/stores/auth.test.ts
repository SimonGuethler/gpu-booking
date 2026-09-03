import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { setCsrfToken } from '../api/client'
import { useAuthStore } from './auth'

const USER = {
  id: 1,
  display_name: 'Admin',
  email: 'admin@example.local',
  role: 'admin',
  color: '#01adb9',
  created_at: '2026-01-01T00:00:00',
}

describe('Cookie-Session im Auth-Store', () => {
  beforeEach(() => {
    setCsrfToken(null)
    setActivePinia(createPinia())
  })

  afterEach(() => {
    setCsrfToken(null)
    vi.unstubAllGlobals()
  })

  it('lädt den aktuellen Admin vor der Routen-Autorisierung', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(USER), {
          status: 200,
          headers: { 'X-CSRF-Token': 'csrf-token' },
        }),
      ),
    )

    const auth = useAuthStore()
    await auth.initialize()

    expect(auth.initialized).toBe(true)
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.isAdmin).toBe(true)
  })

  it('bleibt bei fehlender oder abgelaufener Session abgemeldet', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Ungültige Session.' }), { status: 401 }),
      ),
    )

    const auth = useAuthStore()
    await auth.initialize()

    expect(auth.initialized).toBe(true)
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
  })

  it('löscht die serverseitige und lokale Session beim Logout', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: 'api-token', token_type: 'bearer', user: USER }), {
          status: 200,
          headers: { 'X-CSRF-Token': 'csrf-token' },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    const auth = useAuthStore()
    await auth.login('admin@example.local', 'password123')
    expect(auth.isAuthenticated).toBe(true)

    await auth.logout()
    expect(auth.isAuthenticated).toBe(false)
    expect(fetchMock.mock.calls[1][0]).toContain('/auth/logout')
  })
})
