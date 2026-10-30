import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { public: true, title: '注册' },
    },
    {
      path: '/',
      component: () => import('../layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('../views/HomeView.vue'),
          meta: { title: '首页' },
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('../views/ProfileView.vue'),
          meta: { title: '个人中心' },
        },
        {
          path: 'training',
          name: 'training',
          component: () => import('../views/TrainingView.vue'),
          meta: { title: '智能训练' },
        },
        {
          path: 'training/report',
          name: 'TrainingReport',
          component: () => import('../views/TrainingReportView.vue'),
          meta: { title: '训练报告' },
        },
        {
          path: 'ai-plan',
          name: 'ai-plan',
          component: () => import('../views/AIPlanView.vue'),
          meta: { title: 'AI 计划' },
        },
        {
          path: 'analytics',
          name: 'analytics',
          component: () => import('../views/AnalyticsView.vue'),
          meta: { title: '数据中心' },
        },
        {
          path: 'exercises',
          name: 'exercises',
          component: () => import('../views/ExercisesView.vue'),
          meta: { title: '动作百科' },
        },
        {
          path: 'exercises/graph',
          name: 'exercise-graph',
          component: () => import('../views/ExerciseGraphView.vue'),
          meta: { title: '动作知识图谱' },
        },
        {
          path: 'posture-diagnosis',
          name: 'posture-diagnosis',
          component: () => import('../views/PostureDiagnosisView.vue'),
          meta: { title: '姿态诊断' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
      meta: { public: true, title: '页面未找到' },
    },
  ],
})

const AUTH_PAGES = new Set(['login', 'register'])

router.beforeEach((to) => {
  const token = localStorage.getItem('jwt_token')
  const isPublic = to.meta.public === true

  if (!token && !isPublic) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (token && AUTH_PAGES.has(String(to.name))) {
    return { name: 'home' }
  }
  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = title ? `${title} · FitVision` : 'FitVision — AI 健身教练'
})

export default router
