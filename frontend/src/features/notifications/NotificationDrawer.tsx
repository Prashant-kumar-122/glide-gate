import { useMemo } from 'react'
import { X, Mail, Bell } from 'lucide-react'
import { useNotificationStore } from '@/store/notificationStore'
import type { NotificationRecord } from '@/store/notificationStore'

const CHANNEL_ICON: Record<NotificationRecord['channel'], typeof Bell> = {
  email: Mail,
  sms: Bell,
  in_app: Bell,
}

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  HIGH: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  NORMAL: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  LOW: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
}

function fmtTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ts
  }
}

export function NotificationDrawer({ onClose }: { onClose: () => void }) {
  const raw = useNotificationStore((s) => s.notifications)
  const markAllRead = useNotificationStore((s) => s.markAllRead)

  const notifications = useMemo(
    () => [...raw].sort((a, b) => new Date(b.receivedAt).getTime() - new Date(a.receivedAt).getTime()),
    [raw]
  )

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} aria-hidden="true" />

      <div className="fixed right-0 top-12 z-50 flex h-[calc(100dvh-48px)] w-96 max-w-[calc(100vw-3rem)] flex-col border-l border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-700">
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">
            Notifications
            {notifications.length > 0 && (
              <span className="ml-1.5 text-xs font-normal text-gray-400">
                ({notifications.length})
              </span>
            )}
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={markAllRead}
              className="text-[10px] text-blue-500 hover:underline"
            >
              Mark all read
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              aria-label="Close notifications"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex h-full items-center justify-center px-6 text-center">
              <p className="text-xs text-gray-400 dark:text-gray-600">No notifications yet.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-50 dark:divide-gray-800">
              {notifications.map((n) => {
                const Icon = CHANNEL_ICON[n.channel] ?? Bell
                return (
                  <li
                    key={n.id}
                    className={[
                      'flex items-start gap-3 px-4 py-3',
                      !n.read ? 'bg-blue-50/40 dark:bg-blue-950/20' : '',
                    ].join(' ')}
                  >
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center bg-gray-100 dark:bg-gray-800">
                      <Icon className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start gap-1.5">
                        <p className="text-xs font-medium text-gray-800 dark:text-gray-100 break-words">
                          {n.subject}
                        </p>
                        <span
                          className={[
                            'shrink-0 rounded px-1 py-0.5 text-[9px] font-bold',
                            PRIORITY_COLORS[n.priority] ?? PRIORITY_COLORS.NORMAL,
                          ].join(' ')}
                        >
                          {n.priority}
                        </span>
                      </div>
                      {n.bodyPreview && (
                        <p className="mt-0.5 text-[10px] text-gray-500 dark:text-gray-400 break-words whitespace-pre-line">
                          {n.bodyPreview}
                        </p>
                      )}
                      <p className="mt-0.5 text-[10px] text-gray-400 dark:text-gray-500">
                        {fmtTime(n.receivedAt)}
                      </p>
                    </div>
                    {!n.read && (
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}
