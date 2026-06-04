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
    icon:   'text-red-600 bg-red-50 border border-red-200 dark:text-red-400 dark:bg-red-950/60 dark:border-red-700/30',
    button: 'bg-red-600 hover:bg-red-700 focus-visible:ring-red-500 text-white dark:bg-red-700 dark:hover:bg-red-600',
  },
  warning: {
    icon:   'text-amber-600 bg-amber-50 border border-amber-200 dark:text-amber-400 dark:bg-amber-950/60 dark:border-amber-700/30',
    button: 'bg-amber-600 hover:bg-amber-700 focus-visible:ring-amber-400 text-white',
  },
  default: {
    icon:   'text-primary bg-blue-50 border border-blue-200 dark:bg-primary-subtle dark:border-primary/20',
    button: 'bg-primary hover:bg-primary-hover focus-visible:ring-primary text-white',
  },
}

export default function ConfirmationModal({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel  = 'Cancel',
  variant      = 'default',
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
      <div className="w-full max-w-md border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-900">
        <div className="flex items-start gap-4 p-5">
          <span className={['flex h-9 w-9 shrink-0 items-center justify-center', styles.icon].join(' ')}>
            <AlertTriangle className="h-4 w-4" />
          </span>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
            <div className="mt-1.5 text-xs text-gray-600 dark:text-gray-400">{message}</div>
          </div>
          <button
            onClick={onCancel}
            className="shrink-0 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="flex justify-end gap-2 border-t border-gray-100 px-5 py-3 dark:border-gray-800">
          <button
            ref={cancelRef}
            onClick={onCancel}
            disabled={loading}
            className="rounded-md border border-gray-300 px-4 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 hover:text-gray-900 disabled:opacity-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-gray-100 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={[
              'rounded-md px-4 py-1.5 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 transition-colors',
              styles.button,
            ].join(' ')}
          >
            {loading ? 'Working…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
