import { useEffect, useState } from 'react'
import { X, FileText, Loader2, MessageCircle } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'
import RoleBadge from '@/components/RoleBadge'
import { useComments } from '@/hooks/useComments'
import type { DocumentOut } from '@/lib/api'

type Tab = 'overview' | 'comments'

const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'comments', label: 'Advisor Notes' },
]

interface ClientDocumentModalProps {
  doc: DocumentOut
  caseId: string
  onClose: () => void
}

export default function ClientDocumentModal({ doc, caseId, onClose }: ClientDocumentModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  const { data: comments = [], isLoading: commentsLoading } = useComments(
    activeTab === 'comments' ? caseId : null,
    doc.id,
  )

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="flex w-full max-w-md flex-col rounded-2xl bg-white shadow-2xl" style={{ maxHeight: '85vh' }}>
        {/* Header */}
        <div className="flex items-start justify-between border-b border-gray-200 px-5 py-4">
          <div className="flex items-start gap-2 min-w-0">
            <FileText className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-gray-900">{doc.name}</p>
              <p className="mt-0.5 text-xs text-gray-400">
                v{doc.version} &middot; {new Date(doc.updated_at).toLocaleDateString()}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-3 shrink-0 rounded p-1 text-gray-400 transition-colors hover:text-gray-600"
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
                'flex-1 px-3 py-2.5 text-xs font-medium transition-colors',
                activeTab === t.key
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700',
              ].join(' ')}
            >
              {t.label}
              {t.key === 'comments' && comments.length > 0 && (
                <span className="ml-1 rounded-full bg-blue-100 px-1.5 py-0.5 text-[9px] font-bold text-blue-700">
                  {comments.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-5">
          {activeTab === 'overview' && (
            <div className="flex flex-col gap-3">
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
          )}

          {activeTab === 'comments' && (
            commentsLoading ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              </div>
            ) : comments.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
                <MessageCircle className="h-8 w-8 text-gray-200" />
                <p className="text-sm text-gray-400">No advisor notes yet</p>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {comments.map((c) => (
                  <div key={c.id} className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-700">{c.authorName}</span>
                      <RoleBadge role={c.authorRole} size="sm" />
                      <span className="ml-auto text-[10px] text-gray-400">
                        {new Date(c.createdAt).toLocaleString()}
                      </span>
                    </div>
                    <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700">
                      {c.body}
                    </p>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>
    </div>
  )
}
