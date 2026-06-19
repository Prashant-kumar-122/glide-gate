import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuthStore } from '@/store/authStore'

/**
 * Route audience semantics:
 *   'staff'  — any authenticated user whose role is not 'client'
 *              (covers advisor, sales_manager, admin, and any domain-specific
 *               personas such as deposit_ops or branch_manager)
 *   'client' — only the 'client' persona
 *   'admin'  — only the 'admin' persona
 *   'any'    — any authenticated user regardless of role
 */
export type RouteAudience = 'staff' | 'client' | 'admin' | 'any'

function isAllowed(role: string, audience: RouteAudience): boolean {
  switch (audience) {
    case 'any':    return true
    case 'client': return role === 'client'
    case 'admin':  return role === 'admin'
    case 'staff':  return role !== 'client'
  }
}

function fallbackRoute(role: string): string {
  if (role === 'client') return '/client'
  if (role === 'admin')  return '/admin'
  return '/'
}

interface ProtectedRouteProps {
  children: ReactNode
  audience: RouteAudience
}

export default function ProtectedRoute({ children, audience }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  if (!isAllowed(user.role, audience)) {
    return <Navigate to={fallbackRoute(user.role)} replace />
  }

  return <>{children}</>
}
