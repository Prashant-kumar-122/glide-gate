import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import type { TokenResponse, UserOut } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import type { AuthUser } from '@/store/authStore'
import { getStoredToken, clearStoredToken, keycloakLogout } from '@/lib/authConfig'

// Query keys
export const authQk = {
  profile: ['auth', 'profile'] as const,
}

// Helpers
function toAuthUser(u: UserOut): AuthUser {
  return {
    id: u.id,
    email: u.email,
    firstName: u.first_name,
    lastName: u.last_name,
    role: u.role,
  }
}

// Hooks

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
      setAuth(toAuthUser(data.user))
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
      setAuth(user)
      // Route by role semantics: client → portal, admin → admin panel,
      // all other personas (advisors, domain-specific staff) → workspace.
      const dest = user.role === 'client' ? '/client'
                 : user.role === 'admin'  ? '/admin'
                 : '/'
      navigate(dest)
    },
  })
}

export function useLogout() {
  const { clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      if (getStoredToken()) {
        // Keycloak session — redirect to KC logout (terminates SSO session)
        qc.clear()
        clearAuth()
        keycloakLogout()
        return
      }
      await api.post('/auth/logout')
    },
    onSettled: () => {
      clearStoredToken()
      qc.clear()
      clearAuth()
      navigate('/login')
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
  const { setAuth } = useAuthStore()

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
      setAuth(toAuthUser(updated))
    },
  })
}

// Validates the session on app startup (cookie for local auth, Bearer for Keycloak).
// Clears auth store if the token/cookie is absent or expired.
export function useAuthInit() {
  const { setAuth, clearAuth } = useAuthStore()

  useEffect(() => {
    const kcToken = getStoredToken()
    const req = kcToken
      ? api.get<UserOut>('/auth/me', { headers: { Authorization: `Bearer ${kcToken}` } })
      : api.get<UserOut>('/auth/me')

    req
      .then((res) => setAuth(toAuthUser(res.data)))
      .catch(() => {
        clearStoredToken()
        clearAuth()
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
