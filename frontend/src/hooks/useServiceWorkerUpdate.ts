import { useState, useEffect } from 'react'

export function useServiceWorkerUpdate() {
  const [needsUpdate, setNeedsUpdate] = useState(false)
  const [reg, setReg] = useState<ServiceWorkerRegistration | null>(null)

  useEffect(() => {
    if (!('serviceWorker' in navigator) || import.meta.env.DEV) return

    // Register the service worker built by vite-plugin-pwa
    navigator.serviceWorker
      .register('/sw.js', { scope: '/' })
      .then((registration) => {
        setReg(registration)

        // A waiting SW means an update is ready
        if (registration.waiting) {
          setNeedsUpdate(true)
        }

        registration.addEventListener('updatefound', () => {
          const newSW = registration.installing
          if (!newSW) return
          newSW.addEventListener('statechange', () => {
            if (newSW.state === 'installed' && navigator.serviceWorker.controller) {
              setNeedsUpdate(true)
            }
          })
        })
      })
      .catch((err) => {
        console.error('[SW] registration failed:', err)
      })

    // After skipWaiting the new SW claims all clients; reload to get fresh assets
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      window.location.reload()
    })
  }, [])

  function applyUpdate() {
    if (!reg?.waiting) return
    reg.waiting.postMessage({ type: 'SKIP_WAITING' })
  }

  return { needsUpdate, applyUpdate }
}
