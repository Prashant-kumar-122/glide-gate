import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { CaseOut, CaseSummary } from '@/lib/api'
import { qk } from './useDocuments'

export function useAllCases() {
  return useQuery<CaseOut[]>({
    queryKey: qk.cases,
    queryFn: () => api.get('/cases').then((r) => r.data),
    staleTime: 15_000,
    refetchInterval: 60_000,
  })
}

export function useClientDetail(caseId: string | null) {
  return useQuery<CaseSummary>({
    queryKey: qk.caseSummary(caseId ?? ''),
    queryFn: () => api.get(`/cases/${caseId}/summary`).then((r) => r.data),
    enabled: !!caseId,
    staleTime: 20_000,
  })
}
