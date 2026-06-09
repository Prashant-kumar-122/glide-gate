import { useEffect } from 'react'
import { getSocket } from '@/lib/socket'
import { useAuthStore } from '@/store/authStore'
import { useNotificationStore } from '@/store/notificationStore'
import type { NotificationRecord } from '@/store/notificationStore'
import { fetchMyNotifications } from '@/lib/api'

/**
 * Listens for NOTIFICATION_SENT events on the user-level socket room.
 * Room membership is now server-derived from the authenticated session cookie —
 * no join/leave emits needed from the client.
 */
export function useUserSocket() {
  const user = useAuthStore((s) => s.user)
  const appendNotification = useNotificationStore((s) => s.appendNotification)
  const clearNotifications = useNotificationStore((s) => s.clearNotifications)

  useEffect(() => {
    clearNotifications()
    if (!user?.id) return

    fetchMyNotifications()
      .then((items) => {
        items.forEach((item) => {
          appendNotification({
            id: item.id,
            templateId: item.template_id ?? '',
            channel: (item.channel ?? 'in_app') as NotificationRecord['channel'],
            subject: item.subject ?? 'Notification',
            bodyPreview: item.body_preview ?? '',
            priority: 'NORMAL',
            receivedAt: item.received_at,
            read: true,
          })
        })
      })
      .catch(() => { /* silently ignore if fetch fails */ })

    const socket = getSocket()

    function onNotificationSent(data: {
      notification_id?: string
      template_id?: string
      channel?: string
      subject?: string
      body_preview?: string
      priority?: string
    }) {
      const record: NotificationRecord = {
        id: data.notification_id ?? `${Date.now()}-${Math.random()}`,
        templateId: data.template_id ?? '',
        channel: (data.channel ?? 'in_app') as NotificationRecord['channel'],
        subject: data.subject ?? 'New notification',
        bodyPreview: data.body_preview ?? '',
        priority: data.priority ?? 'NORMAL',
        receivedAt: new Date().toISOString(),
        read: false,
      }
      appendNotification(record)
    }

    socket.on('notification_sent', onNotificationSent)

    return () => {
      socket.off('notification_sent', onNotificationSent)
    }
  }, [user?.id, appendNotification, clearNotifications])
}
