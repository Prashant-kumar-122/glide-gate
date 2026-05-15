import { useEffect, useRef } from 'react'
import { X, AlertTriangle } from 'lucide-react'
import type { ReactNode } from 'react'

interface ConfirmationModalProps {
  isOpen: boolean
  title: string
  message: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'warning' | 'default'
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}

const VARIANT_STYLES = {
  danger: {
    icon: 'text-red-500 bg-red-50',
    button: 'bg-red-600 hover:bg-red-700 focus-visible:ring-red-500',
  },
  warning: {
    icon: 'text-amber-500 bg-amber-50',
    button: 'bg-amber-500 hover:bg-amber-600 focus-visible:ring-amber-400',
  },
  default: {
    icon: 'text-blue-500 bg-blue-50',
    button: 'bg-blue-600 hover:bg-blue-700 focus-visible:ring-blue-500',
  },
}

export default function ConfirmationModal({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  onConfirm,
  onCancel,
  loading = false,
}: ConfirmationModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  const styles = VARIANT_STYLES[variant]

  useEffect(() => {
    if (isOpen) cancelRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && isOpen) onCancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isOpen, onCancel])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => e.target === e.currentTarget && onCancel()}
    >
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        <div className="flex items-start gap-4 p-6">
          <span className={['flex h-10 w-10 shrink-0 items-center justify-center rounded-full', styles.icon].join(' ')}>
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-gray-900">{title}</h3>
            <div className="mt-1 text-sm text-gray-500">{message}</div>
          </div>
          <button
            onClick={onCancel}
            className="shrink-0 rounded p-1 text-gray-400 hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex justify-end gap-3 border-t border-gray-100 px-6 py-4">
          <button
            ref={cancelRef}
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={[
              'rounded-lg px-4 py-2 text-sm font-medium text-white focus-visible:outline-none focus-visible:ring-2',
              styles.button,
              'disabled:opacity-50',
            ].join(' ')}
          >
            {loading ? 'Working…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
