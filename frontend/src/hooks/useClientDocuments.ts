import { useDocuments, useCaseProgress, useUploadDocument } from '@/hooks/useDocuments'

export function useClientDocuments(caseId: string | null) {
  return useDocuments(caseId)
}

export function useClientProgress(caseId: string | null) {
  return useCaseProgress(caseId)
}

export function useClientUpload(caseId: string) {
  return useUploadDocument(caseId)
}
