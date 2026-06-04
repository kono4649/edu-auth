import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { oidcSession, userApi, type User } from '../api/client'
import { oidcClient } from '../api/oidc'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  login: () => Promise<void>
  logout: () => Promise<void>
  register: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      const redirectedUser = await oidcClient.handleRedirectCallback()
      if (redirectedUser) {
        setUser(redirectedUser)
        setIsLoading(false)
        return
      }

      if (oidcSession.getAccessToken()) {
        try {
          const { data } = await userApi.me()
          setUser(data)
        } catch {
          oidcSession.clear()
        }
      }
      setIsLoading(false)
    }

    initAuth()
  }, [])

  const login = useCallback(async () => {
    await oidcClient.signinRedirect()
  }, [])

  const logout = useCallback(async () => {
    setUser(null)
    await oidcClient.signoutRedirect()
  }, [])

  const register = useCallback(async () => {
    await oidcClient.signinRedirect()
  }, [])

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    isAdmin: user?.role === 'admin',
    login,
    logout,
    register,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
