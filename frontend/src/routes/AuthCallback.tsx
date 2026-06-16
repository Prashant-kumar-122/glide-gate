import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { exchangeCodeForToken, storeToken } from '@/lib/authConfig'
import { api } from '@/lib/api'
import type { UserOut } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'

const ROLE_HOME: Record<string, string> = {
  client:        '/client',
  advisor:       '/',
  admin:         '/admin',
  sales_manager: '/',
}

export default function AuthCallback() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params  = new URLSearchParams(window.location.search)
    const code    = params.get('code')
    const errParam = params.get('error')

    if (errParam) {
      setError(`SSO error: ${errParam} — ${params.get('error_description') ?? ''}`)
      return
    }
    if (!code) {
      navigate('/login', { replace: true })
      return
    }

    exchangeCodeForToken(code)
      .then(({ access_token }) => {
        storeToken(access_token)
        return api.get<UserOut>('/auth/me', {
          headers: { Authorization: `Bearer ${access_token}` },
        })
      })
      .then((res) => {
        const u = res.data
        setAuth({
          id:        u.id,
          email:     u.email,
          firstName: u.first_name,
          lastName:  u.last_name,
          role:      u.role,
        })
        navigate(ROLE_HOME[u.role] ?? '/', { replace: true })
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        setError(`Authentication failed: ${msg}`)
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="max-w-sm text-center space-y-4">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={() => navigate('/login', { replace: true })}
            className="text-sm font-medium text-primary hover:underline"
          >
            Back to login
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-200 border-t-primary dark:border-gray-700" />
    </div>
  )
}
