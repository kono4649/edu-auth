import { oidcSession, type User } from './client'

const OIDC_AUTHORITY = import.meta.env.VITE_OIDC_AUTHORITY ?? 'http://localhost:8080/realms/ecommerce'
const OIDC_CLIENT_ID = import.meta.env.VITE_OIDC_CLIENT_ID ?? 'ecommerce-web'
const OIDC_REDIRECT_URI = import.meta.env.VITE_OIDC_REDIRECT_URI ?? `${window.location.origin}/login`
const OIDC_POST_LOGOUT_REDIRECT_URI =
  import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI ?? `${window.location.origin}/`

interface OidcProfile {
  sub: string
  email?: string
  preferred_username?: string
  realm_access?: { roles?: string[] }
}

interface TokenResponse {
  access_token: string
  id_token: string
}

const PKCE_VERIFIER_KEY = 'oidc_pkce_verifier'
const OIDC_STATE_KEY = 'oidc_state'

function base64UrlDecode(value: string): string {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
  return decodeURIComponent(
    atob(padded)
      .split('')
      .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, '0')}`)
      .join('')
  )
}

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = ''
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte)
  })
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

async function sha256(value: string): Promise<Uint8Array> {
  const data = new TextEncoder().encode(value)
  return new Uint8Array(await crypto.subtle.digest('SHA-256', data))
}

function decodeJwtPayload(token: string): OidcProfile {
  const [, payload] = token.split('.')
  if (!payload) {
    throw new Error('OIDC token payload is missing')
  }
  return JSON.parse(base64UrlDecode(payload)) as OidcProfile
}

function randomUrlSafeValue(): string {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  return base64UrlEncode(bytes)
}

async function buildAuthorizeUrl(): Promise<string> {
  const codeVerifier = randomUrlSafeValue()
  const state = randomUrlSafeValue()
  sessionStorage.setItem(PKCE_VERIFIER_KEY, codeVerifier)
  sessionStorage.setItem(OIDC_STATE_KEY, state)

  const url = new URL(`${OIDC_AUTHORITY}/protocol/openid-connect/auth`)
  url.searchParams.set('client_id', OIDC_CLIENT_ID)
  url.searchParams.set('redirect_uri', OIDC_REDIRECT_URI)
  url.searchParams.set('response_type', 'code')
  url.searchParams.set('scope', 'openid profile email orders:read orders:write')
  url.searchParams.set('state', state)
  url.searchParams.set('code_challenge', base64UrlEncode(await sha256(codeVerifier)))
  url.searchParams.set('code_challenge_method', 'S256')
  return url.toString()
}

function userFromIdToken(idToken: string): User {
  const profile = decodeJwtPayload(idToken)
  const roles = profile.realm_access?.roles ?? []
  return {
    id: profile.sub,
    email: profile.email ?? '',
    username: profile.preferred_username ?? profile.email ?? profile.sub,
    role: roles.includes('admin') ? 'admin' : 'user',
    created_at: '',
  }
}

export const oidcClient = {
  signinRedirect: async () => {
    window.location.assign(await buildAuthorizeUrl())
  },
  signoutRedirect: async () => {
    oidcSession.clear()
    const url = new URL(`${OIDC_AUTHORITY}/protocol/openid-connect/logout`)
    url.searchParams.set('client_id', OIDC_CLIENT_ID)
    url.searchParams.set('post_logout_redirect_uri', OIDC_POST_LOGOUT_REDIRECT_URI)
    window.location.assign(url.toString())
  },
  handleRedirectCallback: async (): Promise<User | null> => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')
    if (!code || !state) {
      return null
    }

    const expectedState = sessionStorage.getItem(OIDC_STATE_KEY)
    const codeVerifier = sessionStorage.getItem(PKCE_VERIFIER_KEY)

    if (state !== expectedState || !codeVerifier) {
      throw new Error('OIDC state or PKCE verifier is invalid')
    }

    sessionStorage.removeItem(OIDC_STATE_KEY)
    sessionStorage.removeItem(PKCE_VERIFIER_KEY)

    const body = new URLSearchParams()
    body.set('grant_type', 'authorization_code')
    body.set('client_id', OIDC_CLIENT_ID)
    body.set('redirect_uri', OIDC_REDIRECT_URI)
    body.set('code', code)
    body.set('code_verifier', codeVerifier)

    const response = await fetch(`${OIDC_AUTHORITY}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    if (!response.ok) {
      throw new Error('OIDC token exchange failed')
    }

    const tokenResponse = (await response.json()) as TokenResponse
    oidcSession.setAccessToken(tokenResponse.access_token)
    window.history.replaceState({}, document.title, window.location.pathname)

    return userFromIdToken(tokenResponse.id_token)
  },
}
