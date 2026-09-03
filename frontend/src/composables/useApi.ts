import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'

import { get } from '../api/client'
import type { AppConfig, Booking, Project, Server, User, UserDirectoryEntry } from '../api/types'
import { toNaiveUtc } from '../calendar/logic'

export function useServers() {
  return useQuery({
    queryKey: ['servers'],
    queryFn: () => get<Server[]>('/servers'),
  })
}

export function useAppConfig() {
  return useQuery({
    queryKey: ['app-config'],
    queryFn: () => get<AppConfig>('/config'),
    staleTime: Number.POSITIVE_INFINITY,
  })
}

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => get<Project[]>('/projects'),
  })
}

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => get<User[]>('/users'),
  })
}

export function useUserDirectory() {
  return useQuery({
    queryKey: ['user-directory'],
    queryFn: () => get<UserDirectoryEntry[]>('/users/directory'),
  })
}

export function useColors() {
  return useQuery({
    queryKey: ['user-colors'],
    queryFn: () => get<string[]>('/users/colors'),
  })
}

export function useBookings(from: () => Date, to: () => Date) {
  const queryKey = computed(
    () => ['bookings', toNaiveUtc(from()), toNaiveUtc(to())] as const,
  )
  return useQuery({
    queryKey,
    queryFn: ({ queryKey: [, fromUtc, toUtc] }) =>
      get<Booking[]>(`/bookings?from=${fromUtc}&to=${toUtc}`),
  })
}

export function useInvalidateAll() {
  const queryClient = useQueryClient()
  return function invalidateAll(): void {
    void queryClient.invalidateQueries({ queryKey: ['bookings'] })
    void queryClient.invalidateQueries({ queryKey: ['servers'] })
    void queryClient.invalidateQueries({ queryKey: ['projects'] })
    void queryClient.invalidateQueries({ queryKey: ['users'] })
    void queryClient.invalidateQueries({ queryKey: ['user-directory'] })
  }
}
