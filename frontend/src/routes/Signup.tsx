import { Navigate } from 'react-router-dom'
import SignupForm from '@/features/auth/SignupForm'
import { useAuthStore } from '@/store/authStore'

export default function Signup() {
  const { isAuthenticated, user } = useAuthStore()

  if (isAuthenticated && user) {
    return <Navigate to="/client" replace />
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4 dark:bg-gray-950">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">GlideGate</h1>
        </div>
        <div className="border border-gray-200 bg-white p-8 dark:border-gray-700 dark:bg-gray-900">
          <h2 className="mb-6 text-xl font-semibold text-gray-900 dark:text-gray-100">Create account</h2>
          <SignupForm />
        </div>
      </div>
    </div>
  )
}
