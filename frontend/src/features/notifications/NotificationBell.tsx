import { useState } from 'react'
import { Bell } from 'lucide-react'
import { useUnreadCount, useNotificationStore } from '@/store/notificationStore'
import { NotificationDrawer } from './NotificationDrawer'

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const unread = useUnreadCount()
  const markAllRead = useNotificationStore((s) => s.markAllRead)

  function toggle() {
    if (!open) markAllRead()
    setOpen((o) => !o)
  }

  return (
    <>
      <button
        onClick={toggle}
        className="relative mr-2 rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
      {open && <NotificationDrawer onClose={() => setOpen(false)} />}
    </>
  )
}
