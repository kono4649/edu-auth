/**
 * 認証コンテキスト
 *
 * アプリ全体でユーザーの認証状態を管理する。
 * ログイン・ログアウト・ユーザー情報の取得をここで一元管理。
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi, tokenStorage, type User } from '../api/client'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // アプリ起動時: localStorage にトークンがあれば認証状態を復元
  useEffect(() => {
    const initAuth = async () => {
      const token = tokenStorage.getAccessToken()
      if (token) {
        try {
          const { data } = await authApi.me()
          setUser(data)
        } catch {
          // トークンが無効（有効期限切れなど）→ クリア
          tokenStorage.clearTokens()
        }
      }
      setIsLoading(false)
    }
    initAuth()
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await authApi.login({ email, password })
    tokenStorage.setTokens(data.access_token, data.refresh_token)
    const { data: userData } = await authApi.me()
    setUser(userData)
  }, [])

  const logout = useCallback(async () => {
    const refreshToken = tokenStorage.getRefreshToken()
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken)
      } catch {
        // ログアウト API が失敗しても、ローカルのトークンはクリアする
      }
    }
    tokenStorage.clearTokens()
    setUser(null)
  }, [])

  const register = useCallback(
    async (email: string, username: string, password: string) => {
      await authApi.register({ email, username, password })
      // 登録後に自動ログイン
      await login(email, password)
    },
    [login]
  )

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
