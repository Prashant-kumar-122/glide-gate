import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { LLMConfig } from '@/lib/api'

const LLM_QK = ['admin', 'llm-config'] as const

const DEFAULT_CONFIG: LLMConfig = {
  provider: 'anthropic',
  model: 'claude-sonnet-4-6',
  temperature: 0.7,
  top_p: 1.0,
  seed: null,
  frequency_penalty: 0.0,
  presence_penalty: 0.0,
  max_retries: 3,
  cache_ttl: 300,
}

export function useLLMConfig() {
  return useQuery<LLMConfig>({
    queryKey: LLM_QK,
    queryFn: () => api.get('/admin/llm-config').then((r) => r.data),
    staleTime: 120_000,
    retry: false,
    placeholderData: DEFAULT_CONFIG,
  })
}

export function useUpdateLLMConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (config: Partial<LLMConfig>) =>
      api.put('/admin/llm-config', config).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: LLM_QK })
    },
  })
}
