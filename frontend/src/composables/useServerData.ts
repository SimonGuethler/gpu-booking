import { useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'

import type { Project, ProjectCreate } from '../api/types'
import { post } from '../api/client'
import { useProjects, useServers } from './useApi'

export function useServerData() {
  const queryClient = useQueryClient()

  const serversQuery = useServers()
  const projectsQuery = useProjects()

  const servers = computed(() => serversQuery.data.value ?? [])
  const projects = computed(() => projectsQuery.data.value ?? [])

  const serversLoading = computed(() => serversQuery.isLoading.value)
  const projectsLoading = computed(() => projectsQuery.isLoading.value)

  async function saveProject(payload: ProjectCreate): Promise<Project> {
    const project = await post<Project>('/projects', payload)
    void queryClient.invalidateQueries({ queryKey: ['projects'] })
    return project
  }

  return { servers, projects, serversLoading, projectsLoading, saveProject }
}
