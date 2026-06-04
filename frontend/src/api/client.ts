import axios from 'axios'

const BASE_URL = '/api'

let accessToken: string | null = null

export const oidcSession = {
  getAccessToken: () => accessToken,
  setAccessToken: (token: string) => {
    accessToken = token
  },
  clear: () => {
    accessToken = null
  },
}

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = oidcSession.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      oidcSession.clear()
    }
    return Promise.reject(error)
  }
)

export interface User {
  id: string
  email: string
  username: string
  role: 'user' | 'admin'
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
  user_id: string
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

export const userApi = {
  me: () => apiClient.get<User>('/users/me'),
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
  updateRole: (userId: string, role: string) =>
    apiClient.put<User>(`/admin/users/${userId}/role`, { role }),
}
