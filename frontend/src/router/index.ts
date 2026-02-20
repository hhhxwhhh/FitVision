import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import MainLayout from '../layouts/MainLayout.vue'
import HomeView from '../views/HomeView.vue'
import ProfileView from '../views/ProfileView.vue'
import TrainingView from '../views/TrainingView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'
import ExercisesView from '../views/ExercisesView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView
    },
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: HomeView
        },
        {
          path: 'profile',
          name: 'profile',
          component: ProfileView
        },
        {
          path: 'training',
          name: 'training',
          component: TrainingView
        },
        {
          path: 'training/report',
          name: 'TrainingReport',
          component: () => import('../views/TrainingReportView.vue')
        },
        {
          path: 'ai-plan', 
          name: 'ai-plan',
          component: () => import('../views/AIPlanView.vue')
        },
        {
          path: 'analytics',
          name: 'analytics',
          component: AnalyticsView
        },
        {
          path: 'exercises',
          name: 'exercises',
          component: ExercisesView
        },
        {
          path: 'exercises/graph',
          name: 'exercise-graph',
          component: () => import('../views/ExerciseGraphView.vue')
        }
      ]
    }
  ]
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('jwt_token')
  if (!token && to.path !== '/login' && to.path !== '/register') {
    next('/login')
  } else {
    next()
  }
})

export default router