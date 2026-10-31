<template>
  <AuthShell>
    <div class="form-head">
      <span class="fv-eyebrow">WELCOME BACK</span>
      <h2>登录 FitVision</h2>
      <p>继续你的训练节奏，AI 教练已经准备好了。</p>
    </div>

    <el-form
      ref="formRef"
      class="auth-form"
      label-position="top"
      :model="form"
      :rules="rules"
      size="large"
      @submit.prevent="handleLogin"
    >
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" placeholder="请输入用户名" autocomplete="username">
          <template #prefix>
            <el-icon><User /></el-icon>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="请输入密码"
          autocomplete="current-password"
        >
          <template #prefix>
            <el-icon><Lock /></el-icon>
          </template>
        </el-input>
      </el-form-item>

      <el-button
        type="primary"
        class="submit-btn"
        :loading="loading.login"
        native-type="submit"
      >
        登录
        <el-icon><Right /></el-icon>
      </el-button>
    </el-form>

    <div class="form-footer">
      <span>还没有账号？</span>
      <el-link type="primary" :underline="false" @click="goRegister">立即创建</el-link>
    </div>

    <transition name="el-fade-in">
      <el-alert
        v-if="message"
        :title="message"
        :type="msgType"
        show-icon
        class="auth-alert"
        @close="message = ''"
      />
    </transition>
  </AuthShell>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Lock, Right, User } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import apiClient from '../api'
import AuthShell from '../components/auth/AuthShell.vue'

const router = useRouter()
const route = useRoute()
const redirectTarget = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  password: '',
})

const rules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度应在 3 到 20 个字符之间', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码长度至少 6 位', trigger: 'blur' },
  ],
})

const message = ref('')
const msgType = ref<'success' | 'error' | 'info' | 'warning'>('info')
const loading = reactive({ login: false })

const handleLogin = async () => {
  if (!formRef.value || loading.login) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.login = true
  message.value = ''
  try {
    const res = await apiClient.post('/auth/login/', form)

    localStorage.setItem('jwt_token', res.data.access)
    localStorage.setItem('refresh_token', res.data.refresh)
    localStorage.setItem('username', res.data.username)

    message.value = `欢迎回来，${res.data.username}`
    msgType.value = 'success'
    window.setTimeout(() => router.push(redirectTarget), 420)
  } catch (err: unknown) {
    const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data
    message.value =
      (typeof data?.error === 'string' && data.error) ||
      (typeof data?.detail === 'string' && data.detail) ||
      '登录失败，请检查账号密码'
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
.form-head {
  margin-bottom: 26px;
}

.form-head h2 {
  margin: 10px 0 8px;
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -0.035em;
  color: var(--fv-text);
}

.form-head p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--fv-text-2);
}

.auth-form :deep(.el-form-item__label) {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--fv-text-2);
  padding-bottom: 6px;
}

.auth-form :deep(.el-input__wrapper) {
  height: 46px;
  border-radius: 12px;
  background: var(--fv-surface-2);
  box-shadow: 0 0 0 1px transparent inset;
  transition: box-shadow 0.2s ease;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--fv-primary) inset !important;
}

.auth-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  margin-top: 6px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: var(--fv-shadow-glow);
}

.form-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 22px;
  font-size: 13px;
  color: var(--fv-text-2);
}

.auth-alert {
  margin-top: 18px;
  border-radius: 12px;
}
</style>
