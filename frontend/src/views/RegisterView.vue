<template>
  <AuthShell>
    <div class="form-head">
      <span class="fv-eyebrow">CREATE ACCOUNT</span>
      <h2>开启训练之旅</h2>
      <p>30 秒完成注册，AI 会自动为你建立训练档案。</p>
    </div>

    <el-form
      ref="formRef"
      class="auth-form"
      label-position="top"
      :model="form"
      :rules="rules"
      size="large"
      @submit.prevent="handleRegister"
    >
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" placeholder="3–20 个字符" autocomplete="username">
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
          placeholder="至少 8 位，避免纯数字"
          autocomplete="new-password"
        >
          <template #prefix>
            <el-icon><Lock /></el-icon>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item label="确认密码" prop="passwordConfirm">
        <el-input
          v-model="form.passwordConfirm"
          type="password"
          show-password
          placeholder="再次输入密码"
          autocomplete="new-password"
        >
          <template #prefix>
            <el-icon><Lock /></el-icon>
          </template>
        </el-input>
      </el-form-item>

      <el-button type="primary" class="submit-btn" :loading="loading" native-type="submit">
        创建账号
        <el-icon><Right /></el-icon>
      </el-button>
    </el-form>

    <div class="form-footer">
      <span>已有账号？</span>
      <el-link type="primary" :underline="false" @click="goLogin">立即登录</el-link>
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
import { useRouter } from 'vue-router'
import { Lock, Right, User } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import apiClient from '../api'
import AuthShell from '../components/auth/AuthShell.vue'

const router = useRouter()
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  password: '',
  passwordConfirm: '',
})

const rules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度应在 3 到 20 个字符之间', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码长度至少 8 位', trigger: 'blur' },
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
      trigger: 'blur',
    },
  ],
})

const message = ref('')
const msgType = ref<'success' | 'error' | 'info' | 'warning'>('info')
const loading = ref(false)

function extractError(data: unknown): string {
  if (!data || typeof data !== 'object') return '注册失败，请稍后重试'
  for (const value of Object.values(data as Record<string, unknown>)) {
    if (typeof value === 'string' && value) return value
    if (Array.isArray(value) && value.length) return String(value[0])
  }
  return '注册失败，请稍后重试'
}

const handleRegister = async () => {
  if (!formRef.value || loading.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  message.value = ''
  try {
    await apiClient.post('/auth/register/', {
      username: form.username,
      password: form.password,
      password_confirm: form.passwordConfirm,
    })

    message.value = '注册成功，正在进入 FitVision…'
    msgType.value = 'success'

    const loginRes = await apiClient.post('/auth/login/', {
      username: form.username,
      password: form.password,
    })

    localStorage.setItem('jwt_token', loginRes.data.access)
    localStorage.setItem('refresh_token', loginRes.data.refresh)
    localStorage.setItem('username', loginRes.data.username)

    window.setTimeout(() => router.push('/'), 420)
  } catch (err: unknown) {
    const data = (err as { response?: { data?: unknown } }).response?.data
    message.value = extractError(data)
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
.form-head {
  margin-bottom: 24px;
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

.auth-form :deep(.el-form-item) {
  margin-bottom: 16px;
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
  margin-top: 20px;
  font-size: 13px;
  color: var(--fv-text-2);
}

.auth-alert {
  margin-top: 18px;
  border-radius: 12px;
}
</style>
