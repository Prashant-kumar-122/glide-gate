import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SalesManagerReviewOut, SalesDecisionOut } from '@/lib/api'

export const salesReviewQk = {
  all: ['sales-reviews'] as const,
  pending: () => [...salesReviewQk.all, 'pending'] as const,
  byCase: (caseId: string) => [...salesReviewQk.all, 'case', caseId] as const,
}

export function useSalesReviewsByCase(caseId: string | null) {
  return useQuery({
    queryKey: salesReviewQk.byCase(caseId ?? ''),
    queryFn: async () => {
      const res = await api.get<SalesManagerReviewOut[]>('/sales-reviews', {
        params: { case_id: caseId, include_decided: true },
      })
      return res.data
    },
    enabled: !!caseId,
    refetchInterval: 10_000,
  })
}

export function usePendingSalesReviews() {
  return useQuery({
    queryKey: salesReviewQk.pending(),
    queryFn: async () => {
      const res = await api.get<SalesManagerReviewOut[]>('/sales-reviews')
      return res.data
    },
    refetchInterval: 15_000,
  })
}

export function useDecideSalesReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      reviewId,
      decision,
      decision_notes,
    }: {
      reviewId: string
      decision: 'APPROVED' | 'REJECTED' | 'MORE_INFO_REQUESTED'
      decision_notes?: string
    }) => {
      const res = await api.post<SalesDecisionOut>(`/sales-reviews/${reviewId}/decide`, {
        decision,
        decision_notes,
      })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: salesReviewQk.all })
    },
  })
}
