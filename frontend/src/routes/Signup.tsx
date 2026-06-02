import { Navigate } from 'react-router-dom'
import SignupForm from '@/features/auth/SignupForm'
import { useAuthStore } from '@/store/authStore'

export default function Signup() {
  const { isAuthenticated, user } = useAuthStore()

  if (isAuthenticated && user) {
    return <Navigate to="/client" replace />
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4 dark:bg-gray-800">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">GlideGate</h1>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Wealth Management Onboarding Platform</p>
        </div>
        <div className="rounded-2xl bg-white p-8 shadow-sm dark:bg-gray-800">
          <h2 className="mb-6 text-xl font-semibold text-gray-900 dark:text-gray-100">Create account</h2>
          <SignupForm />
        </div>
      </div>
    </div>
  )
}
