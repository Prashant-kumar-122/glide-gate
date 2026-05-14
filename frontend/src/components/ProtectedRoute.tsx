import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuthStore } from '@/store/authStore'
import type { AuthUser } from '@/store/authStore'

const DEFAULT_ROUTE: Record<AuthUser['role'], string> = {
  client: '/client',
  advisor: '/',
  admin: '/admin',
}

interface ProtectedRouteProps {
  children: ReactNode
  allowedRoles: AuthUser['role'][]
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={DEFAULT_ROUTE[user.role]} replace />
  }

  return <>{children}</>
}
