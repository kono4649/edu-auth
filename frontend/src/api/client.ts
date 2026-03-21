/**
 * Axios クライアント設定
 *
 * 【学習ポイント】
 * フロントエンドでの JWT 管理:
 * 1. localStorage にトークンを保存（シンプルだが XSS に注意）
 * 2. リクエストインターセプターで Authorization ヘッダーを自動付与
 * 3. レスポンスインターセプターで 401 時にトークンリフレッシュを試みる
 */
import axios from 'axios'

const BASE_URL = '/api'

// トークンの localStorage キー
const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

export const tokenStorage = {
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  },
  setAccessToken: (accessToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  },
  clearTokens: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}

// Axios インスタンスの作成
export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * リクエストインターセプター
 * 全リクエストに Authorization: Bearer <token> ヘッダーを自動付与
 */
apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// リフレッシュ中フラグ（複数の 401 が同時に来た場合の多重リフレッシュ防止）
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: string) => void
  reject: (error: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token!)
    }
  })
  failedQueue = []
}

/**
 * レスポンスインターセプター
 * 401 Unauthorized 時にリフレッシュトークンを使ってアクセストークンを更新する
 *
 * 【フロー】
 * 1. API 呼び出し → 401
 * 2. refresh_token で /auth/refresh を呼ぶ
 * 3. 成功: 新 access_token を保存して元のリクエストをリトライ
 * 4. 失敗: ログアウト処理（トークンクリア + ログインページへ）
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 401 かつ未リトライ かつ /auth/refresh 以外
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      if (isRefreshing) {
        // リフレッシュ中は待機してキューに追加
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return apiClient(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = tokenStorage.getRefreshToken()
      if (!refreshToken) {
        tokenStorage.clearTokens()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const newAccessToken = data.access_token
        tokenStorage.setAccessToken(newAccessToken)
        processQueue(null, newAccessToken)
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        tokenStorage.clearTokens()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// ─── API 関数 ────────────────────────────────────────────────────────────────

export interface User {
  id: number
  email: string
  username: string
  role: 'user' | 'admin'
  is_active: boolean
  created_at: string
}

export interface Product {
  id: number
  name: string
  description: string | null
  price: number
  stock: number
  is_active: boolean
  created_at: string
}

export interface Order {
  id: number
  user_id: number
  status: string
  total_amount: number
  created_at: string
  items: OrderItem[]
}

export interface OrderItem {
  id: number
  product_id: number
  quantity: number
  unit_price: number
}

export const authApi = {
  register: (data: { email: string; username: string; password: string }) =>
    apiClient.post<User>('/auth/register', data),

  login: (data: { email: string; password: string }) =>
    apiClient.post<{ access_token: string; refresh_token: string; token_type: string }>(
      '/auth/login',
      data
    ),

  logout: (refreshToken: string) =>
    apiClient.post('/auth/logout', { refresh_token: refreshToken }),

  me: () => apiClient.get<User>('/auth/me'),
}

export const productsApi = {
  list: () => apiClient.get<Product[]>('/products'),
  get: (id: number) => apiClient.get<Product>(`/products/${id}`),
  create: (data: Omit<Product, 'id' | 'is_active' | 'created_at'>) =>
    apiClient.post<Product>('/products', data),
  update: (id: number, data: Partial<Product>) =>
    apiClient.put<Product>(`/products/${id}`, data),
  delete: (id: number) => apiClient.delete(`/products/${id}`),
}

export const ordersApi = {
  list: () => apiClient.get<Order[]>('/orders'),
  get: (id: number) => apiClient.get<Order>(`/orders/${id}`),
  create: (items: { product_id: number; quantity: number }[]) =>
    apiClient.post<Order>('/orders', { items }),
  updateStatus: (id: number, status: string) =>
    apiClient.put<Order>(`/orders/${id}/status`, { status }),
}

export const adminApi = {
  listUsers: () => apiClient.get<User[]>('/admin/users'),
  updateRole: (userId: number, role: string) =>
    apiClient.put<User>(`/admin/users/${userId}/role`, { role }),
  deactivateUser: (userId: number) =>
    apiClient.put<User>(`/admin/users/${userId}/deactivate`),
}
