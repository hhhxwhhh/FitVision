// frontend/src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus' // 引入 UI 组件库
import 'element-plus/dist/index.css'   // 引入 UI 样式文件 (别漏了这行)
import './style.css'                  // 引入全局样式
import App from './App.vue'
import router from './router'          // 引入我们写的路由配置

const app = createApp(App)

// 安装插件
app.use(createPinia())
app.use(router)        // 启用路由
app.use(ElementPlus)   // 启用 UI 组件

// 挂载应用
app.mount('#app')