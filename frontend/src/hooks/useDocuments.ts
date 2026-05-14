import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { DocumentOut, CaseSummary, DiffResult, ValidationResult, CaseOut } from '@/lib/api'

// ── Query keys ────────────────────────────────────────────────────────────────

export const qk = {
  cases: ['cases'] as const,
  caseDetail: (id: string) => ['cases', id] as const,
  caseSummary: (id: string) => ['cases', id, 'summary'] as const,
  documents: (caseId: string) => ['cases', caseId, 'documents'] as const,
  document: (docId: string) => ['documents', docId] as const,
  diff: (docId: string) => ['documents', docId, 'diff'] as const,
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useCases() {
  return useQuery<CaseOut[]>({
    queryKey: qk.cases,
    queryFn: () => api.get('/cases').then((r) => r.data),
    staleTime: 30_000,
  })
}

export function useCaseDetail(caseId: string | null) {
  return useQuery<CaseOut>({
    queryKey: qk.caseDetail(caseId ?? ''),
    queryFn: () => api.get(`/cases/${caseId}`).then((r) => r.data),
    enabled: !!caseId,
    staleTime: 30_000,
  })
}

export function useCaseProgress(caseId: string | null) {
  return useQuery<CaseSummary>({
    queryKey: qk.caseSummary(caseId ?? ''),
    queryFn: () => api.get(`/cases/${caseId}/summary`).then((r) => r.data),
    enabled: !!caseId,
    staleTime: 20_000,
  })
}

export function useDocuments(caseId: string | null) {
  return useQuery<DocumentOut[]>({
    queryKey: qk.documents(caseId ?? ''),
    queryFn: () => api.get(`/cases/${caseId}/documents`).then((r) => r.data),
    enabled: !!caseId,
    staleTime: 15_000,
  })
}

export function useDocument(docId: string | null) {
  return useQuery<DocumentOut>({
    queryKey: qk.document(docId ?? ''),
    queryFn: () => api.get(`/documents/${docId}`).then((r) => r.data),
    enabled: !!docId,
    staleTime: 15_000,
  })
}

export function useDiffResult(docId: string | null) {
  return useQuery<DiffResult>({
    queryKey: qk.diff(docId ?? ''),
    queryFn: () => api.get(`/documents/${docId}/diff`).then((r) => r.data),
    enabled: !!docId,
    staleTime: 60_000,
  })
}

export function useValidateDocument(caseId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (docId: string) => api.post(`/documents/${docId}/validate`).then((r) => r.data),
    onSuccess: (_data, docId) => {
      qc.invalidateQueries({ queryKey: qk.document(docId) })
      if (caseId) qc.invalidateQueries({ queryKey: qk.documents(caseId) })
    },
  })
}

export function useUploadDocument(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ file, category }: { file: File; category: string }) => {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('category', category)
      return api.post(`/cases/${caseId}/documents`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then((r) => r.data as DocumentOut)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.documents(caseId) })
      qc.invalidateQueries({ queryKey: qk.caseSummary(caseId) })
    },
  })
}

export function useUpdateDocumentStatus(caseId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ docId, status }: { docId: string; status: string }) =>
      api.patch(`/documents/${docId}`, { status }).then((r) => r.data),
    onSuccess: (_data, { docId }) => {
      qc.invalidateQueries({ queryKey: qk.document(docId) })
      if (caseId) {
        qc.invalidateQueries({ queryKey: qk.documents(caseId) })
        qc.invalidateQueries({ queryKey: qk.caseSummary(caseId) })
      }
    },
  })
}

// Merge incoming socket payload into the documents list cache
export function applyDocumentStatusUpdate(
  qc: ReturnType<typeof useQueryClient>,
  caseId: string,
  docId: string,
  newStatus: string,
) {
  qc.setQueryData<DocumentOut[]>(qk.documents(caseId), (prev) =>
    prev?.map((d) => (d.id === docId ? { ...d, status: newStatus as DocumentOut['status'] } : d)),
  )
}

// Inject a newly uploaded doc from socket without a full refetch
export function applyDocumentUploaded(
  qc: ReturnType<typeof useQueryClient>,
  caseId: string,
) {
  qc.invalidateQueries({ queryKey: qk.documents(caseId) })
  qc.invalidateQueries({ queryKey: qk.caseSummary(caseId) })
}

// Refresh validation result in the document cache
export function applyValidationResult(
  qc: ReturnType<typeof useQueryClient>,
  docId: string,
  result: ValidationResult,
) {
  qc.setQueryData<DocumentOut>(qk.document(docId), (prev) =>
    prev ? { ...prev, validation_result: result, has_validation_result: true } : prev,
  )
}
