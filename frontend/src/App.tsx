import { useState } from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
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

const NAV_LINKS: { to: string; label: string; roles: string[] }[] = [
  { to: '/', label: 'Advisor Workspace', roles: ['advisor'] },
  { to: '/contact-centre', label: 'Contact Centre', roles: ['advisor'] },
  { to: '/agent-trace', label: 'Agent Trace', roles: ['advisor', 'admin'] },
  { to: '/admin', label: 'Admin Config', roles: ['admin'] },
]

function NavBar() {
  const { user, isAuthenticated } = useAuthStore()
  const [menuOpen, setMenuOpen] = useState(false)

  const visibleLinks = isAuthenticated && user
    ? NAV_LINKS.filter((l) => l.roles.includes(user.role))
    : []

  return (
    <nav className="relative flex items-center bg-gray-900 px-4 py-3 text-sm text-gray-300 lg:px-6">
      <span className="mr-4 font-semibold text-white">GlideGate</span>

      {/* Desktop nav links — hidden on mobile */}
      {visibleLinks.map((l) => (
        <Link key={l.to} to={l.to} className="hidden hover:text-white lg:block lg:mr-1">
          {l.label}
        </Link>
      ))}

      {/* Spacer pushes right-side items to the end */}
      <div className="flex-1" />

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
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
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
