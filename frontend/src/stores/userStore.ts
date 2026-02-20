import { defineStore } from 'pinia'
import apiClient from '@/api'

// 定义用户类型
interface User {
  id: number
  username: string
  nickname: string
  email: string
  avatar: string
}

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null as User | null,
    isAuthenticated: false,
    loading: false,
    error: null as string | null
  }),
  
  getters: {
    userName: (state) => state.user?.nickname || state.user?.username || '',
    userAvatar: (state) => state.user?.avatar || ''
  },
  
  actions: {
    async fetchUser() {
        try {
            const userRes = await apiClient.get('/auth/me/')
            this.user = userRes.data
            this.isAuthenticated = true
            // 同步一下 localStorage 给非 store 场景用
            localStorage.setItem('username', this.userName)
            if (this.userAvatar) {
                localStorage.setItem('user_avatar', this.userAvatar)
            }
        } catch (error) {
            this.isAuthenticated = false
            console.error('Fetch user failed', error)
        }
    },

    async login(credentials: { username: string; password: string }) {
      this.loading = true
      this.error = null
      
      try {
        const response = await apiClient.post('/auth/login/', credentials)
        const { access, refresh } = response.data
        
        localStorage.setItem('jwt_token', access)
        localStorage.setItem('refresh_token', refresh)
        
        // 获取用户信息
        const userRes = await apiClient.get('/auth/me/')
        this.user = userRes.data
        this.isAuthenticated = true
        
        return { success: true }
      } catch (error: any) {
        this.error = error.response?.data?.detail || '登录失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    
    logout() {
      localStorage.removeItem('jwt_token')
      localStorage.removeItem('refresh_token')
      this.user = null
      this.isAuthenticated = false
      this.error = null
    }
  }
})