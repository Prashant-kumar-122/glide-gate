import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useLogin } from '@/hooks/useAuth'
import { startKeycloakLogin } from '@/lib/authConfig'

export default function LoginForm() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showLocal, setShowLocal] = useState(false)
  const login = useLogin()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    login.mutate({ email, password })
  }

  return (
    <div className="flex flex-col gap-4">
      {/* ── Primary: SSO ──────────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => startKeycloakLogin()}
        className="flex w-full items-center justify-center gap-2.5 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary-hover"
      >
        <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
          <path d="M12 1.5C6.201 1.5 1.5 6.201 1.5 12S6.201 22.5 12 22.5 22.5 17.799 22.5 12 17.799 1.5 12 1.5zm0 3.75a2.25 2.25 0 1 1 0 4.5 2.25 2.25 0 0 1 0-4.5zm0 12.75c-3 0-5.655-1.528-7.2-3.848A9.104 9.104 0 0 1 12 12.75c2.524 0 4.8.99 6.45 2.596A8.981 8.981 0 0 1 12 18z" />
        </svg>
        Sign in with SSO
      </button>

      <p className="text-center text-[10px] text-gray-400 dark:text-gray-600 leading-relaxed">
        Use your organisation's single sign-on credentials.
      </p>

      {/* ── Divider ───────────────────────────────────────────────────── */}
      <div className="relative flex items-center gap-3">
        <div className="h-px flex-1 bg-gray-200 dark:bg-gray-800" />
        <span className="text-[10px] font-medium uppercase tracking-widest text-gray-400 dark:text-gray-600">
          or
        </span>
        <div className="h-px flex-1 bg-gray-200 dark:bg-gray-800" />
      </div>

      {/* ── Secondary: email + password (collapsible) ──────────────────── */}
      {!showLocal ? (
        <button
          type="button"
          onClick={() => setShowLocal(true)}
          className="w-full rounded-md border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          Sign in with email &amp; password
        </button>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          {login.error && (
            <div className="border border-red-300 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-700/40 dark:bg-red-950/60 dark:text-red-300">
              {(login.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                ?? 'Authentication failed. Check your credentials.'}
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-[10px] font-semibold uppercase tracking-widest text-gray-600 dark:text-gray-500">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 dark:placeholder-gray-600"
              placeholder="you@institution.com"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-[10px] font-semibold uppercase tracking-widest text-gray-600 dark:text-gray-500">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 dark:placeholder-gray-600"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={login.isPending}
            className="rounded-md border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            {login.isPending ? 'Authenticating…' : 'Sign In'}
          </button>
        </form>
      )}

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <p className="text-center text-xs text-gray-500 dark:text-gray-600">
        No account?{' '}
        <Link to="/signup" className="font-medium text-primary hover:underline">
          Sign up
        </Link>
      </p>
    </div>
  )
}
