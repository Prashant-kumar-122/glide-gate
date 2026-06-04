import { useState } from 'react'
import { Bell } from 'lucide-react'
import { useUnreadCount, useNotificationStore } from '@/store/notificationStore'
import { NotificationDrawer } from './NotificationDrawer'

export function NotificationBell() {
  const [open,       setOpen]       = useState(false)
  const unread      = useUnreadCount()
  const markAllRead = useNotificationStore((s) => s.markAllRead)

  function toggle() {
    if (!open) markAllRead()
    setOpen((o) => !o)
  }

  return (
    <>
      <button
        onClick={toggle}
        className="relative rounded p-1.5 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-300"
        aria-label="Notifications"
      >
        <Bell className="h-3.5 w-3.5" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5 items-center justify-center bg-red-500 text-[8px] font-bold text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
      {open && <NotificationDrawer onClose={() => setOpen(false)} />}
    </>
  )
}
