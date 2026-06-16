import { useState, useEffect, lazy, Suspense } from 'react'
import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import { Menu, X, Sun, Moon, WifiOff, RefreshCw } from 'lucide-react'

import Login from '@/routes/Login'
import Signup from '@/routes/Signup'
import AuthCallback from '@/routes/AuthCallback'

const AdvisorWorkspace = lazy(() => import('@/routes/AdvisorWorkspace'))
const ClientPortal     = lazy(() => import('@/routes/ClientPortal'))
const ContactCentre    = lazy(() => import('@/routes/ContactCentre'))
const AgentTrace       = lazy(() => import('@/routes/AgentTrace'))
const AdminConfig      = lazy(() => import('@/routes/AdminConfig'))
const Profile          = lazy(() => import('@/routes/Profile'))

import ProtectedRoute from '@/components/ProtectedRoute'
import ErrorBoundary from '@/components/ErrorBoundary'
import UserMenu from '@/features/auth/UserMenu'
import { NotificationBell } from '@/features/notifications/NotificationBell'
import { NotificationToast } from '@/features/notifications/NotificationToast'
import { useUserSocket } from '@/hooks/useUserSocket'
import { useAuthStore } from '@/store/authStore'
import { useThemeStore } from '@/store/themeStore'
import { useOnlineStatus } from '@/hooks/useOnlineStatus'
import { useServiceWorkerUpdate } from '@/hooks/useServiceWorkerUpdate'
import { useAuthInit } from '@/hooks/useAuth'
import { usePushRefresh } from '@/hooks/usePushRefresh'

const NAV_LINKS: { to: string; label: string; roles: string[] }[] = [
  { to: '/',               label: 'Workspace',      roles: ['advisor', 'sales_manager'] },
  { to: '/contact-centre', label: 'Contact Centre', roles: ['advisor', 'sales_manager'] },
  { to: '/agent-trace',    label: 'Agent Trace',    roles: ['advisor', 'sales_manager', 'admin'] },
  { to: '/admin',          label: 'Admin',          roles: ['admin'] },
]

function NavBar() {
  const { user, isAuthenticated } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  const ROLE_HOME: Record<string, string> = {
    client:        '/client',
    advisor:       '/',
    sales_manager: '/',
    admin:         '/admin',
  }
  const homeRoute = user ? (ROLE_HOME[user.role] ?? '/login') : '/login'

  const visibleLinks = isAuthenticated && user
    ? NAV_LINKS.filter((l) => l.roles.includes(user.role))
    : []

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950">
      {/* Main nav row */}
      <div className="flex h-11 items-center px-4 lg:px-6">
        {/* Brand mark */}
        <Link
          to={homeRoute}
          className="mr-6 flex items-center gap-2.5 hover:opacity-80 transition-opacity shrink-0"
        >
          <div className="flex h-6 w-6 items-center justify-center bg-primary shrink-0">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <rect x="1" y="1" width="4" height="4" fill="white" opacity="0.9" />
              <rect x="7" y="1" width="4" height="4" fill="white" opacity="0.6" />
              <rect x="1" y="7" width="4" height="4" fill="white" opacity="0.6" />
              <rect x="7" y="7" width="4" height="4" fill="white" opacity="0.3" />
            </svg>
          </div>
          <span className="text-sm font-semibold tracking-tight text-gray-900 dark:text-white">GlideGate</span>
        </Link>

        {/* Vertical rule */}
        {visibleLinks.length > 0 && (
          <div className="mr-4 h-4 w-px bg-gray-200 dark:bg-gray-800 hidden lg:block" aria-hidden="true" />
        )}

        {/* Desktop nav links */}
        <div className="hidden h-full items-center lg:flex">
          {visibleLinks.map((l) => {
            const isActive = location.pathname === l.to
            return (
              <Link
                key={l.to}
                to={l.to}
                className={[
                  'relative flex h-full items-center px-3.5 text-xs font-medium transition-colors',
                  'after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:transition-colors',
                  isActive
                    ? 'text-primary after:bg-primary'
                    : 'text-gray-500 hover:text-gray-800 after:bg-transparent hover:after:bg-gray-200 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:after:bg-gray-700',
                ].join(' ')}
              >
                {l.label}
              </Link>
            )
          })}
        </div>

        <div className="flex-1" />

        {/* Right controls */}
        <div className="flex items-center gap-0.5">
          {isAuthenticated && <NotificationBell />}

          <button
            onClick={toggleTheme}
            className="rounded p-1.5 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-300"
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark'
              ? <Sun className="h-3.5 w-3.5" />
              : <Moon className="h-3.5 w-3.5" />
            }
          </button>

          {isAuthenticated && <UserMenu />}

          {visibleLinks.length > 0 && (
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className="ml-1 rounded p-1.5 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-300 lg:hidden"
              aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={menuOpen}
            >
              {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div className="border-t border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950 lg:hidden">
          {visibleLinks.map((l) => {
            const isActive = location.pathname === l.to
            return (
              <Link
                key={l.to}
                to={l.to}
                onClick={() => setMenuOpen(false)}
                className={[
                  'flex items-center py-3 text-xs font-medium transition-colors',
                  isActive
                    ? 'border-l-2 border-primary pl-[19px] pr-5 text-primary bg-blue-50 dark:text-white dark:bg-gray-900'
                    : 'border-l-2 border-transparent px-5 text-gray-500 hover:bg-gray-50 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-gray-900 dark:hover:text-gray-200',
                ].join(' ')}
              >
                {l.label}
              </Link>
            )
          })}
        </div>
      )}
    </nav>
  )
}

export default function App() {
  const theme = useThemeStore((s) => s.theme)
  const isOnline = useOnlineStatus()
  const { needsUpdate, applyUpdate } = useServiceWorkerUpdate()

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  // Re-validate the session cookie on app startup; clears auth if expired
  useAuthInit()
  useUserSocket()
  usePushRefresh()

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-50 dark:bg-gray-950">
      <NavBar />

      {/* Offline banner */}
      {!isOnline && (
        <div
          role="alert"
          className="flex items-center gap-2 border-b border-amber-300 bg-amber-50 px-4 py-2 text-xs font-medium text-amber-800 dark:border-amber-700/50 dark:bg-amber-950/60 dark:text-amber-300"
        >
          <WifiOff className="h-3.5 w-3.5 shrink-0" />
          You are offline. Some features are unavailable until your connection is restored.
        </div>
      )}

      {/* SW update banner — non-dismissible; stale banking UI is dangerous */}
      {needsUpdate && (
        <div
          role="alert"
          className="flex items-center justify-between gap-2 border-b border-primary/30 bg-primary/10 px-4 py-2 text-xs"
        >
          <span className="font-medium text-primary dark:text-blue-300">
            A new version of GlideGate is available.
          </span>
          <button
            onClick={applyUpdate}
            className="flex items-center gap-1.5 rounded bg-primary px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-primary-hover transition-colors shrink-0"
          >
            <RefreshCw className="h-3 w-3" />
            Refresh now
          </button>
        </div>
      )}

      <main className="flex flex-1 flex-col overflow-y-auto">
        <Suspense fallback={
          <div className="flex min-h-screen items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-200 border-t-primary dark:border-gray-700" />
          </div>
        }>
          <Routes>
            <Route path="/login"         element={<Login />} />
            <Route path="/signup"        element={<Signup />} />
            <Route path="/auth/callback" element={<AuthCallback />} />

            <Route
              path="/profile"
              element={
                <ProtectedRoute allowedRoles={['client', 'advisor', 'admin', 'sales_manager']}>
                  <ErrorBoundary><Profile /></ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/"
              element={
                <ProtectedRoute allowedRoles={['advisor', 'sales_manager']}>
                  <ErrorBoundary><AdvisorWorkspace /></ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/contact-centre"
              element={
                <ProtectedRoute allowedRoles={['advisor', 'sales_manager']}>
                  <ErrorBoundary><ContactCentre /></ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/agent-trace"
              element={
                <ProtectedRoute allowedRoles={['advisor', 'admin', 'sales_manager']}>
                  <ErrorBoundary><AgentTrace /></ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <ErrorBoundary><AdminConfig /></ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/client"
              element={
                <ProtectedRoute allowedRoles={['client']}>
                  <ErrorBoundary><ClientPortal /></ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Suspense>
      </main>
      <NotificationToast />
    </div>
  )
}
