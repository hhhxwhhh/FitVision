import { defineStore } from 'pinia'
import apiClient from '@/api'

export interface User {
  id: number
  username: string
  nickname: string
  email: string
  avatar: string
}

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null as User | null,
  }),

  getters: {
    userName: (state) => state.user?.nickname || state.user?.username || '',
    userAvatar: (state) => state.user?.avatar || '',
    isAuthenticated: (state) => Boolean(state.user),
  },

  actions: {
    async fetchUser() {
      try {
        const { data } = await apiClient.get<User>('/auth/me/')
        this.user = data
        // 同步给非 store 场景（如旧版页面）使用
        localStorage.setItem('username', this.userName)
        if (this.userAvatar) localStorage.setItem('user_avatar', this.userAvatar)
      } catch (error) {
        this.user = null
        console.error('Fetch user failed', error)
      }
    },

    logout() {
      localStorage.removeItem('jwt_token')
      localStorage.removeItem('refresh_token')
      this.user = null
    },
  },
})
