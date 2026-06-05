import {
  Fingerprint,
  DollarSign,
  Scale,
  Shield,
  Building,
  FileText,
} from 'lucide-react'
import type { ReactNode } from 'react'
import CategoryCard from '@/components/CategoryCard'
import DocumentRow from '@/components/DocumentRow'
import UploadButton from '@/components/UploadButton'
import SalesReviewPanel from './SalesReviewPanel'
import { useDocuments, useCaseProgress, useUploadDocument } from '@/hooks/useDocuments'
import { useComments } from '@/hooks/useComments'
import { useAuthStore } from '@/store/authStore'
import type { DocumentOut } from '@/lib/api'

const CATEGORIES: { key: string; label: string; icon: ReactNode }[] = [
  { key: 'identity',   label: 'Identity',   icon: <Fingerprint className="h-3.5 w-3.5" /> },
  { key: 'financial',  label: 'Financial',  icon: <DollarSign className="h-3.5 w-3.5" /> },
  { key: 'legal',      label: 'Legal',      icon: <Scale className="h-3.5 w-3.5" /> },
  { key: 'insurance',  label: 'Insurance',  icon: <Shield className="h-3.5 w-3.5" /> },
  { key: 'compliance', label: 'Compliance', icon: <FileText className="h-3.5 w-3.5" /> },
  { key: 'entity',     label: 'Entity',     icon: <Building className="h-3.5 w-3.5" /> },
]

function groupByCategory(docs: DocumentOut[]) {
  const map: Record<string, DocumentOut[]> = {}
  for (const doc of docs) {
    const cat = doc.category ?? 'other'
    if (!map[cat]) map[cat] = []
    map[cat].push(doc)
  }
  return map
}

interface DocumentWorkspacePanelProps {
  caseId: string
}

export default function DocumentWorkspacePanel({ caseId }: DocumentWorkspacePanelProps) {
  const { data: docs, isLoading: docsLoading } = useDocuments(caseId)
  const { data: summary } = useCaseProgress(caseId)
  const uploadMutation = useUploadDocument(caseId)
  const { data: comments = [] } = useComments(caseId)
  const userRole = useAuthStore(s => s.user?.role)

  const isSalesReview = summary?.current_stage === 'SALES_REVIEW'

  const commentCountByDoc = comments.reduce<Record<string, number>>((acc, c) => {
    if (c.documentId) acc[c.documentId] = (acc[c.documentId] ?? 0) + 1
    return acc
  }, {})

  const byCategory = groupByCategory(docs ?? [])

  function handleUpload(category: string, files: File[]) {
    const catDocs = byCategory[category] ?? []
    const latestDoc = catDocs[catDocs.length - 1]
    files.forEach((file) =>
      uploadMutation.mutate({ file, category, parentDocId: latestDoc?.id }),
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-5">

      {/* Sales Manager Review banner — only shown when case is in SALES_REVIEW stage */}
      {isSalesReview && <SalesReviewPanel caseId={caseId} userRole={userRole} />}


      {/* Document categories */}
      <section>
        <p className="mb-2.5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
          <FileText className="h-3.5 w-3.5" />
          Document Categories
        </p>

        {docsLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse bg-gray-100 dark:bg-gray-800" />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {CATEGORIES.map((cat) => {
              const catDocs = byCategory[cat.key] ?? []
              const approved = catDocs.filter((d) => d.status === 'APPROVED').length

              return (
                <CategoryCard
                  key={cat.key}
                  title={cat.label}
                  icon={cat.icon}
                  totalDocs={catDocs.length}
                  approvedDocs={approved}
                  defaultOpen={catDocs.length > 0}
                  badge={
                    catDocs.some((d) => d.status === 'NEEDS_REVISION') ? (
                      <span className="border border-red-300 bg-red-50 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-red-700 dark:border-red-600/30 dark:bg-red-950/50 dark:text-red-400">
                        Action Required
                      </span>
                    ) : undefined
                  }
                >
                  <div className="flex flex-col gap-0">
                    {catDocs.map((doc) => (
                      <DocumentRow
                        key={doc.id}
                        doc={{
                          id: doc.id,
                          name: doc.name,
                          status: doc.status,
                          version: doc.version,
                          updatedAt: doc.updated_at,
                          hasValidationResult: doc.has_validation_result,
                          hasDiff: doc.has_diff,
                          commentCount: commentCountByDoc[doc.id] ?? 0,
                        }}
                        caseId={caseId}
                      />
                    ))}

                    <div className="mt-2 px-1">
                      {catDocs[catDocs.length - 1]?.status === 'APPROVED' ? (
                        <div className="flex items-center justify-center gap-2 border border-green-300 bg-green-50 px-4 py-2.5 text-[10px] font-semibold text-green-700 dark:border-green-700/30 dark:bg-green-950/30 dark:text-green-400">
                          <span>✓</span>
                          <span>Document approved — no further uploads needed</span>
                        </div>
                      ) : (
                        <UploadButton
                          label={`Upload ${cat.label} document`}
                          onUpload={(files) => handleUpload(cat.key, files)}
                          disabled={uploadMutation.isPending}
                        />
                      )}
                    </div>
                  </div>
                </CategoryCard>
              )
            })}
          </div>
        )}
      </section>

    </div>
  )
}
