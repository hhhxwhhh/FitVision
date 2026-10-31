// frontend/src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus' // 引入 UI 组件库
import 'element-plus/dist/index.css' // 引入 UI 样式文件 (别漏了这行)
import 'element-plus/theme-chalk/dark/css-vars.css' // Element Plus 深色变量
import './style.css' // 引入全局样式
import App from './App.vue'
import router from './router' // 引入我们写的路由配置

const app = createApp(App)

// 安装插件
app.use(createPinia())
app.use(router) // 启用路由
app.use(ElementPlus) // 启用 UI 组件

// 兜底记录未捕获的组件异常，便于定位线上问题
app.config.errorHandler = (error, _instance, info) => {
  console.error('[FitVision] Unhandled error:', error, info)
}

// 令牌完全失效时统一跳转登录页，并保留当前地址
window.addEventListener('fitvision:unauthorized', () => {
  const current = router.currentRoute.value
  if (current.name !== 'login') {
    router.push({ name: 'login', query: { redirect: current.fullPath } })
  }
})

// 生产环境注册 Service Worker，提供可安装 PWA 与离线应用外壳
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .catch((error) => console.warn('[FitVision] Service worker registration failed:', error))
  })
}

// 挂载应用
app.mount('#app')
