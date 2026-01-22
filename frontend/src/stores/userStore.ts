import { defineStore } from 'pinia'
import axios from 'axios'

// 定义用户类型
interface User {
  id: number
  username: string
  email: string
}

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null as User | null,
    isAuthenticated: false,
    loading: false,
    error: null as string | null
  }),
  
  getters: {
    userName: (state) => state.user?.username || ''
  },
  
  actions: {
    async login(credentials: { username: string; password: string }) {
      this.loading = true
      this.error = null
      
      try {
        // 这里是模拟登录，实际应调用真实API
        console.log('Login attempt with:', credentials)
        // 模拟成功的登录响应
        this.user = {
          id: 1,
          username: credentials.username,
          email: `${credentials.username}@fitvision.com`
        }
        this.isAuthenticated = true
        return { success: true }
      } catch (error: any) {
        this.error = '登录失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    
    logout() {
      this.user = null
      this.isAuthenticated = false
      this.error = null
    }
  }
})