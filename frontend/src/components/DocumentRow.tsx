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
  if (status === 'APPROVED')       return <CheckCircle className="h-3.5 w-3.5 text-green-500" />
  if (status === 'NEEDS_REVISION') return <AlertCircle className="h-3.5 w-3.5 text-red-500" />
  if (status === 'UNDER_REVIEW')   return <Clock className="h-3.5 w-3.5 text-amber-500" />
  return <FileText className="h-3.5 w-3.5 text-gray-400" />
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
        'flex w-full items-center gap-3 px-3 py-2 text-left transition-colors',
        isActive
          ? 'bg-blue-50 border-l-2 border-primary pl-[10px] dark:bg-primary/10'
          : 'border-l-2 border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/60',
      ].join(' ')}
    >
      <StatusIcon status={doc.status} />

      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-gray-800 dark:text-gray-200">{doc.name}</p>
        <p className="font-mono text-[10px] text-gray-500 dark:text-gray-400">
          v{doc.version} · {new Date(doc.updatedAt).toLocaleDateString()}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        {doc.hasDiff && (
          <span className="border border-amber-300 bg-amber-50 px-1 py-0.5 text-[9px] font-medium uppercase tracking-wide text-amber-700 dark:border-amber-600/40 dark:bg-amber-950/40 dark:text-amber-400">
            DIFF
          </span>
        )}
        {doc.hasValidationResult && (
          <span className="border border-blue-300 bg-blue-50 px-1 py-0.5 text-[9px] font-medium uppercase tracking-wide text-blue-700 dark:border-blue-600/40 dark:bg-blue-950/40 dark:text-blue-400">
            AI
          </span>
        )}
        {(doc.commentCount ?? 0) > 0 && (
          <span className="flex items-center gap-0.5 border border-gray-300 bg-gray-50 px-1 py-0.5 text-[9px] font-medium text-gray-600 dark:border-gray-600/40 dark:bg-transparent dark:text-gray-400">
            <MessageCircle className="h-2.5 w-2.5" />
            {doc.commentCount}
          </span>
        )}
        <StatusBadge status={doc.status} size="sm" showDot={false} />
      </div>
    </button>
  )
}
