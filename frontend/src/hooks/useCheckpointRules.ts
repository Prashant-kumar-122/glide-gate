import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { CheckpointRuleOut, CreateCheckpointRuleRequest } from '@/lib/api'

export const checkpointQk = {
  all: ['checkpoint-rules'] as const,
}

export function useCheckpointRules() {
  return useQuery({
    queryKey: checkpointQk.all,
    queryFn: () =>
      api.get<CheckpointRuleOut[]>('/admin/checkpoint-rules').then((r) => r.data),
  })
}

export function useCreateCheckpointRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateCheckpointRuleRequest) =>
      api.post<CheckpointRuleOut>('/admin/checkpoint-rules', body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: checkpointQk.all }),
  })
}

export function useDeleteCheckpointRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ruleId: string) =>
      api.delete<{ deleted: string }>(`/admin/checkpoint-rules/${ruleId}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: checkpointQk.all }),
  })
}

export function useResetCheckpointRules() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api
        .post<CheckpointRuleOut[]>('/admin/checkpoint-rules/reset')
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: checkpointQk.all }),
  })
}
