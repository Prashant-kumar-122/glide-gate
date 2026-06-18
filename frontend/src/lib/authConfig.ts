const KC_URL    = (import.meta.env.VITE_KEYCLOAK_URL    as string | undefined) ?? 'http://18.60.103.228:8180'
const KC_REALM  = (import.meta.env.VITE_KEYCLOAK_REALM  as string | undefined) ?? 'glidegate'
const KC_CLIENT = (import.meta.env.VITE_KEYCLOAK_CLIENT_ID as string | undefined) ?? 'glidegate-frontend'

function redirectUri() {
  return `${window.location.origin}/auth/callback`
}

export const authEndpoints = {
  auth:   `${KC_URL}/realms/${KC_REALM}/protocol/openid-connect/auth`,
  token:  `${KC_URL}/realms/${KC_REALM}/protocol/openid-connect/token`,
  logout: `${KC_URL}/realms/${KC_REALM}/protocol/openid-connect/logout`,
}

function base64url(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let s = ''
  for (const b of bytes) s += String.fromCharCode(b)
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

export async function startKeycloakLogin(): Promise<void> {
  const verifier = base64url(crypto.getRandomValues(new Uint8Array(32)).buffer)
  const state    = base64url(crypto.getRandomValues(new Uint8Array(16)).buffer)

  // crypto.subtle requires HTTPS or localhost — fall back to plain PKCE on HTTP + IP
  let challenge: string
  let challengeMethod: string
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
    challenge       = base64url(buf)
    challengeMethod = 'S256'
  } else {
    challenge       = verifier
    challengeMethod = 'plain'
  }

  sessionStorage.setItem('kc_verifier', verifier)
  sessionStorage.setItem('kc_state', state)

  const params = new URLSearchParams({
    client_id:             KC_CLIENT,
    redirect_uri:          redirectUri(),
    response_type:         'code',
    scope:                 'openid email profile',
    code_challenge:        challenge,
    code_challenge_method: challengeMethod,
    state,
  })
  window.location.href = `${authEndpoints.auth}?${params}`
}

export async function exchangeCodeForToken(
  code: string,
): Promise<{ access_token: string; refresh_token: string; expires_in: number }> {
  const verifier = sessionStorage.getItem('kc_verifier')
  if (!verifier) throw new Error('Missing PKCE verifier')

  const body = new URLSearchParams({
    grant_type:    'authorization_code',
    client_id:     KC_CLIENT,
    redirect_uri:  redirectUri(),
    code,
    code_verifier: verifier,
  })

  const resp = await fetch(authEndpoints.token, {
    method:  'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`Token exchange failed (${resp.status}): ${text}`)
  }
  return resp.json() as Promise<{ access_token: string; refresh_token: string; expires_in: number }>
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem('kc_access_token')
}

export function storeToken(token: string): void {
  sessionStorage.setItem('kc_access_token', token)
}

export function getStoredRefreshToken(): string | null {
  return sessionStorage.getItem('kc_refresh_token')
}

export function storeRefreshToken(token: string): void {
  sessionStorage.setItem('kc_refresh_token', token)
}

export function clearStoredToken(): void {
  sessionStorage.removeItem('kc_access_token')
  sessionStorage.removeItem('kc_refresh_token')
  sessionStorage.removeItem('kc_verifier')
  sessionStorage.removeItem('kc_state')
}

export async function refreshKeycloakToken(): Promise<{
  access_token: string
  refresh_token: string
  expires_in: number
}> {
  const refreshToken = getStoredRefreshToken()
  if (!refreshToken) throw new Error('No refresh token stored')

  const body = new URLSearchParams({
    grant_type:    'refresh_token',
    client_id:     KC_CLIENT,
    refresh_token: refreshToken,
  })

  const resp = await fetch(authEndpoints.token, {
    method:  'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`Token refresh failed (${resp.status}): ${text}`)
  }
  return resp.json() as Promise<{ access_token: string; refresh_token: string; expires_in: number }>
}

export function keycloakLogout(postLogoutRedirectUri?: string): void {
  clearStoredToken()
  const uri = postLogoutRedirectUri ?? `${window.location.origin}/login`
  const params = new URLSearchParams({ client_id: KC_CLIENT, post_logout_redirect_uri: uri })
  window.location.href = `${authEndpoints.logout}?${params}`
}
