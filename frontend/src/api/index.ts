import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

/**
 * Base URL for the Django API.
 *
 * - Development: `/api` (proxied to the Django dev server by Vite).
 * - Production: set `VITE_API_BASE_URL` (e.g. `https://api.example.com/api`).
 */
const configuredBase = import.meta.env.VITE_API_BASE_URL || '/api'
export const API_BASE_URL = configuredBase.replace(/\/+$/, '')

/** Origin used to turn relative `/media/...` paths into absolute URLs. */
const API_ORIGIN = /^https?:\/\//i.test(API_BASE_URL) ? new URL(API_BASE_URL).origin : ''

const AUTH_PATHS = ['/auth/login/', '/auth/register/', '/auth/refresh/']

interface RetryableRequest extends InternalAxiosRequestConfig {
  _retry?: boolean
}

/**
 * Resolve a media path returned by the backend into something an `<img>` can
 * load, regardless of whether the API is proxied or served from another origin.
 */
export function resolveMediaUrl(path?: string | null): string {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  return API_ORIGIN ? `${API_ORIGIN}${normalized}` : normalized
}

export function clearSession(): void {
  localStorage.removeItem('jwt_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('username')
  localStorage.removeItem('user_avatar')
  window.dispatchEvent(new CustomEvent('fitvision:unauthorized'))
}

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 秒，兼容 VLM 图片分析等耗时请求
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：附加 JWT
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('jwt_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) throw new Error('No refresh token available')

  const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, { refresh })
  const access = data.access as string
  localStorage.setItem('jwt_token', access)
  if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
  return access
}

// 响应拦截器：访问令牌过期时自动刷新并重放原请求
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableRequest | undefined
    const status = error.response?.status
    const url = config?.url ?? ''
    const isAuthPath = AUTH_PATHS.some((path) => url.includes(path))

    if (status !== 401 || !config || config._retry) {
      return Promise.reject(error)
    }

    if (isAuthPath) {
      if (!url.includes('/auth/refresh/')) clearSession()
      return Promise.reject(error)
    }

    if (!localStorage.getItem('refresh_token')) {
      clearSession()
      return Promise.reject(error)
    }

    config._retry = true
    try {
      refreshPromise = refreshPromise ?? refreshAccessToken()
      const access = await refreshPromise
      config.headers.Authorization = `Bearer ${access}`
      return apiClient(config)
    } catch (refreshError) {
      clearSession()
      return Promise.reject(refreshError)
    } finally {
      refreshPromise = null
    }
  },
)

export default apiClient
