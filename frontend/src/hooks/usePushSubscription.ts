import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  const bytes = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) bytes[i] = rawData.charCodeAt(i)
  return bytes
}

export type PushPermission = 'default' | 'granted' | 'denied'

export function usePushSubscription() {
  const [permission, setPermission] = useState<PushPermission>('default')
  const [subscribed, setSubscribed] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!('Notification' in window)) return
    setPermission(Notification.permission as PushPermission)

    // Check if already subscribed
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready
        .then((reg) => reg.pushManager.getSubscription())
        .then((sub) => setSubscribed(!!sub))
        .catch(() => {/* SW not yet active */})
    }
  }, [])

  const subscribe = useCallback(async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return
    setIsLoading(true)
    try {
      // getRegistration() resolves immediately; navigator.serviceWorker.ready hangs
      // forever in dev mode (no SW registered) or any context without an active SW.
      const existingReg = await navigator.serviceWorker.getRegistration('/')
      if (!existingReg) throw new Error('No service worker registered')

      const { data } = await api.get<{ public_key: string }>('/push/public-key')
      const reg = await navigator.serviceWorker.ready
      const pushSub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(data.public_key),
      })
      const json = pushSub.toJSON()
      await api.post('/push/subscribe', {
        endpoint: pushSub.endpoint,
        keys: {
          p256dh: json.keys?.p256dh ?? '',
          auth: json.keys?.auth ?? '',
        },
      })
      setPermission('granted')
      setSubscribed(true)
    } catch {
      setPermission(
        'Notification' in window
          ? (Notification.permission as PushPermission)
          : 'denied'
      )
    } finally {
      setIsLoading(false)
    }
  }, [])

  const unsubscribe = useCallback(async () => {
    if (!('serviceWorker' in navigator)) return
    setIsLoading(true)
    try {
      const reg = await navigator.serviceWorker.ready
      const pushSub = await reg.pushManager.getSubscription()
      if (pushSub) {
        const json = pushSub.toJSON()
        await api.delete('/push/subscribe', {
          data: {
            endpoint: pushSub.endpoint,
            keys: {
              p256dh: json.keys?.p256dh ?? '',
              auth: json.keys?.auth ?? '',
            },
          },
        })
        await pushSub.unsubscribe()
      }
      setSubscribed(false)
    } catch (err) {
      console.error('[Push] unsubscribe failed:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const isPushSupported =
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window

  return { permission, subscribed, isLoading, isPushSupported, subscribe, unsubscribe }
}
