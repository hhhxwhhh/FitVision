<template>
  <div class="login-container">
    <el-card class="box-card">
      <h2>FitVision 用户入口</h2>
      
      <el-form label-width="80px" class="login-form">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>

        <div class="btn-group">
          <el-button type="primary" @click="handleLogin" :loading="loading">登录</el-button>
          <el-button @click="handleRegister" :loading="loading">注册</el-button>
        </div>
      </el-form>

      <el-alert v-if="message" :title="message" :type="msgType" show-icon style="margin-top: 20px" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const form = reactive({ username: '', password: '' })
const message = ref('')
const msgType = ref('info') // success / error / info
const loading = ref(false)

// 后端地址
const API_BASE = 'http://127.0.0.1:8000/api/auth'

// 登录逻辑
const handleLogin = async () => {
  if (!form.username || !form.password) return alert('请输入完整信息')
  
  loading.value = true
  try {
    const res = await axios.post(`${API_BASE}/login/`, form)
    
    // 1. 存 Token
    localStorage.setItem('jwt_token', res.data.access)
    localStorage.setItem('username', res.data.username)
    
    message.value = `欢迎回来，${res.data.username}！正在跳转...`
    msgType.value = 'success'

    // 2. 跳转到首页
    setTimeout(() => { router.push('/') }, 1500)

  } catch (err: any) {
    message.value = err.response?.data?.error || '登录失败，请检查账号密码'
    msgType.value = 'error'
  } finally {
    loading.value = false
  }
}

// 注册逻辑
const handleRegister = async () => {
  if (!form.username || !form.password) return alert('请输入完整信息')
  
  loading.value = true
  try {
    const res = await axios.post(`${API_BASE}/register/`, form)
    message.value = '注册成功！请直接点击登录'
    msgType.value = 'success'
  } catch (err: any) {
    // 处理后端返回的错误信息 (比如用户名已存在)
    const errorData = err.response?.data
    // 如果是对象错误（如字段校验），转成字符串显示
    message.value = typeof errorData === 'object' ? JSON.stringify(errorData) : '注册失败'
    msgType.value = 'error'
  } finally {
    loading.value = false
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
.box-card { width: 400px; padding: 20px; }
.btn-group { display: flex; justify-content: space-around; margin-top: 30px; }
</style>