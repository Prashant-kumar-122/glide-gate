import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import type { TokenResponse, UserOut } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import type { AuthUser } from '@/store/authStore'

// ── Query keys ────────────────────────────────────────────────────────────────

export const authQk = {
  profile: ['auth', 'profile'] as const,
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function toAuthUser(u: UserOut): AuthUser {
  return {
    id: u.id,
    email: u.email,
    firstName: u.first_name,
    lastName: u.last_name,
    role: u.role,
  }
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useSignup() {
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (data: {
      email: string
      first_name: string
      last_name: string
      password: string
      confirm_password: string
    }) => {
      const res = await api.post<TokenResponse>('/auth/signup', data)
      return res.data
    },
    onSuccess: (data) => {
      qc.clear()
      setAuth(data.access_token, toAuthUser(data.user))
      navigate('/client')
    },
  })
}

export function useLogin() {
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (data: { email: string; password: string }) => {
      const res = await api.post<TokenResponse>('/auth/login', data)
      return res.data
    },
    onSuccess: (data) => {
      const user = toAuthUser(data.user)
      qc.clear()
      setAuth(data.access_token, user)
      const defaultRoute: Record<string, string> = {
        client: '/client',
        advisor: '/',
        admin: '/admin',
      }
      navigate(defaultRoute[user.role] ?? '/')
    },
  })
}

export function useProfile() {
  const { isAuthenticated } = useAuthStore()
  return useQuery({
    queryKey: authQk.profile,
    queryFn: async () => {
      const res = await api.get<UserOut>('/auth/me')
      return res.data
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  })
}

export function useUpdateProfile() {
  const qc = useQueryClient()
  const { user, setAuth, token } = useAuthStore()

  return useMutation({
    mutationFn: async (data: {
      email?: string
      first_name?: string
      last_name?: string
      password?: string
      confirm_password?: string
    }) => {
      const res = await api.patch<UserOut>('/auth/me', data)
      return res.data
    },
    onSuccess: (updated) => {
      qc.setQueryData(authQk.profile, updated)
      if (token && user) {
        setAuth(token, toAuthUser(updated))
      }
    },
  })
}
