import { useEffect } from 'react'
import { getSocket } from '@/lib/socket'
import { useAuthStore } from '@/store/authStore'
import { useNotificationStore } from '@/store/notificationStore'
import type { NotificationRecord } from '@/store/notificationStore'
import { fetchMyNotifications } from '@/lib/api'

/**
 * Joins the user-level socket room (user:{userId}) on authentication.
 * Listens for NOTIFICATION_SENT events that are emitted directly to the user
 * (e.g. case-created notifications that fire before any case room is joined).
 */
export function useUserSocket() {
  const user = useAuthStore((s) => s.user)
  const appendNotification = useNotificationStore((s) => s.appendNotification)
  const clearNotifications = useNotificationStore((s) => s.clearNotifications)

  useEffect(() => {
    // Always start clean when the user identity changes
    clearNotifications()
    if (!user?.id) return

    // Load persisted notifications from DB — shown as read (historical)
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
      .catch(() => {/* silently ignore if fetch fails */})

    const socket = getSocket()

    function joinRoom() {
      socket.emit('join_user_room', { user_id: user!.id })
      console.debug('[useUserSocket] joined user room', user!.id)
    }

    // Join now (or buffer if not yet connected) and re-join on every reconnect
    joinRoom()
    socket.on('connect', joinRoom)

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
      console.debug('[useUserSocket] notification_sent received', data)
      appendNotification(record)
    }

    socket.on('notification_sent', onNotificationSent)

    return () => {
      socket.off('connect', joinRoom)
      socket.off('notification_sent', onNotificationSent)
      socket.emit('leave_user_room', { user_id: user.id })
    }
  }, [user?.id, appendNotification, clearNotifications])
}
