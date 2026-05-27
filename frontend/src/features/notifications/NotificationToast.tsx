import { useEffect, useState } from 'react'
import { Mail, Bell, X } from 'lucide-react'
import { useNotificationStore } from '@/store/notificationStore'
import type { NotificationRecord } from '@/store/notificationStore'

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  HIGH: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  NORMAL: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  LOW: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
}

export function NotificationToast() {
  const notifications = useNotificationStore((s) => s.notifications)
  const [visible, setVisible] = useState<NotificationRecord | null>(null)

  const latest = notifications[0]

  useEffect(() => {
    if (!latest) return
    setVisible(latest)
    const t = setTimeout(() => setVisible(null), 4000)
    return () => clearTimeout(t)
  }, [latest?.id])

  if (!visible) return null

  const Icon = visible.channel === 'email' ? Mail : Bell

  return (
    <div className="fixed bottom-5 right-5 z-50 flex w-80 items-start gap-3 rounded-xl border border-gray-200 bg-white p-3.5 shadow-lg dark:border-gray-700 dark:bg-gray-800">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 dark:bg-blue-950">
        <Icon className="h-4 w-4 text-blue-500" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-xs font-semibold text-gray-800 dark:text-gray-100">
            {visible.subject}
          </p>
          <span
            className={[
              'shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold',
              PRIORITY_COLORS[visible.priority] ?? PRIORITY_COLORS.NORMAL,
            ].join(' ')}
          >
            {visible.priority}
          </span>
        </div>
        {visible.bodyPreview && (
          <p className="mt-0.5 truncate text-[10px] text-gray-500 dark:text-gray-400">
            {visible.bodyPreview}
          </p>
        )}
      </div>
      <button
        onClick={() => setVisible(null)}
        className="shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        aria-label="Dismiss notification"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
