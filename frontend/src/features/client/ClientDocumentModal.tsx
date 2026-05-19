import { useEffect, useState } from 'react'
import { X, FileText, Loader2, Download } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'
import CommentThread from '@/components/CommentThread'
import { useComments, useAddComment } from '@/hooks/useComments'
import { api, type DocumentOut } from '@/lib/api'

type Tab = 'overview' | 'comments'

const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'comments', label: 'Comments' },
]

interface ClientDocumentModalProps {
  doc: DocumentOut
  caseId: string
  onClose: () => void
}

export default function ClientDocumentModal({ doc, caseId, onClose }: ClientDocumentModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [downloading, setDownloading] = useState(false)

  async function handleDownload() {
    if (downloading) return
    setDownloading(true)
    try {
      const res = await api.get(`/documents/${doc.id}/download`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = doc.name ?? `document-${doc.id}`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setDownloading(false)
    }
  }

  const { data: comments = [], isLoading: commentsLoading } = useComments(
    activeTab === 'comments' ? caseId : null,
    doc.id,
  )
  const addCommentMutation = useAddComment(caseId)

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

              <button
                onClick={handleDownload}
                disabled={downloading}
                className="mt-2 flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100 disabled:opacity-50"
              >
                {downloading
                  ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  : <Download className="h-3.5 w-3.5" />
                }
                {downloading ? 'Downloading…' : 'Download original'}
              </button>
            </div>
          )}

          {activeTab === 'comments' && (
            commentsLoading ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              </div>
            ) : (
              <CommentThread
                comments={comments}
                currentRole="Client"
                hideVisibility
                onAddComment={(body) =>
                  addCommentMutation.mutate({
                    body,
                    visibility: 'ALL',
                    document_id: doc.id,
                  })
                }
              />
            )
          )}
        </div>
      </div>
    </div>
  )
}
