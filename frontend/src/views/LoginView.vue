<template>
  <div class="login-container">
    <div class="login-content">
      <div class="brand-section">
        <h1>FitVision</h1>
        <p class="brand-slogan">AI 驱动的个人智能训练助手</p>
      </div>

      <el-card class="login-card glass-effect">
        <h2 class="form-title">用户入口</h2>

        <el-form label-position="top" class="login-form" :model="form" :rules="rules" ref="formRef" size="large">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="请输入用户名">
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" show-password placeholder="请输入密码">
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <div class="action-buttons">
            <el-button type="primary" @click="handleLogin" :loading="loading.login" class="full-width-btn shadow-btn">
              登录
            </el-button>
          </div>
        </el-form>

        <div class="form-footer">
          <span class="footer-text">还没有账号？</span>
          <el-link type="primary" :underline="false" @click="goRegister">立即注册</el-link>
        </div>

        <transition name="el-fade-in">
          <el-alert v-if="message" :title="message" :type="msgType" show-icon class="mt-4" @close="message = ''" />
        </transition>
      </el-card>

      <div class="footer-copyright">
        &copy; 2026 FitVision AI. All rights reserved.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  password: ''
})

const rules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度应在3到20个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '长度应在6到20个字符之间', trigger: 'blur' }
  ]
})

const message = ref('')
const msgType = ref<'success' | 'error' | 'info' | 'warning'>('info')
const loading = reactive({
  login: false
})

const API_BASE = 'http://127.0.0.1:8000/api/auth'

const handleLogin = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.login = true
  message.value = ''
  try {
    const res = await axios.post(`${API_BASE}/login/`, form)

    localStorage.setItem('jwt_token', res.data.access)
    localStorage.setItem('username', res.data.username)

    message.value = `欢迎回来，${res.data.username}！正在跳转...`
    msgType.value = 'success'

    setTimeout(() => { router.push('/') }, 1000)
  } catch (err: any) {
    message.value = err.response?.data?.error || '登录失败，请检查账号密码'
    msgType.value = 'error'
  } finally {
    loading.login = false
  }
}

const goRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.login-container {
  --milan-bg-main: #F5F2ED; /* 页面亮面主色 */
  --milan-bg-surface: #E5E0D8; /* 边框 / 分隔 */
  --milan-text-primary: #3C2F2F; /* 主标题 / 正文 */
  --milan-text-secondary: #7D756D; /* 辅助文字 */
  --milan-accent: #BEA47E; /* 主按钮 / 交互强调 */
  --milan-accent-soft: #D5C6B0; /* 次级高亮 */
  --milan-accent-deep: #9F8462; /* 深强调 */
  --milan-overlay: rgba(245, 242, 237, 0.08); /* 玻璃蒙层 */
  --milan-overlay-strong: rgba(60, 47, 47, 0.2); /* 输入框深底 */

  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: radial-gradient(circle at top left, #CDB99A, #4C403A);
  background-size: cover;
  position: relative;
  overflow: hidden;
}

/* Background Accents */
.login-container::before {
  content: '';
  position: absolute;
  top: -10%;
  left: -10%;
  width: 50%;
  height: 50%;
  background: radial-gradient(circle, rgba(245, 242, 237, 0.2) 0%, rgba(0, 0, 0, 0) 70%);
  border-radius: 50%;
  z-index: 1;
}

.login-container::after {
  content: '';
  position: absolute;
  bottom: -10%;
  right: -10%;
  width: 60%;
  height: 60%;
  background: radial-gradient(circle, rgba(190, 164, 126, 0.22) 0%, rgba(0, 0, 0, 0) 70%);
  border-radius: 50%;
  z-index: 1;
}

.login-content {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 420px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.brand-section {
  text-align: center;
  margin-bottom: 30px;
  color: var(--milan-bg-main);
}

.brand-section h1 {
  font-size: 42px;
  font-weight: 800;
  margin: 0;
  letter-spacing: -1px;
  background: linear-gradient(135deg, #F5F2ED 0%, #E5E0D8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-slogan {
  margin-top: 8px;
  font-size: 16px;
  color: #E5E0D8;
  font-weight: 300;
}

.login-card {
  width: 100%;
  border-radius: 20px;
  border: 1px solid rgba(229, 224, 216, 0.35);
  background: var(--milan-overlay) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 25px 50px -12px rgba(60, 47, 47, 0.45) !important;
}

.login-card :deep(.el-card__body) {
  padding: 32px;
}

.form-title {
  text-align: center;
  color: var(--milan-bg-main);
  margin: 0 0 24px 0;
  font-size: 20px;
  font-weight: 600;
}

.login-form :deep(.el-form-item__label) {
  color: #E5E0D8;
}

.login-form :deep(.el-input__wrapper) {
  background-color: var(--milan-overlay-strong);
  box-shadow: 0 0 0 1px rgba(229, 224, 216, 0.2) inset;
  color: var(--milan-bg-main);
}

.login-form :deep(.el-input__inner) {
  color: var(--milan-bg-main);
}

.login-form :deep(.el-input__inner::placeholder) {
  color: #B7ADA2;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 32px;
}

.full-width-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  border-radius: 8px;
}

.shadow-btn {
  box-shadow: 0 4px 6px -1px rgba(190, 164, 126, 0.35), 0 2px 4px -1px rgba(190, 164, 126, 0.18);
}

.mt-4 {
  margin-top: 16px;
}

.form-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
}

.footer-text {
  color: #E5E0D8;
  margin-right: 4px;
}

.footer-copyright {
  margin-top: 40px;
  color: #D5C6B0;
  font-size: 12px;
}

.login-container :deep(.el-button--primary) {
  --el-button-bg-color: var(--milan-accent);
  --el-button-border-color: var(--milan-accent);
  --el-button-hover-bg-color: var(--milan-accent-deep);
  --el-button-hover-border-color: var(--milan-accent-deep);
  --el-button-active-bg-color: var(--milan-accent-deep);
  --el-button-active-border-color: var(--milan-accent-deep);
  --el-button-text-color: var(--milan-bg-main);
}

.login-container :deep(.el-link.el-link--primary) {
  --el-link-text-color: #F5F2ED;
  --el-link-hover-text-color: var(--milan-accent-soft);
}

.login-container :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--milan-accent-soft) inset !important;
}

/* Animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-content {
  animation: fadeInUp 0.8s ease-out;
}
</style>