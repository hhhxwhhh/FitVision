<template>
  <div class="register-container">
    <div class="register-content">
      <div class="brand-section">
        <h1>FitVision</h1>
        <p class="brand-slogan">开启你的智能训练之旅</p>
      </div>

      <el-card class="register-card glass-effect">
        <h2 class="form-title">创建账号</h2>

        <el-form label-position="top" class="register-form" :model="form" :rules="rules" ref="formRef" size="large">
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

          <el-form-item label="确认密码" prop="passwordConfirm">
            <el-input v-model="form.passwordConfirm" type="password" show-password placeholder="请再次输入密码">
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <div class="action-buttons">
            <el-button type="primary" @click="handleRegister" :loading="loading" class="full-width-btn shadow-btn">
              注册
            </el-button>
          </div>
        </el-form>

        <div class="form-footer">
          <span class="footer-text">已有账号？</span>
          <el-link type="primary" :underline="false" @click="goLogin">立即登录</el-link>
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
  password: '',
  passwordConfirm: ''
})

const rules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度应在3到20个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '长度应在6到20个字符之间', trigger: 'blur' }
  ],
  passwordConfirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!value) {
          callback(new Error('请再次输入密码'))
        } else if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
})

const message = ref('')
const msgType = ref<'success' | 'error' | 'info' | 'warning'>('info')
const loading = ref(false)

const API_BASE = 'http://127.0.0.1:8000/api/auth'

const handleRegister = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  message.value = ''
  try {
    await axios.post(`${API_BASE}/register/`, {
      username: form.username,
      password: form.password,
      password_confirm: form.passwordConfirm
    })
    message.value = '注册成功，正在登录...'
    msgType.value = 'success'

    const loginRes = await axios.post(`${API_BASE}/login/`, {
      username: form.username,
      password: form.password
    })

    localStorage.setItem('jwt_token', loginRes.data.access)
    localStorage.setItem('username', loginRes.data.username)

    router.push('/')
  } catch (err: any) {
    const errorData = err.response?.data
    if (typeof errorData === 'object') {
      message.value = (Object.values(errorData)[0] as string) || '注册失败'
    } else {
      message.value = errorData || '注册失败'
    }
    msgType.value = 'error'
  } finally {
    loading.value = false
  }
}

const goLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: radial-gradient(circle at top right, #0ea5e9, #0f172a);
  background-size: cover;
  position: relative;
  overflow: hidden;
}

.register-container::before {
  content: '';
  position: absolute;
  top: -12%;
  right: -12%;
  width: 50%;
  height: 50%;
  background: radial-gradient(circle, rgba(14, 165, 233, 0.18) 0%, rgba(0, 0, 0, 0) 70%);
  border-radius: 50%;
  z-index: 1;
}

.register-container::after {
  content: '';
  position: absolute;
  bottom: -10%;
  left: -10%;
  width: 60%;
  height: 60%;
  background: radial-gradient(circle, rgba(34, 197, 94, 0.12) 0%, rgba(0, 0, 0, 0) 70%);
  border-radius: 50%;
  z-index: 1;
}

.register-content {
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
  color: white;
}

.brand-section h1 {
  font-size: 42px;
  font-weight: 800;
  margin: 0;
  letter-spacing: -1px;
  background: linear-gradient(135deg, #ffffff 0%, #bae6fd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-slogan {
  margin-top: 8px;
  font-size: 16px;
  color: #cbd5f5;
  font-weight: 300;
}

.register-card {
  width: 100%;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
}

.register-card :deep(.el-card__body) {
  padding: 32px;
}

.form-title {
  text-align: center;
  color: #fff;
  margin: 0 0 24px 0;
  font-size: 20px;
  font-weight: 600;
}

.register-form :deep(.el-form-item__label) {
  color: #cbd5e1;
}

.register-form :deep(.el-input__wrapper) {
  background-color: rgba(0, 0, 0, 0.2);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset;
  color: white;
}

.register-form :deep(.el-input__inner) {
  color: white;
}

.register-form :deep(.el-input__inner::placeholder) {
  color: #64748b;
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
  box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.35), 0 2px 4px -1px rgba(14, 165, 233, 0.1);
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
  color: #94a3b8;
  margin-right: 4px;
}

.footer-copyright {
  margin-top: 40px;
  color: #475569;
  font-size: 12px;
}

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

.register-content {
  animation: fadeInUp 0.8s ease-out;
}
</style>
