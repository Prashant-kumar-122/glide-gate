import { Routes, Route, Navigate, Link } from 'react-router-dom'
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

  const visibleLinks = isAuthenticated && user
    ? NAV_LINKS.filter((l) => l.roles.includes(user.role))
    : []

  return (
    <nav className="flex items-center gap-4 bg-gray-900 px-6 py-3 text-sm text-gray-300">
      <span className="mr-4 font-semibold text-white">GlideGate</span>
      {visibleLinks.map((l) => (
        <Link key={l.to} to={l.to} className="hover:text-white">
          {l.label}
        </Link>
      ))}
      {isAuthenticated && <UserMenu />}
    </nav>
  )
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <NavBar />
      <main className="flex-1">
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
