import { useState, useEffect, lazy, Suspense } from 'react'
import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import { Menu, X, Sun, Moon, Building2 } from 'lucide-react'

// Login/Signup are always the first pages loaded — keep them eager
import Login from '@/routes/Login'
import Signup from '@/routes/Signup'

// All other routes are lazy-loaded so each role only pays for its own bundle
const AdvisorWorkspace = lazy(() => import('@/routes/AdvisorWorkspace'))
const ClientPortal = lazy(() => import('@/routes/ClientPortal'))
const ContactCentre = lazy(() => import('@/routes/ContactCentre'))
const AgentTrace = lazy(() => import('@/routes/AgentTrace'))
const AdminConfig = lazy(() => import('@/routes/AdminConfig'))
const Profile = lazy(() => import('@/routes/Profile'))

import ProtectedRoute from '@/components/ProtectedRoute'
import ErrorBoundary from '@/components/ErrorBoundary'
import UserMenu from '@/features/auth/UserMenu'
import { NotificationBell } from '@/features/notifications/NotificationBell'
import { NotificationToast } from '@/features/notifications/NotificationToast'
import { useUserSocket } from '@/hooks/useUserSocket'
import { useAuthStore } from '@/store/authStore'
import { useThemeStore } from '@/store/themeStore'

const NAV_LINKS: { to: string; label: string; roles: string[] }[] = [
  { to: '/', label: 'Advisor Workspace', roles: ['advisor'] },
  { to: '/contact-centre', label: 'Contact Centre', roles: ['advisor'] },
  { to: '/agent-trace', label: 'Agent Trace', roles: ['advisor', 'admin'] },
  { to: '/admin', label: 'Admin Config', roles: ['admin'] },
]

function NavBar() {
  const { user, isAuthenticated } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  const ROLE_HOME: Record<string, string> = {
    client: '/client',
    advisor: '/',
    admin: '/admin',
  }
  const homeRoute = user ? (ROLE_HOME[user.role] ?? '/login') : '/login'

  const visibleLinks = isAuthenticated && user
    ? NAV_LINKS.filter((l) => l.roles.includes(user.role))
    : []

  return (
    <nav className="sticky top-0 z-50 flex items-center bg-gray-900 px-4 py-3 text-sm text-gray-300 lg:px-6">
      <Link to={homeRoute} className="flex items-center gap-3 mr-4 hover:opacity-80 transition-opacity">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
          <Building2 className="w-4 h-4 text-white" />
        </div>
        <span className="font-semibold text-white">GlideGate</span>
      </Link>

      {/* Desktop nav links — hidden on mobile */}
      {visibleLinks.map((l) => (
        <Link key={l.to} to={l.to} className="hidden lg:block px-3 py-1.5 rounded-lg hover:bg-gray-700 hover:text-white transition-colors">
          {l.label}
        </Link>
      ))}

      {/* Spacer pushes right-side items to the end */}
      <div className="flex-1" />

      {isAuthenticated && <NotificationBell />}

      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="mr-2 rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white"
        aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>

      {/* User menu — always visible */}
      {isAuthenticated && <UserMenu />}

      {/* Hamburger toggle — only on mobile when nav links exist */}
      {visibleLinks.length > 0 && (
        <button
          onClick={() => setMenuOpen((o) => !o)}
          className="ml-2 rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white lg:hidden"
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      )}

      {/* Mobile dropdown — slides down from navbar */}
      {menuOpen && (
        <div className="absolute left-0 right-0 top-full z-50 border-t border-gray-700 bg-gray-900 py-1 shadow-xl lg:hidden">
          {visibleLinks.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              onClick={() => setMenuOpen(false)}
              className="block px-5 py-3.5 text-sm text-gray-300 transition-colors hover:bg-gray-800 hover:text-white active:bg-gray-700"
            >
              {l.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  )
}

export default function App() {
  const theme = useThemeStore((s) => s.theme)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  useUserSocket()

  return (
    <div className="flex min-h-screen flex-col bg-gray-50 dark:bg-gray-950">
      <NavBar />
      <main className="flex flex-1 flex-col">
        <Suspense fallback={
          <div className="flex min-h-screen items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          </div>
        }>
          <Routes>
            {/* Public routes — eager, no ErrorBoundary needed */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            {/* Protected: all authenticated roles */}
            <Route
              path="/profile"
              element={
                <ProtectedRoute allowedRoles={['client', 'advisor', 'admin']}>
                  <ErrorBoundary>
                    <Profile />
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />

            {/* Advisor-only */}
            <Route
              path="/"
              element={
                <ProtectedRoute allowedRoles={['advisor']}>
                  <ErrorBoundary>
                    <AdvisorWorkspace />
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/contact-centre"
              element={
                <ProtectedRoute allowedRoles={['advisor']}>
                  <ErrorBoundary>
                    <ContactCentre />
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />

            {/* Advisor + Admin */}
            <Route
              path="/agent-trace"
              element={
                <ProtectedRoute allowedRoles={['advisor', 'admin']}>
                  <ErrorBoundary>
                    <AgentTrace />
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />

            {/* Admin-only */}
            <Route
              path="/admin"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <ErrorBoundary>
                    <AdminConfig />
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />

            {/* Client-only */}
            <Route
              path="/client"
              element={
                <ProtectedRoute allowedRoles={['client']}>
                  <ErrorBoundary>
                    <ClientPortal />
                  </ErrorBoundary>
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
