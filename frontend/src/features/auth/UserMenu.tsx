import { useRef, useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { User, ChevronDown, LogOut, Download, Bell } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import { useLogout } from '@/hooks/useAuth'
import { usePwaInstall } from '@/hooks/usePwaInstall'
import { usePushSubscription } from '@/hooks/usePushSubscription'
import { PushPermissionModal } from '@/features/notifications/PushPermissionModal'

export default function UserMenu() {
  const { user } = useAuthStore()
  const logout = useLogout()
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [showPushModal, setShowPushModal] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { canInstall, isIos, promptInstall, dismiss } = usePwaInstall()
  const { permission, subscribed, isLoading: pushLoading, isPushSupported, unsubscribe } = usePushSubscription()

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  if (!user) return null

  function handleSignOut() {
    qc.clear()
    setOpen(false)
    logout.mutate()
  }

  const fullName = `${user.firstName} ${user.lastName}`
  const initials = `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`

  return (
    <>
    <div ref={ref} className="relative ml-1">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded px-2 py-1 text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200 transition-colors"
      >
        <div className="flex h-6 w-6 items-center justify-center bg-gray-200 text-[10px] font-bold text-gray-700 dark:bg-gray-700 dark:text-gray-200 shrink-0">
          {initials}
        </div>
        <div className="hidden md:block text-left">
          <div className="text-xs font-medium text-gray-800 dark:text-gray-200 leading-tight">{fullName}</div>
        </div>
        <ChevronDown className={`h-3 w-3 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-56 border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900">
          {/* Identity row */}
          <div className="border-b border-gray-100 px-3 py-2.5 dark:border-gray-800">
            <p className="truncate text-xs font-semibold text-gray-900 dark:text-gray-200">{fullName}</p>
            <p className="truncate text-[10px] font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500 mt-0.5">
              {user.role.replace(/_/g, ' ')}
            </p>
            <p className="truncate text-[10px] text-gray-400 dark:text-gray-600 mt-0.5">{user.email}</p>
          </div>

          <Link
            to="/profile"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2.5 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-gray-100 transition-colors"
          >
            <User className="h-3.5 w-3.5 text-gray-400" />
            View Profile
          </Link>

          {/* PWA install affordance */}
          {canInstall && (
            <button
              onClick={() => { promptInstall(); setOpen(false) }}
              className="flex w-full items-center gap-2.5 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-gray-100 transition-colors"
            >
              <Download className="h-3.5 w-3.5 text-gray-400" />
              Install GlideGate
            </button>
          )}

          {/* iOS "Add to Home Screen" instructional fallback */}
          {isIos && (
            <button
              onClick={() => { dismiss(); setOpen(false) }}
              className="flex w-full items-center gap-2.5 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors"
            >
              <Download className="h-3.5 w-3.5 text-gray-400" />
              <span>Tap <strong>Share</strong> → <strong>Add to Home Screen</strong></span>
            </button>
          )}

          {/* Push notification opt-in / opt-out */}
          {isPushSupported && permission !== 'denied' && (
            <button
              onClick={() => {
                if (subscribed) {
                  unsubscribe()
                } else {
                  // Show pre-prompt explainer before triggering native browser dialog
                  setShowPushModal(true)
                }
                setOpen(false)
              }}
              disabled={pushLoading}
              className="flex w-full items-center gap-2.5 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-gray-100 transition-colors disabled:opacity-50"
            >
              <Bell className="h-3.5 w-3.5 text-gray-400" />
              {subscribed ? 'Disable Push Alerts' : 'Enable Push Alerts'}
            </button>
          )}

          <div className="mx-3 my-1 border-t border-gray-100 dark:border-gray-800" />

          <button
            onClick={handleSignOut}
            disabled={logout.isPending}
            className="flex w-full items-center gap-2.5 px-3 py-2 text-xs text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-950/50 dark:hover:text-red-300 transition-colors disabled:opacity-50"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign Out
          </button>
        </div>
      )}
    </div>

    {/* Push pre-prompt explainer — rendered outside the dropdown so it survives close */}
    {showPushModal && (
      <PushPermissionModal onClose={() => setShowPushModal(false)} />
    )}
    </>
  )
}
