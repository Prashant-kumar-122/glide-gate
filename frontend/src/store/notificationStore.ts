import { create } from 'zustand'

export interface NotificationRecord {
  id: string
  templateId: string
  channel: 'email' | 'sms' | 'in_app'
  subject: string
  bodyPreview: string
  priority: string
  receivedAt: string
  read: boolean
}

interface NotificationStore {
  notifications: NotificationRecord[]
  appendNotification: (n: NotificationRecord) => void
  markAllRead: () => void
  clearNotifications: () => void
}

export const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  appendNotification: (n) =>
    set((s) =>
      s.notifications.some((x) => x.id === n.id)
        ? s
        : { notifications: [n, ...s.notifications] },
    ),
  markAllRead: () =>
    set((s) => ({ notifications: s.notifications.map((n) => ({ ...n, read: true })) })),
  clearNotifications: () => set({ notifications: [] }),
}))

export const useUnreadCount = () =>
  useNotificationStore((s) => s.notifications.filter((n) => !n.read).length)
