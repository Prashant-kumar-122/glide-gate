import { Bell, X } from 'lucide-react'
import { usePushSubscription } from '@/hooks/usePushSubscription'

interface Props {
  onClose: () => void
}

/**
 * Pre-prompt explainer shown before the native browser Notification.requestPermission()
 * dialog. Displaying this first dramatically reduces permanent permission denials because
 * users understand what they're agreeing to before the browser prompt appears.
 */
export function PushPermissionModal({ onClose }: Props) {
  const { subscribe, isLoading } = usePushSubscription()

  async function handleEnable() {
    await subscribe()
    onClose()
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="push-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="w-full max-w-sm border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-900">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-gray-100 px-4 py-3.5 dark:border-gray-800">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center bg-primary/10">
              <Bell className="h-4 w-4 text-primary" />
            </div>
            <h2 id="push-modal-title" className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Enable push alerts
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-4 py-4 text-xs text-gray-600 dark:text-gray-400 space-y-2">
          <p>
            GlideGate would like to send you push notifications for case updates —
            document reviews, compliance decisions, and status changes — even when
            the app is closed.
          </p>
          <p className="text-gray-400 dark:text-gray-500">
            You can change this at any time in your profile or in browser settings.
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 border-t border-gray-100 px-4 py-3 dark:border-gray-800">
          <button
            onClick={onClose}
            className="rounded px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-300 transition-colors"
          >
            Not now
          </button>
          <button
            onClick={handleEnable}
            disabled={isLoading}
            className="rounded bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Enabling…' : 'Enable notifications'}
          </button>
        </div>
      </div>
    </div>
  )
}
