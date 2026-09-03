import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { get, post, setCsrfToken } from '../api/client'
import type { User } from '../api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const initialized = ref(false)
  let initialization: Promise<void> | null = null

  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(email: string, password: string): Promise<void> {
    loading.value = true
    try {
      const session = await post<{ user: User }>('/auth/login', {
        email,
        password,
      })
      user.value = session.user
    } finally {
      loading.value = false
    }
  }

  async function fetchMe(): Promise<void> {
    user.value = await get<User>('/auth/me')
  }

  function initialize(): Promise<void> {
    if (initialized.value) return Promise.resolve()
    if (initialization) return initialization

    initialization = (async () => {
      try {
        await fetchMe()
      } catch {
        clearSession()
      } finally {
        initialized.value = true
      }
    })()
    return initialization
  }

  function clearSession(): void {
    user.value = null
    setCsrfToken(null)
  }

  async function logout(): Promise<void> {
    try {
      await post<void>('/auth/logout', {})
    } finally {
      clearSession()
    }
  }

  return {
    user,
    loading,
    initialized,
    isAuthenticated,
    isAdmin,
    login,
    fetchMe,
    initialize,
    logout,
    clearSession,
  }
})
