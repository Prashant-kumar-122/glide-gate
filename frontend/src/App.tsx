import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import { Menu, X, Sun, Moon, Building2 } from 'lucide-react'
import AdvisorWorkspace from '@/routes/AdvisorWorkspace'
import ClientPortal from '@/routes/ClientPortal'
import ContactCentre from '@/routes/ContactCentre'
import AgentTrace from '@/routes/AgentTrace'
import AdminConfig from '@/routes/AdminConfig'
import Login from '@/routes/Login'
import Signup from '@/routes/Signup'
import Profile from '@/routes/Profile'
import ProtectedRoute from '@/components/ProtectedRoute'
import UserMenu from '@/features/auth/UserMenu'
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

  const ROLE_LABELS: Record<string, string> = {
    client: 'Client Portal',
    advisor: 'Advisor Portal',
    admin: 'Admin Portal',
  }
  const pageLabel = user ? ROLE_LABELS[user.role] : undefined

  const visibleLinks = isAuthenticated && user
    ? NAV_LINKS.filter((l) => l.roles.includes(user.role))
    : []

  return (
    <nav className="sticky top-0 z-50 flex items-center bg-gray-900 px-4 py-3 text-sm text-gray-300 lg:px-6">
      <div className="flex items-center gap-3 mr-4">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
          <Building2 className="w-4 h-4 text-white" />
        </div>
        <span className="font-semibold text-white">GlideGate</span>
        {pageLabel && (
          <span className="text-gray-400 text-sm hidden md:block">/ {pageLabel}</span>
        )}
      </div>

      {/* Desktop nav links — hidden on mobile */}
      {visibleLinks.map((l) => (
        <Link key={l.to} to={l.to} className="hidden lg:block px-3 py-1.5 rounded-lg hover:bg-gray-700 hover:text-white transition-colors">
          {l.label}
        </Link>
      ))}

      {/* Spacer pushes right-side items to the end */}
      <div className="flex-1" />

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

  return (
    <div className="flex min-h-screen flex-col bg-gray-50 dark:bg-gray-950">
      <NavBar />
      <main className="flex flex-1 flex-col">
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Protected: all authenticated roles */}
          <Route
            path="/profile"
            element={
              <ProtectedRoute allowedRoles={['client', 'advisor', 'admin']}>
                <Profile />
              </ProtectedRoute>
            }
          />

          {/* Advisor-only */}
          <Route
            path="/"
            element={
              <ProtectedRoute allowedRoles={['advisor']}>
                <AdvisorWorkspace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/contact-centre"
            element={
              <ProtectedRoute allowedRoles={['advisor']}>
                <ContactCentre />
              </ProtectedRoute>
            }
          />

          {/* Advisor + Admin */}
          <Route
            path="/agent-trace"
            element={
              <ProtectedRoute allowedRoles={['advisor', 'admin']}>
                <AgentTrace />
              </ProtectedRoute>
            }
          />

          {/* Admin-only */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminConfig />
              </ProtectedRoute>
            }
          />

          {/* Client-only */}
          <Route
            path="/client"
            element={
              <ProtectedRoute allowedRoles={['client']}>
                <ClientPortal />
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </main>
    </div>
  )
}
