import type { Gpu } from '../api/types'

type ServerGpu = Pick<Gpu, 'id' | 'server_id'>

export function filterGpuIdsForServer(
  selectedGpuIds: number[],
  gpus: ServerGpu[],
  serverId: number,
): number[] {
  const allowedIds = new Set(
    gpus.filter((gpu) => gpu.server_id === serverId).map((gpu) => gpu.id),
  )
  return selectedGpuIds.filter((gpuId) => allowedIds.has(gpuId))
}
