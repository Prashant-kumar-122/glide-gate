import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { DecisionOut, ReviewOut } from '@/lib/api'

export const reviewQk = {
  all: ['reviews'] as const,
  pending: () => [...reviewQk.all, 'pending'] as const,
  byCase: (caseId: string) => [...reviewQk.all, 'case', caseId] as const,
  detail: (reviewId: string) => [...reviewQk.all, reviewId] as const,
  evidence: (reviewId: string) => [...reviewQk.all, reviewId, 'evidence'] as const,
}

export function usePendingReviews() {
  return useQuery({
    queryKey: reviewQk.pending(),
    queryFn: async () => {
      const res = await api.get<ReviewOut[]>('/reviews')
      return res.data
    },
    refetchInterval: 15_000,
  })
}

export function useReviewsByCase(caseId: string | null) {
  return useQuery({
    queryKey: reviewQk.byCase(caseId ?? ''),
    queryFn: async () => {
      const res = await api.get<ReviewOut[]>('/reviews', {
        params: { case_id: caseId, include_decided: true },
      })
      return res.data
    },
    enabled: !!caseId,
  })
}

export function useReview(reviewId: string | null) {
  return useQuery({
    queryKey: reviewQk.detail(reviewId ?? ''),
    queryFn: async () => {
      const res = await api.get<ReviewOut>(`/reviews/${reviewId}`)
      return res.data
    },
    enabled: !!reviewId,
  })
}

export function useEvidencePacket(reviewId: string | null) {
  return useQuery({
    queryKey: reviewQk.evidence(reviewId ?? ''),
    queryFn: async () => {
      const res = await api.get<{ review_id: string; evidence_packet: ReviewOut['evidence_packet'] }>(
        `/reviews/${reviewId}/evidence`
      )
      return res.data.evidence_packet
    },
    enabled: !!reviewId,
  })
}

export function useDecideReview() {
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
      const res = await api.post<DecisionOut>(`/reviews/${reviewId}/decide`, {
        decision,
        decision_notes,
      })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: reviewQk.all })
    },
  })
}
