import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'
import ConfirmationModal from '@/components/ConfirmationModal'
import { DOC_STATUS_LABEL, DOC_STATUS_ORDER } from '@/design-system/tokens'
import type { DocumentStatus } from '@/design-system/tokens'

const ALLOWED_TRANSITIONS: Record<DocumentStatus, DocumentStatus[]> = {
  NOT_REQUESTED: ['REQUESTED'],
  REQUESTED: ['RECEIVED'],
  RECEIVED: ['UNDER_REVIEW', 'NEEDS_REVISION'],
  UNDER_REVIEW: ['APPROVED', 'NEEDS_REVISION'],
  NEEDS_REVISION: ['RECEIVED'],
  APPROVED: [],
}

interface StatusEditorProps {
  currentStatus: DocumentStatus
  onStatusChange: (newStatus: DocumentStatus) => void
  isUpdating?: boolean
}

export default function StatusEditor({
  currentStatus,
  onStatusChange,
  isUpdating,
}: StatusEditorProps) {
  const [pendingStatus, setPendingStatus] = useState<DocumentStatus | null>(null)
  const allowed = ALLOWED_TRANSITIONS[currentStatus]

  function handleSelect(status: DocumentStatus) {
    setPendingStatus(status)
  }

  function handleConfirm() {
    if (pendingStatus) {
      onStatusChange(pendingStatus)
      setPendingStatus(null)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Status</h4>

      <div className="flex items-center gap-2">
        <StatusBadge status={currentStatus} size="md" />
        {allowed.length === 0 && (
          <span className="text-xs text-gray-400">No transitions available</span>
        )}
      </div>

      {allowed.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-xs text-gray-500">Move to:</p>
          <div className="flex flex-wrap gap-2">
            {DOC_STATUS_ORDER.filter((s) => allowed.includes(s)).map((s) => (
              <button
                key={s}
                onClick={() => handleSelect(s)}
                disabled={isUpdating}
                className="flex items-center gap-1.5 border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:border-primary hover:bg-blue-50 hover:text-primary disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-primary dark:hover:bg-primary-subtle dark:hover:text-blue-300"
              >
                <ChevronDown className="h-3 w-3" />
                {DOC_STATUS_LABEL[s]}
              </button>
            ))}
          </div>
        </div>
      )}

      <ConfirmationModal
        isOpen={!!pendingStatus}
        title="Update document status"
        message={
          pendingStatus ? (
            <span>
              Change status from <strong>{DOC_STATUS_LABEL[currentStatus]}</strong> to{' '}
              <strong>{DOC_STATUS_LABEL[pendingStatus]}</strong>?
            </span>
          ) : null
        }
        confirmLabel="Update Status"
        onConfirm={handleConfirm}
        onCancel={() => setPendingStatus(null)}
        loading={isUpdating}
      />
    </div>
  )
}
