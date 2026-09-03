import type { ApiError } from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL?.trim() || '/api').replace(/\/+$/, '')
export const AUTH_UNAUTHORIZED_EVENT = 'auth:unauthorized'
let csrfToken: string | null = null

try {
  // Entfernt bei der ersten Ausführung noch vorhandene Tokens aus älteren Versionen.
  globalThis.localStorage?.removeItem('gpu_booking_token')
} catch {
  // Web Storage kann durch Browserrichtlinien vollständig gesperrt sein.
}

export function setCsrfToken(token: string | null): void {
  csrfToken = token
}

export class ApiRequestError extends Error {
  status: number
  detail: string
  payload: unknown

  constructor(status: number, detail: string, payload: unknown = detail) {
    super(detail)
    this.status = status
    this.detail = detail
    this.payload = payload
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  const method = options.method?.toUpperCase() ?? 'GET'
  if (csrfToken && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers.set('X-CSRF-Token', csrfToken)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      credentials: 'include',
    })
  } catch {
    throw new ApiRequestError(0, 'Backend nicht erreichbar. Bitte Verbindung und API-Konfiguration prüfen.')
  }

  const responseCsrfToken = response.headers.get('X-CSRF-Token')
  if (responseCsrfToken) setCsrfToken(responseCsrfToken)

  if (response.status === 204) return undefined as T

  const text = await response.text()
  let body: unknown
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = null
  }

  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') {
      setCsrfToken(null)
      if (path !== '/auth/me' && typeof window !== 'undefined') {
        window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT))
      }
    }
    const payload = (body as ApiError | null)?.detail
    const detail =
      typeof payload === 'string'
        ? payload
        : typeof payload?.message === 'string'
          ? payload.message
          : `Fehler ${response.status}`
    throw new ApiRequestError(response.status, detail, payload)
  }
  return body as T
}

export const get = <T>(path: string) => api<T>(path)
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, { method: 'POST', body: JSON.stringify(body) })
export const patch = <T>(path: string, body: unknown) =>
  api<T>(path, { method: 'PATCH', body: JSON.stringify(body) })
export const del = (path: string) => api<void>(path, { method: 'DELETE' })
