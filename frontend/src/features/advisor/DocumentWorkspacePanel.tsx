import {
  FolderOpen,
  Fingerprint,
  DollarSign,
  Scale,
  Shield,
  Building,
  FileText,
  BadgeCheck,
  ClipboardList,
} from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import CategoryCard from '@/components/CategoryCard'
import DocumentRow from '@/components/DocumentRow'
import UploadButton from '@/components/UploadButton'
import ParallelProductTracks from './ParallelProductTracks'
import SalesReviewPanel from './SalesReviewPanel'
import OnboardingFormView from '@/features/client/OnboardingFormView'
import { useDocuments, useCaseProgress, useUploadDocument, useAccount, useQuestionnaireSchema, useCollectedFields } from '@/hooks/useDocuments'
import { useComments } from '@/hooks/useComments'
import { useAuthStore } from '@/store/authStore'
import type { DocumentOut } from '@/lib/api'

type WorkspaceTab = 'documents' | 'application'

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
  const { data: summary, isLoading: summaryLoading } = useCaseProgress(caseId)
  const { data: account } = useAccount(caseId, summary?.current_stage === 'COMPLETE')
  const uploadMutation = useUploadDocument(caseId)
  const { data: comments = [] } = useComments(caseId)
  const { data: schemaData, isLoading: schemaLoading } = useQuestionnaireSchema(caseId)
  const { data: collectedData, isLoading: collectedLoading } = useCollectedFields(caseId)
  const userRole = useAuthStore(s => s.user?.role)

  const isSalesReview = summary?.current_stage === 'SALES_REVIEW'
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('documents')

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

  const tabs: { id: WorkspaceTab; label: string; icon: typeof FileText }[] = [
    { id: 'documents',   label: 'Documents',   icon: FileText },
    { id: 'application', label: 'Application', icon: ClipboardList },
  ]

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-5">
      {/* Case progress header */}
      {(summaryLoading || summary) && (
        <div className="border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {summary?.case_name ?? summary?.client_name ?? '…'}
              </p>
              <p className="mt-1 text-[10px] text-gray-600 dark:text-gray-500">
                Stage:{' '}
                <span className="font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-300">
                  {summary?.current_stage ?? '…'}
                </span>
                {summary?.escalated && (
                  <span className="ml-2 border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-amber-700 dark:border-amber-600/30 dark:bg-amber-950/50 dark:text-amber-400">
                    ESCALATED
                  </span>
                )}
              </p>
              {account && account.map((acc) => (
                <p key={acc.account_number} className="mt-1 flex items-center gap-1 font-mono text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                  <BadgeCheck className="w-3 h-3 shrink-0" />
                  {acc.product.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}: {acc.account_number}
                </p>
              ))}
            </div>
            <div className="text-right shrink-0">
              <p className="font-mono text-2xl font-bold tabular-nums text-gray-900 dark:text-gray-100">
                {summary?.overall_progress ?? 0}%
              </p>
              <p className="text-[10px] text-gray-400">completion</p>
            </div>
          </div>
        </div>
      )}

      {/* Sales Manager Review banner */}
      {isSalesReview && (
        <SalesReviewPanel caseId={caseId} userRole={userRole} />
      )}

      {/* Product tracks */}
      <section>
        <p className="mb-2.5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
          <FolderOpen className="h-3.5 w-3.5" />
          Product Tracks
        </p>
        <ParallelProductTracks
          tracks={summary?.products ?? []}
          isLoading={summaryLoading}
        />
      </section>

      {/* Tabbed workspace */}
      <div className="border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
        {/* Tab bar */}
        <div className="flex border-b border-gray-200 dark:border-gray-800">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={[
                'flex flex-1 items-center justify-center gap-2 py-2.5 text-xs font-medium border-b-2 transition-colors',
                activeTab === id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
              ].join(' ')}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Documents tab */}
        {activeTab === 'documents' && (
          <div className="p-4">
            <p className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
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
          </div>
        )}

        {/* Application tab */}
        {activeTab === 'application' && (
          <OnboardingFormView
            caseId={caseId}
            clientData={collectedData?.client_data ?? {}}
            schema={schemaData?.fields ?? []}
            isLoading={schemaLoading || collectedLoading}
            readOnly
            hideReadOnlyLabel
          />
        )}
      </div>
    </div>
  )
}
