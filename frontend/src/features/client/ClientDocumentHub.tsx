import { useState } from 'react'
import { FolderOpen } from 'lucide-react'
import DocumentUploadCard from './DocumentUploadCard'
import ClientDocumentModal from './ClientDocumentModal'
import { useClientDocuments, useClientUpload } from '@/hooks/useClientDocuments'
import { useComments } from '@/hooks/useComments'
import type { DocumentOut } from '@/lib/api'

const CATEGORIES = [
  'identity',
  'financial',
  'legal',
  'insurance',
  'compliance',
  'entity',
] as const

function groupByCategory(docs: DocumentOut[]): Record<string, DocumentOut[]> {
  const map: Record<string, DocumentOut[]> = {}
  for (const doc of docs) {
    const cat = doc.category ?? 'other'
    if (!map[cat]) map[cat] = []
    map[cat].push(doc)
  }
  return map
}

interface ClientDocumentHubProps {
  caseId: string | null
}

export default function ClientDocumentHub({ caseId }: ClientDocumentHubProps) {
  const { data: docs, isLoading } = useClientDocuments(caseId)
  const upload = useClientUpload(caseId ?? '')
  const { data: comments = [] } = useComments(caseId)
  const [selectedDoc, setSelectedDoc] = useState<DocumentOut | null>(null)

  const commentCountByDoc = comments.reduce<Record<string, number>>((acc, c) => {
    if (c.documentId) acc[c.documentId] = (acc[c.documentId] ?? 0) + 1
    return acc
  }, {})

  if (!caseId) {
    return (
      <div className="flex h-40 items-center justify-center">
        <p className="text-sm text-gray-400">Select a case to view documents</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-36 animate-pulse rounded-2xl bg-gray-200" />
        ))}
      </div>
    )
  }

  const byCategory = groupByCategory(docs ?? [])
  const totalDocs = docs?.length ?? 0
  const approvedDocs = docs?.filter((d) => d.status === 'APPROVED').length ?? 0

  return (
    <div>
      {totalDocs > 0 && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5">
          <FolderOpen className="h-4 w-4 text-gray-400" />
          <p className="text-xs text-gray-600">
            <span className="font-semibold text-gray-900">{approvedDocs}</span> of{' '}
            <span className="font-semibold text-gray-900">{totalDocs}</span> document
            {totalDocs !== 1 ? 's' : ''} approved
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {CATEGORIES.map((cat) => (
          <DocumentUploadCard
            key={cat}
            category={cat}
            documents={byCategory[cat] ?? []}
            commentCountByDoc={commentCountByDoc}
            onUpload={(file) => upload.mutate({ file, category: cat })}
            onDocumentClick={setSelectedDoc}
            isUploading={upload.isPending}
          />
        ))}
      </div>

      {selectedDoc && caseId && (
        <ClientDocumentModal
          doc={selectedDoc}
          caseId={caseId}
          onClose={() => setSelectedDoc(null)}
        />
      )}
    </div>
  )
}
