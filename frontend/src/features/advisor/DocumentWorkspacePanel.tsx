import {
  FolderOpen,
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
import ParallelProductTracks from './ParallelProductTracks'
import { useDocuments, useCaseProgress, useUploadDocument } from '@/hooks/useDocuments'
import type { DocumentOut } from '@/lib/api'

const CATEGORIES: { key: string; label: string; icon: ReactNode }[] = [
  { key: 'identity', label: 'Identity', icon: <Fingerprint className="h-4 w-4" /> },
  { key: 'financial', label: 'Financial', icon: <DollarSign className="h-4 w-4" /> },
  { key: 'legal', label: 'Legal', icon: <Scale className="h-4 w-4" /> },
  { key: 'insurance', label: 'Insurance', icon: <Shield className="h-4 w-4" /> },
  { key: 'compliance', label: 'Compliance', icon: <FileText className="h-4 w-4" /> },
  { key: 'entity', label: 'Entity', icon: <Building className="h-4 w-4" /> },
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
  const { data: summary, isLoading: summaryLoading } = useCaseProgress(caseId)
  const uploadMutation = useUploadDocument(caseId)

  const byCategory = groupByCategory(docs ?? [])

  function handleUpload(category: string, files: File[]) {
    files.forEach((file) =>
      uploadMutation.mutate({ file, category }),
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-6 overflow-y-auto p-6">
      {/* Case progress header */}
      {(summaryLoading || summary) && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-gray-900">
                {summary?.client_name ?? '…'}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                Stage:{' '}
                <span className="font-medium text-gray-700">
                  {summary?.current_stage ?? '…'}
                </span>
                {summary?.escalated && (
                  <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                    ESCALATED
                  </span>
                )}
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900 tabular-nums">
                {summary?.overall_progress ?? 0}%
              </p>
              <p className="text-xs text-gray-400">overall</p>
            </div>
          </div>
        </div>
      )}

      {/* Parallel product tracks */}
      <section>
        <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          <FolderOpen className="h-4 w-4" />
          Product Tracks
        </h3>
        <ParallelProductTracks
          tracks={summary?.products ?? []}
          isLoading={summaryLoading}
        />
      </section>

      {/* Document categories */}
      <section>
        <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          <FileText className="h-4 w-4" />
          Document Categories
        </h3>

        {docsLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-xl bg-gray-200" />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-3">
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
                      <span className="rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-semibold text-red-700">
                        Action needed
                      </span>
                    ) : undefined
                  }
                >
                  <div className="flex flex-col gap-0.5">
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
                        }}
                        caseId={caseId}
                      />
                    ))}

                    <div className="mt-2 px-1">
                      <UploadButton
                        label={`Upload ${cat.label} document`}
                        onUpload={(files) => handleUpload(cat.key, files)}
                        disabled={uploadMutation.isPending}
                      />
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
