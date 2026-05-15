import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AgentOut, AgentTraceOut } from '@/lib/api'

export const agentQk = {
  agents: ['agents'] as const,
  trace: (caseId: string) => ['agents', 'trace', caseId] as const,
}

export function useAgents() {
  return useQuery<AgentOut[]>({
    queryKey: agentQk.agents,
    queryFn: () => api.get('/agents').then((r) => r.data),
    staleTime: 60_000,
    retry: false,
  })
}

export function useAgentTrace(caseId: string | null) {
  return useQuery<AgentTraceOut>({
    queryKey: agentQk.trace(caseId ?? ''),
    queryFn: () => api.get(`/agents/trace/${caseId}`).then((r) => r.data),
    enabled: !!caseId,
    staleTime: 10_000,
    refetchInterval: 15_000,
    retry: false,
  })
}
