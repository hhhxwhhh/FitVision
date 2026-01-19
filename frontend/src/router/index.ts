import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import HomeView from '../views/HomeView.vue'    // 新增
import ProfileView from '../views/ProfileView.vue' // 新增
import TrainingView from '../views/TrainingView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView
    },
    {
      path: '/training',
      name: 'training',
      component: TrainingView
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: AnalyticsView
    }
  ]
})

// 简单的路由守卫：没登录不准看首页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('jwt_token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router