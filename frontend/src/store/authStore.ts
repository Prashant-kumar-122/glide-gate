import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface AuthUser {
  id: string
  email: string
  firstName: string
  lastName: string
  role: string  // persona code — any domain-configured persona, not just the 4 built-in ones
}

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  setAuth: (user: AuthUser) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setAuth: (user) => set({ user, isAuthenticated: true }),
      clearAuth: () => set({ user: null, isAuthenticated: false }),
    }),
    // Non-sensitive user profile (no token) kept in localStorage so PWA sessions
    // survive close/reopen. Cookie validity is re-checked via /api/auth/me on startup.
    { name: 'gg_auth', storage: createJSONStorage(() => localStorage) }
  )
)
