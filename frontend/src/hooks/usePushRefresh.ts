import { useEffect } from 'react'
import { fetchMyNotifications } from '@/lib/api'
import { useNotificationStore } from '@/store/notificationStore'
import type { NotificationRecord } from '@/store/notificationStore'

/**
 * Listens for PUSH_RECEIVED messages from the service worker and refreshes
 * the in-app notification list. This is needed because push is only sent when
 * the user has no active socket, so the Socket.IO path won't deliver the event.
 */
export function usePushRefresh() {
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return

    function onMessage(event: MessageEvent) {
      if (event.data?.type !== 'PUSH_RECEIVED') return

      fetchMyNotifications()
        .then((items) => {
          const { appendNotification } = useNotificationStore.getState()
          for (const item of items) {
            appendNotification({
              id: item.id,
              templateId: item.template_id ?? '',
              channel: (item.channel as NotificationRecord['channel']) ?? 'in_app',
              subject: item.subject ?? '',
              bodyPreview: item.body_preview ?? '',
              priority: 'NORMAL',
              receivedAt: item.received_at,
              read: false,
            })
          }
        })
        .catch(() => { /* socket will eventually sync if it reconnects */ })
    }

    navigator.serviceWorker.addEventListener('message', onMessage)
    return () => navigator.serviceWorker.removeEventListener('message', onMessage)
  }, [])
}
