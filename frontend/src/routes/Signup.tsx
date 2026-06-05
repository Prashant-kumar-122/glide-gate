import { Navigate } from 'react-router-dom'
import SignupForm from '@/features/auth/SignupForm'
import AuthLayout from '@/features/auth/AuthLayout'
import { useAuthStore } from '@/store/authStore'

export default function Signup() {
  const { isAuthenticated, user } = useAuthStore()

  if (isAuthenticated && user) {
    return <Navigate to="/client" replace />
  }

  return (
    <AuthLayout eyebrow="Client Registration" heading="Create your account">
      <SignupForm />
    </AuthLayout>
  )
}
