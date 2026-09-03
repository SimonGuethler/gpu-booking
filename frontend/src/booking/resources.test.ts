import { describe, expect, it } from 'vitest'

import { filterGpuIdsForServer } from './resources'

const gpus = [
  { id: 1, server_id: 10 },
  { id: 2, server_id: 10 },
  { id: 3, server_id: 20 },
]

describe('filterGpuIdsForServer', () => {
  it('behält nur ausgewählte GPUs des aktiven Servers', () => {
    expect(filterGpuIdsForServer([1, 2, 3], gpus, 10)).toEqual([1, 2])
  })

  it('zählt keine Auswahl eines anderen Servers', () => {
    expect(filterGpuIdsForServer([3], gpus, 10)).toEqual([])
  })
})
