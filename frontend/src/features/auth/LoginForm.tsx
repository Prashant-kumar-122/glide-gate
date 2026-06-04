import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useLogin } from '@/hooks/useAuth'

export default function LoginForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useLogin()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    login.mutate({ email, password })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {login.error && (
        <div className="border border-red-300 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-700/40 dark:bg-red-950/60 dark:text-red-300">
          {(login.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Authentication failed. Check your credentials.'}
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
        className="mt-1 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {login.isPending ? 'Authenticating…' : 'Sign In'}
      </button>

      <p className="text-center text-xs text-gray-500 dark:text-gray-600">
        No account?{' '}
        <Link to="/signup" className="font-medium text-primary hover:underline">
          Request access
        </Link>
      </p>
    </form>
  )
}
