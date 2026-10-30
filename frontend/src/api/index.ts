import axios from 'axios'

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

// 响应拦截器：清理失效的登录态
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jwt_token')
      localStorage.removeItem('username')
      window.dispatchEvent(new CustomEvent('fitvision:unauthorized'))
    }
    return Promise.reject(error)
  },
)

export default apiClient
