import { X, FileText, Download, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useDocument, useDiffResult, useValidateDocument, useUpdateDocumentStatus } from '@/hooks/useDocuments'
import { useComments, useAddComment } from '@/hooks/useComments'
import StatusBadge from '@/components/StatusBadge'
import CommentThread from '@/components/CommentThread'
import AIValidationPanel from './AIValidationPanel'
import VersionDiffPanel from './VersionDiffPanel'
import StatusEditor from './StatusEditor'
import type { DocumentStatus } from '@/design-system/tokens'

type DrawerTab = 'overview' | 'validation' | 'diff' | 'comments'

const TABS: { key: DrawerTab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'validation', label: 'AI Validation' },
  { key: 'diff', label: 'Version Diff' },
  { key: 'comments', label: 'Comments' },
]

export default function DocumentDetailDrawer({ caseId }: { caseId: string }) {
  const { activeDocumentId, isDrawerOpen, setDrawerOpen } = useWorkspaceStore()
  const [activeTab, setActiveTab] = useState<DrawerTab>('overview')

  const { data: doc, isLoading: docLoading } = useDocument(
    isDrawerOpen ? activeDocumentId : null,
  )
  const { data: diff, isLoading: diffLoading } = useDiffResult(
    activeTab === 'diff' && activeDocumentId && doc?.has_diff ? activeDocumentId : null,
  )
  const { data: comments = [], isLoading: commentsLoading } = useComments(
    activeTab === 'comments' ? caseId : null,
    activeDocumentId,
  )
  const addCommentMutation = useAddComment(caseId)

  const validateMutation = useValidateDocument(caseId)
  const statusMutation = useUpdateDocumentStatus(caseId)

  function handleStatusChange(newStatus: DocumentStatus) {
    if (!activeDocumentId) return
    statusMutation.mutate({ docId: activeDocumentId, status: newStatus })
  }

  function handleRunValidation() {
    if (!activeDocumentId) return
    validateMutation.mutate(activeDocumentId)
  }

  if (!isDrawerOpen) return null

  return (
    <>
      {/* Backdrop (mobile only) */}
      <div
        className="fixed inset-0 z-30 bg-black/20 lg:hidden"
        onClick={() => setDrawerOpen(false)}
      />

      {/* Drawer panel */}
      <aside className="flex w-96 shrink-0 flex-col border-l border-gray-200 bg-white shadow-xl">
        {/* Drawer header */}
        <div className="flex items-start justify-between border-b border-gray-200 px-4 py-3">
          <div className="flex items-start gap-2">
            <FileText className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
            <div className="min-w-0">
              {docLoading ? (
                <div className="h-4 w-40 animate-pulse rounded bg-gray-200" />
              ) : (
                <p className="truncate text-sm font-semibold text-gray-900">
                  {doc?.name ?? 'Document'}
                </p>
              )}
              {doc && (
                <p className="mt-0.5 text-xs text-gray-400">
                  v{doc.version} &middot;{' '}
                  {new Date(doc.updated_at).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => setDrawerOpen(false)}
            className="rounded p-1 text-gray-400 transition-colors hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={[
                'flex-1 px-2 py-2.5 text-xs font-medium transition-colors',
                activeTab === t.key
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700',
              ].join(' ')}
            >
              {t.label}
              {t.key === 'validation' && doc?.has_validation_result && (
                <span className="ml-1 rounded-full bg-indigo-100 px-1 py-0.5 text-[9px] font-bold text-indigo-700">
                  ✓
                </span>
              )}
              {t.key === 'diff' && doc?.has_diff && (
                <span className="ml-1 rounded-full bg-amber-100 px-1 py-0.5 text-[9px] font-bold text-amber-700">
                  Δ
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-4">
          {docLoading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
            </div>
          ) : !doc ? (
            <p className="text-center text-sm text-gray-400 py-10">Document not found</p>
          ) : (
            <>
              {activeTab === 'overview' && (
                <div className="flex flex-col gap-5">
                  {/* Meta */}
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Status</span>
                      <StatusBadge status={doc.status} size="md" />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Category</span>
                      <span className="text-xs font-medium text-gray-700 capitalize">
                        {doc.category.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Version</span>
                      <span className="text-xs font-medium text-gray-700">v{doc.version}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Uploaded</span>
                      <span className="text-xs text-gray-700">
                        {new Date(doc.created_at).toLocaleString()}
                      </span>
                    </div>
                    {doc.checksum_sha256 && (
                      <div className="flex flex-col gap-0.5">
                        <span className="text-xs text-gray-500">SHA-256</span>
                        <span className="font-mono text-[10px] text-gray-400 break-all">
                          {doc.checksum_sha256}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Download stub */}
                  <a
                    href={`/api/documents/${doc.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download original
                  </a>

                  {/* Status editor */}
                  <div className="border-t border-gray-100 pt-4">
                    <StatusEditor
                      currentStatus={doc.status}
                      onStatusChange={handleStatusChange}
                      isUpdating={statusMutation.isPending}
                    />
                  </div>
                </div>
              )}

              {activeTab === 'validation' && (
                <AIValidationPanel
                  result={doc.validation_result}
                  onRunValidation={handleRunValidation}
                  isRunning={validateMutation.isPending}
                />
              )}

              {activeTab === 'diff' && (
                <VersionDiffPanel
                  diff={diff ?? doc.diff_result}
                  isLoading={diffLoading}
                />
              )}

              {activeTab === 'comments' && (
                commentsLoading ? (
                  <div className="flex items-center justify-center py-10">
                    <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                  </div>
                ) : (
                  <CommentThread
                    comments={comments}
                    currentRole="Advisor"
                    onAddComment={(body, visibility) => {
                      addCommentMutation.mutate({
                        body,
                        visibility,
                        document_id: activeDocumentId ?? undefined,
                      })
                    }}
                  />
                )
              )}
            </>
          )}
        </div>
      </aside>
    </>
  )
}
