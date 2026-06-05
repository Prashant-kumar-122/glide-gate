import { Navigate } from 'react-router-dom'
import LoginForm from '@/features/auth/LoginForm'
import AuthLayout from '@/features/auth/AuthLayout'
import { useAuthStore } from '@/store/authStore'

export default function Login() {
  const { isAuthenticated, user } = useAuthStore()

  if (isAuthenticated && user) {
    const defaultRoute: Record<string, string> = {
      client:  '/client',
      advisor: '/',
      admin:   '/admin',
    }
    return <Navigate to={defaultRoute[user.role] ?? '/'} replace />
  }

  return (
    <AuthLayout eyebrow="Secure Portal Access" heading="Sign in to your account">
      <LoginForm />
    </AuthLayout>
  )
}
