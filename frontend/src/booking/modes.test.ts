import { describe, expect, it } from 'vitest'

import { MODE_LABELS, modeLabel } from './modes'

describe('modeLabel', () => {
  it('bildet die stabilen API-Werte auf sichtbare Begriffe ab', () => {
    expect(MODE_LABELS).toEqual({
      train: 'Vollbelegung',
      dev: 'Teilbelegung',
      cpu: 'CPU',
    })
    expect(modeLabel('dev')).toBe('Teilbelegung')
  })
})
