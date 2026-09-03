import type { Mode } from '../api/types'

export const MODE_LABELS: Record<Mode, string> = {
  train: 'Vollbelegung',
  dev: 'Teilbelegung',
  cpu: 'CPU',
}

export function modeLabel(mode: Mode): string {
  return MODE_LABELS[mode]
}
