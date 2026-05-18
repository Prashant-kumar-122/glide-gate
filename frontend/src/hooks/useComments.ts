import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { CollaborationComment } from '@/lib/api'
import type { Comment } from '@/components/CommentThread'

export const commentQK = {
  comments: (caseId: string, docId?: string | null) =>
    docId
      ? ['cases', caseId, 'comments', docId]
      : ['cases', caseId, 'comments'],
}

function toComment(c: CollaborationComment): Comment {
  return {
    id: c.id,
    authorName: c.author_name,
    authorRole: c.author_role as Comment['authorRole'],
    body: c.body,
    createdAt: c.created_at,
    visibility: c.visibility,
    documentId: c.document_id,
  }
}

export function useComments(caseId: string | null, documentId?: string | null) {
  return useQuery<Comment[]>({
    queryKey: commentQK.comments(caseId ?? '', documentId),
    queryFn: async () => {
      const params = documentId ? `?document_id=${documentId}` : ''
      const res = await api.get(`/cases/${caseId}/comments${params}`)
      return (res.data as CollaborationComment[]).map(toComment)
    },
    enabled: !!caseId,
    staleTime: 10_000,
  })
}

export function useAddComment(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { body: string; visibility: string; document_id?: string | null }) =>
      api.post(`/cases/${caseId}/comments`, payload).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases', caseId, 'comments'] })
    },
  })
}
