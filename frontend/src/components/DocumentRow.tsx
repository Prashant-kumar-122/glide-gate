import { FileText, Clock, AlertCircle, CheckCircle, MessageCircle } from 'lucide-react'
import { useWorkspaceStore } from '@/store/workspaceStore'
import StatusBadge from './StatusBadge'
import type { DocumentStatus } from '@/design-system/tokens'

export interface DocumentRowData {
  id: string
  name: string
  status: DocumentStatus
  version: number
  updatedAt: string
  hasValidationResult?: boolean
  hasDiff?: boolean
  commentCount?: number
}

interface DocumentRowProps {
  doc: DocumentRowData
  caseId: string
}

function StatusIcon({ status }: { status: DocumentStatus }) {
  if (status === 'APPROVED') return <CheckCircle className="h-4 w-4 text-green-500" />
  if (status === 'NEEDS_REVISION') return <AlertCircle className="h-4 w-4 text-red-500" />
  if (status === 'UNDER_REVIEW') return <Clock className="h-4 w-4 text-amber-500" />
  return <FileText className="h-4 w-4 text-gray-400" />
}

export default function DocumentRow({ doc, caseId: _caseId }: DocumentRowProps) {
  const { activeDocumentId, setActiveDocument, setDrawerOpen } = useWorkspaceStore()
  const isActive = activeDocumentId === doc.id

  function handleClick() {
    setActiveDocument(doc.id)
    setDrawerOpen(true)
  }

  return (
    <button
      onClick={handleClick}
      className={[
        'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors',
        isActive
          ? 'bg-blue-50 ring-1 ring-blue-200'
          : 'hover:bg-gray-50',
      ].join(' ')}
    >
      <StatusIcon status={doc.status} />

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-800">{doc.name}</p>
        <p className="text-xs text-gray-400">
          v{doc.version} &middot; {new Date(doc.updatedAt).toLocaleDateString()}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        {doc.hasDiff && (
          <span className="rounded bg-amber-100 px-1 py-0.5 text-[10px] font-medium text-amber-700">
            DIFF
          </span>
        )}
        {doc.hasValidationResult && (
          <span className="rounded bg-indigo-100 px-1 py-0.5 text-[10px] font-medium text-indigo-700">
            AI
          </span>
        )}
        {(doc.commentCount ?? 0) > 0 && (
          <span className="flex items-center gap-0.5 rounded-full bg-blue-100 px-1.5 py-0.5 text-[9px] font-bold text-blue-600">
            <MessageCircle className="h-2.5 w-2.5" />
            {doc.commentCount}
          </span>
        )}
        <StatusBadge status={doc.status} size="sm" showDot={false} />
      </div>
    </button>
  )
}
