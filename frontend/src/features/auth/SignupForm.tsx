import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useSignup } from '@/hooks/useAuth'

export default function SignupForm() {
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm_password: '',
  })
  const signup = useSignup()

  function set(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    signup.mutate(form)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {signup.error && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {(signup.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Signup failed. Please try again.'}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <label htmlFor="first_name" className="text-sm font-medium text-gray-700 dark:text-gray-300">First name</label>
          <input
            id="first_name"
            type="text"
            autoComplete="given-name"
            required
            value={form.first_name}
            onChange={set('first_name')}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="last_name" className="text-sm font-medium text-gray-700 dark:text-gray-300">Last name</label>
          <input
            id="last_name"
            type="text"
            autoComplete="family-name"
            required
            value={form.last_name}
            onChange={set('last_name')}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="email" className="text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={form.email}
          onChange={set('email')}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="password" className="text-sm font-medium text-gray-700 dark:text-gray-300">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={form.password}
          onChange={set('password')}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
        <p className="text-xs text-gray-400">Min 8 characters with at least 1 digit</p>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="confirm_password" className="text-sm font-medium text-gray-700 dark:text-gray-300">Confirm password</label>
        <input
          id="confirm_password"
          type="password"
          autoComplete="new-password"
          required
          value={form.confirm_password}
          onChange={set('confirm_password')}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
      </div>

      <button
        type="submit"
        disabled={signup.isPending}
        className="mt-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {signup.isPending ? 'Creating account…' : 'Create account'}
      </button>

      <p className="text-center text-sm text-gray-500 dark:text-gray-400">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-blue-600 hover:underline dark:text-blue-400">Sign in</Link>
      </p>
    </form>
  )
}
