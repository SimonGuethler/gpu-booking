import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AUTH_UNAUTHORIZED_EVENT, get, post, setCsrfToken } from './client'

describe('Cookie-Authentifizierung', () => {
  let browserWindow: EventTarget

  beforeEach(() => {
    setCsrfToken(null)
    browserWindow = new EventTarget()
    vi.stubGlobal('window', browserWindow)
  })

  afterEach(() => {
    setCsrfToken(null)
    vi.unstubAllGlobals()
  })

  it('sendet Cookies und den CSRF-Header, aber keinen Bearer-Token', async () => {
    setCsrfToken('csrf-token')
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await post('/projects', { name: 'Test' })

    const [, options] = fetchMock.mock.calls[0]
    const headers = options.headers as Headers
    expect(options.credentials).toBe('include')
    expect(headers.get('X-CSRF-Token')).toBe('csrf-token')
    expect(headers.has('Authorization')).toBe(false)
  })

  it('meldet eine abgelaufene Cookie-Session zentral ab', async () => {
    const unauthorized = vi.fn()
    browserWindow.addEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorized)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Session abgelaufen.' }), { status: 401 }),
      ),
    )

    await expect(get('/projects')).rejects.toMatchObject({ status: 401 })
    expect(unauthorized).toHaveBeenCalledOnce()
  })

  it('überlässt die erwartete 401-Initialisierung dem Auth-Store', async () => {
    const unauthorized = vi.fn()
    browserWindow.addEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorized)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Nicht angemeldet.' }), { status: 401 }),
      ),
    )

    await expect(get('/auth/me')).rejects.toMatchObject({ status: 401 })
    expect(unauthorized).not.toHaveBeenCalled()
  })

  it('emittiert bei fehlgeschlagenem Login kein Unauthorized-Event', async () => {
    const unauthorized = vi.fn()
    browserWindow.addEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorized)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'E-Mail-Adresse oder Passwort falsch.' }), {
          status: 401,
        }),
      ),
    )

    await expect(post('/auth/login', { email: 'alice@example.local' })).rejects.toMatchObject({
      status: 401,
    })
    expect(unauthorized).not.toHaveBeenCalled()
  })
})
