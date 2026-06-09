/// <reference lib="WebWorker" />
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'
import { registerRoute } from 'workbox-routing'
import { NetworkOnly } from 'workbox-strategies'

declare const self: ServiceWorkerGlobalScope

// Remove precache entries from previous SW versions
cleanupOutdatedCaches()

// Precache all Vite build assets — the manifest list is injected by vite-plugin-pwa
// at build time via self.__WB_MANIFEST (excluded from this source comment).
precacheAndRoute(self.__WB_MANIFEST)

// NEVER CACHE — all API routes and financial/PII/auth data.
// CI assertion in src/tests/sw-cache-rules.test.ts verifies this list is exhaustive.
const NETWORK_ONLY_PATTERNS = [
  /\/api\//,
  /\/socket\.io\//,
]

for (const pattern of NETWORK_ONLY_PATTERNS) {
  registerRoute(pattern, new NetworkOnly())
}

// Handle skip-waiting message from workbox-window (triggered by the update banner)
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})

// Web Push — show a notification from the thin payload (no sensitive data in body)
self.addEventListener('push', (event) => {
  if (!event.data) return
  let data: Record<string, string> = {}
  try {
    data = event.data.json() as Record<string, string>
  } catch {
    return
  }

  event.waitUntil(
    Promise.all([
      self.registration.showNotification(data.title ?? 'GlideGate', {
        body: data.body_preview ?? '',
        icon: '/icons/icon.svg',
        badge: '/icons/icon.svg',
        tag: data.notification_id,
        data: { url: data.url ?? '/' },
      }),
      // Tell every open app window to refresh the notification list.
      // The app may be open but without a socket (that's why push was used),
      // so it won't receive the Socket.IO event — it needs this signal.
      self.clients
        .matchAll({ type: 'window' })
        .then((clients) => {
          for (const client of clients) {
            client.postMessage({ type: 'PUSH_RECEIVED' })
          }
        }),
    ])
  )
})

// Notification click — focus an existing window or open the deep-link URL
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = (event.notification.data as { url?: string })?.url ?? '/'

  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        const existing = windowClients.find((c) =>
          c.url.startsWith(self.location.origin)
        )
        if (existing) {
          return existing.focus()
        }
        return self.clients.openWindow(targetUrl)
      })
  )
})
