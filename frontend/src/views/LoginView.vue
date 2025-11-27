<template>
  <div class="login-container">
    <el-card class="box-card">
      <h2>FitVision 用户入口</h2>

      <el-form label-width="80px" class="login-form" :model="form" :rules="rules" ref="formRef">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>

        <div class="btn-group">
          <el-button type="primary" @click="handleLogin" :loading="loading.login">
            登录
          </el-button>
          <el-button @click="handleRegister" :loading="loading.register">
            注册
          </el-button>
        </div>
      </el-form>

      <el-alert v-if="message" :title="message" :type="msgType" show-icon style="margin-top: 20px" closable
        @close="message = ''" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
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
  login: false,
  register: false
})

const API_BASE = 'http://127.0.0.1:8000/api/auth'

const handleLogin = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.login = true
  try {
    const res = await axios.post(`${API_BASE}/login/`, form)

    localStorage.setItem('jwt_token', res.data.access)
    localStorage.setItem('username', res.data.username)

    message.value = `欢迎回来，${res.data.username}！正在跳转...`
    msgType.value = 'success'

    setTimeout(() => { router.push('/') }, 1500)
  } catch (err: any) {
    message.value = err.response?.data?.error || '登录失败，请检查账号密码'
    msgType.value = 'error'
  } finally {
    loading.login = false
  }
}

const handleRegister = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.register = true
  try {
    await axios.post(`${API_BASE}/register/`, form)
    message.value = '注册成功！请直接点击登录'
    msgType.value = 'success'

    // 清空密码字段
    form.password = ''
  } catch (err: any) {
    const errorData = err.response?.data
    if (typeof errorData === 'object') {
      message.value = Object.values(errorData)[0] as string || '注册失败'
    } else {
      message.value = errorData || '注册失败'
    }
    msgType.value = 'error'
  } finally {
    loading.register = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #2c3e50;
}

.box-card {
  width: 400px;
  padding: 20px;
}

.btn-group {
  display: flex;
  justify-content: space-around;
  margin-top: 30px;
}
</style>