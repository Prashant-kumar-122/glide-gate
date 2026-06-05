import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getTasks, getTask, decideTask } from '@/lib/api'
import type { TaskOut, TaskDecideRequest } from '@/lib/api'

export const taskQk = {
  all: ['tasks'] as const,
  list: (role: string, caseId?: string) =>
    [...taskQk.all, 'list', role, caseId ?? ''] as const,
  detail: (taskId: string) => [...taskQk.all, 'detail', taskId] as const,
}

export function useTasks(role: 'advisor' | 'sales_manager', caseId?: string) {
  return useQuery<TaskOut[]>({
    queryKey: taskQk.list(role, caseId),
    queryFn: () => getTasks(role, caseId),
    staleTime: 15_000,
  })
}

export function useTaskDetail(taskId: string | null) {
  return useQuery<TaskOut>({
    queryKey: taskQk.detail(taskId ?? ''),
    queryFn: () => getTask(taskId!),
    enabled: !!taskId,
    staleTime: 10_000,
  })
}

export function useDecideTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      taskId,
      decision,
      decision_notes,
    }: {
      taskId: string
      decision: TaskDecideRequest['decision']
      decision_notes?: string
    }) => decideTask(taskId, { decision, decision_notes }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskQk.all })
    },
  })
}
