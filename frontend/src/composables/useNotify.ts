import { useToast } from 'primevue/usetoast'

export function useNotify(): (
  severity: 'success' | 'error',
  summary: string,
  detail?: string,
) => void {
  const toast = useToast()
  return (severity, summary, detail = ''): void => {
    toast.add({ severity, summary, detail, life: 3500 })
  }
}
