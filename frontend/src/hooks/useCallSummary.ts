import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { CallSummary } from '@/lib/api'

export const ccQk = {
  callSummary: (caseId: string) => ['call-summary', caseId] as const,
}

export function useCallSummary(caseId: string | null) {
  return useQuery<CallSummary>({
    queryKey: ccQk.callSummary(caseId ?? ''),
    queryFn: () => api.get(`/cases/${caseId}/call-summary`).then((r) => r.data),
    enabled: !!caseId,
    retry: false,
    staleTime: 60_000,
  })
}
